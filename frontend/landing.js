/* landing.js — BEE landing page logic */

const API = window.location.port === '8000' ? '' : 'http://localhost:8000';

// ── Modal helpers ──
function openModal(id) {
  const el = document.getElementById(id);
  el.style.display = 'flex'; el.style.opacity = '0';
  requestAnimationFrame(() => { el.style.transition = 'opacity 0.25s'; el.style.opacity = '1'; });
}
function closeModal(id) {
  const el = document.getElementById(id);
  el.style.opacity = '0'; setTimeout(() => el.style.display = 'none', 250);
}
function bgClose(e, id) { if (e.target === e.currentTarget) closeModal(id); }

// ── Skills flow ──
async function startWithSkills() {
  const input = document.getElementById('skillsInput').value.trim();
  if (!input) { showWarn('skillWarn', 'skillWarnText', 'Please enter at least one skill.'); return; }

  const skills = input.split(',').map(s => s.trim()).filter(Boolean);
  const btn = document.getElementById('skillsStartBtn');
  btn.disabled = true; btn.textContent = 'Starting...';

  showLoading('Generating your interview...');
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90000);
    const res = await fetch(`${API}/api/start-with-skills`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skills }),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    const data = await res.json();
    if (!res.ok) {
      hideLoading();
      btn.disabled = false; btn.textContent = 'Start Interview →';
      const detail = data.detail;
      const msg = typeof detail === 'object' ? detail.message : detail;
      showWarn('skillWarn', 'skillWarnText', msg || 'Failed to start interview.');
      return;
    }
    // Store session info and redirect
    sessionStorage.setItem('bee_session_id', data.session_id);
    sessionStorage.setItem('bee_skills', JSON.stringify(data.skills));
    window.location.href = 'interview.html';
  } catch (e) {
    hideLoading();
    btn.disabled = false; btn.textContent = 'Start Interview →';
    if (e.name === 'AbortError') {
      showWarn('skillWarn', 'skillWarnText', 'Request timed out — HF model may be loading. Try again in 30s.');
    } else {
      showWarn('skillWarn', 'skillWarnText', 'Network error. Please try again.');
    }
  }
}

// Allow Enter key to submit
document.getElementById('skillsInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') startWithSkills();
});

// ── Resume flow ──
let selectedFile = null;
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  selectedFile = file;
  document.getElementById('fileDropIcon').className = 'fas fa-file-check';
  document.getElementById('fileDropText').textContent = file.name;
  const btn = document.getElementById('resumeStartBtn');
  btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = 'pointer';
}

async function startWithResume() {
  if (!selectedFile) return;
  const btn = document.getElementById('resumeStartBtn');
  btn.disabled = true; btn.textContent = 'Uploading...';
  showLoading('Processing resume...');

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const abortCtrl = new AbortController();
    const resumeTimeout = setTimeout(() => abortCtrl.abort(), 90000);
    const res = await fetch(`${API}/api/start-with-resume`, { method: 'POST', body: formData, signal: abortCtrl.signal });
    clearTimeout(resumeTimeout);
    const data = await res.json();
    if (!res.ok) {
      hideLoading();
      btn.disabled = false; btn.textContent = 'Start Interview →';
      const msg = typeof data.detail === 'string' ? data.detail : 'Failed to process resume.';
      showWarn('resumeWarn', 'resumeWarnText', msg);
      return;
    }
    sessionStorage.setItem('bee_session_id', data.session_id);
    sessionStorage.setItem('bee_skills', JSON.stringify(data.skills));
    window.location.href = 'interview.html';
  } catch (e) {
    hideLoading();
    btn.disabled = false; btn.textContent = 'Start Interview →';
    if (e.name === 'AbortError') {
      showWarn('resumeWarn', 'resumeWarnText', 'Request timed out — HF model may be loading. Try again in 30s.');
    } else {
      showWarn('resumeWarn', 'resumeWarnText', 'Network error. Please try again.');
    }
  }
}

function showWarn(warnId, textId, msg) {
  document.getElementById(textId).textContent = msg;
  document.getElementById(warnId).style.display = 'flex';
}

function showLoading(text) {
  document.getElementById('loadingText').textContent = text || 'Loading...';
  document.getElementById('globalLoading').style.display = 'flex';
  initLoadingNeural('loadCanvas');
}
function hideLoading() {
  document.getElementById('globalLoading').style.display = 'none';
}

// ── Typewriter BEE ──
const beeText = 'BEE';
const beeTitleEl = document.getElementById('beeTitleText');
const beeCursor = document.getElementById('beeCursor');
let typed = 0;
function typeWriter() {
  if (typed <= beeText.length) {
    beeTitleEl.textContent = beeText.slice(0, typed);
    typed++;
    setTimeout(typeWriter, typed === 1 ? 300 : 220);
  } else {
    setTimeout(() => { if (beeCursor) beeCursor.style.display = 'none'; }, 3000);
  }
}
setTimeout(typeWriter, 500);

