// Contoso HR Agent — Pipeline Runs page
// Displays a list of evaluation runs on the left and a detailed
// pipeline trace on the right, showing the parallel fan-out architecture.

const API_BASE = '';
let allRuns = [];
let selectedId = null;

// ---------------------------------------------------------------------------
// Load + render run list
// ---------------------------------------------------------------------------

async function loadRuns() {
  try {
    const res = await fetch(`${API_BASE}/api/candidates?limit=100`);
    if (!res.ok) return;
    allRuns = await res.json();

    const countEl = document.getElementById('run-count');
    countEl.textContent = `${allRuns.length} run${allRuns.length !== 1 ? 's' : ''} — auto-refreshes every 10s`;

    renderRunList();

    // Auto-select first run if nothing selected yet
    if (!selectedId && allRuns.length > 0) {
      selectRun(allRuns[0].candidate_id);
    }
  } catch { /* server unavailable */ }
}

function renderRunList() {
  const container = document.getElementById('run-list');
  if (!allRuns.length) {
    container.innerHTML = `
      <div style="padding:24px;text-align:center;color:var(--contoso-gray-dark);font-size:13px">
        No runs yet — drop a resume into the Chat page to start.
      </div>`;
    return;
  }

  container.innerHTML = allRuns.map(run => {
    const isActive = run.candidate_id === selectedId;
    const cls = decisionClass(run.decision);
    const dur = run.duration_seconds ? `${run.duration_seconds.toFixed(1)}s` : '—';
    const ts  = formatTimestamp(run.timestamp_utc);
    const shortFile = run.filename.length > 28 ? run.filename.slice(0, 28) + '…' : run.filename;
    return `
      <div class="run-item ${isActive ? 'active' : ''}" onclick="selectRun('${run.candidate_id}')">
        <div class="run-item-top">
          <div>
            <div class="run-item-name">${escapeHtml(run.candidate_name)}</div>
            <div class="run-item-file" title="${escapeHtml(run.filename)}">${escapeHtml(shortFile)}</div>
          </div>
          <span class="badge badge-${cls}" style="flex-shrink:0">${escapeHtml(run.decision)}</span>
        </div>
        <div class="run-item-meta">
          <span class="run-item-score">${run.overall_score}/100</span>
          <span class="run-item-time">${ts} · ${dur}</span>
        </div>
      </div>`;
  }).join('');
}

// ---------------------------------------------------------------------------
// Select a run and load its full trace
// ---------------------------------------------------------------------------

