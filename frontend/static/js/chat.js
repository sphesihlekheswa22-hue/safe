/* SafeRoute Safety Assistant — floating chat widget */
(function () {
  "use strict";

  const PUBLIC_PAGES = ["/", "/login"];
  if (PUBLIC_PAGES.includes(location.pathname)) return;

  const panel = document.getElementById("sr-chat-panel");
  const toggle = document.getElementById("sr-chat-toggle");
  const closeBtn = document.getElementById("sr-chat-close");
  const form = document.getElementById("sr-chat-form");
  const input = document.getElementById("sr-chat-input");
  const messages = document.getElementById("sr-chat-messages");
  const suggestionsEl = document.getElementById("sr-chat-suggestions");

  if (!panel || !toggle) return;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function formatReply(text) {
    return esc(text)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }

  function appendMessage(role, html, extra) {
    const wrap = document.createElement("div");
    wrap.className = role === "user" ? "sr-chat-msg sr-chat-msg-user" : "sr-chat-msg sr-chat-msg-bot";
    wrap.innerHTML = `<div class="sr-chat-bubble">${html}${extra || ""}</div>`;
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
  }

  function setSuggestions(list) {
    suggestionsEl.innerHTML = "";
    if (!list || !list.length) return;
    list.forEach((s) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "sr-chat-chip";
      btn.textContent = s;
      btn.addEventListener("click", () => {
        input.value = s;
        form.requestSubmit();
      });
      suggestionsEl.appendChild(btn);
    });
  }

  function showTyping() {
    const el = document.createElement("div");
    el.id = "sr-chat-typing";
    el.className = "sr-chat-msg sr-chat-msg-bot";
    el.innerHTML = '<div class="sr-chat-bubble sr-chat-typing"><span></span><span></span><span></span></div>';
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    document.getElementById("sr-chat-typing")?.remove();
  }

  function openChat() {
    panel.classList.remove("hidden");
    toggle.classList.add("sr-chat-toggle-open");
    input.focus();
  }

  function closeChat() {
    panel.classList.add("hidden");
    toggle.classList.remove("sr-chat-toggle-open");
  }

  toggle.addEventListener("click", () => {
    panel.classList.contains("hidden") ? openChat() : closeChat();
  });
  closeBtn?.addEventListener("click", closeChat);

  appendMessage(
    "bot",
    formatReply(
      "Hi! I'm your **SafeRoute Safety Assistant** for **Gauteng**. I use **live platform data**, **real-time web search**, and **SAST** time — ask about Soshanguve, Pretoria CBD, Hatfield, incidents, or safe routes."
    )
  );
  setSuggestions(["Is Soshanguve safe?", "Recent incidents", "Route from Pretoria Station to Hatfield", "Highest risk areas"]);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    appendMessage("user", esc(text));
    input.value = "";
    setSuggestions([]);
    showTyping();

    try {
      const data = await SR.post("/api/chat/message", { message: text });
      hideTyping();
      let extra = "";
      if (data.action && data.action.href) {
        extra = `<a href="${esc(data.action.href)}" class="sr-chat-action">${esc(data.action.label || "Learn more")} →</a>`;
      }
      appendMessage("bot", formatReply(data.reply), extra);
      setSuggestions(data.suggestions || []);
    } catch (err) {
      hideTyping();
      appendMessage("bot", esc(err.message || "Sorry, I couldn't respond right now."));
    }
  });
})();