// ── Speech Bubble ──
const quotes = [
  "god, you must be itching for this...",
  "good luck! ...you'll need it :)",
  "oh brave soul, let's begin",
  "your recruiter is watching. probably.",
  "just vibe.",
  "50% chance the model gives up midway... pls don't blame me.",
  "the algorithm judges you now",
  "even jarvis failed interviews once",
  "deep breaths. or don't. idk.",
  "15 questions. no escape.",
  "your LinkedIn says expert. prove it.",
  "nervous? i can tell.",
  "i've seen better... and worse.",
  "they are in the trees...",
  "are you fine?",
  "technically you could just guess",
  "what's the worst that could happen?",
  "buzzin' with confidence? ...sorry",
  "knowledge is power. or so they say.",
  "let's find out what you're made of :D",
  "what's the funny numba???",
];
let currentQuote = -1;
let bubbleTimer = null, typeTimer = null, titleClickCount = 0;
let autoQuoteTimer = null;
const bubble = document.getElementById('speechBubble');

function getRandomQuote() {
  let idx;
  do { idx = Math.floor(Math.random() * quotes.length); } while (idx === currentQuote);
  currentQuote = idx;
  return quotes[idx];
}

function typeIntoBubble(text) {
  clearTimeout(typeTimer);
  bubble.textContent = '';
  let i = 0;
  function step() {
    if (i <= text.length) { bubble.textContent = text.slice(0, i); i++; typeTimer = setTimeout(step, 38); }
  }
  step();
}

function showAutoBubble() {
  bubble.className = 'speech-bubble dir-right';
  bubble.classList.add('visible');
  typeIntoBubble(getRandomQuote());
  clearTimeout(bubbleTimer);
  bubbleTimer = setTimeout(() => bubble.classList.remove('visible'), 4200);
}

function resetAutoQuoteTimer() {
  clearTimeout(autoQuoteTimer);
  autoQuoteTimer = setTimeout(showAutoBubble, 7000);
}

// Start auto-quote timer on page load
resetAutoQuoteTimer();

// Reset timer only on meaningful interactions, NOT mousemove
['keydown', 'click', 'touchstart'].forEach(evt =>
  document.addEventListener(evt, resetAutoQuoteTimer, { passive: true })
);

function onBallClick() {
  clearTimeout(autoQuoteTimer);
  resetAutoQuoteTimer();
  bubble.className = 'speech-bubble dir-right';
  bubble.classList.add('visible');
  typeIntoBubble(getRandomQuote());
  clearTimeout(bubbleTimer);
  bubbleTimer = setTimeout(() => bubble.classList.remove('visible'), 4200);

  const anims = ['vibrate', 'shake', 'spin', 'glitch', 'vibrate', 'shake'];
  const anim = anims[titleClickCount % anims.length];
  beeTitle.classList.remove('shake', 'spin', 'vibrate', 'glitch');
  void beeTitle.offsetWidth;
  beeTitle.classList.add(anim);
  beeTitle.addEventListener('animationend', () => beeTitle.classList.remove(anim), { once: true });
  titleClickCount++;
}

const beeTitle = document.getElementById('beeTitle');
const titleWrap = document.getElementById('beeTitleWrap');
titleWrap.addEventListener('click', () => {
  const anims = ['vibrate', 'shake', 'spin', 'glitch', 'vibrate', 'shake'];
  const anim = anims[titleClickCount % anims.length];
  beeTitle.classList.remove('shake', 'spin', 'vibrate', 'glitch');
  void beeTitle.offsetWidth;
  beeTitle.classList.add(anim);
  beeTitle.addEventListener('animationend', () => beeTitle.classList.remove(anim), { once: true });
  titleClickCount++;
});

