/* interview.js — BEE interview page logic */

const API = '';
let sessionId = null;
let skills = [];
let currentQuestion = null;
let timerInterval = null;
let elapsedSeconds = 0;
let isSubmitting = false;

// CodeMirror instance
let cmEditor = null;

const SECTION_MAP = [
  { type: 'theory',   indices: [1,2,3,4,5,6],     dotsId: 'dotsTheory'   },
  { type: 'aptitude', indices: [7,8,9,10,11],      dotsId: 'dotsAptitude' },
  { type: 'coding',   indices: [12,13,14],          dotsId: 'dotsCoding'   },
  { type: 'hr',       indices: [15],                dotsId: 'dotsHr'       },
];

// CodeMirror mode map
const LANG_MODES = {
  python:     'python',
  javascript: 'javascript',
  typescript: 'text/typescript',
  java:       'text/x-java',
  cpp:        'text/x-c++src',
  c:          'text/x-csrc',
  go:         'go',
  rust:       'rust',
  ruby:       'ruby',
  kotlin:     'text/x-kotlin',
  swift:      'text/x-swift',
  r:          'r',
  scala:      'text/x-scala',
  matlab:     'text/plain',
};

// ── Init ──
window.addEventListener('DOMContentLoaded', async () => {
  sessionId = sessionStorage.getItem('bee_session_id');
  skills = JSON.parse(sessionStorage.getItem('bee_skills') || '[]');

  if (!sessionId) { window.location.href = 'index.html'; return; }

  // Render skill tags
  const skillTagsEl = document.getElementById('skillTags');
  skills.forEach(s => {
    const tag = document.createElement('span');
    tag.className = 's-tag';
    tag.textContent = s;
    skillTagsEl.appendChild(tag);
  });

  // Build dots
  SECTION_MAP.forEach(({ dotsId, indices }) => {
    const container = document.getElementById(dotsId);
    indices.forEach(i => {
      const dot = document.createElement('div');
      dot.className = 'dot';
      dot.id = `dot-${i}`;
      dot.textContent = i;
      dot.title = `Q${i}`;
      container.appendChild(dot);
    });
  });

  initMiniNeural('logoCanvas', 30);
  initLoadingNeural('loadCanvas');
  initCodeMirror();

  try {
    const res = await fetch(`${API}/api/current-question/${sessionId}`);
    if (!res.ok) { window.location.href = 'index.html'; return; }
    const data = await res.json();
    renderQuestion(data);
  } catch (e) {
    console.error('Failed to load question:', e);
    window.location.href = 'index.html';
  }

  startTimer();
});

// ── CodeMirror setup ──
function initCodeMirror() {
  const wrapper = document.getElementById('cmWrapper');
  cmEditor = CodeMirror(wrapper, {
    value: '',
    mode: 'python',
    theme: 'dracula',
    lineNumbers: true,
    matchBrackets: true,
    autoCloseBrackets: true,
    indentUnit: 4,
    tabSize: 4,
    indentWithTabs: false,
    lineWrapping: false,
    extraKeys: {
      Tab: cm => cm.execCommand('indentMore'),
      'Shift-Tab': cm => cm.execCommand('indentLess'),
    },
  });

  cmEditor.on('change', () => {
    const len = cmEditor.getValue().length;
    const el = document.getElementById('codeCharCt');
    if (el) el.textContent = len + ' chars';
  });
}

function changeLanguage(lang) {
  if (!cmEditor) return;
  const mode = LANG_MODES[lang] || 'text/plain';
  cmEditor.setOption('mode', mode);
  // Refresh so new mode highlights correctly
  setTimeout(() => cmEditor.refresh(), 10);
}

// ── Timer ──
function startTimer() {
  timerInterval = setInterval(() => {
    elapsedSeconds++;
    const m = String(Math.floor(elapsedSeconds / 60)).padStart(2, '0');
    const s = String(elapsedSeconds % 60).padStart(2, '0');
    document.getElementById('timerDisplay').textContent = `${m}:${s}`;
  }, 1000);
}

