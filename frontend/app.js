// ==========================================================================
// LENNY'S GROWTH TERMINAL — CLIENT LOGIC
// Minimalist, robust event architecture for vector search and essay generation.
// ==========================================================================

let currentSessionId = null;
let currentProvider = "groq"; // Default high-speed hardware inference
let activeArtifactData = null;

// DOM Selectors
const sidebar = document.getElementById("sidebar");
const sessionListEl = document.getElementById("session-list");
const sessionCountTag = document.getElementById("session-count-tag");
const btnNewChat = document.getElementById("btn-new-chat");
const providerSelect = document.getElementById("provider-select");
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
  setupGuestNavigation();
});

function setupEventListeners() {
  // Chat form submit
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  // Textarea enter submit (Shift+Enter for newline)
  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Global shortcut (Cmd/Ctrl + N for new session)
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "n") {
      e.preventDefault();
      startNewChat();
      showToast("Started new session", "Session reset");
    }
  });

  // Auto-resize input textarea
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + "px";
  });

  // New Chat button
  btnNewChat.addEventListener("click", () => {
    startNewChat();
  });

  // Clear Chat button
  if (btnClearChat) {
    btnClearChat.addEventListener("click", () => {
      startNewChat();
      showToast("Conversation cleared", "Clean workspace");
    });
  }

  // Provider selector change
  providerSelect.addEventListener("change", (e) => {
    currentProvider = e.target.value;
    updateProviderHint();
    showToast(`Active inference: ${providerSelect.options[providerSelect.selectedIndex].text.split('(')[0].trim()}`, "Engine updated");
  });

  // Dismiss error
  btnDismissError.addEventListener("click", () => {
    errorBanner.style.display = "none";
  });

  // Brief prompt cards click handler
  document.querySelectorAll(".brief-card, .prompt-card").forEach((card) => {
    card.addEventListener("click", () => {
      const prompt = card.getAttribute("data-prompt");
      if (prompt) {
        messageInput.value = prompt;
        handleSendMessage();
      }
    });
  });

  // Artifact tabs
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
      showToast("Essay markdown copied to clipboard", "Copied");
    }
  });

  // Download HTML Document
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
        showToast("HTML document exported", "Exported");
      }
    });
  }
}

