const API_BASE = window.location.origin;

// --- State Management ---
const state = {
  resumeFile: null,
  jdFile: null,
  analysis: null,
  currentSkillQuestions: [],
  currentQuestionIndex: 0,
  evaluations: {}, // skill -> array of evaluation results
  gapAnalysis: null
};

// --- DOM Elements ---
const els = {
  // Upload
  resumeFile: document.getElementById('resumeFile'),
  resumeFileName: document.getElementById('resumeFileName'),
  resumeFileInfo: document.getElementById('resumeFileInfo'),
  resumeRemove: document.getElementById('resumeRemove'),
  toggleResumeText: document.getElementById('toggleResumeText'),
  resumeText: document.getElementById('resumeText'),

  jdFile: document.getElementById('jdFile'),
  jdFileName: document.getElementById('jdFileName'),
  jdFileInfo: document.getElementById('jdFileInfo'),
  jdRemove: document.getElementById('jdRemove'),
  toggleJdText: document.getElementById('toggleJdText'),
  jdText: document.getElementById('jdText'),

  analyzeBtn: document.getElementById('analyzeBtn'),
  analyzeBtnText: document.getElementById('analyzeBtnText'),
  analyzeBtnSpinner: document.getElementById('analyzeBtnSpinner'),
  progressBar: document.getElementById('progressBar'),
  progressFill: document.getElementById('progressFill'),
  progressLabel: document.getElementById('progressLabel'),

  // Sections
  sections: {
    upload: document.getElementById('upload'),
    skills: document.getElementById('skills'),
    interview: document.getElementById('interview'),
    gaps: document.getElementById('gaps'),
    learning: document.getElementById('learning')
  },
  navLinks: document.querySelectorAll('.navbar__link')
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  setupUploadListeners();
  setupNavigation();
  setupInterviewListeners();
  setupGapAndLearningListeners();
});

// --- Toast Notifications ---
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// --- Navigation ---
function setupNavigation() {
  els.navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = link.getAttribute('href').substring(1);
      showSection(targetId);
    });
  });

  // Mobile nav toggle
  const navToggle = document.getElementById('navToggle');
  const navLinksContainer = document.querySelector('.navbar__links');
  if (navToggle && navLinksContainer) {
    navToggle.addEventListener('click', () => {
      navLinksContainer.classList.toggle('open');
    });
  }
}

function showSection(id) {
  Object.values(els.sections).forEach(sec => sec?.classList.add('hidden'));
  if (els.sections[id]) els.sections[id].classList.remove('hidden');

  els.navLinks.forEach(l => l.classList.remove('active'));
  const activeLink = document.querySelector(`.navbar__link[href="#${id}"]`);
  if (activeLink) activeLink.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// --- Text Extraction Utilities ---
function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve();
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

async function extractTextFromFile(file) {
  if (!file) return "";
  const name = file.name.toLowerCase();

  try {
    if (name.endsWith('.pdf')) {
      await loadScript('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js');
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
      const arrayBuffer = await file.arrayBuffer();
      const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      let text = '';
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();
        text += content.items.map(item => item.str).join(' ') + '\n';
      }
      return text;
    } else if (name.endsWith('.docx')) {
      await loadScript('https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.4.21/mammoth.browser.min.js');
      const arrayBuffer = await file.arrayBuffer();
      const result = await window.mammoth.extractRawText({ arrayBuffer });
      return result.value;
    } else {
      return await file.text();
    }
  } catch (err) {
    console.error(`Failed to extract text from ${file.name}:`, err);
    throw new Error(`Could not parse ${file.name}. Please paste the text instead.`);
  }
}

