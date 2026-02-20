/* results.js — BEE results page logic */

const API = window.location.port === '8000' ? '' : 'http://localhost:8000';

window.addEventListener('DOMContentLoaded', () => {
  const raw = sessionStorage.getItem('bee_results');
  const sessionId = sessionStorage.getItem('bee_session_id');

  if (!raw) {
    // No results found, go home
    window.location.href = 'index.html';
    return;
  }

  const results = JSON.parse(raw);
  initMiniNeural('logoCanvas2', 30);
  renderResults(results);

  // Animate score ring after short delay
  setTimeout(() => animateScore(results.percentage || 0), 300);

  // Store session id for restart
  window._sessionId = sessionId;
});

function renderResults(r) {
  const pct = r.percentage ?? 0;
  const verdict = (r.verdict || 'POOR').toLowerCase();

  // Score display
  document.getElementById('scorePct').textContent = pct + '%';
  const pill = document.getElementById('verdictPill');
  pill.textContent = (r.verdict || 'POOR');
  pill.className = 'verdict-pill ' + verdict;

  // Section bars
  const ss = r.section_scores || {};
  setSection('theory', ss.theory);
  setSection('aptitude', ss.aptitude);
  setSection('coding', ss.coding);
  setSection('hr', ss.hr);

  // Weak areas
  const weakList = document.getElementById('weakAreasList');
  weakList.innerHTML = '';
  if (r.weak_areas && r.weak_areas.length > 0) {
    r.weak_areas.forEach(w => {
      const el = document.createElement('div');
      el.className = 'weak-item';
      el.innerHTML = `<span class="weak-name">${w.topic}</span>`;
      weakList.appendChild(el);
    });
  } else {
    weakList.innerHTML = '<p style="color:var(--text2);font-size:0.82rem;">No major weak areas detected. Great performance!</p>';
  }

  // Suggestions
  const suggList = document.getElementById('suggestionsList');
  suggList.innerHTML = '';
  (r.improvement_suggestions || []).forEach(s => {
    const el = document.createElement('div');
    el.className = 'suggestion-item';
    el.innerHTML = `<i class="fas fa-chevron-right"></i>${s}`;
    suggList.appendChild(el);
  });

  // Resources
  const resList = document.getElementById('resourcesList');
  resList.innerHTML = '';
  if (r.learning_resources && r.learning_resources.length > 0) {
    r.learning_resources.forEach(url => {
      const el = document.createElement('a');
      el.className = 'resource-link';
      el.href = url;
      el.target = '_blank';
      el.rel = 'noopener';
      const domain = url.replace('https://', '').replace('http://', '').split('/')[0];
      el.innerHTML = `<i class="fas fa-external-link-alt"></i><span>${domain}</span>`;
      resList.appendChild(el);
    });
  } else {
    document.getElementById('resourcesSection').style.display = 'none';
  }

  // Review cards
  const reviewList = document.getElementById('reviewList');
  reviewList.innerHTML = '';
  (r.review || []).forEach(item => {
    const scoreClass = item.score >= 70 ? 'pass' : item.score >= 40 ? 'warn' : 'fail';
    const iconClass = scoreClass === 'pass' ? 'fa-check-circle' : scoreClass === 'warn' ? 'fa-minus-circle' : 'fa-times-circle';

    const card = document.createElement('div');
    card.className = `review-card ${scoreClass}`;
    card.innerHTML = `
      <div class="review-top">
        <span class="review-meta">Q${item.index} · ${capitalize(item.type)} · ${capitalize(item.difficulty)}</span>
        <i class="fas ${iconClass} review-icon ${scoreClass}"></i>
      </div>
      <div class="review-q">${escHtml(item.question)}</div>
      <div class="review-a">${escHtml(item.answer.slice(0, 200))}${item.answer.length > 200 ? '...' : ''}</div>
      <div class="review-fb"><i class="fas fa-lightbulb"></i>${escHtml(item.feedback)}</div>
    `;
    reviewList.appendChild(card);
  });
}

function setSection(name, data) {
  if (!data) return;
  const pct = data.percentage ?? 0;
  document.getElementById(`${name}Pct`).textContent = pct + '%';
  document.getElementById(`${name}Bar`).style.width = pct + '%';
}

function animateScore(pct) {
  const ring = document.getElementById('ringFill');
  const circumference = 2 * Math.PI * 50; // r=50 → exact circumference ≈ 314.159
  const offset = circumference - (circumference * pct) / 100;
  ring.style.strokeDashoffset = offset;
}

async function restartInterview() {
  const sessionId = window._sessionId;
  if (!sessionId) { window.location.href = 'index.html'; return; }

  try {
    const res = await fetch(`${API}/api/restart/${sessionId}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) { window.location.href = 'index.html'; return; }
    sessionStorage.setItem('bee_session_id', data.session_id);
    sessionStorage.setItem('bee_skills', JSON.stringify(data.skills));
    // Only clear results after confirming new session data is stored
    sessionStorage.removeItem('bee_results');
    window.location.href = 'interview.html';
  } catch (e) {
    window.location.href = 'index.html';
  }
}

function capitalize(str) { return str ? str.charAt(0).toUpperCase() + str.slice(1) : ''; }

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Mini neural for logo
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
