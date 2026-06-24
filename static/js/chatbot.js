import { $, $$, csrfToken, onReady, safeJsonParse, setToneText } from "./modules/dom.js";


const HISTORY_KEY = "ai-solution-chat-history";
const OPEN_KEY = "ai-solution-chat-open";
const ASSISTANT_NAME = "AI Solution Assistant";
const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");


function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}


function applyInlineMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  return html;
}


function renderMarkdownish(text) {
  const lines = String(text || "").replace(/\r/g, "").split("\n");
  const chunks = [];
  let listType = "";

  const closeList = () => {
    if (!listType) return;
    chunks.push(listType === "ol" ? "</ol>" : "</ul>");
    listType = "";
  };

  const openList = (nextType) => {
    if (listType === nextType) return;
    closeList();
    chunks.push(nextType === "ol" ? "<ol>" : "<ul>");
    listType = nextType;
  };

  lines.forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      return;
    }
    if (line.startsWith("## ")) {
      closeList();
      chunks.push(`<h4>${applyInlineMarkdown(line.slice(3))}</h4>`);
      return;
    }
    if (line.startsWith("- ")) {
      openList("ul");
      chunks.push(`<li>${applyInlineMarkdown(line.slice(2))}</li>`);
      return;
    }
    if (/^\d+\.\s/.test(line)) {
      openList("ol");
      chunks.push(`<li>${applyInlineMarkdown(line.replace(/^\d+\.\s/, ""))}</li>`);
      return;
    }
    closeList();
    chunks.push(`<p>${applyInlineMarkdown(line)}</p>`);
  });

  closeList();
  return chunks.join("");
}


function saveHistory(history) {
  window.sessionStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(-12)));
}


function loadHistory() {
  return safeJsonParse(window.sessionStorage.getItem(HISTORY_KEY) || "[]", []);
}


function setOpenState(open) {
  window.sessionStorage.setItem(OPEN_KEY, open ? "true" : "false");
}


function wasOpen() {
  return window.sessionStorage.getItem(OPEN_KEY) === "true";
}


function timestamp() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}


function scrollMessages(container) {
  container.scrollTo({ top: container.scrollHeight, behavior: reducedMotionQuery.matches ? "auto" : "smooth" });
}


function resizeComposer(input) {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
}


function setStatus(text, tone = "neutral") {
  setToneText($("[data-chatbot-status]"), text, tone);
}


function appendMessage(container, text, type, { typing = false } = {}) {
  const row = document.createElement("div");
  row.className = `message-row message-row--${type}`;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.innerHTML = `
    <span class="message-avatar ${type === "user" ? "message-avatar--user" : ""}">${type === "user" ? "You" : "AI"}</span>
    <span class="message-author">${type === "user" ? "You" : ASSISTANT_NAME}</span>
    <span class="message-time">${timestamp()}</span>
  `;

  const bubble = document.createElement("div");
  bubble.className = type === "user" ? "user-bubble" : "bot-bubble";

  if (typing) {
    bubble.classList.add("typing");
    bubble.innerHTML =
      `<span class="typing-label">${ASSISTANT_NAME} is preparing a response</span><span class="typing-dots"><span></span><span></span><span></span></span>`;
  } else if (type === "assistant") {
    bubble.innerHTML = renderMarkdownish(text);
  } else {
    bubble.textContent = text;
  }

  row.append(meta, bubble);
  container.appendChild(row);
  scrollMessages(container);
  return row;
}


function wait(duration) {
  return new Promise((resolve) => window.setTimeout(resolve, duration));
}


async function typeAssistantMessage(container, text) {
  const row = appendMessage(container, "", "assistant");
  const bubble = $(".bot-bubble", row);
  if (!bubble) return row;

  if (reducedMotionQuery.matches || text.length < 10) {
    bubble.innerHTML = renderMarkdownish(text);
    scrollMessages(container);
    return row;
  }

  const step = Math.max(1, Math.ceil(text.length / 90));
  for (let index = step; index <= text.length; index += step) {
    bubble.innerHTML = renderMarkdownish(text.slice(0, index));
    scrollMessages(container);
    await wait(10);
  }
  bubble.innerHTML = renderMarkdownish(text);
  scrollMessages(container);
  return row;
}


function renderHistory(container, history, welcomeMessage) {
  container.innerHTML = "";
  const items = history.length ? history : [{ role: "assistant", text: welcomeMessage }];
  items.forEach((item) => appendMessage(container, item.text, item.role === "user" ? "user" : "assistant"));
}


async function fetchBackendHistory() {
  try {
    const response = await window.fetch("/api/chat/history");
    if (!response.ok) return [];
    const data = await response.json();
    return Array.isArray(data.history) ? data.history : [];
  } catch (error) {
    return [];
  }
}


async function parseJsonSafely(response) {
  try {
    return await response.json();
  } catch (error) {
    return {};
  }
}


async function postChatMessage(message, signal) {
  const options = {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
    },
    body: JSON.stringify({ message }),
    signal,
  };

  let lastError = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await window.fetch("/api/chat", options);
      if (response.status >= 500 && attempt === 0) {
        await wait(350);
        continue;
      }
      return response;
    } catch (error) {
      lastError = error;
      if (error?.name === "AbortError" || attempt > 0) break;
      await wait(350);
    }
  }
  throw lastError || new Error("Chat request failed");
}


