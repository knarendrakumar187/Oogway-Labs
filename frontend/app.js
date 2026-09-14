// The Lenny Growth Assistant - Frontend Application Logic

let currentSessionId = null;
let currentProvider = "mock"; // Default for instant zero-setup evaluation
let activeArtifactData = null;

// DOM Elements
const sidebar = document.getElementById("sidebar");
const sessionListEl = document.getElementById("session-list");
const btnNewChat = document.getElementById("btn-new-chat");
const providerSelect = document.getElementById("provider-select");
const providerDot = document.getElementById("provider-dot");
const providerHint = document.getElementById("provider-hint");
const dbStatLabel = document.getElementById("db-stat-label");

const activeSessionTitle = document.getElementById("active-session-title");
const welcomeScreen = document.getElementById("welcome-screen");
const messageFeed = document.getElementById("message-feed");
const messagesArea = document.getElementById("messages-area");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const btnSend = document.getElementById("btn-send");

const errorBanner = document.getElementById("error-banner");
const errorTitle = document.getElementById("error-title");
const errorDesc = document.getElementById("error-desc");
const errorTip = document.getElementById("error-tip");
const btnDismissError = document.getElementById("btn-dismiss-error");

const toggleArtifactBtn = document.getElementById("toggle-artifact-btn");
const artifactPanel = document.getElementById("artifact-panel");
const artifactTitle = document.getElementById("artifact-title");
const artifactWordCount = document.getElementById("artifact-word-count");
const sandboxIframe = document.getElementById("sandbox-iframe");
const rawMarkdownView = document.getElementById("raw-markdown-view");
const tabBtnVisual = document.getElementById("tab-btn-visual");
const tabBtnRaw = document.getElementById("tab-btn-raw");
const btnCopyMarkdown = document.getElementById("btn-copy-markdown");
const btnCloseArtifact = document.getElementById("btn-close-artifact");

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  initHealthCheck();
  loadSessions();
  setupEventListeners();
});

function setupEventListeners() {
  // Chat form submit
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  // Textarea enter key submit (Shift+Enter for newline)
  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Auto-resize textarea
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + "px";
  });

  // New Chat button
  btnNewChat.addEventListener("click", () => {
    startNewChat();
  });

  // Provider selector change
  providerSelect.addEventListener("change", (e) => {
    currentProvider = e.target.value;
    updateProviderHint();
  });

  // Dismiss error banner
  btnDismissError.addEventListener("click", () => {
    errorBanner.style.display = "none";
  });

  // Starter prompt cards
  document.querySelectorAll(".prompt-card").forEach((card) => {
    card.addEventListener("click", () => {
      const prompt = card.getAttribute("data-prompt");
      if (prompt) {
        messageInput.value = prompt;
        handleSendMessage();
      }
    });
  });

  // Artifact panel tabs
  tabBtnVisual.addEventListener("click", () => {
    tabBtnVisual.classList.add("active");
    tabBtnRaw.classList.remove("active");
    sandboxIframe.style.display = "block";
    rawMarkdownView.style.display = "none";
  });

  tabBtnRaw.addEventListener("click", () => {
    tabBtnRaw.classList.add("active");
    tabBtnVisual.classList.remove("active");
    sandboxIframe.style.display = "none";
    rawMarkdownView.style.display = "block";
  });

  // Artifact panel controls
  btnCloseArtifact.addEventListener("click", () => {
    artifactPanel.classList.remove("open");
  });

  toggleArtifactBtn.addEventListener("click", () => {
    if (activeArtifactData) {
      artifactPanel.classList.toggle("open");
    }
  });

  btnCopyMarkdown.addEventListener("click", () => {
    if (activeArtifactData && activeArtifactData.essay_markdown) {
      navigator.clipboard.writeText(activeArtifactData.essay_markdown);
      btnCopyMarkdown.textContent = "✓ Copied!";
      setTimeout(() => {
        btnCopyMarkdown.textContent = "📋 Copy MD";
      }, 2000);
    }
  });
}

// --- Health Check & Provider Status ---
async function initHealthCheck() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    dbStatLabel.textContent = `DB: ${data.database_backend} | Chunks: ${data.indexed_chunks}`;

    // Populate active provider
    if (data.available_providers) {
      if (data.available_providers.groq) {
        providerSelect.value = "groq";
        currentProvider = "groq";
      } else if (data.available_providers.ollama) {
        providerSelect.value = "ollama";
        currentProvider = "ollama";
      } else {
        providerSelect.value = "mock";
        currentProvider = "mock";
      }
      updateProviderHint();
    }
  } catch (err) {
    console.warn("Could not reach /api/health:", err);
    dbStatLabel.textContent = "DB: Offline";
    providerDot.className = "status-dot error";
  }
}

