const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const messagesElement = document.querySelector("#messages");
const welcome = document.querySelector("#welcome");
const history = [];

function addMessage(role, text, extraClass = "") {
  const message = document.createElement("div");
  message.className = `message ${role}${extraClass ? ` ${extraClass}` : ""}`;
  message.textContent = text;
  messagesElement.append(message);
  messagesElement.scrollTop = messagesElement.scrollHeight;
  return message;
}

async function sendMessage(text) {
  const cleanText = text.trim();
  if (!cleanText || sendButton.disabled) return;

  welcome.hidden = true;
  addMessage("user", cleanText);
  input.value = "";
  input.style.height = "auto";
  sendButton.disabled = true;
  input.disabled = true;
  const typing = addMessage("assistant", "...", "typing");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: cleanText, history: history.slice(-12) }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "The assistant could not answer right now.");
    }

    typing.remove();
    addMessage("assistant", result.reply);
    history.push(
      { role: "user", content: cleanText },
      { role: "assistant", content: result.reply },
    );
    if (history.length > 12) history.splice(0, history.length - 12);
  } catch (error) {
    typing.remove();
    const message = error instanceof TypeError
      ? "I can't reach the chatbot server. Run run.bat and keep its server window open, then try again."
      : error.message;
    addMessage("assistant", message, "error");
  } finally {
    sendButton.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(input.value);
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 150)}px`;
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.textContent));
});

const navToggle = document.querySelector("#nav-toggle");
const navLinks = document.querySelector("#nav-links");

navToggle.addEventListener("click", () => {
  const isOpen = navToggle.getAttribute("aria-expanded") === "true";
  navToggle.setAttribute("aria-expanded", String(!isOpen));
  navToggle.setAttribute("aria-label", isOpen ? "Open navigation" : "Close navigation");
  navLinks.classList.toggle("is-open", !isOpen);
});

navLinks.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    navToggle.setAttribute("aria-expanded", "false");
    navToggle.setAttribute("aria-label", "Open navigation");
    navLinks.classList.remove("is-open");
  });
});