// ── Sparkles ──
(function () {
  const canvas = document.getElementById('sparkleCanvas');
  if (!canvas) return;
  const s1 = document.getElementById('s1');
  function resize() { canvas.width = s1.offsetWidth; canvas.height = s1.offsetHeight; }
  resize(); window.addEventListener('resize', resize);
  const ctx = canvas.getContext('2d');
  const sparks = [];
  function spawnSpark() {
    sparks.push({ x: Math.random() * canvas.width, y: Math.random() * canvas.height, size: 0.5 + Math.random() * 2.5, alpha: 0, maxAlpha: 0.15 + Math.random() * 0.35, life: 0, maxLife: 60 + Math.random() * 120 });
  }
  setInterval(spawnSpark, 180);
  function drawSparks() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = sparks.length - 1; i >= 0; i--) {
      const s = sparks[i]; s.life++;
      const halfLife = s.maxLife / 2;
      s.alpha = s.life < halfLife ? (s.life / halfLife) * s.maxAlpha : ((s.maxLife - s.life) / halfLife) * s.maxAlpha;
      if (s.life >= s.maxLife) { sparks.splice(i, 1); continue; }
      ctx.save(); ctx.globalAlpha = s.alpha; ctx.translate(s.x, s.y);
      const grd = ctx.createRadialGradient(0, 0, 0, 0, 0, s.size * 4);
      grd.addColorStop(0, 'rgba(245,200,66,1)'); grd.addColorStop(1, 'transparent');
      ctx.beginPath(); ctx.arc(0, 0, s.size * 4, 0, Math.PI * 2); ctx.fillStyle = grd; ctx.fill();
      ctx.beginPath(); ctx.arc(0, 0, s.size * 0.6, 0, Math.PI * 2); ctx.fillStyle = '#fff8e1'; ctx.fill();
      ctx.restore();
    }
    requestAnimationFrame(drawSparks);
  }
  drawSparks();
})();

// ── Cursor glow ──
(function () {
  const glow = document.getElementById('cursorGlow');
  const s1 = document.getElementById('s1');
  if (!glow || !s1) return;
  s1.addEventListener('mousemove', (e) => {
    const rect = s1.getBoundingClientRect();
    glow.style.left = (e.clientX - rect.left) + 'px';
    glow.style.top = (e.clientY - rect.top) + 'px';
    glow.style.opacity = '1';
  });
  s1.addEventListener('mouseleave', () => { glow.style.opacity = '0'; });
})();

// ── Init neural canvases ──
(function () {
  // Inline neural.js functions since we can't guarantee load order across pages
  // Main neural ball
  const canvas = document.getElementById('neuralCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = 200, H = 200, CX = 100, CY = 100, R = 72;
  const N = 24; let t = 0;
  const nodes = Array.from({ length: N }, (_, i) => {
    const phi = Math.acos(-1 + (2 * i) / N), theta = Math.sqrt(N * Math.PI) * phi;
    return { bx: Math.cos(theta) * Math.sin(phi), by: Math.sin(theta) * Math.sin(phi), bz: Math.cos(phi), pulse: Math.random() * Math.PI * 2 };
  });
  const conns = [];
  for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) {
    const dx = nodes[i].bx - nodes[j].bx, dy = nodes[i].by - nodes[j].by, dz = nodes[i].bz - nodes[j].bz;
    if (Math.sqrt(dx * dx + dy * dy + dz * dz) < 0.9) conns.push([i, j]);
  }
  function proj(x, y, z, rx, ry) {
    const y1 = y * Math.cos(rx) - z * Math.sin(rx), z1 = y * Math.sin(rx) + z * Math.cos(rx);
    const x2 = x * Math.cos(ry) + z1 * Math.sin(ry);
    return { sx: CX + x2 * R, sy: CY + y1 * R, sz: -x * Math.sin(ry) + z1 * Math.cos(ry) };
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    const rx = t * 0.28, ry = t * 0.46;
    for (const [i, j] of conns) {
      const a = proj(nodes[i].bx, nodes[i].by, nodes[i].bz, rx, ry);
      const b = proj(nodes[j].bx, nodes[j].by, nodes[j].bz, rx, ry);
      const d = (a.sz + b.sz) / 2, alpha = (d + 1) / 2 * 0.55;
      ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy);
      ctx.strokeStyle = `rgba(212,160,23,${alpha * 0.65})`; ctx.lineWidth = 0.9; ctx.stroke();
    }
    for (const n of nodes) {
      const p = proj(n.bx, n.by, n.bz, rx, ry);
      const depth = (p.sz + 1) / 2, pulse = 0.6 + 0.4 * Math.sin(t * 3 + n.pulse), alpha = depth * pulse;
      const sz = 1.5 + depth * 2.8;
      const grd = ctx.createRadialGradient(p.sx, p.sy, 0, p.sx, p.sy, sz * 3);
      grd.addColorStop(0, `rgba(212,160,23,${alpha * 0.5})`); grd.addColorStop(1, 'transparent');
      ctx.beginPath(); ctx.arc(p.sx, p.sy, sz * 3, 0, Math.PI * 2); ctx.fillStyle = grd; ctx.fill();
      ctx.beginPath(); ctx.arc(p.sx, p.sy, sz, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(245,200,66,${alpha})`; ctx.fill();
    }
    t += 0.007; requestAnimationFrame(draw);
  }
  draw();
})();

// Mini neural for loading canvas
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