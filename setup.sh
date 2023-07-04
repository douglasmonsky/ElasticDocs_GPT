mkdir -p ~/.streamlit/

port_variable=$PORT

printf "\
[server]\n\
headless = true\n\
enableCORS=false\n\
port = %s\n\
" "$port_variable" > ~/.streamlit/config.toml
