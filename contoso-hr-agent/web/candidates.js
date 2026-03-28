// Contoso HR Agent — Candidates Grid

const API_BASE = '';
let currentFilter = 'all';
let allCandidates = [];
let refreshTimer = null;

// Load on init
loadCandidates();
loadStats();
startAutoRefresh();

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadCandidates() {
  showRefreshing(true);
  try {
    const url = currentFilter === 'all'
      ? `${API_BASE}/api/candidates?limit=50`
      : `${API_BASE}/api/candidates?limit=50&decision=${currentFilter}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allCandidates = await res.json();
    renderGrid(allCandidates);
    updateRefreshLabel();
  } catch (err) {
    console.error('Load error:', err);
    showGridError();
  } finally {
    showRefreshing(false);
  }
}

async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById('stat-total').textContent = data.total_evaluations || 0;
    document.getElementById('stat-advance').textContent = data.by_decision?.advance || 0;
    document.getElementById('stat-hold').textContent = data.by_decision?.hold || 0;
    document.getElementById('stat-reject').textContent = data.by_decision?.reject || 0;
    document.getElementById('stat-score').textContent =
      data.average_score ? Math.round(data.average_score) : '–';
  } catch (err) {
    console.error('Stats error:', err);
  }
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    loadCandidates();
    loadStats();
  }, 10000);
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderGrid(candidates) {
  const grid = document.getElementById('candidates-grid');

  if (!candidates.length) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="icon">📋</div>
        <p>No candidates yet.<br>
           <a href="chat.html" style="color:var(--contoso-blue)">Upload a resume</a> to get started.</p>
      </div>`;
    return;
  }

  grid.innerHTML = candidates.map(c => {
    const scoreClass = c.overall_score >= 70 ? 'high' : c.overall_score >= 40 ? 'med' : 'low';
    return `
      <div class="card candidate-card" onclick="openDetail('${c.candidate_id}')">
        <div class="top">
          <div>
            <div class="candidate-name">${escapeHtml(c.candidate_name || 'Unknown')}</div>
            <div class="candidate-file">📄 ${escapeHtml(c.filename)}</div>
          </div>
          <div class="badge badge-${c.decision}">${c.decision}</div>
        </div>
        <div class="candidate-scores">
          <div class="score-row">
            <span class="score-label">Overall</span>
            <div class="score-bar"><div class="score-fill ${scoreClass}" style="width:${c.overall_score}%"></div></div>
            <span class="score-num">${c.overall_score}</span>
          </div>
        </div>
        <div class="candidate-footer">
          <span class="candidate-time">${formatDateTime(c.timestamp_utc)}</span>
          ${c.duration_seconds ? `<span style="font-size:11px;color:var(--contoso-gray-dark)">${c.duration_seconds.toFixed(1)}s</span>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function showGridError() {
  document.getElementById('candidates-grid').innerHTML = `
    <div class="empty-state" style="grid-column:1/-1">
      <div class="icon">⚠️</div>
      <p>Could not load candidates.<br>Is the server running on port 8080?</p>
    </div>`;
}

// ---------------------------------------------------------------------------
// Detail Modal
// ---------------------------------------------------------------------------

async function openDetail(candidateId) {
  const backdrop = document.getElementById('modal-backdrop');
  const body = document.getElementById('modal-body');

  backdrop.style.display = 'flex';
  body.innerHTML = '<div style="text-align:center;padding:32px"><div class="spinner"></div></div>';

  try {
    const res = await fetch(`${API_BASE}/api/candidates/${candidateId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderModal(data);
  } catch (err) {
    body.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><p>Could not load details: ${err.message}</p></div>`;
  }
}

function renderModal(data) {
  const e = data.candidate_eval;
  const d = data.hr_decision;
  const decision = d.decision;

  document.getElementById('modal-name').textContent = data.candidate_name || 'Unknown Candidate';
  document.getElementById('modal-file').textContent = `📄 ${data.filename}  |  ID: ${data.candidate_id}`;

  const skillClass = e.skills_match_score >= 70 ? 'high' : e.skills_match_score >= 40 ? 'med' : 'low';
  const expClass = e.experience_score >= 70 ? 'high' : e.experience_score >= 40 ? 'med' : 'low';

  const strengthsHtml = (e.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('') || '<li>None noted</li>';
  const flagsHtml = (e.red_flags || []).map(f => `<li class="red">${escapeHtml(f)}</li>`).join('') || '<li>None</li>';
  const nextStepsHtml = (d.next_steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join('') || '<li>See HR</li>';

  document.getElementById('modal-body').innerHTML = `
    <div class="decision-banner ${decision}">
      ${decision === 'advance' ? '✅' : decision === 'hold' ? '⏸️' : '❌'}
      Decision: ${decision.toUpperCase()}  |  Score: ${d.overall_score}/100
    </div>

    <div class="detail-section">
      <div class="section-title">Scores</div>
      <div class="detail-grid">
        <div class="detail-metric">
          <div class="dm-value" style="color:${skillClass==='high'?'var(--contoso-green)':skillClass==='med'?'#7A5C00':'var(--contoso-red)'}">${e.skills_match_score}</div>
          <div class="dm-label">Skills Match</div>
          <div class="score-bar" style="width:100%;margin-top:6px">
            <div class="score-fill ${skillClass}" style="width:${e.skills_match_score}%"></div>
          </div>
        </div>
        <div class="detail-metric">
          <div class="dm-value" style="color:${expClass==='high'?'var(--contoso-green)':expClass==='med'?'#7A5C00':'var(--contoso-red)'}">${e.experience_score}</div>
          <div class="dm-label">Experience Depth</div>
          <div class="score-bar" style="width:100%;margin-top:6px">
            <div class="score-fill ${expClass}" style="width:${e.experience_score}%"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="detail-section">
      <div class="section-title">Decision Reasoning</div>
      <div class="reasoning-box">${escapeHtml(d.reasoning)}</div>
    </div>

    <div class="detail-grid" style="margin-bottom:20px">
      <div class="detail-section">
        <div class="section-title">✅ Strengths</div>
        <ul class="list-items">${strengthsHtml}</ul>
      </div>
      <div class="detail-section">
        <div class="section-title">⚠️ Red Flags</div>
        <ul class="list-items">${flagsHtml}</ul>
      </div>
    </div>

    ${e.culture_fit_notes ? `
    <div class="detail-section">
      <div class="section-title">Culture Fit</div>
      <p style="font-size:13px">${escapeHtml(e.culture_fit_notes)}</p>
    </div>` : ''}

    <div class="detail-section">
      <div class="section-title">Next Steps</div>
      <ul class="list-items">${nextStepsHtml}</ul>
    </div>

    ${d.policy_compliance_notes ? `
    <div class="detail-section">
      <div class="section-title">Policy Notes</div>
      <div class="reasoning-box" style="border-color:var(--contoso-yellow);background:#FFFBF0">${escapeHtml(d.policy_compliance_notes)}</div>
    </div>` : ''}

    ${data.duration_seconds ? `
    <div style="font-size:11px;color:var(--contoso-gray-dark);margin-top:8px">
      Evaluated in ${data.duration_seconds.toFixed(1)}s  |  ${formatDateTime(data.timestamp_utc)}
    </div>` : ''}
  `;
}

function closeModal(e) {
  if (!e || e.target === document.getElementById('modal-backdrop') || !e.target) {
    document.getElementById('modal-backdrop').style.display = 'none';
  }
}

// Keyboard: Escape to close
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// ---------------------------------------------------------------------------
// Filters & UI Helpers
// ---------------------------------------------------------------------------

function setFilter(filter, btn) {
  currentFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadCandidates();
}

function showRefreshing(on) {
  document.getElementById('refresh-spinner').style.display = on ? 'inline-block' : 'none';
}

function updateRefreshLabel() {
  const now = new Date();
  document.getElementById('refresh-label').textContent =
    `Last updated ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatDateTime(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' +
           d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}