// --- Upload Section Logic ---
function setupUploadListeners() {
  // Resume handlers
  els.resumeFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      state.resumeFile = e.target.files[0];
      els.resumeFileName.textContent = state.resumeFile.name;
      els.resumeFileInfo.classList.remove('hidden');
      els.resumeText.classList.add('hidden');
      els.resumeText.value = '';
    }
    checkAnalyzeReady();
  });
  els.resumeRemove.addEventListener('click', () => {
    state.resumeFile = null;
    els.resumeFile.value = '';
    els.resumeFileInfo.classList.add('hidden');
    checkAnalyzeReady();
  });
  els.toggleResumeText.addEventListener('click', () => {
    els.resumeText.classList.toggle('hidden');
    if (!els.resumeText.classList.contains('hidden')) els.resumeText.focus();
  });
  els.resumeText.addEventListener('input', checkAnalyzeReady);

  // JD handlers
  els.jdFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      state.jdFile = e.target.files[0];
      els.jdFileName.textContent = state.jdFile.name;
      els.jdFileInfo.classList.remove('hidden');
      els.jdText.classList.add('hidden');
      els.jdText.value = '';
    }
    checkAnalyzeReady();
  });
  els.jdRemove.addEventListener('click', () => {
    state.jdFile = null;
    els.jdFile.value = '';
    els.jdFileInfo.classList.add('hidden');
    checkAnalyzeReady();
  });
  els.toggleJdText.addEventListener('click', () => {
    els.jdText.classList.toggle('hidden');
    if (!els.jdText.classList.contains('hidden')) els.jdText.focus();
  });
  els.jdText.addEventListener('input', checkAnalyzeReady);

  // Analyze button
  els.analyzeBtn.addEventListener('click', handleAnalyze);
}

function checkAnalyzeReady() {
  const hasResume = state.resumeFile || els.resumeText.value.trim().length > 20;
  const hasJd = state.jdFile || els.jdText.value.trim().length > 20;
  els.analyzeBtn.disabled = !(hasResume && hasJd);
}