// ── Render question ──
function renderQuestion(data) {
  const q = data.question;
  const progress = data.progress;
  const rephrasesRemaining = data.rephrases_remaining ?? 2;
  currentQuestion = data;

  // Tags
  const typeTag = document.getElementById('qTypeTag');
  typeTag.textContent = capitalize(q.type);
  typeTag.className = `q-tag ${q.type}`;

  const diffTag = document.getElementById('qDiffTag');
  diffTag.textContent = capitalize(q.difficulty);
  diffTag.className = `q-tag ${q.difficulty}`;

  const num = String(progress.current).padStart(2, '0');
  const total = String(progress.total).padStart(2, '0');
  document.getElementById('qNum').textContent = `(${num} / ${total})`;
  document.getElementById('questionText').textContent = q.question;

  // Rephrase
  document.getElementById('rephraseCount').textContent = rephrasesRemaining;
  const rephraseBtn = document.getElementById('rephraseBtn');
  rephraseBtn.disabled = rephrasesRemaining === 0;

  // Sidebar
  document.getElementById('progressVal').textContent = `${progress.current} / ${progress.total}`;
  document.getElementById('sectionVal').textContent = capitalize(q.type);
  document.getElementById('difficultyVal').textContent = capitalize(q.difficulty);

  updateDots(progress.current);

  // ── Toggle answer area vs code editor ──
  const isCoding = q.type === 'coding';
  const answerBox = document.getElementById('answerBox');
  const codeEditorBox = document.getElementById('codeEditorBox');

  if (isCoding) {
    answerBox.style.display = 'none';
    codeEditorBox.style.display = 'flex';
    if (cmEditor) {
      cmEditor.setValue('');
      cmEditor.refresh();
      setTimeout(() => cmEditor.refresh(), 50); // ensure render after layout
    }
    document.getElementById('codeCharCt').textContent = '0 chars';
  } else {
    answerBox.style.display = 'flex';
    codeEditorBox.style.display = 'none';
    const ta = document.getElementById('answerTa');
    ta.value = '';
    ta.placeholder = 'Type your answer here...';
    document.getElementById('charCt').textContent = '0 chars';
  }

  // ── Banners: hide ALL on new question ──
  hideBanner('warnBanner');
  hideBanner('shortBanner');
  hideBanner('evalBanner');

  // Re-enable submit
  document.getElementById('submitBtn').disabled = false;
  document.getElementById('codeSubmitBtn').disabled = false;
  isSubmitting = false;
}

function updateDots(currentIdx) {
  for (let i = 1; i <= 15; i++) {
    const dot = document.getElementById(`dot-${i}`);
    if (!dot) continue;
    if (i < currentIdx) {
      dot.className = 'dot done'; dot.textContent = '';
    } else if (i === currentIdx) {
      dot.className = 'dot current'; dot.textContent = i;
    } else {
      dot.className = 'dot'; dot.textContent = i;
    }
  }
}

// ── Get current answer value (textarea or CodeMirror) ──
function getCurrentAnswer() {
  const isCoding = currentQuestion?.question?.type === 'coding';
  if (isCoding && cmEditor) {
    return cmEditor.getValue().trim();
  }
  return document.getElementById('answerTa').value.trim();
}

