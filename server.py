import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
MAX_REQUEST_BYTES = 64 * 1024
MAX_MESSAGE_CHARS = 4000
MAX_HISTORY_MESSAGES = 12
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def load_knowledge():
    """Load local Markdown, text, and JSON files as context for store questions."""
    files = [BASE_DIR / "knowledge.md"]
    knowledge_dir = BASE_DIR / "knowledge"
    if knowledge_dir.is_dir():
        files.extend(
            path
            for path in knowledge_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json"}
        )

    sections = []
    for path in files:
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                sections.append(f"--- {path.relative_to(BASE_DIR)} ---\n{content}")
    return "\n\n".join(sections) or "No store-specific information has been provided."


def build_system_prompt(knowledge):
    return (
        "You are a friendly, helpful customer-support chatbot. Answer both "
        "e-commerce questions and general or unrelated questions naturally. "
        "For store-specific questions, use the supplied store knowledge and do "
        "not invent policies, prices, order details, or contact information. If "
        "the knowledge does not contain the answer, say so clearly and suggest "
        "how the customer can get help. For general questions, answer using "
        "your general knowledge. Be concise, useful, and honest.\n\n"
        f"Store knowledge:\n{knowledge}"
    )


def ask_ollama(messages):
    request = Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(
            {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        logging.error("Ollama returned HTTP %s: %s", exc.code, detail)
        raise RuntimeError(f"Ollama returned HTTP {exc.code}. Is the model available?") from exc
    except (URLError, TimeoutError) as exc:
        logging.error("Could not reach Ollama at %s: %s", OLLAMA_URL, exc)
        raise RuntimeError(
            "Could not connect to Ollama. Make sure the Ollama app is running."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logging.error("Ollama returned an invalid response: %s", exc)
        raise RuntimeError("Ollama returned an invalid response.") from exc

    response_message = result.get("message")
    message = response_message.get("content") if isinstance(response_message, dict) else None
    if not isinstance(message, str) or not message.strip():
        logging.error("Ollama response did not contain message content")
        raise RuntimeError("Ollama returned an empty response. Please try again.")
    return message.strip()


class ChatbotHandler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            self.send_json(200, {"ok": True, "model": OLLAMA_MODEL})
            return

        file_entry = STATIC_FILES.get(self.path)
        if file_entry is None:
            self.send_error(404)
            return

        filename, content_type = file_entry
        content = (BASE_DIR / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Invalid Content-Length header."})
            return
        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            self.send_json(413, {"error": "Request body is empty or too large."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(400, {"error": "Request body must be valid JSON."})
            return
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "Request body must be a JSON object."})
            return

        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            self.send_json(400, {"error": "Enter a message before sending."})
            return
        if len(message) > MAX_MESSAGE_CHARS:
            self.send_json(400, {"error": "Messages must be 4,000 characters or fewer."})
            return

        history = payload.get("history", [])
        if not isinstance(history, list) or len(history) > MAX_HISTORY_MESSAGES:
            self.send_json(400, {"error": "Chat history must contain at most 12 messages."})
            return
        clean_history = []
        for item in history:
            if (
                not isinstance(item, dict)
                or item.get("role") not in {"user", "assistant"}
                or not isinstance(item.get("content"), str)
                or not item["content"].strip()
                or len(item["content"]) > MAX_MESSAGE_CHARS
            ):
                self.send_json(400, {"error": "Chat history contains an invalid message."})
                return
            clean_history.append(
                {"role": item["role"], "content": item["content"].strip()}
            )

        try:
            knowledge = load_knowledge()
            answer = ask_ollama(
                [
                    {"role": "system", "content": build_system_prompt(knowledge)},
                    *clean_history,
                    {"role": "user", "content": message.strip()},
                ]
            )
        except (OSError, RuntimeError) as exc:
            logging.error("Chat request failed: %s", exc)
            self.send_json(502, {"error": str(exc)})
            return
        self.send_json(200, {"reply": answer})

    def log_message(self, format_string, *args):
        logging.info("%s - %s", self.address_string(), format_string % args)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    host = os.environ.get("CHATBOT_HOST", "127.0.0.1")
    port = int(os.environ.get("CHATBOT_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), ChatbotHandler)
    print(f"Customer support chatbot running at http://{host}:{port}")
    print(f"Using Ollama model: {OLLAMA_MODEL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping chatbot...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