function updateProviderHint() {
  if (currentProvider === "mock") {
    providerHint.textContent = "Deterministic extractive synthesis (zero dependencies)";
    providerDot.className = "status-dot";
  } else if (currentProvider === "ollama") {
    providerHint.textContent = "Local laptop Ollama inference (llama3.1:8b)";
    providerDot.className = "status-dot";
  } else if (currentProvider === "openai") {
    providerHint.textContent = "OpenAI Cloud API (gpt-4o-mini)";
    providerDot.className = "status-dot";
  } else if (currentProvider === "anthropic") {
    providerHint.textContent = "Anthropic Cloud API (Claude 3.5 Sonnet)";
    providerDot.className = "status-dot";
  } else if (currentProvider === "groq") {
    providerHint.textContent = "⚡ Groq Cloud API (llama3-8b-8192 · Ultra-fast free tier)";
    providerDot.className = "status-dot active";
  }
}

// --- Session Management ---
async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    if (!res.ok) return;
    const sessions = await res.json();

    sessionListEl.innerHTML = "";
    if (sessions.length === 0) {
      sessionListEl.innerHTML = '<div class="session-empty">No conversations yet</div>';
      return;
    }

    sessions.forEach((s) => {
      const item = document.createElement("div");
      item.className = `session-item ${s.id === currentSessionId ? "active" : ""}`;
      item.innerHTML = `
        <div class="session-item-title" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</div>
        <button class="session-item-delete" title="Delete conversation">&times;</button>
      `;

      item.querySelector(".session-item-title").addEventListener("click", () => {
        selectSession(s.id);
      });

      item.querySelector(".session-item-delete").addEventListener("click", (e) => {
        e.stopPropagation();
        deleteSession(s.id);
      });

      sessionListEl.appendChild(item);
    });
  } catch (err) {
    console.error("Error loading sessions:", err);
  }
}

function startNewChat() {
  currentSessionId = null;
  activeSessionTitle.textContent = "New Conversation";
  welcomeScreen.style.display = "block";
  messageFeed.innerHTML = "";
  errorBanner.style.display = "none";
  loadSessions();
  messageInput.focus();
}

async function selectSession(sessionId) {
  currentSessionId = sessionId;
  welcomeScreen.style.display = "none";
  messageFeed.innerHTML = "";
  errorBanner.style.display = "none";

  try {
    const res = await fetch(`/api/sessions/${sessionId}`);
    if (!res.ok) throw new Error("Could not load session history");
    const detail = await res.json();

    activeSessionTitle.textContent = detail.title || "Conversation";

    detail.messages.forEach((msg) => {
      appendMessageToUI(msg.role, msg.content, msg.sources_cited, msg.provider_used, msg.id);
    });

    loadSessions();
    scrollToBottom();
  } catch (err) {
    showError("Session Load Error", err.message, "Try creating a new chat session.");
  }
}

async function deleteSession(sessionId) {
  if (!confirm("Are you sure you want to delete this conversation?")) return;
  try {
    await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
    if (currentSessionId === sessionId) {
      startNewChat();
    } else {
      loadSessions();
    }
  } catch (err) {
    console.error("Error deleting session:", err);
  }
}

// --- Chat Sending & Message Handling ---
async function handleSendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  welcomeScreen.style.display = "none";
  errorBanner.style.display = "none";

  // Append user bubble
  appendMessageToUI("user", text);
  messageInput.value = "";
  messageInput.style.height = "auto";
  btnSend.disabled = true;

  // Append loading indicator bubble
  const loadingBubble = appendLoadingBubble();
  scrollToBottom();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        message: text,
        provider: currentProvider
      })
    });

    loadingBubble.remove();

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      const detail = errJson.detail || {};
      throw {
        title: detail.error || "Request Failed",
        message: detail.detail || `Server returned error HTTP ${res.status}`,
        troubleshooting: detail.troubleshooting || "Check backend console logs."
      };
    }

    const data = await res.json();
    currentSessionId = data.session_id;

    // Append assistant response
    appendMessageToUI("assistant", data.answer, data.sources, data.provider_used, data.message_id);

    // Refresh session sidebar list
    loadSessions();
  } catch (err) {
    loadingBubble.remove();
    showError(
      err.title || "Provider / Chat Error",
      err.message || String(err),
      err.troubleshooting || "Switch provider to 'Mock' in the sidebar dropdown to run without external dependencies."
    );
  } finally {
    btnSend.disabled = false;
    scrollToBottom();
  }
}

