let currentStudentData = null;
let charts = {};
let currentSectionData = null;
let sectionCharts = {};

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadStudentsList();
    loadLeaderboard();
    loadBatchAnalytics();
    updateStudentCount();
    loadCourses();
    loadAssignmentsFilter();
});

function setupEventListeners() {
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => switchView(btn.getAttribute('data-view')));
    });
    
    const dashboardSearchBtn = document.getElementById('searchBtnDashboard');
    const dashboardSearchInput = document.getElementById('searchRollInput');
    if (dashboardSearchBtn) dashboardSearchBtn.addEventListener('click', () => loadStudentData());
    if (dashboardSearchInput) dashboardSearchInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') loadStudentData(); });
    
    const topSearchBtn = document.getElementById('searchBtn');
    const topSearchInput = document.getElementById('searchRoll');
    if (topSearchBtn) {
        topSearchBtn.addEventListener('click', () => {
            const roll = topSearchInput.value.trim();
            if (dashboardSearchInput) dashboardSearchInput.value = roll;
            loadStudentData();
        });
    }
    if (topSearchInput) {
        topSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const roll = topSearchInput.value.trim();
                if (dashboardSearchInput) dashboardSearchInput.value = roll;
                loadStudentData();
            }
        });
    }
    
    document.getElementById('addStudentBtn')?.addEventListener('click', () => openModal('addStudentModal'));
    document.getElementById('uploadFileBtn')?.addEventListener('click', () => openModal('uploadModal'));
    document.getElementById('exportDataBtn')?.addEventListener('click', () => exportData());
    document.getElementById('confirmUpload')?.addEventListener('click', () => uploadFile());
    document.getElementById('loadSectionBtn')?.addEventListener('click', () => loadSectionDashboard());
    document.getElementById('assignStudentBtn')?.addEventListener('click', () => openAssignModal());
    document.getElementById('viewAssignmentsBtn')?.addEventListener('click', () => openViewAssignmentsModal());
    document.getElementById('confirmAssignBtn')?.addEventListener('click', () => assignStudentToSection());
    
    document.getElementById('addStudentForm')?.addEventListener('submit', (e) => { e.preventDefault(); addStudent(); });
    document.getElementById('leaderboardFilter')?.addEventListener('change', () => loadLeaderboard());
    document.getElementById('studentSearch')?.addEventListener('input', () => filterStudents());
    document.getElementById('viewAssignmentsFilter')?.addEventListener('change', () => loadAllAssignments());
    
    document.querySelectorAll('.close').forEach(btn => btn.addEventListener('click', () => closeModal()));
    window.addEventListener('click', (e) => { if (e.target.classList.contains('modal')) closeModal(); });
    
    // IntegrityAI Button - Open new page (same tab)
    const integrityAiBtn = document.getElementById('integrityAiBtn');
    const integrityAiLink = document.getElementById('integrityAiLink');
    if (integrityAiBtn && integrityAiLink) {
        integrityAiBtn.addEventListener('click', (e) => {
            const roll = document.getElementById('searchRollInput')?.value.trim();
            if (!roll) {
                e.preventDefault();
                showToast('Please search for a student first', 'warning');
            } else {
                integrityAiLink.href = `/integrity-ai?roll=${encodeURIComponent(roll)}`;
            }
        });
    }
}

function switchView(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`${view}View`)?.classList.add('active');
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-view') === view) btn.classList.add('active');
    });
    if (view === 'students') loadStudentsList();
    else if (view === 'leaderboard') loadLeaderboard();
    else if (view === 'analytics') loadBatchAnalytics();
}

async function loadStudentData() {
    const roll = document.getElementById('searchRollInput')?.value.trim();
    if (!roll) { showToast('Enter a roll number', 'warning'); return; }
    showLoading();
    try {
        const response = await fetch(`/api/student/${encodeURIComponent(roll)}`);
        if (!response.ok) { if (response.status === 404) showToast('Student not found!', 'error'); showEmptyDashboard(); throw new Error(); }
        const data = await response.json();
        currentStudentData = data;
        displayStudentDetails(data);
    } catch (error) { showToast('Error loading student data', 'error'); showEmptyDashboard(); }
    finally { hideLoading(); }
}

function showEmptyDashboard() {
    const studentInfoCard = document.getElementById('studentInfoCard');
    if (studentInfoCard) studentInfoCard.innerHTML = `<div class="empty-state"><i class="fas fa-code"></i><h3>No Student Selected</h3><p>Enter a roll number above to view performance analytics</p></div>`;
    document.getElementById('statsPanel').style.display = 'none';
    document.getElementById('emptyRightPanel').style.display = 'flex';
}

