// ==========================================================================
// OOGWAY LABS — LENNY GROWTH INTELLIGENCE FRONTEND LOGIC (v1.2)
// Enhanced Executive Experience: RAG Exploration, Toast Feedback & Ship 30
// ==========================================================================

let currentSessionId = null;
let currentProvider = "groq"; // Default to high-speed cloud inference
let activeArtifactData = null;

// DOM Elements
const sidebar = document.getElementById("sidebar");
const sessionListEl = document.getElementById("session-list");
const sessionCountTag = document.getElementById("session-count-tag");
const btnNewChat = document.getElementById("btn-new-chat");
const providerSelect = document.getElementById("provider-select");
const providerPulse = document.getElementById("provider-pulse");
const providerHint = document.getElementById("provider-hint");
const providerStatusBadge = document.getElementById("provider-status-badge");
const dbStatLabel = document.getElementById("db-stat-label");
const dbStatShort = document.getElementById("db-stat-short");
const activeProviderPill = document.getElementById("active-provider-pill");

const activeSessionTitle = document.getElementById("active-session-title");
const welcomeScreen = document.getElementById("welcome-screen");
const messageFeed = document.getElementById("message-feed");
const messagesArea = document.getElementById("messages-area");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const btnSend = document.getElementById("btn-send");
const btnClearChat = document.getElementById("btn-clear-chat");

const errorBanner = document.getElementById("error-banner");
const errorTitle = document.getElementById("error-title");
const errorDesc = document.getElementById("error-desc");
const errorTip = document.getElementById("error-tip");
const btnDismissError = document.getElementById("btn-dismiss-error");

const toggleArtifactBtn = document.getElementById("toggle-artifact-btn");
const artifactPanel = document.getElementById("artifact-panel");
const artifactTitle = document.getElementById("artifact-title");
const artifactWordCount = document.getElementById("artifact-word-count");
const readingTimePill = document.getElementById("reading-time-pill");
const artifactProviderPill = document.getElementById("artifact-provider-pill");
const sandboxIframe = document.getElementById("sandbox-iframe");
const rawMarkdownView = document.getElementById("raw-markdown-view");
const tabBtnVisual = document.getElementById("tab-btn-visual");
const tabBtnRaw = document.getElementById("tab-btn-raw");
const btnCopyMarkdown = document.getElementById("btn-copy-markdown");
const btnDownloadHtml = document.getElementById("btn-download-html");
const btnCloseArtifact = document.getElementById("btn-close-artifact");
const toastContainer = document.getElementById("toast-container");

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  initHealthCheck();
  loadSessions();
  setupEventListeners();
  setupCategoryTabs();
  setupGuestChips();
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

  // Global keyboard shortcuts (Cmd/Ctrl + N for new session)
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "n") {
      e.preventDefault();
      startNewChat();
      showToast("Started new session", "✨");
    }
  });

  // Auto-resize textarea
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 140) + "px";
  });

  // New Chat button
  btnNewChat.addEventListener("click", () => {
    startNewChat();
  });

  // Clear Chat button
  if (btnClearChat) {
    btnClearChat.addEventListener("click", () => {
      startNewChat();
      showToast("Conversation cleared", "🧹");
    });
  }

  // Provider selector change
  providerSelect.addEventListener("change", (e) => {
    currentProvider = e.target.value;
    updateProviderHint();
    showToast(`Switched inference to ${providerSelect.options[providerSelect.selectedIndex].text.split('(')[0].trim()}`, "⚡");
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

  // Copy Markdown
  btnCopyMarkdown.addEventListener("click", () => {
    if (activeArtifactData && activeArtifactData.essay_markdown) {
      navigator.clipboard.writeText(activeArtifactData.essay_markdown);
      showToast("Atomic essay markdown copied!", "📋");
    }
  });

  // Download Standalone HTML
  if (btnDownloadHtml) {
    btnDownloadHtml.addEventListener("click", () => {
      if (activeArtifactData && activeArtifactData.essay_html) {
        const blob = new Blob([activeArtifactData.essay_html], { type: "text/html" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const slug = (activeArtifactData.title || "ship30-essay")
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .slice(0, 40);
        a.download = `${slug}.html`;
        a.click();
        URL.revokeObjectURL(url);
        showToast("HTML essay exported successfully!", "💾");
      }
    });
  }
}

// --- Prompt Category Filtering ---
function setupCategoryTabs() {
  const tabs = document.querySelectorAll(".cat-tab");
  const cards = document.querySelectorAll(".prompt-card");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      const cat = tab.getAttribute("data-cat");
      cards.forEach((card) => {
        const cardCat = card.getAttribute("data-category");
        if (cat === "all" || cardCat === cat) {
          card.style.display = "flex";
        } else {
          card.style.display = "none";
        }
      });
    });
  });
}