async function selectRun(candidateId) {
  selectedId = candidateId;
  renderRunList(); // update active state

  const panel = document.getElementById('trace-panel');
  panel.innerHTML = `
    <div class="trace-empty">
      <div class="spinner"></div>
      <span style="font-size:13px;color:var(--contoso-gray-dark)">Loading trace…</span>
    </div>`;

  try {
    const res = await fetch(`${API_BASE}/api/candidates/${candidateId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const result = await res.json();
    renderTrace(result);
  } catch (err) {
    panel.innerHTML = `<div class="trace-empty"><div class="icon">⚠️</div><span>Failed to load trace</span></div>`;
  }
}

// ---------------------------------------------------------------------------
// Render pipeline trace
// ---------------------------------------------------------------------------

function renderTrace(r) {
  const panel = document.getElementById('trace-panel');
  const eval_ = r.candidate_eval;
  const dec   = r.hr_decision;
  const cls   = decisionClass(dec.decision);
  const dur   = r.duration_seconds ? `${r.duration_seconds.toFixed(1)}s` : '—';

  panel.innerHTML = `
    <!-- Trace header -->
    <div class="trace-header">
      <div>
        <div class="trace-title">${escapeHtml(r.candidate_name)}</div>
        <div class="trace-subtitle">${escapeHtml(r.filename)} &nbsp;·&nbsp; run ${escapeHtml(r.run_id.slice(0, 8))}</div>
      </div>
      <div class="trace-meta">
        <div class="trace-meta-item">
          <div class="value">${dur}</div>
          <div class="label">Duration</div>
        </div>
        <div class="trace-meta-item">
          <div class="value">${dec.overall_score}/100</div>
          <div class="label">Score</div>
        </div>
        <div class="trace-meta-item">
          <span class="decision-pill pill-${cls}">${escapeHtml(dec.decision)}</span>
        </div>
      </div>
    </div>

    <!-- Pipeline diagram -->
    <div class="pipeline">

      <!-- Node 1: Intake -->
      ${nodeHtml('intake', '📥', 'Intake', 'Node 1', `
        ${dataRow('Candidate', escapeHtml(r.candidate_name))}
        ${dataRow('File', escapeHtml(r.filename))}
        ${dataRow('Candidate ID', escapeHtml(r.candidate_id))}
        ${dataRow('Timestamp', escapeHtml(formatTimestamp(r.timestamp_utc)))}
      `)}

      ${connector()}

      <!-- Nodes 2+3: Parallel fan-out -->
      <div class="parallel-section">
        <div class="parallel-label">⚡ parallel fan-out — these two agents run concurrently</div>
        <div class="parallel-nodes">

          <!-- Policy Expert -->
          ${nodeHtml('policy', '📋', 'Policy Expert', 'Node 2 · ChromaDB', `
            ${dataRow('Policy summary', '')}
            <div style="font-size:12px;line-height:1.5;color:#333;margin-top:4px">
              ${escapeHtml(r.policy_context_summary || 'Standard Contoso MCT trainer policy applies.')}
            </div>
          `)}

          <!-- Resume Analyst -->
          ${nodeHtml('analyst', '🔍', 'Resume Analyst', 'Node 3 · Brave Search', `
            ${dataRow('Skills match', `<span class="score-pill">${eval_.skills_match_score}/100</span>`)}
            ${dataRow('Experience', `<span class="score-pill">${eval_.experience_score}/100</span>`)}
            ${eval_.recommended_role ? dataRow('Best-fit role', escapeHtml(eval_.recommended_role)) : ''}
            ${eval_.strengths.length ? `
              <div class="data-key" style="margin-top:6px">Strengths</div>
              <ul class="bullet-list">${eval_.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>` : ''}
            ${eval_.red_flags.length ? `
              <div class="data-key" style="margin-top:6px">Red flags</div>
              <ul class="bullet-list">${eval_.red_flags.map(f => `<li class="red">${escapeHtml(f)}</li>`).join('')}</ul>` : ''}
          `)}

        </div>
      </div>

      ${connector()}

      <!-- Node 4: Decision Maker -->
      ${nodeHtml('decision', '⚖️', 'Decision Maker', 'Node 4 · pure reasoning', `
        ${dataRow('Disposition', `<span class="decision-pill pill-${cls}">${escapeHtml(dec.decision)}</span>`)}
        ${dataRow('Overall score', `<span class="score-pill">${dec.overall_score}/100</span>`)}
        <div class="reasoning-block">${escapeHtml(dec.reasoning)}</div>
        ${dec.next_steps.length ? `
          <div class="data-key" style="margin-top:8px">Next steps</div>
          <ul class="bullet-list">${dec.next_steps.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>` : ''}
      `)}

      ${connector()}

      <!-- Node 5: Notify -->
      ${nodeHtml('notify', '✅', 'Notify', 'Node 5 · no LLM', `
        ${dataRow('Duration', dur)}
        ${dataRow('Saved to', 'SQLite hr.db + data/outgoing/')}
        ${dataRow('Run ID', escapeHtml(r.run_id.slice(0, 16) + '…'))}
      `)}

    </div>
  `;
}

// ---------------------------------------------------------------------------
// HTML helpers
// ---------------------------------------------------------------------------

function nodeHtml(type, icon, label, badge, bodyHtml) {
  return `
    <div class="pipeline-node node-${type}">
      <div class="node-header">
        <span class="node-icon">${icon}</span>
        <span class="node-label">${label}</span>
        <span class="node-badge">${badge}</span>
      </div>
      <div class="node-body">${bodyHtml}</div>
    </div>`;
}

function connector() {
  return `<div class="connector"><div class="connector-arrow"></div></div>`;
}

function dataRow(key, val) {
  return `<div class="data-row">
    <span class="data-key">${key}</span>
    <span class="data-val">${val}</span>
  </div>`;
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function decisionClass(decision) {
  if (decision === 'Strong Match')   return 'strong';
  if (decision === 'Possible Match') return 'possible';
  if (decision === 'Needs Review')   return 'review';
  return 'nq';
}

function formatTimestamp(ts) {
  try {
    return new Date(ts).toLocaleString([], {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return ts; }
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Init + auto-refresh
// ---------------------------------------------------------------------------

loadRuns();
setInterval(loadRuns, 10000);