function displayStudentDetails(data) {
    const stats = data.stats;
    document.getElementById('studentInfoCard').innerHTML = `<div class="student-detail-view"><h2><i class="fas fa-user-graduate"></i> ${escapeHtml(data.name)}</h2><div class="roll-badge"><i class="fas fa-id-card"></i> ${escapeHtml(data.roll)}</div><div class="leetcode-ids-list">${data.leetcode_ids.map(id => `<span class="leetcode-tag"><i class="fab fa-leetcode"></i> ${escapeHtml(id)}</span>`).join('')}</div></div>`;
    document.getElementById('easyValue').textContent = stats.Easy || 0;
    document.getElementById('mediumValue').textContent = stats.Medium || 0;
    document.getElementById('hardValue').textContent = stats.Hard || 0;
    document.getElementById('totalValue').textContent = stats.All || 0;
    
    const topicsList = document.getElementById('topicsList');
    const weakTopicsPanel = document.getElementById('weakTopicsPanel');
    if (topicsList && weakTopicsPanel) {
        if (data.weak_topics && data.weak_topics.length) {
            topicsList.innerHTML = data.weak_topics.map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('');
            weakTopicsPanel.style.display = 'block';
        } else {
            topicsList.innerHTML = '<span style="color: var(--success);">✨ Great job! No weak areas found.</span>';
            weakTopicsPanel.style.display = 'block';
        }
    }
    document.getElementById('statsPanel').style.display = 'flex';
    document.getElementById('emptyRightPanel').style.display = 'none';
    if (charts.difficulty) charts.difficulty.destroy();
    const ctx = document.getElementById('difficultyChart');
    if (ctx) {
        charts.difficulty = new Chart(ctx, {
            type: 'doughnut',
            data: { labels: ['Easy', 'Medium', 'Hard'], datasets: [{ data: [stats.Easy || 0, stats.Medium || 0, stats.Hard || 0], backgroundColor: ['#10b981', '#f59e0b', '#ef4444'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: true, cutout: '65%', plugins: { legend: { position: 'bottom', labels: { color: '#f1f5f9' } }, tooltip: { callbacks: { label: (ctx) => { const total = ctx.dataset.data.reduce((a,b)=>a+b,0); const pct = total>0?((ctx.parsed/total)*100).toFixed(1):0; return `${ctx.label}: ${ctx.parsed} (${pct}%)`; } } } } }
        });
    }
}

async function loadStudentsList() {
    try {
        const response = await fetch('/api/students');
        const students = await response.json();
        window.allStudents = students;
        displayStudents(students);
        updateStudentCount();
        populateStudentSelect(students);
    } catch (error) { console.error(error); }
}

function displayStudents(students) {
    const container = document.getElementById('studentsList');
    if (!container) return;
    if (!students.length) { container.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><p>No students found</p></div>'; return; }
    container.innerHTML = students.map(s => `<div class="student-card" onclick="viewStudentDetails('${s.roll}')"><h4><i class="fas fa-user"></i> ${escapeHtml(s.name)}</h4><div class="roll">${escapeHtml(s.roll)}</div><div class="student-stats-mini"><span><i class="fas fa-smile easy"></i> ${s.stats.Easy || 0}</span><span><i class="fas fa-chart-line medium"></i> ${s.stats.Medium || 0}</span><span><i class="fas fa-fire hard"></i> ${s.stats.Hard || 0}</span></div><div class="leetcode-ids">${s.leetcode_ids.map(id => `@${escapeHtml(id)}`).join(', ')}</div></div>`).join('');
}

function filterStudents() { if (window.allStudents) { const term = document.getElementById('studentSearch')?.value.toLowerCase() || ''; displayStudents(window.allStudents.filter(s => s.name.toLowerCase().includes(term) || s.roll.toLowerCase().includes(term))); } }

async function loadLeaderboard() {
    try { const res = await fetch('/api/leaderboard'); displayLeaderboard(await res.json(), document.getElementById('leaderboardFilter')?.value || 'total'); }
    catch(e) { console.error(e); }
}

function displayLeaderboard(data, sortBy) {
    const container = document.getElementById('leaderboardTable');
    if (!container) return;
    let sorted = [...data];
    if (sortBy === 'easy') sorted.sort((a,b)=>b.easy-a.easy);
    else if (sortBy === 'medium') sorted.sort((a,b)=>b.medium-a.medium);
    else if (sortBy === 'hard') sorted.sort((a,b)=>b.hard-a.hard);
    else sorted.sort((a,b)=>b.total_solved-a.total_solved);
    sorted.forEach((s,i)=>s.rank=i+1);
    container.innerHTML = `<table class="leaderboard-table"><thead><tr><th>Rank</th><th>Student</th><th>Roll</th><th>Easy</th><th>Medium</th><th>Hard</th><th>Total</th></tr></thead><tbody>${sorted.map(s => `<tr onclick="viewStudentDetails('${s.roll}')"><td class="${s.rank===1?'rank-1':s.rank===2?'rank-2':s.rank===3?'rank-3':''}">#${s.rank}</td><td><strong>${escapeHtml(s.name)}</strong></td><td>${escapeHtml(s.roll)}</td><td>${s.easy}</td><td>${s.medium}</td><td>${s.hard}</td><td><strong>${s.total_solved}</strong></td></tr>`).join('')}</tbody></table>`;
}

async function loadBatchAnalytics() {
    try { const res = await fetch('/api/batch-analytics'); displayBatchAnalytics(await res.json()); }
    catch(e) { console.error(e); }
}

function displayBatchAnalytics(analytics) {
    const batch = analytics['Your Batch'];
    if (!batch) return;
    document.getElementById('totalStudentsHero').textContent = batch.count;
    document.getElementById('totalProblemsHero').textContent = batch.total_all;
    document.getElementById('avgProblemsHero').textContent = Math.round(batch.avg_total);
    document.getElementById('totalEasyCount').textContent = batch.total_easy;
    document.getElementById('totalMediumCount').textContent = batch.total_medium;
    document.getElementById('totalHardCount').textContent = batch.total_hard;
    const totalAll = batch.total_easy + batch.total_medium + batch.total_hard;
    document.getElementById('easyProgressFill').style.width = totalAll ? (batch.total_easy/totalAll*100)+'%' : '0%';
    document.getElementById('mediumProgressFill').style.width = totalAll ? (batch.total_medium/totalAll*100)+'%' : '0%';
    document.getElementById('hardProgressFill').style.width = totalAll ? (batch.total_hard/totalAll*100)+'%' : '0%';
    document.getElementById('statEasy').textContent = batch.total_easy;
    document.getElementById('statMedium').textContent = batch.total_medium;
    document.getElementById('statHard').textContent = batch.total_hard;
    document.getElementById('statRatio').textContent = `${batch.total_easy}:${batch.total_medium}:${batch.total_hard}`;
    if (charts.batchDoughnut) charts.batchDoughnut.destroy();
    if (charts.batchBar) charts.batchBar.destroy();
    const doughnutCtx = document.getElementById('batchDoughnutChart');
    if (doughnutCtx) charts.batchDoughnut = new Chart(doughnutCtx, { type: 'doughnut', data: { labels: ['Easy','Medium','Hard'], datasets: [{ data: [batch.total_easy,batch.total_medium,batch.total_hard], backgroundColor: ['#10b981','#f59e0b','#ef4444'] }] }, options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#f1f5f9' } } } } });
    const barCtx = document.getElementById('batchBarChart');
    if (barCtx) charts.batchBar = new Chart(barCtx, { type: 'bar', data: { labels: ['Easy','Medium','Hard'], datasets: [{ label: 'Problems Solved', data: [batch.total_easy,batch.total_medium,batch.total_hard], backgroundColor: ['#10b981','#f59e0b','#ef4444'], borderRadius: 8 }] }, options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: '#f1f5f9' } } }, scales: { y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#f1f5f9' } }, x: { ticks: { color: '#f1f5f9' } } } } });
    const topList = document.getElementById('topPerformersList');
    if (topList && batch.students) topList.innerHTML = batch.students.slice(0,5).map((s,i)=>`<div class="performer-item"><div class="performer-rank rank-${i+1}">${i+1}</div><div class="performer-info"><div class="performer-name">${escapeHtml(s)}</div></div></div>`).join('');
}

function viewStudentDetails(roll) { document.getElementById('searchRollInput').value = roll; switchView('dashboard'); loadStudentData(); }

async function addStudent() {
    const roll = document.getElementById('rollNumber')?.value.trim();
    const name = document.getElementById('studentName')?.value.trim();
    const idsStr = document.getElementById('leetcodeIds')?.value.trim();
    if (!roll || !name || !idsStr) { showToast('All fields are required', 'warning'); return; }
    const ids = idsStr.split(',').map(id=>id.trim()).filter(id=>id);
    if (!ids.length) { showToast('Enter at least one LeetCode username', 'warning'); return; }
    showLoading();
    try {
        const res = await fetch('/api/student', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ roll, name, leetcode_ids: ids }) });
        const data = await res.json();
        if (res.ok) { showToast(data.message, 'success'); closeModal(); document.getElementById('addStudentForm')?.reset(); loadStudentsList(); loadLeaderboard(); loadBatchAnalytics(); updateStudentCount(); }
        else showToast(data.error, 'error');
    } catch(e) { showToast('Network error', 'error'); }
    finally { hideLoading(); }
}

async function uploadFile() {
    const file = document.getElementById('uploadFile')?.files[0];
    if (!file) { showToast('Select a file', 'warning'); return; }
    const formData = new FormData(); formData.append('file', file);
    showLoading();
    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) { showToast(data.message, 'success'); closeModal(); document.getElementById('uploadFile').value = ''; loadStudentsList(); loadLeaderboard(); loadBatchAnalytics(); updateStudentCount(); }
        else showToast(data.error, 'error');
    } catch(e) { showToast('Upload failed', 'error'); }
    finally { hideLoading(); }
}

async function exportData() { window.location.href = '/api/export'; showToast('Export started!', 'success'); }

async function updateStudentCount() {
    try { const res = await fetch('/api/students'); const students = await res.json(); document.getElementById('studentCount').textContent = students.length; }
    catch(e) { console.error(e); }
}

function openModal(id) { document.getElementById(id)?.classList.add('active'); }
function closeModal() { document.querySelectorAll('.modal').forEach(m=>m.classList.remove('active')); }
function showLoading() { document.getElementById('loadingOverlay')?.classList.add('active'); }
function hideLoading() { document.getElementById('loadingOverlay')?.classList.remove('active'); }
function showToast(msg, type='info') { const toast = document.getElementById('toast'); if(toast){ toast.textContent = msg; toast.className = `toast ${type} show`; setTimeout(()=>toast.classList.remove('show'),3000); } }
function escapeHtml(str) { if(!str) return ''; return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

async function loadCourses() {
    try {
        const res = await fetch('/api/courses');
        const courses = await res.json();
        const courseSelect = document.getElementById('courseSelect');
        const assignCourseSelect = document.getElementById('assignCourseSelect');
        if (courseSelect) {
            courseSelect.innerHTML = '<option value="">Select Course</option>';
            courses.forEach(c => { const opt = document.createElement('option'); opt.value = c.id; opt.textContent = `${c.name} (${c.code})`; courseSelect.appendChild(opt); });
            courseSelect.onchange = async () => {
                const sectionSelect = document.getElementById('sectionSelect');
                const loadBtn = document.getElementById('loadSectionBtn');
                if (!courseSelect.value) { sectionSelect.innerHTML = '<option value="">Select Section</option>'; sectionSelect.disabled = true; loadBtn.disabled = true; return; }
                loadBtn.disabled = true; sectionSelect.disabled = true; sectionSelect.innerHTML = '<option value="">Loading...</option>';
                try {
                    const secRes = await fetch(`/api/courses/${courseSelect.value}/sections`);
                    const sections = await secRes.json();
                    sectionSelect.innerHTML = '<option value="">Select Section</option>';
                    sections.forEach(s => { const opt = document.createElement('option'); opt.value = s.id; opt.textContent = `${s.name} (${s.code||'No code'})`; sectionSelect.appendChild(opt); });
                    sectionSelect.disabled = false;
                    sectionSelect.onchange = () => { loadBtn.disabled = !sectionSelect.value; };
                } catch(e) { sectionSelect.innerHTML = '<option value="">Error loading sections</option>'; }
            };
        }
        if (assignCourseSelect) {
            assignCourseSelect.innerHTML = '<option value="">Select Course</option>';
            courses.forEach(c => { const opt = document.createElement('option'); opt.value = c.id; opt.textContent = `${c.name} (${c.code})`; assignCourseSelect.appendChild(opt); });
            assignCourseSelect.onchange = async () => {
                const assignSectionSelect = document.getElementById('assignSectionSelect');
                if (!assignCourseSelect.value) { assignSectionSelect.innerHTML = '<option value="">First select a course</option>'; assignSectionSelect.disabled = true; return; }
                assignSectionSelect.disabled = true; assignSectionSelect.innerHTML = '<option value="">Loading sections...</option>';
                try {
                    const secRes = await fetch(`/api/courses/${assignCourseSelect.value}/sections`);
                    const sections = await secRes.json();
                    assignSectionSelect.innerHTML = '<option value="">Select Section</option>';
                    sections.forEach(s => { const opt = document.createElement('option'); opt.value = s.id; opt.textContent = `${s.name} (${s.code||'No code'})`; assignSectionSelect.appendChild(opt); });
                    assignSectionSelect.disabled = false;
                } catch(e) { assignSectionSelect.innerHTML = '<option value="">Error loading sections</option>'; }
            };
        }
    } catch(e) { console.error(e); }
}

async function loadSectionDashboard() {
    const sectionId = document.getElementById('sectionSelect')?.value;
    if (!sectionId) { showToast('Select a section first', 'warning'); return; }
    showLoading();
    try {
        const res = await fetch(`/api/section/${sectionId}/dashboard`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        currentSectionData = data;
        displaySectionDashboard(data);
        switchView('sectionDashboard');
        showToast(`Loaded ${data.section.course_name} - ${data.section.name}`, 'success');
    } catch(e) { showToast('Error loading section dashboard', 'error'); }
    finally { hideLoading(); }
}

function displaySectionDashboard(data) {
    const s = data.section, stats = data.stats;
    document.getElementById('sectionTitle').textContent = `${s.course_name} - ${s.name}`;
    document.getElementById('sectionStudentCount').textContent = stats.total_students;
    document.getElementById('sectionEasyCount').textContent = stats.total_easy;
    document.getElementById('sectionMediumCount').textContent = stats.total_medium;
    document.getElementById('sectionHardCount').textContent = stats.total_hard;
    document.getElementById('sectionTotalCount').textContent = stats.total_solved;
    const leaderboardDiv = document.getElementById('sectionLeaderboardTable');
    if (leaderboardDiv && data.leaderboard) {
        if (!data.leaderboard.length) leaderboardDiv.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><p>No students in this section</p></div>';
        else leaderboardDiv.innerHTML = data.leaderboard.map(s => `<div class="leaderboard-item" onclick="viewStudentDetails('${s.roll}')"><div class="leaderboard-rank ${s.rank===1?'rank-1':s.rank===2?'rank-2':s.rank===3?'rank-3':''}">#${s.rank}</div><div class="leaderboard-info"><div class="leaderboard-name">${escapeHtml(s.name)}</div><div class="leaderboard-roll">${escapeHtml(s.roll)}</div></div><div class="leaderboard-scores"><span class="easy">${s.stats.Easy}</span><span class="medium">${s.stats.Medium}</span><span class="hard">${s.stats.Hard}</span></div><div class="leaderboard-total">${s.stats.Easy+s.stats.Medium+s.stats.Hard}</div></div>`).join('');
    }
    document.getElementById('sectionSummary').innerHTML = `<div class="summary-item"><span class="summary-label"><i class="fas fa-chart-line"></i> Total Hard</span><span class="summary-value">${stats.total_hard}</span></div><div class="summary-item"><span class="summary-label"><i class="fas fa-chart-pie"></i> Ratio</span><span class="summary-value">${stats.total_easy}:${stats.total_medium}:${stats.total_hard}</span></div><div class="summary-item"><span class="summary-label"><i class="fas fa-crown"></i> Top Performer</span><span class="summary-value highlight">${data.leaderboard[0]?escapeHtml(data.leaderboard[0].name):'N/A'}</span></div><div class="progress-ring"><div class="progress-ring-fill" style="width:${stats.total_students?(data.leaderboard.filter(s=>(s.stats.Easy+s.stats.Medium+s.stats.Hard)>20).length/stats.total_students*100):0}%"></div></div>`;
    if (sectionCharts.difficulty) sectionCharts.difficulty.destroy();
    const chartCtx = document.getElementById('sectionDifficultyChart');
    if (chartCtx) sectionCharts.difficulty = new Chart(chartCtx, { type: 'doughnut', data: { labels: ['Easy','Medium','Hard'], datasets: [{ data: [stats.total_easy,stats.total_medium,stats.total_hard], backgroundColor: ['#10b981','#f59e0b','#ef4444'], borderWidth: 0 }] }, options: { responsive: true, maintainAspectRatio: true, cutout: '60%', plugins: { legend: { position: 'bottom', labels: { color: '#f1f5f9' } }, tooltip: { callbacks: { label: (ctx) => { const total = ctx.dataset.data.reduce((a,b)=>a+b,0); const pct = total?((ctx.parsed/total)*100).toFixed(1):0; return `${ctx.label}: ${ctx.parsed} (${pct}%)`; } } } } } });
}

function populateStudentSelect(students) {
    const sel = document.getElementById('assignStudentSelect');
    if (!sel) return;
    sel.innerHTML = '<option value="">Select Student</option>';
    students.forEach(s => { const opt = document.createElement('option'); opt.value = s.roll; opt.textContent = `${s.name} (${s.roll})`; sel.appendChild(opt); });
}

async function openAssignModal() { if (!window.allStudents) await loadStudentsList(); openModal('assignSectionModal'); }
async function assignStudentToSection() {
    const studentRoll = document.getElementById('assignStudentSelect')?.value;
    const sectionId = document.getElementById('assignSectionSelect')?.value;
    if (!studentRoll || !sectionId) { showToast('Select student and section', 'warning'); return; }
    showLoading();
    try {
        const res = await fetch('/api/assign-student', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ student_roll: studentRoll, section_id: parseInt(sectionId) }) });
        const data = await res.json();
        if (res.ok) { showToast(data.message, 'success'); closeModal(); document.getElementById('assignStudentSelect').value = ''; document.getElementById('assignCourseSelect').value = ''; document.getElementById('assignSectionSelect').innerHTML = '<option value="">First select a course</option>'; document.getElementById('assignSectionSelect').disabled = true; const ss = document.getElementById('sectionSelect'); if(ss && ss.value && document.getElementById('sectionDashboardView').classList.contains('active')) loadSectionDashboard(); }
        else showToast(data.error, 'error');
    } catch(e) { showToast('Error assigning student', 'error'); }
    finally { hideLoading(); }
}

