# Local e-commerce customer support chatbot

A complete customer-support website with Home, About, Features, Contact, and
AI Chat sections, powered by the already-installed Ollama model `llama3.2:3b`.
The chat path remains browser JavaScript → Python `server.py` → local Ollama.
The app uses Python's standard library and system fonts, so it does not need a
Python package installation or an internet connection.

## Run it

1. Make sure the Ollama app is running. You do not need to download a model.
2. Double-click `run.bat` in this folder. It starts the server if needed,
   waits until it is ready, and opens the chat in your browser.
3. Keep the chatbot server window open while chatting.
4. To stop the chatbot, press **Ctrl+C** in the server window.

The first response can take a little longer while Ollama starts the model.

## Add your store information

Edit `knowledge.md`, or add `.md`, `.txt`, and `.json` files to the `knowledge`
folder. The chatbot reads those files when it answers. Add only accurate store
policies, product information, and contact details. If store information is
missing, it will say that it does not know instead of inventing an answer. It
also answers general questions using the model's general knowledge.

## Settings

The defaults use `llama3.2:3b`, Ollama at `http://127.0.0.1:11434`, and the chat
page at `http://127.0.0.1:8000`. To change these, set `OLLAMA_MODEL`,
`OLLAMA_URL`, `CHATBOT_HOST`, or `CHATBOT_PORT` before starting `server.py`.
The chat server binds to `127.0.0.1` by default, keeping it accessible only
from this computer.