async function handleAnalyze() {
  setLoadingState(true, 'Reading files...');

  try {
    // 1. Get text
    const resumeStr = state.resumeFile ? await extractTextFromFile(state.resumeFile) : els.resumeText.value.trim();
    const jdStr = state.jdFile ? await extractTextFromFile(state.jdFile) : els.jdText.value.trim();

    if (resumeStr.length < 20 || jdStr.length < 20) {
      throw new Error("Extracted text is too short. Please provide valid documents.");
    }

    setLoadingState(true, 'Analyzing skills...');

    // 2. Call API
    const response = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_description: jdStr, resume: resumeStr })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error: ${response.status}`);
    }

    const data = await response.json();
    state.analysis = data;

    // 3. Render Results
    renderSkillsSection(data);
    showToast('Analysis complete!', 'success');
    showSection('skills');

  } catch (error) {
    console.error(error);
    showToast(error.message, 'error');
  } finally {
    setLoadingState(false);
  }
}

function setLoadingState(isLoading, message = '') {
  els.analyzeBtn.disabled = isLoading;
  if (isLoading) {
    els.analyzeBtnText.classList.add('hidden');
    els.analyzeBtnSpinner.classList.remove('hidden');
    els.progressBar.classList.remove('hidden');
    els.progressLabel.textContent = message;
    els.progressFill.style.width = '60%'; // Fake progress
  } else {
    els.analyzeBtnText.classList.remove('hidden');
    els.analyzeBtnSpinner.classList.add('hidden');
    els.progressBar.classList.add('hidden');
    els.progressFill.style.width = '0%';
  }
}

// --- Skills Section Logic ---
function renderSkillsSection(data) {
  // Score Ring
  const scoreVal = Math.round(data.match_percentage);
  document.getElementById('scoreValue').textContent = `${scoreVal}%`;
  const offset = 327 - (327 * scoreVal) / 100;
  document.getElementById('scoreRingFill').style.strokeDashoffset = offset;

  // Clouds
  renderChips('jdSkillsCloud', data.jd_skills, 'chip--jd');
  renderChips('resumeSkillsCloud', data.resume_skills, 'chip--resume');
  renderChips('missingSkillsCloud', data.missing_skills, 'chip--missing');
  renderChips('extraSkillsCloud', data.extra_skills || [], 'chip--extra');

  // Table with evidence
  const tbody = document.getElementById('skillTableBody');
  tbody.innerHTML = '';
  data.matched_skills.forEach(match => {
    const tr = document.createElement('tr');
    const statusClass = match.found_in_resume ? 'status-found' : 'status-missing';
    const statusText = match.found_in_resume ? 'Found' : 'Missing';

    // Proficiency badge with color
    const profLevel = match.proficiency_estimate || 'unknown';
    const profScore = match.proficiency_score || 0;
    const profBadgeClass = `badge badge--prof-${profLevel}`;
    const profText = `${profLevel} (${profScore})`;

    // Evidence source tags
    const evidenceSources = match.evidence_sources || [];
    let evidenceHtml = '';
    if (evidenceSources.length > 0) {
      evidenceHtml = evidenceSources.map(src => {
        let tagClass = 'evidence-tag';
        if (src.startsWith('Skills')) tagClass += ' evidence-tag--skills';
        else if (src.startsWith('Project')) tagClass += ' evidence-tag--project';
        else if (src.startsWith('Cert')) tagClass += ' evidence-tag--cert';
        else if (src.startsWith('Exp')) tagClass += ' evidence-tag--exp';
        else if (src.startsWith('Achievement')) tagClass += ' evidence-tag--achievement';
        return `<span class="${tagClass}">${src}</span>`;
      }).join(' ');
    } else {
      evidenceHtml = '<span class="evidence-tag evidence-tag--none">—</span>';
    }

    // Match method
    const matchVia = match.matched_via || '';
    let matchBadge = '';
    if (matchVia) {
      matchBadge = `<span class="badge badge--match-${matchVia}">${matchVia}</span>`;
    } else {
      matchBadge = '<span class="badge" style="opacity:0.3">—</span>';
    }

    tr.innerHTML = `
      <td><strong>${match.skill}</strong></td>
      <td class="${statusClass}">${statusText}</td>
      <td><span class="${profBadgeClass}">${profText}</span></td>
      <td class="evidence-cell">${evidenceHtml}</td>
      <td>${matchBadge}</td>
    `;
    tbody.appendChild(tr);
  });

  // Populate Interview Select
  const skillSelect = document.getElementById('skillSelect');
  skillSelect.innerHTML = '';
  data.jd_skills.forEach(skill => {
    const opt = document.createElement('option');
    opt.value = skill;
    opt.textContent = skill;
    skillSelect.appendChild(opt);
  });

  document.getElementById('startInterviewBtn').addEventListener('click', () => showSection('interview'));
}

function renderChips(containerId, items, chipClass) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';
  if (!items || items.length === 0) {
    container.innerHTML = '<span class="chip" style="opacity:0.5">None</span>';
    return;
  }
  items.forEach(item => {
    const span = document.createElement('span');
    span.className = `chip ${chipClass}`;
    span.textContent = item;
    container.appendChild(span);
  });
}

// --- Interview Section Logic ---
function setupInterviewListeners() {
  document.getElementById('generateQuestionsBtn').addEventListener('click', handleGenerateQuestions);
  document.getElementById('submitAnswerBtn').addEventListener('click', handleSubmitAnswer);
  document.getElementById('showHintsBtn').addEventListener('click', () => {
    document.getElementById('hintsBox').classList.toggle('hidden');
  });
  document.getElementById('nextQuestionBtn').addEventListener('click', () => navigateQuestion(1));
  document.getElementById('prevQuestionBtn').addEventListener('click', () => navigateQuestion(-1));
  document.getElementById('runGapBtn').addEventListener('click', () => showSection('gaps'));
}

async function handleGenerateQuestions() {
  const skill = document.getElementById('skillSelect').value;
  const difficulty = document.getElementById('difficultySelect').value;
  const btn = document.getElementById('generateQuestionsBtn');

  if (!skill) return showToast('Please select a skill', 'error');

  btn.disabled = true;
  btn.textContent = 'Generating...';

  try {
    const response = await fetch(`${API_BASE}/generate-questions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        skill: skill,
        difficulty: difficulty,
        count: 3,
        context: els.jdText.value.substring(0, 500) || "Job interview"
      })
    });

    if (!response.ok) throw new Error('Failed to generate questions');
    const data = await response.json();

    state.currentSkillQuestions = data.questions;
    state.currentQuestionIndex = 0;

    document.getElementById('interviewPlaceholder').classList.add('hidden');
    document.getElementById('questionCard').classList.remove('hidden');
    document.getElementById('questionNav').classList.remove('hidden');
    document.getElementById('evalCard').classList.add('hidden');

    renderCurrentQuestion();
    showToast('Questions generated!', 'success');

  } catch (error) {
    console.error(error);
    showToast(error.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate Questions';
  }
}