async function loadAssignmentsFilter() {
    try {
        const courses = await (await fetch('/api/courses')).json();
        const filter = document.getElementById('viewAssignmentsFilter');
        if (!filter) return;
        filter.innerHTML = '<option value="">All Sections</option>';
        for (const c of courses) {
            const sections = await (await fetch(`/api/courses/${c.id}/sections`)).json();
            sections.forEach(s => { const opt = document.createElement('option'); opt.value = s.id; opt.textContent = `${c.name} - ${s.name}`; filter.appendChild(opt); });
        }
    } catch(e) { console.error(e); }
}
async function openViewAssignmentsModal() { openModal('viewAssignmentsModal'); await loadAllAssignments(); }
async function loadAllAssignments() {
    const filterVal = document.getElementById('viewAssignmentsFilter')?.value;
    const listDiv = document.getElementById('assignmentsList');
    if (!listDiv) return;
    listDiv.innerHTML = '<div class="empty-state">Loading assignments...</div>';
    try {
        let assignments = await (await fetch('/api/section-assignments')).json();
        if (filterVal) assignments = assignments.filter(a => a.section_id === parseInt(filterVal));
        if (!assignments.length) { listDiv.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><p>No students assigned</p></div>'; return; }
        listDiv.innerHTML = `<table class="leaderboard-table"><thead><tr><th>Student</th><th>Roll</th><th>Course</th><th>Section</th><th>Action</th></tr></thead><tbody>${assignments.map(a => `<tr><td><strong>${escapeHtml(a.student_name)}</strong></td><td>${escapeHtml(a.student_roll)}</td><td>${escapeHtml(a.course_name)}</td><td>${escapeHtml(a.section_name)}</td><td><button onclick="unassignStudent('${a.student_roll}', ${a.section_id})" class="icon-btn" style="background:rgba(239,68,68,0.2)"><i class="fas fa-trash"></i></button></td></tr>`).join('')}</tbody></table>`;
    } catch(e) { listDiv.innerHTML = '<div class="empty-state">Error loading assignments</div>'; }
}
async function unassignStudent(roll, secId) {
    if (!confirm(`Remove student ${roll} from section?`)) return;
    showLoading();
    try {
        const res = await fetch('/api/unassign-student', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ student_roll: roll, section_id: secId }) });
        const data = await res.json();
        if (res.ok) { showToast(data.message, 'success'); await loadAllAssignments(); const ss = document.getElementById('sectionSelect'); if(ss && ss.value && document.getElementById('sectionDashboardView').classList.contains('active')) loadSectionDashboard(); }
        else showToast(data.error, 'error');
    } catch(e) { showToast('Error', 'error'); }
    finally { hideLoading(); }
}