// --- Topic Category Filtering ---
function setupCategoryTabs() {
  const tabs = document.querySelectorAll(".cat-tab");
  const cards = document.querySelectorAll(".brief-card, .prompt-card");

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

// --- Guest Navigation & Quick Queries ---
function setupGuestNavigation() {
  const items = document.querySelectorAll(".guest-nav-item, .guest-chip");
  const guestQueries = {
    "Elena Verna": "What did Elena Verna say about B2B growth tactics that never work?",
    "Marty Cagan": "What did Marty Cagan say about product discovery and empowered product managers?",
    "Brian Balfour": "What did Brian Balfour say about ChatGPT as a new growth channel?",
    "Shreyas Doshi": "What is Shreyas Doshi's LNO framework for PM time and task prioritization?",
    "Casey Winters": "How does Casey Winters think about retention loops vs top-of-funnel acquisition?",
    "Annie Duke": "What does Annie Duke teach about decision quality vs outcome bias?",
    "Sean Ellis": "How does Sean Ellis define North Star metrics and growth experimentation?",
    "Brian Chesky": "What did Brian Chesky explain about founder-mode product leadership at Airbnb?",
    "April Dunford": "How does April Dunford describe product positioning and competitive alternatives?"
  };

  items.forEach((item) => {
    item.addEventListener("click", () => {
      items.forEach((i) => i.classList.remove("active"));
      item.classList.add("active");

      const guest = item.getAttribute("data-guest");
      if (guest === "all") {
        document.querySelectorAll(".brief-card, .prompt-card").forEach((c) => c.style.display = "flex");
      } else if (guestQueries[guest]) {
        messageInput.value = guestQueries[guest];
        messageInput.focus();
        showToast(`Loaded query for ${guest}`, "Query selected");
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
      dbStatLabel.textContent = `Indexed: ${data.indexed_chunks} Chunks (${data.episodes_indexed} Episodes) · ${data.database_backend}`;
    }
    if (dbStatShort) {
      dbStatShort.textContent = data.database_backend;
    }

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
    if (dbStatLabel) dbStatLabel.textContent = "Offline";
    if (providerStatusBadge) {
      providerStatusBadge.innerHTML = '<span style="color:#f43f5e">Offline</span>';
    }
  }
}

function updateProviderHint() {
  if (currentProvider === "groq") {
    providerHint.textContent = "Hardware-accelerated cloud inference (~0.8s latency)";
    if (providerStatusBadge) {
      providerStatusBadge.innerHTML = '<span class="dot-live"></span> Active';
    }
    if (activeProviderPill) activeProviderPill.textContent = "Groq LPU";
  } else if (currentProvider === "mock") {
    providerHint.textContent = "Deterministic extractive synthesis (Zero dependencies)";
    if (providerStatusBadge) {
      providerStatusBadge.innerHTML = '<span class="dot-live" style="background:#38bdf8"></span> Verified';
    }
    if (activeProviderPill) activeProviderPill.textContent = "Local Extractive";
  } else if (currentProvider === "ollama") {
    providerHint.textContent = "Local host Ollama inference (llama3.1:8b)";
    if (providerStatusBadge) {
      providerStatusBadge.innerHTML = '<span class="dot-live" style="background:#818cf8"></span> Local';
    }
    if (activeProviderPill) activeProviderPill.textContent = "Local Ollama";
  } else if (currentProvider === "openai") {
    providerHint.textContent = "OpenAI API (gpt-4o-mini)";
    if (providerStatusBadge) {
      providerStatusBadge.innerHTML = '<span class="dot-live" style="background:#10b981"></span> Cloud';
    }
    if (activeProviderPill) activeProviderPill.textContent = "OpenAI";
  } else if (currentProvider === "anthropic") {
    providerHint.textContent = "Anthropic API (Claude 3.5 Sonnet)";
    if (providerStatusBadge) {
      providerStatusBadge.innerHTML = '<span class="dot-live" style="background:#a855f7"></span> Cloud';
    }
    if (activeProviderPill) activeProviderPill.textContent = "Anthropic";
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
      sessionListEl.innerHTML = `<div class="session-empty">No previous sessions</div>`;
      return;
    }

    sessions.forEach((s) => {
      const item = document.createElement("div");
      item.className = `session-item ${s.id === currentSessionId ? "active" : ""}`;
      item.innerHTML = `
        <div class="session-item-title" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</div>
        <button class="session-item-delete" title="Delete">&times;</button>
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
  activeSessionTitle.textContent = "New Session";
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

    activeSessionTitle.textContent = detail.title || "Session";

    detail.messages.forEach((msg) => {
      appendMessageToUI(msg.role, msg.content, msg.sources_cited, msg.provider_used, msg.id);
    });

    loadSessions();
    scrollToBottom();
  } catch (err) {
    showError("Session Load Error", err.message, "Try initiating a new session.");
  }
}

async function deleteSession(sessionId) {
  if (!confirm("Delete this conversation session?")) return;
  try {
    await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
    showToast("Session removed", "Deleted");
    if (currentSessionId === sessionId) {
      startNewChat();
    } else {
      loadSessions();
    }
  } catch (err) {
    console.error("Error deleting session:", err);
  }
}

// --- Query Processing ---
async function handleSendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  welcomeScreen.style.display = "none";
  errorBanner.style.display = "none";

  appendMessageToUI("user", text);
  messageInput.value = "";
  messageInput.style.height = "auto";
  btnSend.disabled = true;

  const loadingBubble = appendProcessingIndicator();
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
        title: detail.error || "Inference Failed",
        message: detail.detail || `HTTP error ${res.status}`,
        troubleshooting: detail.troubleshooting || "Check engine settings or switch to Local Extractive in the sidebar."
      };
    }

    const data = await res.json();
    currentSessionId = data.session_id;

    const durationSec = ((Date.now() - startTime) / 1000).toFixed(1);
    const providerWithDuration = `${data.provider_used} · ${durationSec}s`;

    appendMessageToUI("assistant", data.answer, data.sources, providerWithDuration, data.message_id);
    loadSessions();
  } catch (err) {
    loadingBubble.remove();
    showError(
      err.title || "Inference Engine Error",
      err.message || String(err),
      err.troubleshooting || "Switch inference provider in the sidebar to run offline."
    );
  } finally {
    btnSend.disabled = false;
    scrollToBottom();
  }
}

// --- Processing Indicator ---
function appendProcessingIndicator() {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.innerHTML = `
    <div class="message-avatar">LT</div>
    <div class="message-content-box">
      <div class="processing-indicator">
        <div class="processing-dots">
          <span class="dot-proc"></span>
          <span class="dot-proc"></span>
          <span class="dot-proc"></span>
        </div>
        <span>Searching 573 transcript chunks · Synthesizing with ${currentProvider.toUpperCase()}...</span>
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

  const avatarText = role === "user" ? "YOU" : "LT";

  let html = `
    <div class="message-avatar">${avatarText}</div>
    <div class="message-content-box">
      <div class="message-bubble">${renderedContent}</div>
  `;

  if (role === "assistant") {
    let sourcesHtml = "";
    if (sources && sources.length > 0) {
      const entriesHtml = sources
        .map((s) => {
          const ytUrl = s.youtube_url || "#";
          const matchPercent = s.relevance_score ? Math.round(s.relevance_score * 100) : 92;
          const quoteSnippet = s.quote_text ? escapeHtml(s.quote_text.slice(0, 100)) + "..." : "";

          return `
            <div class="citation-entry">
              <div class="citation-meta">
                <div class="citation-author-row">
                  <span class="citation-guest">${escapeHtml(s.speaker)}</span>
                  <span class="citation-score">${matchPercent}% match</span>
                </div>
                <span class="citation-episode">${escapeHtml(s.episode_title)}</span>
                ${quoteSnippet ? `<span class="citation-snippet">"${quoteSnippet}"</span>` : ""}
              </div>
              <a href="${escapeHtml(ytUrl)}" target="_blank" rel="noopener noreferrer" class="citation-play-btn" title="Open YouTube timestamp">
                ▶ ${escapeHtml(s.timestamp_range)}
              </a>
            </div>
          `;
        })
        .join("");

      sourcesHtml = `
        <div class="citations-appendix">
          <div class="citations-header-row">
            <span class="citations-label">REFERENCED PODCAST CITATIONS (${sources.length})</span>
          </div>
          <div class="citation-list">
            ${entriesHtml}
          </div>
        </div>
      `;
    }

    const providerBadge = providerUsed ? `<span class="meta-stamp">${escapeHtml(providerUsed)}</span>` : "";

    html += `
        ${sourcesHtml}
        <div class="message-toolbar">
          <button class="btn-tool-action btn-copy-answer" title="Copy response markdown">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            <span>Copy</span>
          </button>
          <button class="btn-ship30-action btn-ship30" data-msg-id="${messageId || ''}" title="Transform this response into a Ship 30 for 30 essay">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
            <span>Ship 30 Essay</span>
          </button>
          ${providerBadge}
        </div>
      </div>
    `;
  } else {
    html += `</div>`;
  }

  row.innerHTML = html;

  const copyBtn = row.querySelector(".btn-copy-answer");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(content);
      showToast("Response copied to clipboard", "Copied");
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

// --- Ship 30 for 30 Studio Trigger ---
async function triggerShip30Skill(messageId, groundedAnswer, sources) {
  artifactPanel.classList.add("open");
  toggleArtifactBtn.style.display = "inline-flex";
  artifactTitle.textContent = "Synthesizing Essay...";
  artifactWordCount.textContent = "Analyzing...";
  if (readingTimePill) readingTimePill.textContent = "Drafting...";
  if (artifactProviderPill) artifactProviderPill.textContent = currentProvider;

  sandboxIframe.srcdoc = `
    <!DOCTYPE html>
    <html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display:flex; flex-direction:column; align-items:center; justify-content:center; height:80vh; color:#6b7280; text-align:center;">
      <div style="font-family: monospace; font-size: 0.85rem; margin-bottom: 0.5rem;">[ENGINEERING ATOMIC ESSAY]</div>
      <h3 style="color:#111827; margin-bottom: 0.5rem; font-size:1.05rem;">Applying Ship 30 for 30 Rubric</h3>
      <p style="font-size:0.8rem; max-width:360px; line-height:1.5;">Formatting The Hook, One Core Idea, Rhythm, and the Actionable Tomorrow at 9 AM Protocol...</p>
    </body></html>
  `;
  rawMarkdownView.textContent = "Synthesizing publication draft...";

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
      throw new Error("Ship 30 transformation failed");
    }

    const data = await res.json();
    activeArtifactData = data;

    artifactTitle.textContent = data.title;
    artifactWordCount.textContent = `${data.word_count} words`;
    
    const readMinutes = Math.max(1, Math.round(data.word_count / 250));
    if (readingTimePill) readingTimePill.textContent = `${readMinutes} min read`;
    if (artifactProviderPill) artifactProviderPill.textContent = data.provider_used || currentProvider;

    sandboxIframe.srcdoc = data.essay_html;
    rawMarkdownView.textContent = data.essay_markdown;

    showToast("Atomic essay generated", "Essay ready");
  } catch (err) {
    showError("Ship 30 Error", err.message, "Verify backend service status.");
    artifactPanel.classList.remove("open");
  }
}

// --- Toast Feedback ---
function showToast(message, title = "") {
  if (!toastContainer) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<span style="color:var(--accent-orange)">■</span><span>${escapeHtml(message)}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = "opacity 0.15s, transform 0.15s";
    toast.style.opacity = "0";
    toast.style.transform = "translateY(6px)";
    setTimeout(() => toast.remove(), 150);
  }, 2200);
}

// --- Utilities ---
function scrollToBottom() {
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

function showError(title, message, tip = "") {
  errorTitle.textContent = title;
  errorDesc.textContent = message;
  errorTip.textContent = tip ? `Hint: ${tip}` : "";
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