function renderCurrentQuestion() {
  const q = state.currentSkillQuestions[state.currentQuestionIndex];
  if (!q) return;

  document.getElementById('questionBadge').textContent = `Q${state.currentQuestionIndex + 1}`;
  document.getElementById('difficultyBadge').textContent = q.difficulty;
  document.getElementById('skillBadge').textContent = q.skill;
  document.getElementById('questionText').textContent = q.question;

  const hintsList = document.getElementById('hintsList');
  hintsList.innerHTML = '';
  if (q.expected_answer_points && q.expected_answer_points.length > 0) {
    q.expected_answer_points.forEach(pt => {
      const li = document.createElement('li');
      li.textContent = pt;
      hintsList.appendChild(li);
    });
  } else {
    hintsList.innerHTML = '<li>No specific hints available.</li>';
  }

  document.getElementById('hintsBox').classList.add('hidden');
  document.getElementById('answerInput').value = '';
  document.getElementById('evalCard').classList.add('hidden');

  // Update nav buttons
  document.getElementById('questionCounter').textContent = `${state.currentQuestionIndex + 1} / ${state.currentSkillQuestions.length}`;
  document.getElementById('prevQuestionBtn').disabled = state.currentQuestionIndex === 0;
  document.getElementById('nextQuestionBtn').disabled = state.currentQuestionIndex === state.currentSkillQuestions.length - 1;
}

function navigateQuestion(dir) {
  state.currentQuestionIndex += dir;
  renderCurrentQuestion();
}

