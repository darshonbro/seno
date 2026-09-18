/* ==========================================================================
   Discord AI Chatbot - Web Panel Client Script
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  fetchBotStatus();
  fetchTrainingRules();
  initInviteGenerator();
});

// ─── Fetch Bot Telemetry & Status ───────────────────────────────────────────
async function fetchBotStatus() {
  const modelEl = document.getElementById('stat-model');
  const prefixEl = document.getElementById('stat-prefix');
  const ownerEl = document.getElementById('stat-owner');
  const statusSubtext = document.getElementById('bot-status-subtext');

  try {
    const res = await fetch('/api/status');
    if (res.ok) {
      const data = await res.json();
      if (data.model && modelEl) modelEl.textContent = data.model;
      if (data.prefix && prefixEl) prefixEl.textContent = data.prefix;
      if (data.owner_id && ownerEl) ownerEl.textContent = data.owner_id;
      if (statusSubtext) statusSubtext.textContent = "Online • Ready";
    }
  } catch (e) {
    if (statusSubtext) statusSubtext.textContent = "Static Portal Mode";
  }
}

// ─── Owner Training & Behavior Management ───────────────────────────────────
async function fetchTrainingRules() {
  const container = document.getElementById('rules-list-container');
  const countEl = document.getElementById('rule-count');
  if (!container) return;

  try {
    const res = await fetch('/api/training');
    if (res.ok) {
      const data = await res.json();
      const rules = data.rules || [];
      if (countEl) countEl.textContent = rules.length;

      if (rules.length === 0) {
        container.innerHTML = `
          <div style="color: var(--text-muted); font-size: 0.85rem; font-style: italic; padding: 0.5rem 0;">
            এখনো কোনো কাস্টম নিয়ম যোগ করা হয়নি। উপরে বক্স থেকে নিয়ম লিখুন অথবা Discord-এ !train কমান্ড ব্যবহার করুন!
          </div>
        `;
        return;
      }

      container.innerHTML = rules.map((rule, idx) => `
        <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(10, 12, 18, 0.7); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 0.7rem 1rem; gap: 0.8rem;">
          <div style="display: flex; align-items: flex-start; gap: 0.6rem; font-size: 0.88rem; color: #f8fafc;">
            <span style="color: var(--accent-cyan); font-weight: 700; font-family: var(--font-mono);">#${idx + 1}</span>
            <span>${escapeHtml(rule)}</span>
          </div>
          <button type="button" class="copy-chip" style="color: var(--accent-pink); border-color: rgba(244, 63, 94, 0.3); padding: 0.3rem 0.6rem;" onclick="deleteRule(${idx + 1})">
            ✕ Delete
          </button>
        </div>
      `).join('');
    }
  } catch (err) {
    // If running in static file mode
    if (container) {
      container.innerHTML = `
        <div style="color: var(--text-muted); font-size: 0.85rem; font-style: italic;">
          (Static Mode: Train via Discord with <code>!train &lt;instruction&gt;</code>)
        </div>
      `;
    }
  }
}

async function handleTrainSubmit(e) {
  e.preventDefault();
  const inputEl = document.getElementById('new-rule-input');
  const rule = inputEl.value.trim();
  if (!rule) return;

  try {
    const res = await fetch('/api/training', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rule: rule })
    });

    if (res.ok) {
      inputEl.value = '';
      showToast("🧠 নতুন আচরণ সফলভাবে ট্রেইনিং সেভ হয়েছে!");
      fetchTrainingRules();
    } else {
      showToast("Failed to save training rule.");
    }
  } catch (err) {
    showToast("Server offline. You can also train in Discord using !train <rule>");
  }
}

async function deleteRule(index) {
  try {
    const res = await fetch(`/api/training/${index}`, { method: 'DELETE' });
    if (res.ok) {
      showToast(`রুল #${index} মুছে ফেলা হয়েছে!`);
      fetchTrainingRules();
    }
  } catch (err) {
    showToast("Error deleting rule.");
  }
}

async function clearAllRules() {
  if (!confirm("আপনি কি নিশ্চিত সব কাস্টম ট্রেইনিং মুছে ফেলতে চান?")) return;
  try {
    const res = await fetch('/api/training', { method: 'DELETE' });
    if (res.ok) {
      showToast("সব কাস্টম ট্রেইনিং রিসেট করা হয়েছে!");
      fetchTrainingRules();
    }
  } catch (err) {
    showToast("Error clearing rules.");
  }
}

function applyPresetRule(preset) {
  const inputEl = document.getElementById('new-rule-input');
  if (inputEl) {
    inputEl.value = preset;
    inputEl.focus();
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ─── Clipboard & URL Helpers ────────────────────────────────────────────────
function copyLegalLink(page) {
  const currentOrigin = window.location.origin;
  const currentPath = window.location.pathname;
  let fullUrl = "";

  if (window.location.protocol.startsWith('http')) {
    const basePath = currentPath.substring(0, currentPath.lastIndexOf('/') + 1);
    fullUrl = `${currentOrigin}${basePath}${page}`;
  } else {
    fullUrl = `https://darshonbro.github.io/seno/${page}`;
  }

  navigator.clipboard.writeText(fullUrl).then(() => {
    showToast(`Copied: ${page} URL for Discord Developer Portal!`);
  }).catch(() => {
    prompt("Copy this URL for Discord Developer Portal:", fullUrl);
  });
}

function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

// ─── Discord Invite Link Generator ──────────────────────────────────────────
function calculatePermissions() {
  const checkboxes = document.querySelectorAll('#perm-checkboxes input[type="checkbox"]');
  let perms = 0;
  checkboxes.forEach(cb => {
    if (cb.checked) {
      perms |= parseInt(cb.value, 10);
    }
  });
  return perms;
}

function updateInviteUrl() {
  const clientIdInput = document.getElementById('client-id-input');
  const previewEl = document.getElementById('invite-preview');
  const inviteBtn = document.getElementById('invite-btn');
  const clientId = clientIdInput.value.trim();

  if (!clientId || !/^\d+$/.test(clientId)) {
    previewEl.textContent = "Enter a valid numeric Client ID above...";
    inviteBtn.style.pointerEvents = 'none';
    inviteBtn.style.opacity = '0.6';
    inviteBtn.removeAttribute('href');
    return "";
  }

  const perms = calculatePermissions();
  const inviteUrl = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&permissions=${perms}&scope=bot%20applications.commands`;

  previewEl.textContent = inviteUrl;
  inviteBtn.setAttribute('href', inviteUrl);
  inviteBtn.style.pointerEvents = 'auto';
  inviteBtn.style.opacity = '1';

  return inviteUrl;
}

function copyInviteUrl() {
  const inviteUrl = updateInviteUrl();
  if (inviteUrl) {
    navigator.clipboard.writeText(inviteUrl).then(() => {
      showToast("Discord Invite URL copied to clipboard!");
    });
  } else {
    showToast("Please enter a numeric Discord Client ID first.");
  }
}

function initInviteGenerator() {
  const savedId = localStorage.getItem('discord_client_id') || '1382092671002345573';
  const input = document.getElementById('client-id-input');
  if (input) {
    input.value = savedId;
    updateInviteUrl();
    input.addEventListener('change', () => {
      localStorage.setItem('discord_client_id', input.value.trim());
    });
  }
}

// ─── Interactive AI Playground ──────────────────────────────────────────────
async function handleChatSubmit(e) {
  e.preventDefault();
  const inputEl = document.getElementById('chat-input');
  const msgText = inputEl.value.trim();
  if (!msgText) return;

  inputEl.value = '';
  appendChatMessage('user', 'You', msgText);

  const typingIndicator = appendTypingIndicator();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msgText, user: 'WebUser' })
    });

    typingIndicator.remove();

    if (res.ok) {
      const data = await res.json();
      appendChatMessage('bot', 'Discord AI Chatbot', data.reply || 'No response received.');
    } else {
      const fallbackReply = generateFallbackAiReply(msgText);
      appendChatMessage('bot', 'Discord AI Chatbot', fallbackReply);
    }
  } catch (err) {
    typingIndicator.remove();
    const fallbackReply = generateFallbackAiReply(msgText);
    appendChatMessage('bot', 'Discord AI Chatbot', fallbackReply);
  }
}

function appendChatMessage(role, author, text) {
  const container = document.getElementById('chat-messages');
  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-msg ${role}`;

  const avatarDiv = document.createElement('div');
  avatarDiv.className = 'chat-avatar';
  avatarDiv.textContent = role === 'user' ? 'U' : 'AI';

  const bubbleDiv = document.createElement('div');
  bubbleDiv.className = 'chat-bubble';

  const authorDiv = document.createElement('div');
  authorDiv.className = 'chat-author';
  authorDiv.textContent = author;

  const contentDiv = document.createElement('div');
  contentDiv.textContent = text;

  bubbleDiv.appendChild(authorDiv);
  bubbleDiv.appendChild(contentDiv);
  msgDiv.appendChild(avatarDiv);
  msgDiv.appendChild(bubbleDiv);

  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
}

function appendTypingIndicator() {
  const container = document.getElementById('chat-messages');
  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-msg bot';
  msgDiv.id = 'typing-indicator';

  const avatarDiv = document.createElement('div');
  avatarDiv.className = 'chat-avatar';
  avatarDiv.textContent = 'AI';

  const bubbleDiv = document.createElement('div');
  bubbleDiv.className = 'chat-bubble';
  bubbleDiv.innerHTML = '<span style="color: var(--text-muted); font-style: italic;">ভাবছে...</span>';

  msgDiv.appendChild(avatarDiv);
  msgDiv.appendChild(bubbleDiv);
  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
  return msgDiv;
}

function clearPlaygroundChat() {
  const container = document.getElementById('chat-messages');
  container.innerHTML = `
    <div class="chat-msg bot">
      <div class="chat-avatar">AI</div>
      <div class="chat-bubble">
        <div class="chat-author">Discord AI Chatbot</div>
        চ্যাট ক্লিয়ার করা হয়েছে! তুমি বাংলায়, ইংলিশে অথবা বাংলিশে যেকোনো কিছু বলতে পারো।
      </div>
    </div>
  `;
  showToast("Playground chat cleared.");
}

function generateFallbackAiReply(text) {
  const lower = text.toLowerCase();
  if (lower.includes('kemon') || lower.includes('how are')) {
    return "আমি ভালো আছি! তুমি কেমন আছো? সার্ভারে সব ঠিকঠাক?";
  } else if (lower.includes('love') || lower.includes('valobashi') || lower.includes('sweet')) {
    return "ধন্যবাদ অনেক! তুমিও অনেক মিষ্টি ❤️";
  } else if (lower.includes('roast')) {
    return "তোমার ফেস দেখে মনে হচ্ছে উইন্ডোজ আপডেট ৯৯% এ এসে আটকে গেছে 😂";
  } else if (lower.includes('sad') || lower.includes('vent') || lower.includes('para')) {
    return "মন খারাপ করো না, সবকিছু ঠিক হয়ে যাবে। আমি তো আছি শোনার জন্য 🫂";
  } else {
    return `বার্তা পেয়েছি: "${text}"। ওয়েব প্যানেল প্লেগ্রাউন্ড সক্রিয় রয়েছে!`;
  }
}