// ── Submit answer ──
async function submitAnswer() {
  if (isSubmitting) return;

  const answer = getCurrentAnswer();
  if (answer.length < 5) {
    // Banner stays — user must fix, not cleared on submit attempt
    showBanner('shortBanner');
    return;
  }

  isSubmitting = true;

  // Only hide shortBanner when actually submitting (valid answer)
  // warnBanner stays visible until next question renders
  hideBanner('shortBanner');

  document.getElementById('submitBtn').disabled = true;
  document.getElementById('codeSubmitBtn').disabled = true;

  showLoading('Evaluating answer...');

  if (currentQuestion) {
    addHistory('q', `Q${currentQuestion.progress.current}: ${currentQuestion.question.question}`);
    addHistory('a', `A${currentQuestion.progress.current}: ${answer.slice(0, 120)}${answer.length > 120 ? '...' : ''}`);
  }

  try {
    const res = await fetch(`${API}/api/submit-answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, answer }),
    });
    const data = await res.json();
    hideLoading();

    if (!res.ok) {
      console.error('Submit error:', data);
      isSubmitting = false;
      document.getElementById('submitBtn').disabled = false;
      document.getElementById('codeSubmitBtn').disabled = false;
      return;
    }

    // Off-topic warning — banner stays, user must re-answer
    if (data.warning) {
      showBanner('warnBanner');
      isSubmitting = false;
      document.getElementById('submitBtn').disabled = false;
      document.getElementById('codeSubmitBtn').disabled = false;
      return;
    }

    if (data.completed) {
      clearInterval(timerInterval);
      sessionStorage.setItem('bee_results', JSON.stringify(data.results));
      window.location.href = 'results.html';
      return;
    }

    // Next question — renderQuestion() will hide all banners
    renderQuestion(data);

  } catch (e) {
    hideLoading();
    console.error('Submit failed:', e);
    isSubmitting = false;
    document.getElementById('submitBtn').disabled = false;
    document.getElementById('codeSubmitBtn').disabled = false;
  }
}

// ── Rephrase ──
async function rephraseQuestion() {
  const rephraseBtn = document.getElementById('rephraseBtn');
  rephraseBtn.disabled = true;
  showLoading('Rephrasing question...');

  try {
    const res = await fetch(`${API}/api/rephrase/${sessionId}`, { method: 'POST' });
    const data = await res.json();
    hideLoading();

    if (!res.ok || data.error) { rephraseBtn.disabled = true; return; }

    document.getElementById('questionText').textContent = data.rephrased_question;
    document.getElementById('rephraseCount').textContent = data.rephrases_remaining;
    rephraseBtn.disabled = data.rephrases_remaining === 0;
    if (currentQuestion) currentQuestion.rephrases_remaining = data.rephrases_remaining;
  } catch (e) {
    hideLoading();
    rephraseBtn.disabled = false;
  }
}

// ── History ──
function addHistory(type, text) {
  const list = document.getElementById('historyList');
  const entry = document.createElement('div');
  entry.className = `h-entry ${type}`;
  entry.textContent = text;
  list.appendChild(entry);
  list.scrollTop = list.scrollHeight;
}

// ── Banner helpers — NO auto-hide, explicit only ──
function showBanner(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = 'flex';
  el.style.opacity = '0';
  requestAnimationFrame(() => {
    el.style.transition = 'opacity 0.3s';
    el.style.opacity = '1';
  });
}
function hideBanner(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.transition = 'opacity 0.25s';
  el.style.opacity = '0';
  setTimeout(() => { el.style.display = 'none'; }, 250);
}

// ── Loading ──
function showLoading(text) {
  document.getElementById('loadingText').textContent = text || 'Loading...';
  document.getElementById('loadOverlay').style.display = 'flex';
}
function hideLoading() {
  document.getElementById('loadOverlay').style.display = 'none';
}

// ── Char counter for textarea ──
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('answerTa').addEventListener('input', function () {
    document.getElementById('charCt').textContent = this.value.length + ' chars';
  });
});

// ── Ctrl+Enter to submit ──
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') submitAnswer();
});

function capitalize(str) { return str ? str.charAt(0).toUpperCase() + str.slice(1) : ''; }

// ── Mini neural (sidebar logo) ──
function initMiniNeural(id, sz) {
  const canvas = document.getElementById(id); if (!canvas) return;
  const ctx = canvas.getContext('2d'), CX = sz / 2, CY = sz / 2, R = sz * 0.38;
  const nodes = Array.from({ length: 8 }, (_, i) => {
    const phi = Math.acos(-1 + (2 * i) / 8), theta = Math.sqrt(8 * Math.PI) * phi;
    return { bx: Math.cos(theta) * Math.sin(phi), by: Math.sin(theta) * Math.sin(phi), bz: Math.cos(phi), pulse: Math.random() * Math.PI * 2 };
  });
  const conns = []; for (let i = 0; i < 8; i++) for (let j = i + 1; j < 8; j++) {
    const dx = nodes[i].bx - nodes[j].bx, dy = nodes[i].by - nodes[j].by, dz = nodes[i].bz - nodes[j].bz;
    if (Math.sqrt(dx * dx + dy * dy + dz * dz) < 1.2) conns.push([i, j]);
  }
  let t = Math.random() * 10;
  function draw() {
    ctx.clearRect(0, 0, sz, sz);
    const rx = t * 0.4, ry = t * 0.6;
    function proj(x, y, z) {
      const y1 = y * Math.cos(rx) - z * Math.sin(rx), z1 = y * Math.sin(rx) + z * Math.cos(rx), x2 = x * Math.cos(ry) + z1 * Math.sin(ry);
      return { sx: CX + x2 * R, sy: CY + y1 * R };
    }
    for (const [i, j] of conns) {
      const a = proj(nodes[i].bx, nodes[i].by, nodes[i].bz), b = proj(nodes[j].bx, nodes[j].by, nodes[j].bz);
      ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy);
      ctx.strokeStyle = 'rgba(212,160,23,0.45)'; ctx.lineWidth = 0.6; ctx.stroke();
    }
    for (const n of nodes) {
      const p = proj(n.bx, n.by, n.bz), d = 0.5, pulse = 0.5 + 0.5 * Math.sin(t * 4 + n.pulse);
      ctx.beginPath(); ctx.arc(p.sx, p.sy, 1 + d * 1.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(245,200,66,${d * pulse})`; ctx.fill();
    }
    t += 0.012; requestAnimationFrame(draw);
  }
  draw();
}