function applyProviderStatus(response, data = {}) {
  const provider = String(data.provider || "").toLowerCase();
  if (data.deduplicated) {
    setStatus("Duplicate request absorbed and the previous reply was restored.", "warning");
    return;
  }
  if (response.status === 429 || provider.includes("rate-limit")) {
    setStatus("Please wait a moment before sending another message.", "warning");
    return;
  }
  if (provider === "gemini") {
    setStatus("Live AI response delivered securely.", "success");
    return;
  }
  if (provider.includes("invalid-key")) {
    setStatus("Live AI credentials need attention. Smart fallback guidance is active.", "warning");
    return;
  }
  if (provider.includes("no-key")) {
    setStatus("Live AI is not configured yet. Smart fallback guidance is active.", "warning");
    return;
  }
  if (provider.includes("network") || provider.includes("timeout")) {
    setStatus("Live AI is temporarily unavailable. Smart fallback guidance is active.", "warning");
    return;
  }
  if (!response.ok) {
    setStatus("The assistant responded with a temporary service issue.", "warning");
    return;
  }
  setStatus("Fallback guidance delivered while live AI is unavailable.", "warning");
}


async function animateWelcome(container, welcomeMessage) {
  container.innerHTML = "";
  const typingRow = appendMessage(container, "", "assistant", { typing: true });
  await wait(reducedMotionQuery.matches ? 60 : 320);
  typingRow.remove();
  await typeAssistantMessage(container, welcomeMessage);
}


onReady(async () => {
  const chatbot = $("[data-chatbot]");
  const form = $("[data-chatbot-form]");
  const messages = $("[data-chatbot-messages]");
  if (!chatbot || !form || !messages) return;
  const input = $("textarea[name='message']", form);
  if (!input) return;

  const welcomeMessage =
    messages.dataset.welcome || "Welcome to AI SOLUTION. Share your industry, workflow, or goal and I will guide you to the best next step.";
  let history = await fetchBackendHistory();
  let pending = false;

  if (!history.length) {
    history = loadHistory();
  }

  if (history.length) {
    renderHistory(messages, history, welcomeMessage);
  } else {
    await animateWelcome(messages, welcomeMessage);
    history = [{ role: "assistant", text: welcomeMessage }];
    saveHistory(history);
  }
  setStatus(history.length > 1 ? "Secure conversation restored for this session." : "Ready to help with services, events, and delivery planning.");
  resizeComposer(input);

  const launchButtons = $$("[data-open-chatbot]");
  const syncOpenState = (open) => {
    chatbot.classList.toggle("open", open);
    chatbot.dataset.state = open ? "open" : "closed";
    $("[data-chatbot-panel]")?.setAttribute("aria-hidden", String(!open));
    launchButtons.forEach((button) => button.setAttribute("aria-expanded", String(open)));
  };

  const open = () => {
    syncOpenState(true);
    setOpenState(true);
    input.focus();
  };

  const close = () => {
    syncOpenState(false);
    setOpenState(false);
  };

  const toggle = () => {
    if (chatbot.classList.contains("open")) {
      close();
      return;
    }
    open();
  };

  if (wasOpen()) {
    open();
  }

  launchButtons.forEach((button) => {
    button.addEventListener("click", toggle);
  });

  $("[data-collapse-chatbot]")?.addEventListener("click", close);
  $("[data-close-chatbot]")?.addEventListener("click", close);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && chatbot.classList.contains("open")) {
      close();
    }
  });

  $("[data-clear-chatbot]")?.addEventListener("click", async () => {
    history = [];
    saveHistory(history);
    renderHistory(messages, history, welcomeMessage);
    input.value = "";
    resizeComposer(input);
    input.focus();
    setStatus("Conversation cleared. Ready for a new question.");
    try {
      await window.fetch("/api/chat/clear", {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken(),
        },
      });
    } catch (error) {
      // Keep local state even if the backend clear fails.
    }
  });

  input.addEventListener("input", () => resizeComposer(input));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message || pending) return;

    open();
    pending = true;
    appendMessage(messages, message, "user");
    history.push({ role: "user", text: message });
    saveHistory(history);
    input.value = "";
    resizeComposer(input);
    input.disabled = true;
    form.dataset.busy = "true";
    messages.setAttribute("aria-busy", "true");
    const submitButton = $("button[type='submit']", form);
    if (submitButton) submitButton.disabled = true;
    setStatus("Thinking through your request...", "progress");
    const typingRow = appendMessage(messages, "", "assistant", { typing: true });
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 22000);

    try {
      const response = await postChatMessage(message, controller.signal);
      const data = await parseJsonSafely(response);
      typingRow.remove();
      const reply = data.reply || data.error || "I could not respond right now.";
      await typeAssistantMessage(messages, reply);
      if (Array.isArray(data.history) && data.history.length) {
        history = data.history;
      } else {
        history.push({ role: "assistant", text: reply });
      }
      saveHistory(history);
      applyProviderStatus(response, data);
    } catch (error) {
      typingRow.remove();
      const reply =
        error?.name === "AbortError"
          ? "The assistant is taking longer than expected. Please try again in a moment."
          : "The assistant is temporarily unavailable. Please use the Contact Us page for urgent requests.";
      await typeAssistantMessage(messages, reply);
      history.push({ role: "assistant", text: reply });
      saveHistory(history);
      setStatus(
        error?.name === "AbortError"
          ? "Response timeout detected. You can retry immediately."
          : "Connection issue detected. Fallback guidance shown.",
        "warning"
      );
    } finally {
      window.clearTimeout(timeoutId);
      pending = false;
      input.disabled = false;
      form.dataset.busy = "false";
      messages.setAttribute("aria-busy", "false");
      if (submitButton) submitButton.disabled = false;
      input.focus();
    }
  });
});