async function handleSubmitAnswer() {
  const answer = document.getElementById('answerInput').value.trim();
  if (answer.length < 10) return showToast('Please provide a longer answer', 'error');

  const q = state.currentSkillQuestions[state.currentQuestionIndex];
  const btn = document.getElementById('submitAnswerBtn');
  btn.disabled = true;
  btn.textContent = 'Evaluating...';

  try {
    const response = await fetch(`${API_BASE}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: q.question,
        answer: answer,
        skill: q.skill,
        difficulty: q.difficulty
      })
    });

    if (!response.ok) throw new Error('Evaluation failed');
    const data = await response.json();

    // Save evaluation state
    if (!state.evaluations[q.skill]) state.evaluations[q.skill] = [];
    state.evaluations[q.skill].push(data.evaluation.final_score);

    renderEvaluation(data);

    // Enable Gap Analysis button if we have at least one evaluation
    document.getElementById('runGapBtn').classList.remove('hidden');

  } catch (error) {
    console.error(error);
    showToast(error.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Submit Answer ↗';
  }
}

function renderEvaluation(data) {
  const evalCard = document.getElementById('evalCard');
  evalCard.classList.remove('hidden');

  const res = data.evaluation;
  document.getElementById('evalFinalScore').textContent = `${res.final_score} / 10`;

  const setMetric = (id, val) => {
    document.getElementById(`${id}Val`).textContent = val;
    setTimeout(() => {
      document.getElementById(id).style.width = `${(val / 10) * 100}%`;
    }, 100);
  };

  setMetric('evalConceptual', res.conceptual_understanding);
  setMetric('evalPractical', res.practical_knowledge);
  setMetric('evalClarity', res.clarity);
  setMetric('evalConfidence', res.confidence);

  document.getElementById('evalFeedbackText').textContent = res.feedback;
  document.getElementById('evalCorrectText').textContent = res.correct_answer;
  document.getElementById('evalNextDiff').textContent = data.next_difficulty;

  evalCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// --- Gap Analysis & Learning Plan Logic ---
function setupGapAndLearningListeners() {
  document.getElementById('runGapBtn').addEventListener('click', handleGapAnalysis);
  document.getElementById('genLearningBtn').addEventListener('click', handleLearningPlan);
}

async function handleGapAnalysis() {
  if (!state.analysis) return showToast('Analysis data missing', 'error');

  // Calculate average scores per skill from evaluations
  const scores = {};
  for (const [skill, evalArray] of Object.entries(state.evaluations)) {
    if (evalArray.length > 0) {
      const sum = evalArray.reduce((a, b) => a + b, 0);
      scores[skill] = parseFloat((sum / evalArray.length).toFixed(2));
    }
  }

  // For skills not evaluated, assign 0
  state.analysis.jd_skills.forEach(skill => {
    if (scores[skill] === undefined) scores[skill] = 0.0;
  });

  const btn = document.getElementById('runGapBtn');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.textContent = 'Running Analysis...';

  try {
    const response = await fetch(`${API_BASE}/gap-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        required_skills: state.analysis.jd_skills,
        scores: scores
      })
    });

    if (!response.ok) throw new Error('Gap analysis failed');
    const data = await response.json();
    state.gapAnalysis = data;

    renderGapAnalysis(data);
    showSection('gaps');
    showToast('Gap analysis generated', 'success');

  } catch (error) {
    console.error(error);
    showToast(error.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

function renderGapAnalysis(data) {
  document.getElementById('readinessValue').textContent = `${data.overall_readiness}%`;
  setTimeout(() => {
    document.getElementById('readinessFill').style.width = `${data.overall_readiness}%`;
  }, 200);

  document.getElementById('highCount').textContent = data.high_priority_count;
  document.getElementById('mediumCount').textContent = data.medium_priority_count;
  document.getElementById('lowCount').textContent = data.low_priority_count;

  const grid = document.getElementById('gapGrid');
  grid.innerHTML = '';

  data.gaps.forEach(gap => {
    const card = document.createElement('div');
    card.className = `gap-card gap-card--${gap.priority}`;
    card.innerHTML = `
      <div class="gap-card__header">
        <span class="gap-card__skill">${gap.skill}</span>
        <span class="badge ${gap.priority === 'HIGH' ? 'badge--difficulty' : 'badge--skill'}">${gap.priority}</span>
      </div>
      <div class="gap-card__score">Current Score: <strong>${gap.score}/10</strong></div>
      <p class="gap-card__rec" style="margin-top:.8rem">${gap.recommendation}</p>
    `;
    grid.appendChild(card);
  });
}

async function handleLearningPlan() {
  if (!state.gapAnalysis) return showToast('Please run gap analysis first', 'error');

  const hours = parseFloat(document.getElementById('learnHours').value) || 2;
  const weeks = parseInt(document.getElementById('learnWeeks').value) || 8;

  const btn = document.getElementById('genLearningBtn');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.textContent = 'Creating Roadmap...';

  try {
    const response = await fetch(`${API_BASE}/learning-plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        skill_gaps: state.gapAnalysis.gaps,
        available_hours_per_day: hours,
        target_weeks: weeks
      })
    });

    if (!response.ok) throw new Error('Learning plan generation failed');
    const data = await response.json();

    renderLearningPlan(data);
    showSection('learning');
    showToast('Learning roadmap ready!', 'success');

  } catch (error) {
    console.error(error);
    showToast(error.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

function renderLearningPlan(data) {
  document.getElementById('planSummary').classList.remove('hidden');
  document.getElementById('planTotalDays').textContent = (data.total_duration_weeks || 0) * 7;
  document.getElementById('planHours').textContent = data.daily_hours || 0;
  document.getElementById('planSkillsCount').textContent = (data.plans || []).length;
  document.getElementById('planSummaryText').textContent = data.summary || '';

  const container = document.getElementById('learningPlans');
  container.innerHTML = '';

  const plans = data.plans || [];
  plans.forEach(plan => {
    if (!plan.topics || plan.topics.length === 0) return;

    const planEl = document.createElement('div');
    planEl.className = 'skill-plan';

    let topicsHtml = '';
    plan.topics.forEach(topic => {
      let subSkillsHtml = '';
      if (topic.sub_skills && topic.sub_skills.length > 0) {
        subSkillsHtml = `<div class="topic-card__subskills" style="font-size: 0.85em; color: var(--text-muted); margin-bottom: 8px;"><b>Sub-skills:</b> ${topic.sub_skills.join(', ')}</div>`;
      }

      let resourcesHtml = '';
      if (topic.resources) {
        topic.resources.forEach(res => {
          let estHours = (res.estimated_hours !== undefined && res.estimated_hours !== null) ? ` (${res.estimated_hours}h)` : '';
          resourcesHtml += `<a href="${res.url || '#'}" target="_blank" class="resource-link">📄 ${res.title} (${res.type})${estHours}</a>`;
        });
      }

      let milestonesHtml = '';
      if (topic.milestones && topic.milestones.length > 0) {
        topic.milestones.forEach(m => {
          milestonesHtml += `<li>${m}</li>`;
        });
      }

      topicsHtml += `
        <div class="topic-card">
          <div class="topic-card__header">
            <span class="topic-card__name">${topic.topic}</span>
          </div>
          ${subSkillsHtml}
          <div class="topic-card__resources">${resourcesHtml}</div>
          <ul class="topic-card__milestones" style="margin-top: 8px; font-size: 0.9em; padding-left: 20px;">${milestonesHtml}</ul>
        </div>
      `;
    });

    let adjacentSkillsHtml = '';
    if (plan.adjacent_skills && plan.adjacent_skills.length > 0) {
      adjacentSkillsHtml = `<div class="skill-plan__adjacent" style="margin-top: 12px; font-size: 0.9em; padding: 12px; background: rgba(0,0,0,0.05); border-radius: 8px;">
        <strong>Adjacent Skills:</strong> ${plan.adjacent_skills.join(', ')}
      </div>`;
    }

    let coversSkillsHtml = '';
    if (plan.covers_skills && plan.covers_skills.length > 0) {
      coversSkillsHtml = `<div style="font-size: 0.85em; color: var(--text-muted); margin-top: 4px;"><b>Covers:</b> ${plan.covers_skills.join(', ')}</div>`;
    }

    planEl.innerHTML = `
      <div class="skill-plan__header">
        <span class="skill-plan__name">${plan.skill} <span style="opacity:0.6;font-size:0.8em;font-weight:normal;margin-left:8px">Target: ${plan.target_score}/10</span></span>
        ${coversSkillsHtml}
      </div>
      <div class="skill-plan__topics">
        ${topicsHtml}
      </div>
      ${adjacentSkillsHtml}
    `;
    container.appendChild(planEl);
  });

  // ── Day-wise Schedule ──────────────────────────────────────────────────
  const daySection = document.createElement('div');
  daySection.style.marginTop = '4rem';
  daySection.style.padding = '2.5rem';
  daySection.style.background = 'rgba(79, 70, 229, 0.05)';
  daySection.style.borderRadius = '20px';
  daySection.style.border = '1px solid rgba(79, 70, 229, 0.15)';
  daySection.style.boxShadow = '0 10px 40px rgba(0,0,0,0.2)';

  const dayHeader = document.createElement('h3');
  dayHeader.innerHTML = '📅 <span style="margin-left:10px">Step-by-Step Daily Roadmap</span>';
  dayHeader.style.marginBottom = '2rem';
  dayHeader.style.fontSize = '1.5rem';
  dayHeader.style.color = '#fff';
  daySection.appendChild(dayHeader);

  // ✅ FIX: show a friendly empty state when backend returns no schedule
  if (!data.day_schedule || data.day_schedule.length === 0) {
    const empty = document.createElement('p');
    empty.textContent = 'No daily schedule could be generated. Try increasing your hours per day or target weeks.';
    empty.style.color = 'var(--text-muted)';
    empty.style.fontSize = '0.95rem';
    daySection.appendChild(empty);
    container.appendChild(daySection);
    return;
  }

  // ✅ FIX: group items by day so carry-over topics on the same day
  //         are merged into one row instead of showing "Day 3" twice.
  const grouped = {};
  data.day_schedule.forEach(item => {
    if (!grouped[item.day]) grouped[item.day] = [];
    grouped[item.day].push(item);
  });

  const dayList = document.createElement('div');
  dayList.style.display = 'flex';
  dayList.style.flexDirection = 'column';
  dayList.style.gap = '0.75rem';

  Object.entries(grouped).forEach(([day, items]) => {
    const itemEl = document.createElement('div');
    itemEl.style.display = 'flex';
    itemEl.style.alignItems = 'center';
    itemEl.style.padding = '1.2rem 1.5rem';
    itemEl.style.background = 'rgba(0, 0, 0, 0.3)';
    itemEl.style.borderRadius = '12px';
    itemEl.style.border = '1px solid rgba(255, 255, 255, 0.05)';
    itemEl.style.transition = 'all 0.3s ease';

    // Build topic string — join multiple topics on the same day with " + "
    const topicsStr = items
      .map(i => `${i.topic} <strong>(${i.hours}h)</strong>`)
      .join(' <span style="opacity:0.4;margin:0 0.4rem">+</span> ');

    // Total hours for this day
    const totalHours = items.reduce((sum, i) => sum + i.hours, 0);

    itemEl.innerHTML = `
      <div style="min-width: 80px; font-weight: 800; color: var(--indigo-light); font-size: 1.1rem;">Day ${day}</div>
      <div style="width: 2px; height: 24px; background: rgba(79, 70, 229, 0.3); margin: 0 1.5rem; flex-shrink:0;"></div>
      <div style="flex: 1; font-weight: 500; font-size: 1rem; color: #fff;">${topicsStr}</div>
      <div style="font-size: 0.85rem; font-weight: 600; color: var(--muted); background: rgba(255,255,255,0.05); padding: 0.3rem 0.8rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); white-space:nowrap; margin-left:1rem;">${Math.round(totalHours * 10) / 10}h total</div>
    `;
    dayList.appendChild(itemEl);
  });

  daySection.appendChild(dayList);
  container.appendChild(daySection);
}