function initLoadingNeural(canvasId) {
  const canvas = document.getElementById(canvasId); if (!canvas) return;
  const ctx = canvas.getContext('2d'), CX = 35, CY = 35, R = 26;
  const nodes = Array.from({ length: 12 }, (_, i) => {
    const phi = Math.acos(-1 + (2 * i) / 12), theta = Math.sqrt(12 * Math.PI) * phi;
    return { bx: Math.cos(theta) * Math.sin(phi), by: Math.sin(theta) * Math.sin(phi), bz: Math.cos(phi), pulse: Math.random() * Math.PI * 2 };
  });
  let t = 0;
  function draw() {
    ctx.clearRect(0, 0, 70, 70);
    const rx = t * 0.5, ry = t * 0.8;
    function proj(x, y, z) {
      const y1 = y * Math.cos(rx) - z * Math.sin(rx), z1 = y * Math.sin(rx) + z * Math.cos(rx), x2 = x * Math.cos(ry) + z1 * Math.sin(ry);
      return { sx: CX + x2 * R, sy: CY + y1 * R, sz: -x * Math.sin(ry) + z1 * Math.cos(ry) };
    }
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].bx - nodes[j].bx, dy = nodes[i].by - nodes[j].by, dz = nodes[i].bz - nodes[j].bz;
      if (Math.sqrt(dx * dx + dy * dy + dz * dz) < 1.0) {
        const a = proj(nodes[i].bx, nodes[i].by, nodes[i].bz), b = proj(nodes[j].bx, nodes[j].by, nodes[j].bz);
        ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy);
        ctx.strokeStyle = 'rgba(212,160,23,0.4)'; ctx.lineWidth = 0.8; ctx.stroke();
      }
    }
    for (const n of nodes) {
      const p = proj(n.bx, n.by, n.bz), d = (p.sz + 1) / 2, pulse = 0.5 + 0.5 * Math.sin(t * 5 + n.pulse);
      ctx.beginPath(); ctx.arc(p.sx, p.sy, 1 + d * 2, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(245,200,66,${d * pulse})`; ctx.fill();
    }
    t += 0.02; requestAnimationFrame(draw);
  }
  draw();
}
