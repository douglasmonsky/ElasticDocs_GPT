import os
import streamlit as st
import openai
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# https://www.elastic.co/blog/chatgpt-elasticsearch-openai-meets-private-data
# Example search query: Show me the API call for an inference processor

load_dotenv()

# Required Environment Variables
es_cloud_id = os.getenv('ES_CLOUD_ID')
es_user = os.getenv('ES_USER')
es_pass = os.getenv('ES_PASS')

openai.api_key = os.getenv('OPENAI_API_KEY')
model = "gpt-4"


# Connect to Elastic Cloud cluster
def es_connect(cid: str, user: str, passwd: str) -> Elasticsearch:
    es = Elasticsearch(cloud_id=cid, basic_auth=(user, passwd))
    return es


# Search ElasticSearch index and return body and URL of the result
def search(query_text: str) -> tuple[str, str]:
    es = es_connect(es_cloud_id, es_user, es_pass)

    # Elasticsearch query (BM25) and kNN configuration for hybrid search
    query = {
        "bool": {
            "must": [{
                "match": {
                    "title": {
                        "query": query_text,
                        "boost": 1
                    }
                }
            }],
            "filter": [{
                "exists": {
                    "field": "elastic-docs_title-vector"
                }
            }]
        }
    }

    knn = {
        "field": "title-vector",
        "k": 1,
        "num_candidates": 20,
        "query_vector_builder": {
            "text_embedding": {
                "model_id": "sentence-transformers__all-distilroberta-v1",
                "model_text": query_text
            }
        },
        "boost": 24
    }
    print(knn)
    fields = ["title", "body_content", "url"]
    index = 'search-elastic-docs'
    resp = es.search(index=index,
                     query=query,
                     knn=knn,
                     fields=fields,
                     size=1,
                     source=False)
    print(resp)
    try:
        body = resp['hits']['hits'][0]['fields']['body_content'][0]
        url = resp['hits']['hits'][0]['fields']['url'][0]
    except IndexError:
        no_result_message = "No results found"
        body = no_result_message
        url = no_result_message

    return body, url


def truncate_text(text: str, max_tokens: int) -> str:
    tokens = text.split()
    if len(tokens) <= max_tokens:
        return text

    return ' '.join(tokens[:max_tokens])


# Generate a response from ChatGPT based on the given prompt
def chat_gpt(prompt: str, model: str = "gpt-4", max_tokens: int = 1024,
             max_context_tokens: int = 4000, safety_margin: int = 5) -> str:
    # Truncate the prompt content to fit within the model's context length
    truncated_prompt = truncate_text(prompt, max_context_tokens - max_tokens - safety_margin)

    response = openai.ChatCompletion.create(model=model,
                                            messages=[{"role": "system", "content": "You are a helpful assistant."},
                                                      {"role": "user", "content": truncated_prompt}])

    return response["choices"][0]["message"]["content"]


st.title("ElasticDocs GPT")

# Main chat form
with st.form("chat_form"):
    query = st.text_input("You: ")
    submit_button = st.form_submit_button("Send")

# Generate and display response on form submission
negResponse = "I'm unable to answer the question based on the information I have from Elastic Docs."
if submit_button:
    resp, url = search(query)
    if resp == "No results found":
        st.write(f"ChatGPT: {negResponse}")
    else:
        prompt = f"Answer this question: {query}\nUsing only the information from this Elastic Doc:" \
                 f" {resp}\nIf the answer is not contained in the supplied doc reply '{negResponse}' and nothing else"
        answer = chat_gpt(prompt)

        if negResponse in answer:
            st.write(f"ChatGPT: {answer.strip()}")
        else:
            st.write(f"ChatGPT: {answer.strip()}\n\nDocs: {url}")