function appendLoadingBubble() {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.innerHTML = `
    <div class="message-bubble" style="color: #64748b; font-style: italic;">
      Searching Lenny's Podcast transcripts & synthesizing grounded insights...
    </div>
  `;
  messageFeed.appendChild(row);
  return row;
}

function appendMessageToUI(role, content, sources = [], providerUsed = "", messageId = null) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  // Markdown parsing with fallback
  let renderedContent = content;
  if (window.marked) {
    try {
      renderedContent = marked.parse(content);
    } catch (e) {
      renderedContent = escapeHtml(content);
    }
  } else {
    renderedContent = escapeHtml(content);
  }

  let html = `<div class="message-bubble">${renderedContent}</div>`;

  // If assistant message, render metadata and sources
  if (role === "assistant") {
    let sourcesHtml = "";
    if (sources && sources.length > 0) {
      const itemsHtml = sources
        .map((s) => {
          const ytUrl = s.youtube_url || "#";
          return `
            <div class="source-pill-item">
              <div class="source-pill-meta">
                <span class="source-guest">${escapeHtml(s.speaker)}</span>
                <span class="source-ep">${escapeHtml(s.episode_title)}</span>
              </div>
              <a href="${escapeHtml(ytUrl)}" target="_blank" rel="noopener noreferrer" class="source-ts-link" title="Open podcast at exact timestamp on YouTube">
                ▶ ${escapeHtml(s.timestamp_range)}
              </a>
            </div>
          `;
        })
        .join("");

      sourcesHtml = `
        <div class="citations-box">
          <div class="citations-header">
            <span>Verified Sources (${sources.length})</span>
          </div>
          <div class="source-pill-list">
            ${itemsHtml}
          </div>
        </div>
      `;
    }

    const providerBadge = providerUsed ? `<span>Via: ${escapeHtml(providerUsed)}</span>` : "";
    
    html += `
      ${sourcesHtml}
      <div class="message-meta">
        ${providerBadge}
        <button class="btn-ship30" data-msg-id="${messageId || ''}" title="Transform this grounded answer into a Ship 30 for 30 atomic essay">
          ⚡ Ship 30 for 30
        </button>
      </div>
    `;
  }

  row.innerHTML = html;

  // Attach Ship 30 button handler
  const shipBtn = row.querySelector(".btn-ship30");
  if (shipBtn) {
    shipBtn.addEventListener("click", () => {
      triggerShip30Skill(messageId, content, sources);
    });
  }

  messageFeed.appendChild(row);
  scrollToBottom();
}

// --- Ship 30 for 30 Skill Trigger ---
async function triggerShip30Skill(messageId, groundedAnswer, sources) {
  // Open artifact panel in loading state
  artifactPanel.classList.add("open");
  toggleArtifactBtn.style.display = "inline-flex";
  artifactTitle.textContent = "Synthesizing Ship 30 for 30 Essay...";
  artifactWordCount.textContent = "Writing...";

  sandboxIframe.srcdoc = `
    <html><body style="font-family: sans-serif; display:flex; align-items:center; justify-content:center; height:80vh; color:#64748b;">
      <p>Applying Ship 30 for 30 Rubric (Hook, Rhythm, 1 Core Idea, Actionable Takeaway)...</p>
    </body></html>
  `;
  rawMarkdownView.textContent = "Synthesizing essay...";

  try {
    const res = await fetch("/api/chat/ship30", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        message_id: messageId,
        grounded_answer: groundedAnswer,
        provider: currentProvider
      })
    });

    if (!res.ok) {
      throw new Error("Ship 30 for 30 transformation failed");
    }

    const data = await res.json();
    activeArtifactData = data;

    artifactTitle.textContent = data.title;
    artifactWordCount.textContent = `${data.word_count} words`;

    // Securely inject HTML into sandboxed iframe (no scripts permitted)
    sandboxIframe.srcdoc = data.essay_html;
    rawMarkdownView.textContent = data.essay_markdown;

  } catch (err) {
    showError("Ship 30 for 30 Error", err.message, "Verify that backend services are active.");
    artifactPanel.classList.remove("open");
  }
}

// --- Helpers ---
function scrollToBottom() {
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

function showError(title, message, tip = "") {
  errorTitle.textContent = title;
  errorDesc.textContent = message;
  errorTip.textContent = tip ? `Tip: ${tip}` : "";
  errorBanner.style.display = "flex";
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
