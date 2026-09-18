/* ==========================================================================
   Discord AI Chatbot - Web Panel Client Script
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  fetchBotStatus();
  initInviteGenerator();
});

// ─── Fetch Bot Telemetry & Status ───────────────────────────────────────────
async function fetchBotStatus() {
  const modelEl = document.getElementById('stat-model');
  const prefixEl = document.getElementById('stat-prefix');
  const channelsEl = document.getElementById('stat-channels');
  const statusSubtext = document.getElementById('bot-status-subtext');

  try {
    const res = await fetch('/api/status');
    if (res.ok) {
      const data = await res.json();
      if (data.model && modelEl) modelEl.textContent = data.model;
      if (data.prefix && prefixEl) prefixEl.textContent = data.prefix;
      if (data.allowed_channels && channelsEl) {
        channelsEl.textContent = data.allowed_channels.map(c => '#' + c).join(', ');
      }
      if (statusSubtext) statusSubtext.textContent = "Online • Ready";
    }
  } catch (e) {
    // Graceful fallback if opened via static file or server not running
    if (statusSubtext) statusSubtext.textContent = "Static Portal Mode";
  }
}

// ─── Clipboard & URL Helpers ────────────────────────────────────────────────
function copyLegalLink(page) {
  const currentOrigin = window.location.origin;
  const currentPath = window.location.pathname;
  let fullUrl = "";

  if (window.location.protocol.startsWith('http')) {
    // If on a web server
    const basePath = currentPath.substring(0, currentPath.lastIndexOf('/') + 1);
    fullUrl = `${currentOrigin}${basePath}${page}`;
  } else {
    // If opened directly via file://
    fullUrl = `https://your-domain.com/${page}`;
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
  // Check if clientId is cached in localStorage
  const savedId = localStorage.getItem('discord_client_id');
  if (savedId) {
    const input = document.getElementById('client-id-input');
    if (input) {
      input.value = savedId;
      updateInviteUrl();
    }
  }

  const clientIdInput = document.getElementById('client-id-input');
  if (clientIdInput) {
    clientIdInput.addEventListener('change', () => {
      localStorage.setItem('discord_client_id', clientIdInput.value.trim());
    });
  }
}

// ─── Interactive AI Playground ──────────────────────────────────────────────
const conversationState = [];

async function handleChatSubmit(e) {
  e.preventDefault();
  const inputEl = document.getElementById('chat-input');
  const msgText = inputEl.value.trim();
  if (!msgText) return;

  inputEl.value = '';
  appendChatMessage('user', 'You', msgText);

  // Add typing indicator
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
      // Offline / Static demo response with realistic tone simulation
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
  bubbleDiv.innerHTML = '<span style="color: var(--text-muted); font-style: italic;">Thinking...</span>';

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
        Chat cleared! Feel free to talk in Bangla, English, Banglish or Hindi.
      </div>
    </div>
  `;
  showToast("Playground chat cleared.");
}

function generateFallbackAiReply(text) {
  const lower = text.toLowerCase();
  if (lower.includes('kemon') || lower.includes('how are')) {
    return "Ami bhalo achi bro! Tumi kemon acho? Server e shob thik thak?";
  } else if (lower.includes('love') || lower.includes('valobashi') || lower.includes('sweet')) {
    return "Aww, thank you so much! You're really sweet too ❤️";
  } else if (lower.includes('roast')) {
    return "Tor face dekhe mone hocche Windows update 99% e eshe freeze hoye gese 😂";
  } else if (lower.includes('sad') || lower.includes('vent') || lower.includes('para')) {
    return "Chinta koro na bro, shob kisu thik hoye jabe. Ami achi toh shunar jonno 🫂";
  } else {
    return `Got your message: "${text}". Web playground is active! When connected to Discord with live API, I'll provide full contextual responses.`;
  }
}
