// Contoso HR Agent — Chat UI
// Chat history is persisted in localStorage under the session_id key.
// The session_id is also sent to the server so the backend can rebuild
// LLM context from data/chat_sessions/{session_id}.json across restarts.

const API_BASE = '';
let sessionId = localStorage.getItem('hr_session_id') || generateId();
localStorage.setItem('hr_session_id', sessionId);
let recentUploads = [];

// ---------------------------------------------------------------------------
// Chat history — localStorage persistence
// Key: "hr_history_{sessionId}"  Value: [{role, text, time}]
// ---------------------------------------------------------------------------

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(`hr_history_${sessionId}`)) || [];
  } catch { return []; }
}

function saveHistory(history) {
  try {
    // Cap at 200 messages to avoid hitting localStorage limits
    const trimmed = history.slice(-200);
    localStorage.setItem(`hr_history_${sessionId}`, JSON.stringify(trimmed));
  } catch { /* storage full — silently skip */ }
}

function appendToHistory(role, text) {
  const history = loadHistory();
  history.push({ role, text, time: new Date().toISOString() });
  saveHistory(history);
}

function clearHistory() {
  localStorage.removeItem(`hr_history_${sessionId}`);
  // Generate a fresh session so the server also starts fresh
  sessionId = generateId();
  localStorage.setItem('hr_session_id', sessionId);
}

// ---------------------------------------------------------------------------
// Restore previous session on page load
// ---------------------------------------------------------------------------

function restoreSession() {
  const history = loadHistory();
  if (!history.length) return;

  const container = document.getElementById('messages');
  // Insert a subtle divider before restored messages
  const divider = document.createElement('div');
  divider.style.cssText = 'text-align:center;font-size:11px;color:var(--contoso-gray-dark);padding:8px 0 4px;';
  divider.textContent = '— previous session restored —';
  container.appendChild(divider);

  history.forEach(({ role, text, time }) => {
    renderMessage(role, text, new Date(time));
  });
  container.scrollTop = container.scrollHeight;
}

// ---------------------------------------------------------------------------
// Messaging
// ---------------------------------------------------------------------------

async function sendMessage(text) {
  const input = document.getElementById('chat-input');
  const message = (text || input.value).trim();
  if (!message) return;

  input.value = '';
  autoResize(input);
  clearSuggestions();

  renderMessage('user', message);
  appendToHistory('user', message);
  setLoading(true);

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    renderMessage('bot', data.reply);
    appendToHistory('bot', data.reply);

    if (data.suggestions && data.suggestions.length) {
      showSuggestions(data.suggestions);
    }
  } catch (err) {
    const errMsg = '⚠️ Connection error. Please check the server is running.';
    renderMessage('bot', errMsg);
    console.error('Chat error:', err);
  } finally {
    setLoading(false);
  }
}

function sendSuggestion(btn) {
  sendMessage(btn.textContent);
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function setLoading(loading) {
  const btn = document.getElementById('send-btn');
  const input = document.getElementById('chat-input');
  btn.disabled = loading;
  input.disabled = loading;
  loading ? appendTypingIndicator() : removeTypingIndicator();
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderMessage(role, text, timestamp) {
  const container = document.getElementById('messages');
  const isBot = role === 'bot';
  const time = timestamp || new Date();

  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = `
    <div class="msg-avatar">${isBot ? 'HR' : 'You'}</div>
    <div>
      <div class="msg-bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>
      <div class="msg-time">${formatTime(time)}</div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

// Keep appendMessage as alias used by upload flow
function appendMessage(role, text) { renderMessage(role, text); }

function appendTypingIndicator() {
  const container = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg bot';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="msg-avatar">HR</div>
    <div>
      <div class="msg-bubble" style="display:flex;align-items:center;gap:8px">
        <div class="spinner"></div>
        <span style="color:#666;font-size:13px">Thinking...</span>
      </div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function showSuggestions(items) {
  const container = document.getElementById('suggestions');
  container.innerHTML = items.map(s =>
    `<button class="suggestion-btn" onclick="sendSuggestion(this)">${escapeHtml(s)}</button>`
  ).join('');
}

function clearSuggestions() {
  document.getElementById('suggestions').innerHTML = '';
}

// ---------------------------------------------------------------------------
// File Upload
// ---------------------------------------------------------------------------

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}

function handleDragLeave() {
  document.getElementById('drop-zone').classList.remove('drag-over');
}

function handleDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) uploadFile(file);
  e.target.value = '';
}

async function uploadFile(file) {
  const allowed = ['.txt', '.md', '.pdf', '.docx'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showUploadStatus('error', `❌ Unsupported type: ${ext}. Use .txt, .md, .pdf, or .docx`);
    return;
  }

  showUploadStatus('loading', `Uploading ${file.name}...`);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: formData });
    const data = await res.json();

    if (data.status === 'queued') {
      showUploadStatus('success', `✅ ${file.name} queued!`);
      addRecentUpload(file.name, data.candidate_id);
      const botMsg = `📄 Resume received: ${file.name}\n\nThe AI pipeline is evaluating it now (Policy Expert → Resume Analyst → Decision Maker). Results appear on the Candidates page — it auto-refreshes every 10s.`;
      renderMessage('bot', botMsg);
      appendToHistory('bot', botMsg);
    } else {
      showUploadStatus('error', `❌ ${data.message}`);
    }
  } catch (err) {
    showUploadStatus('error', `❌ Upload failed: ${err.message}`);
    console.error('Upload error:', err);
  }
}

function showUploadStatus(type, message) {
  const el = document.getElementById('upload-status');
  el.className = `upload-status ${type}`;
  if (type === 'loading') {
    el.innerHTML = `<div class="spinner"></div> <span>${message}</span>`;
  } else {
    el.textContent = message;
  }
  if (type !== 'loading') setTimeout(() => { el.style.display = 'none'; }, 5000);
}

function addRecentUpload(filename, candidateId) {
  recentUploads.unshift({ filename, candidateId, time: new Date() });
  if (recentUploads.length > 5) recentUploads.pop();

  const section = document.getElementById('recent-uploads-section');
  const list = document.getElementById('recent-uploads-list');
  section.style.display = 'block';
  list.innerHTML = recentUploads.map(u => `
    <div class="upload-item">
      <span title="${escapeHtml(u.filename)}">📄 ${escapeHtml(u.filename.length > 22 ? u.filename.slice(0,22) + '…' : u.filename)}</span>
      <span class="badge badge-unknown" style="font-size:10px">${formatTime(u.time)}</span>
    </div>
  `).join('');
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatTime(d) {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.getElementById('welcome-time').textContent = formatTime(new Date());
restoreSession();