// --- Guest Chips Filtering & Quick Queries ---
function setupGuestChips() {
  const chips = document.querySelectorAll(".guest-chip");
  const guestQueries = {
    "Elena Verna": "What did Elena Verna say about B2B growth tactics that never work?",
    "Marty Cagan": "What did Marty Cagan say about product discovery and empowered product managers?",
    "Brian Balfour": "How does Brian Balfour explain the Four Fits framework for sustainable growth?",
    "Shreyas Doshi": "What is Shreyas Doshi's LNO framework for PM time and task prioritization?",
    "Casey Winters": "How does Casey Winters think about retention loops vs top-of-funnel acquisition?",
    "Annie Duke": "What does Annie Duke teach about decision quality vs outcome bias?",
    "Sean Ellis": "How does Sean Ellis define North Star metrics and growth experimentation?",
    "Brian Chesky": "What did Brian Chesky explain about founder-mode product leadership at Airbnb?",
    "April Dunford": "How does April Dunford describe product positioning and competitive alternatives?"
  };

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");

      const guest = chip.getAttribute("data-guest");
      if (guest === "all") {
        document.querySelectorAll(".prompt-card").forEach((c) => c.style.display = "flex");
      } else if (guestQueries[guest]) {
        messageInput.value = guestQueries[guest];
        messageInput.focus();
        showToast(`Loaded query for ${guest}`, "🎙️");
      }
    });
  });
}

// --- Health Check & Provider Status ---
async function initHealthCheck() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    if (dbStatLabel) {
      dbStatLabel.textContent = `Vector Store Connected · ${data.database_backend}`;
    }
    if (dbStatShort) {
      dbStatShort.textContent = data.database_backend;
    }

    // Auto-select preferred active provider
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
    if (dbStatLabel) dbStatLabel.textContent = "DB: Offline";
    if (providerPulse) providerPulse.className = "pulse-indicator error";
    if (providerStatusBadge) {
      providerStatusBadge.textContent = "Offline";
      providerStatusBadge.style.color = "#f43f5e";
    }
  }
}

function updateProviderHint() {
  if (currentProvider === "groq") {
    providerHint.textContent = "⚡ Groq Cloud LPU (compound-mini · Ultra-fast ~1.2s inference)";
    if (providerPulse) providerPulse.className = "pulse-indicator";
    if (providerStatusBadge) {
      providerStatusBadge.textContent = "Cloud Active";
      providerStatusBadge.style.color = "#34d399";
    }
    if (activeProviderPill) activeProviderPill.textContent = "⚡ Groq Cloud LPU";
  } else if (currentProvider === "mock") {
    providerHint.textContent = "🛡️ Deterministic extractive synthesis directly from transcripts (zero external keys)";
    if (providerPulse) providerPulse.className = "pulse-indicator";
    if (providerStatusBadge) {
      providerStatusBadge.textContent = "Local Extractive";
      providerStatusBadge.style.color = "#38bdf8";
    }
    if (activeProviderPill) activeProviderPill.textContent = "🛡️ Extractive RAG";
  } else if (currentProvider === "ollama") {
    providerHint.textContent = "💻 Local laptop Ollama inference (llama3.1:8b)";
    if (providerPulse) providerPulse.className = "pulse-indicator";
    if (providerStatusBadge) {
      providerStatusBadge.textContent = "Local Ollama";
      providerStatusBadge.style.color = "#818cf8";
    }
    if (activeProviderPill) activeProviderPill.textContent = "💻 Local Ollama";
  } else if (currentProvider === "openai") {
    providerHint.textContent = "🌐 OpenAI Cloud API (gpt-4o-mini)";
    if (providerPulse) providerPulse.className = "pulse-indicator";
    if (providerStatusBadge) {
      providerStatusBadge.textContent = "OpenAI Active";
      providerStatusBadge.style.color = "#10b981";
    }
    if (activeProviderPill) activeProviderPill.textContent = "🌐 OpenAI Cloud";
  } else if (currentProvider === "anthropic") {
    providerHint.textContent = "🧠 Anthropic Cloud API (Claude 3.5 Sonnet)";
    if (providerPulse) providerPulse.className = "pulse-indicator";
    if (providerStatusBadge) {
      providerStatusBadge.textContent = "Claude Active";
      providerStatusBadge.style.color = "#a855f7";
    }
    if (activeProviderPill) activeProviderPill.textContent = "🧠 Anthropic Cloud";
  }
}

// --- Session Management ---
async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    if (!res.ok) return;
    const sessions = await res.json();

    if (sessionCountTag) {
      sessionCountTag.textContent = sessions.length;
    }

    sessionListEl.innerHTML = "";
    if (sessions.length === 0) {
      sessionListEl.innerHTML = `
        <div class="session-empty">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          <span>No conversations yet</span>
        </div>
      `;
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
  activeSessionTitle.textContent = "Executive Growth Advisor";
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
    showToast("Session deleted", "🗑️");
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

  // Append neural loading indicator bubble
  const loadingBubble = appendNeuralLoadingBubble();
  scrollToBottom();

  const startTime = Date.now();

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
        title: detail.error || "Inference Request Failed",
        message: detail.detail || `Server returned error HTTP ${res.status}`,
        troubleshooting: detail.troubleshooting || "Check provider settings or switch to 'Mock' in the sidebar."
      };
    }

    const data = await res.json();
    currentSessionId = data.session_id;

    const durationSec = ((Date.now() - startTime) / 1000).toFixed(1);
    const providerWithDuration = `${data.provider_used} · ${durationSec}s`;

    // Append assistant response
    appendMessageToUI("assistant", data.answer, data.sources, providerWithDuration, data.message_id);

    // Refresh session sidebar list
    loadSessions();
  } catch (err) {
    loadingBubble.remove();
    showError(
      err.title || "Provider / Inference Error",
      err.message || String(err),
      err.troubleshooting || "Switch provider to 'Mock' in the sidebar dropdown to run with zero dependencies."
    );
  } finally {
    btnSend.disabled = false;
    scrollToBottom();
  }
}

// --- Neural Loading Animation ---
function appendNeuralLoadingBubble() {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.innerHTML = `
    <div class="message-avatar">🎙️</div>
    <div class="message-body-wrapper">
      <div class="neural-loading-box">
        <div class="neural-status-step">
          <div class="neural-wave-dots">
            <span class="neural-dot"></span>
            <span class="neural-dot"></span>
            <span class="neural-dot"></span>
          </div>
          <span>Retrieving 573 vector chunks & synthesizing with ${currentProvider.toUpperCase()}...</span>
        </div>
      </div>
    </div>
  `;
  messageFeed.appendChild(row);
  return row;
}

// --- Message Rendering ---
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

  const avatar = role === "user" 
    ? `<div class="message-avatar">U</div>` 
    : `<div class="message-avatar">🎙️</div>`;

  let html = `
    ${avatar}
    <div class="message-body-wrapper">
      <div class="message-bubble">${renderedContent}</div>
  `;

  // Assistant additions: citations & action toolbar
  if (role === "assistant") {
    let sourcesHtml = "";
    if (sources && sources.length > 0) {
      const itemsHtml = sources
        .map((s) => {
          const ytUrl = s.youtube_url || "#";
          const matchPercent = s.relevance_score ? Math.round(s.relevance_score * 100) : 92;
          const quoteSnippet = s.quote_text ? escapeHtml(s.quote_text.slice(0, 95)) + "..." : "";

          return `
            <div class="source-pill-item">
              <div class="source-pill-meta">
                <div class="source-guest-row">
                  <span class="source-guest">${escapeHtml(s.speaker)}</span>
                  <span class="source-score-pill">${matchPercent}% match</span>
                </div>
                <span class="source-ep">${escapeHtml(s.episode_title)}</span>
                ${quoteSnippet ? `<span class="source-quote-preview">"${quoteSnippet}"</span>` : ""}
              </div>
              <a href="${escapeHtml(ytUrl)}" target="_blank" rel="noopener noreferrer" class="source-ts-link" title="Play on YouTube at exact timestamp">
                ▶ ${escapeHtml(s.timestamp_range)}
              </a>
            </div>
          `;
        })
        .join("");

      sourcesHtml = `
        <div class="citations-box">
          <div class="citations-header">
            <span class="citations-title">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
              Verified Podcast Sources (${sources.length})
            </span>
          </div>
          <div class="source-pill-list">
            ${itemsHtml}
          </div>
        </div>
      `;
    }

    const providerBadge = providerUsed ? `<span class="provider-stamp">⚡ ${escapeHtml(providerUsed)}</span>` : "";

    html += `
        ${sourcesHtml}
        <div class="message-actions-bar">
          <button class="btn-action btn-copy-answer" title="Copy answer markdown">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            <span>Copy</span>
          </button>
          <button class="btn-ship30" data-msg-id="${messageId || ''}" title="Transform this answer into an executive Ship 30 for 30 atomic essay">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
            <span>Ship 30 for 30 Essay</span>
          </button>
          ${providerBadge}
        </div>
      </div>
    `;
  } else {
    html += `</div>`;
  }

  row.innerHTML = html;

  // Event handlers
  const copyBtn = row.querySelector(".btn-copy-answer");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(content);
      showToast("Answer copied to clipboard!", "📋");
    });
  }

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
  if (readingTimePill) readingTimePill.textContent = "Calculating...";
  if (artifactProviderPill) artifactProviderPill.textContent = `Via ${currentProvider}`;

  sandboxIframe.srcdoc = `
    <!DOCTYPE html>
    <html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display:flex; flex-direction:column; align-items:center; justify-content:center; height:80vh; color:#94a3b8; text-align:center;">
      <div style="font-size: 2rem; margin-bottom: 0.5rem; animation: pulse 1.5s infinite;">⚡</div>
      <h3 style="color:#ffffff; margin-bottom: 0.5rem; font-size:1.1rem;">Engineering Ship 30 for 30 Atomic Essay</h3>
      <p style="font-size:0.85rem; max-width:380px; line-height:1.5;">Applying the rigorous rubric: The Hook, 1 Core Idea, Rhythm, Bold Takeaways, and Tomorrow at 9 AM Protocol...</p>
    </body></html>
  `;
  rawMarkdownView.textContent = "Synthesizing publication-ready essay...";

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
    
    const readMinutes = Math.max(1, Math.round(data.word_count / 250));
    if (readingTimePill) readingTimePill.textContent = `📖 ~${readMinutes} min read`;
    if (artifactProviderPill) artifactProviderPill.textContent = `Via ${data.provider_used || currentProvider}`;

    // Inject styled HTML into sandboxed iframe
    sandboxIframe.srcdoc = data.essay_html;
    rawMarkdownView.textContent = data.essay_markdown;

    showToast("Atomic essay generated successfully!", "🎉");
  } catch (err) {
    showError("Ship 30 for 30 Error", err.message, "Verify that backend services are active.");
    artifactPanel.classList.remove("open");
  }
}

// --- Toast Notification Helper ---
function showToast(message, icon = "✓") {
  if (!toastContainer) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = "opacity 0.2s, transform 0.2s";
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 200);
  }, 2400);
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
