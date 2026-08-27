/**
 * AI Data Quality Analyzer — Application Logic
 * Handles file upload, API communication, dashboard rendering, and chart creation
 */

const API_BASE = 'http://localhost:5000/api';

// ── State ──────────────────────────────────────────────────────────
let state = {
    sessionId: null,
    filename: null,
    analysis: null,
    recommendations: null,
    cleaningResult: null,
    selectedCleanOps: new Set(),
    charts: {},
};

// ── Initialization ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setupUpload();
    setupNavigation();
});

// ── File Upload ────────────────────────────────────────────────────
function setupUpload() {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('file-input');

    zone.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFileUpload(files[0]);
    });

    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
    });
}

async function handleFileUpload(file) {
    // Validate client-side
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
        showError('Invalid file type. Please upload a CSV or Excel file (.csv, .xlsx, .xls).');
        return;
    }

    if (file.size > 50 * 1024 * 1024) {
        showError('File too large. Maximum size is 50MB.');
        return;
    }

    showLoading('Uploading your dataset...', 'Validating file structure and contents');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            showError(data.error || 'Upload failed');
            hideLoading();
            return;
        }

        state.sessionId = data.session_id;
        state.filename = data.filename;

        // Update header
        document.getElementById('header-filename').textContent = data.filename;
        document.getElementById('header-actions').classList.remove('hidden');

        // Start analysis
        await runAnalysis();
    } catch (err) {
        showError('Failed to upload file. Please check your connection and try again.');
        hideLoading();
    }
}

async function runAnalysis() {
    showLoading('Analyzing data quality...', 'Profiling columns, detecting issues, scoring quality');

    try {
        const res = await fetch(`${API_BASE}/analysis/${state.sessionId}`);
        const data = await res.json();

        if (!res.ok) {
            showError(data.error || 'Analysis failed');
            hideLoading();
            return;
        }

        state.analysis = data.analysis;
        state.recommendations = data.recommendations;

        renderDashboard();
        switchToTab('overview');

        hideLoading();
        showSuccess('Analysis complete! Explore your results.');
    } catch (err) {
        showError('Analysis failed: ' + err.message);
        hideLoading();
    }
}

// ── Navigation ─────────────────────────────────────────────────────
function setupNavigation() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;
            switchToTab(tabId);
        });
    });
}

function switchToTab(tabId) {
    // Show navigation if hidden
    document.getElementById('nav-tabs').classList.remove('hidden');

    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    const activeTab = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
    if (activeTab) activeTab.classList.add('active');

    // Hide upload, show tab panel
    document.getElementById('section-upload').classList.remove('active');
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`section-${tabId}`);
    if (panel) panel.classList.add('active');
}

// ── Dashboard Rendering ───────────────────────────────────────────
function renderDashboard() {
    if (!state.analysis) return;

    renderOverview();
    renderColumnsTable();
    renderIssues();
    renderRecommendations();
    renderCleaningOptions();
    updateExportButtons();
}

// ── Overview ───────────────────────────────────────────────────────
function renderOverview() {
    const { summary, category_scores, overall_score } = state.analysis;

    // Quality Score Gauge
    const gauge = document.getElementById('gauge-fill');
    const circumference = 2 * Math.PI * 52; // r=52
    const offset = circumference - (overall_score / 100) * circumference;
    gauge.style.strokeDasharray = circumference;
    gauge.style.strokeDashoffset = circumference; // Start from 0

    // Determine gauge class
    gauge.classList.remove('excellent', 'good', 'fair', 'poor');
    if (overall_score >= 80) gauge.classList.add('excellent');
    else if (overall_score >= 60) gauge.classList.add('good');
    else if (overall_score >= 40) gauge.classList.add('fair');
    else gauge.classList.add('poor');

    // Animate gauge
    requestAnimationFrame(() => {
        setTimeout(() => {
            gauge.style.strokeDashoffset = offset;
        }, 100);
    });

    // Animate score number
    animateNumber('score-number', 0, overall_score, 1500);

    // Category scores
    const catContainer = document.getElementById('score-categories');
    catContainer.innerHTML = '';
    for (const [cat, score] of Object.entries(category_scores)) {
        const color = score >= 80 ? 'var(--gradient-success)' :
                      score >= 60 ? 'var(--gradient-primary)' :
                      score >= 40 ? 'var(--gradient-warning)' : 'var(--gradient-danger)';
        catContainer.innerHTML += `
            <div class="score-category">
                <span class="cat-name">${cat}</span>
                <div class="cat-bar">
                    <div class="cat-bar-fill" style="width: 0%; background: ${color};" data-width="${score}%"></div>
                </div>
                <span class="cat-value">${score}</span>
            </div>
        `;
    }

    // Animate category bars
    requestAnimationFrame(() => {
        setTimeout(() => {
            catContainer.querySelectorAll('.cat-bar-fill').forEach(bar => {
                bar.style.width = bar.dataset.width;
            });
        }, 200);
    });

    // Stats grid
    const statsGrid = document.getElementById('stats-grid');
    statsGrid.innerHTML = `
        <div class="stat-card primary">
            <span class="stat-icon">📊</span>
            <div class="stat-value">${summary.total_rows.toLocaleString()}</div>
            <div class="stat-label">Total Rows</div>
        </div>
        <div class="stat-card info">
            <span class="stat-icon">📋</span>
            <div class="stat-value">${summary.total_columns}</div>
            <div class="stat-label">Columns</div>
        </div>
        <div class="stat-card ${summary.missing_percentage > 5 ? 'danger' : summary.missing_percentage > 0 ? 'warning' : 'success'}">
            <span class="stat-icon">❓</span>
            <div class="stat-value">${summary.total_missing.toLocaleString()}</div>
            <div class="stat-label">Missing Cells (${summary.missing_percentage}%)</div>
        </div>
        <div class="stat-card ${summary.duplicate_percentage > 5 ? 'danger' : summary.total_duplicates > 0 ? 'warning' : 'success'}">
            <span class="stat-icon">📑</span>
            <div class="stat-value">${summary.total_duplicates.toLocaleString()}</div>
            <div class="stat-label">Duplicates (${summary.duplicate_percentage}%)</div>
        </div>
        <div class="stat-card ${summary.total_issues > 10 ? 'danger' : summary.total_issues > 0 ? 'warning' : 'success'}">
            <span class="stat-icon">⚡</span>
            <div class="stat-value">${summary.total_issues}</div>
            <div class="stat-label">Issues Found</div>
        </div>
        <div class="stat-card primary">
            <span class="stat-icon">💾</span>
            <div class="stat-value">${summary.memory_usage_mb}</div>
            <div class="stat-label">Size (MB)</div>
        </div>
    `;

    // Render charts
    renderCharts();
}

function animateNumber(elementId, start, end, duration) {
    const el = document.getElementById(elementId);
    const range = end - start;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        const current = Math.round(start + range * eased);
        el.textContent = current;
        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}

// ── Charts ─────────────────────────────────────────────────────────
function renderCharts() {
    // Destroy existing charts
    Object.values(state.charts).forEach(c => c.destroy());
    state.charts = {};

    const chartDefaults = {
        color: '#9fa8da',
        borderColor: 'rgba(255, 255, 255, 0.08)',
    };

    Chart.defaults.color = chartDefaults.color;
    Chart.defaults.borderColor = chartDefaults.borderColor;

    renderMissingChart();
    renderScoresChart();
    renderIssuesChart();
    renderDtypesChart();
}

function renderMissingChart() {
    const missing = state.analysis.missing_values.columns;
    const labels = Object.keys(missing);
    const values = labels.map(k => missing[k].percentage);

    if (labels.length === 0) {
        document.getElementById('chart-missing').parentElement.querySelector('.card-title').innerHTML =
            '<span class="icon">📉</span> Missing Values — None detected ✅';
        return;
    }

    // Show top 15
    const sorted = labels.map((l, i) => ({ label: l, value: values[i] }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 15);

    state.charts.missing = new Chart(document.getElementById('chart-missing'), {
        type: 'bar',
        data: {
            labels: sorted.map(s => truncate(s.label, 15)),
            datasets: [{
                label: 'Missing %',
                data: sorted.map(s => s.value),
                backgroundColor: sorted.map(s =>
                    s.value > 20 ? 'rgba(255, 65, 108, 0.7)' :
                    s.value > 5 ? 'rgba(255, 152, 0, 0.7)' :
                    'rgba(102, 126, 234, 0.7)'
                ),
                borderRadius: 6,
                borderSkipped: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.parsed.y}% missing`
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Missing %' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                x: { grid: { display: false } },
            },
        },
    });
}

function renderScoresChart() {
    const scores = state.analysis.category_scores;
    const labels = Object.keys(scores).map(k => k.charAt(0).toUpperCase() + k.slice(1));
    const values = Object.values(scores);

    state.charts.scores = new Chart(document.getElementById('chart-scores'), {
        type: 'radar',
        data: {
            labels,
            datasets: [{
                label: 'Quality Score',
                data: values,
                backgroundColor: 'rgba(102, 126, 234, 0.15)',
                borderColor: 'rgba(102, 126, 234, 0.8)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                pointBorderColor: '#fff',
                pointBorderWidth: 1,
                pointRadius: 5,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { stepSize: 20, backdropColor: 'transparent' },
                    grid: { color: 'rgba(255,255,255,0.06)' },
                    angleLines: { color: 'rgba(255,255,255,0.06)' },
                    pointLabels: { font: { size: 12 } },
                },
            },
        },
    });
}

function renderIssuesChart() {
    const issues = state.analysis.issues;
    const categories = {};
    issues.forEach(i => {
        categories[i.category] = (categories[i.category] || 0) + 1;
    });

    const labels = Object.keys(categories).map(k => k.charAt(0).toUpperCase() + k.slice(1));
    const values = Object.values(categories);
    const colors = ['rgba(102, 126, 234, 0.7)', 'rgba(240, 147, 251, 0.7)',
                    'rgba(79, 172, 254, 0.7)', 'rgba(255, 152, 0, 0.7)',
                    'rgba(255, 65, 108, 0.7)'];

    state.charts.issues = new Chart(document.getElementById('chart-issues'), {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, values.length),
                borderWidth: 0,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: { position: 'bottom', labels: { padding: 15, usePointStyle: true, pointStyle: 'circle' } },
            },
        },
    });
}

function renderDtypesChart() {
    const profiles = state.analysis.column_profiles;
    const types = {};
    Object.values(profiles).forEach(p => {
        const t = p.inferred_type || 'unknown';
        types[t] = (types[t] || 0) + 1;
    });

    const labels = Object.keys(types);
    const values = Object.values(types);
    const colors = [
        'rgba(102, 126, 234, 0.7)', 'rgba(56, 239, 125, 0.7)', 'rgba(240, 147, 251, 0.7)',
        'rgba(242, 201, 76, 0.7)', 'rgba(79, 172, 254, 0.7)', 'rgba(255, 65, 108, 0.7)',
        'rgba(0, 242, 254, 0.7)', 'rgba(255, 152, 0, 0.7)',
    ];

    state.charts.dtypes = new Chart(document.getElementById('chart-dtypes'), {
        type: 'polarArea',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, values.length),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 15, usePointStyle: true, pointStyle: 'circle' } },
            },
            scales: {
                r: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { display: false } },
            },
        },
    });
}

// ── Columns Table ──────────────────────────────────────────────────
function renderColumnsTable() {
    const profiles = state.analysis.column_profiles;
    const issues = state.analysis.issues;
    const outliers = state.analysis.outliers.columns || {};
    const tbody = document.getElementById('columns-tbody');
    tbody.innerHTML = '';

    let idx = 0;
    for (const [col, profile] of Object.entries(profiles)) {
        idx++;
        const colIssues = issues.filter(i => i.column === col);
        const outlierCount = outliers[col]?.iqr_outliers || 0;
        const hasIssues = colIssues.length > 0;
        const worstSeverity = colIssues.length > 0 ?
            colIssues.reduce((worst, i) => {
                const rank = { critical: 0, high: 1, medium: 2, low: 3 };
                return rank[i.severity] < rank[worst] ? i.severity : worst;
            }, 'low') : null;

        const statusBadge = !hasIssues ?
            '<span class="badge badge-success">✓ Clean</span>' :
            `<span class="badge badge-${worstSeverity === 'critical' || worstSeverity === 'high' ? 'danger' : 'warning'}">${colIssues.length} issue${colIssues.length > 1 ? 's' : ''}</span>`;

        tbody.innerHTML += `
            <tr>
                <td>${idx}</td>
                <td class="col-name">${col}</td>
                <td><span class="badge badge-primary">${profile.dtype}</span></td>
                <td>${profile.inferred_type}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div class="progress-bar" style="width: 60px;">
                            <div class="progress-fill ${profile.missing_pct > 20 ? 'danger' : profile.missing_pct > 5 ? 'warning' : 'good'}"
                                 style="width: ${Math.min(profile.missing_pct, 100)}%"></div>
                        </div>
                        <span>${profile.missing_pct}%</span>
                    </div>
                </td>
                <td>${profile.unique_count.toLocaleString()} <span style="color: var(--text-muted);">(${profile.unique_pct}%)</span></td>
                <td>${outlierCount > 0 ? `<span class="badge badge-warning">${outlierCount}</span>` : '—'}</td>
                <td>${colIssues.length}</td>
                <td>${statusBadge}</td>
            </tr>
        `;
    }
}

// ── Issues ─────────────────────────────────────────────────────────
function renderIssues() {
    const issues = state.analysis.issues;

    // Summary cards
    const severityCounts = { critical: 0, high: 0, medium: 0, low: 0 };
    issues.forEach(i => severityCounts[i.severity]++);

    const summaryEl = document.getElementById('issues-summary');
    summaryEl.innerHTML = ['critical', 'high', 'medium', 'low'].map(sev => `
        <div class="severity-card ${sev}">
            <div class="sev-count">${severityCounts[sev]}</div>
            <div class="sev-label">${sev}</div>
        </div>
    `).join('');

    // Issues badge in nav
    const badge = document.getElementById('issues-badge');
    if (issues.length > 0) {
        badge.textContent = issues.length;
        badge.classList.remove('hidden');
    }

    // Filter buttons
    const filterEl = document.getElementById('issues-filter');
    filterEl.innerHTML = `
        <button class="filter-btn active" data-filter="all" onclick="filterIssues('all', this)">All (${issues.length})</button>
        ${['critical', 'high', 'medium', 'low'].filter(s => severityCounts[s] > 0).map(s =>
            `<button class="filter-btn" data-filter="${s}" onclick="filterIssues('${s}', this)">${s.charAt(0).toUpperCase() + s.slice(1)} (${severityCounts[s]})</button>`
        ).join('')}
    `;

    // Issue cards
    renderIssueCards(issues);
}

function renderIssueCards(issues) {
    const listEl = document.getElementById('issues-list');
    listEl.innerHTML = issues.map(issue => `
        <div class="issue-card ${issue.severity}" data-severity="${issue.severity}">
            <span class="issue-severity-badge ${issue.severity}">${issue.severity}</span>
            <div class="issue-content">
                <div class="issue-title">${issue.description}</div>
                <div class="issue-meta">
                    <span>📋 ${issue.column}</span>
                    <span>📁 ${issue.category}</span>
                    <span>📊 ${issue.affected_pct}% affected</span>
                </div>
            </div>
        </div>
    `).join('');
}

function filterIssues(severity, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const issues = state.analysis.issues;
    const filtered = severity === 'all' ? issues : issues.filter(i => i.severity === severity);
    renderIssueCards(filtered);
}

// ── Recommendations ────────────────────────────────────────────────
function renderRecommendations() {
    const recs = state.recommendations || [];
    document.getElementById('rec-count').textContent = `${recs.length} insight${recs.length !== 1 ? 's' : ''}`;

    const listEl = document.getElementById('recommendations-list');
    listEl.innerHTML = recs.map((rec, i) => {
        const icons = {
            'Missing Values': '❓',
            'Duplicates': '📑',
            'Data Types': '🔢',
            'Outliers': '📈',
            'Invalid Values': '⚠️',
            'Consistency': '🔗',
            'Overall': '📊',
        };
        const icon = icons[rec.category] || '💡';

        return `
            <div class="rec-card" id="rec-${i}">
                <div class="rec-card-header" onclick="toggleRec(${i})">
                    <span class="rec-icon">${icon}</span>
                    <div class="rec-title-area">
                        <div class="rec-title">${rec.title}</div>
                        <div class="rec-category">${rec.category} • ${rec.column}</div>
                    </div>
                    <span class="rec-priority ${rec.priority}">${rec.priority}</span>
                    <span class="rec-toggle">▼</span>
                </div>
                <div class="rec-card-body">
                    <div class="rec-card-body-inner">
                        <div class="rec-explanation">
                            <span class="label">🔍 Analysis</span>
                            ${rec.explanation}
                        </div>
                        <div class="rec-action">
                            <span class="label">✅ Recommended Action</span>
                            ${rec.action}
                        </div>
                        ${rec.auto_fixable && rec.fix_operation ? `
                            <button class="rec-fix-btn" onclick="applyRecFix(${i})">
                                🔧 Apply Fix
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function toggleRec(index) {
    const card = document.getElementById(`rec-${index}`);
    card.classList.toggle('expanded');
}

async function applyRecFix(index) {
    const rec = state.recommendations[index];
    if (!rec.fix_operation) return;

    showLoading('Applying fix...', rec.title);

    try {
        const res = await fetch(`${API_BASE}/clean/${state.sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ operations: [rec.fix_operation] }),
        });
        const data = await res.json();

        if (!res.ok) {
            showError(data.error || 'Fix failed');
            hideLoading();
            return;
        }

        state.cleaningResult = data;
        renderCleaningResults(data);
        switchToTab('cleaning');
        enableExportButtons();
        hideLoading();
        showSuccess('Fix applied successfully!');
    } catch (err) {
        showError('Fix failed: ' + err.message);
        hideLoading();
    }
}

// ── Cleaning ───────────────────────────────────────────────────────
function renderCleaningOptions() {
    const analysis = state.analysis;
    const options = [];

    // Fill missing values
    const missingCols = Object.keys(analysis.missing_values.columns);
    if (missingCols.length > 0) {
        options.push({
            id: 'fill_missing',
            icon: '🔧',
            title: 'Fill Missing Values',
            desc: `Auto-fill ${analysis.summary.total_missing.toLocaleString()} missing values across ${missingCols.length} columns using intelligent strategies (mean/median/mode)`,
            impact: `${analysis.summary.missing_percentage}% of cells affected`,
            operation: { type: 'fill_missing', params: { columns: [], strategy: 'auto' } },
        });
    }

    // Remove duplicates
    if (analysis.duplicates.total_duplicates > 0) {
        options.push({
            id: 'remove_duplicates',
            icon: '🗑️',
            title: 'Remove Duplicate Rows',
            desc: `Remove ${analysis.duplicates.total_duplicates.toLocaleString()} exact duplicate rows, keeping the first occurrence`,
            impact: `${analysis.duplicates.duplicate_percentage}% of rows`,
            operation: { type: 'remove_duplicates', params: { keep: 'first' } },
        });
    }

    // Handle outliers
    const outlierCols = Object.keys(analysis.outliers.columns || {});
    if (outlierCols.length > 0) {
        const totalOutliers = Object.values(analysis.outliers.columns)
            .reduce((sum, c) => sum + c.iqr_outliers, 0);
        options.push({
            id: 'handle_outliers',
            icon: '📏',
            title: 'Handle Outliers',
            desc: `Cap ${totalOutliers.toLocaleString()} outliers in ${outlierCols.length} columns at IQR boundaries`,
            impact: `${outlierCols.length} numeric columns`,
            operation: { type: 'handle_outliers', params: { columns: outlierCols, method: 'cap' } },
        });
    }

    // Fix data types
    const typeIssues = analysis.issues.filter(i => i.type === 'type_mismatch' || i.type === 'mixed_data_types');
    if (typeIssues.length > 0) {
        const typeCols = [...new Set(typeIssues.map(i => i.column))];
        options.push({
            id: 'fix_data_types',
            icon: '🔄',
            title: 'Fix Data Types',
            desc: `Convert ${typeCols.length} column(s) to their correct data types`,
            impact: `${typeCols.length} columns`,
            operation: { type: 'fix_data_types', params: { columns: typeCols } },
        });
    }

    // Standardize values
    const consistencyIssues = analysis.issues.filter(i =>
        i.type === 'case_inconsistency' || i.type === 'whitespace_issues' || i.type === 'extra_whitespace'
    );
    if (consistencyIssues.length > 0) {
        const consCols = [...new Set(consistencyIssues.map(i => i.column))];
        options.push({
            id: 'standardize_values',
            icon: '✨',
            title: 'Standardize Values',
            desc: `Fix case inconsistencies and whitespace issues in ${consCols.length} column(s)`,
            impact: `${consCols.length} text columns`,
            operation: { type: 'standardize_values', params: { columns: consCols } },
        });
    }

    // If no issues found
    if (options.length === 0) {
        document.getElementById('cleaning-options').innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <span class="empty-icon">✨</span>
                <h3>Dataset is already clean!</h3>
                <p>No cleaning operations are needed for this dataset.</p>
            </div>
        `;
        return;
    }

    const container = document.getElementById('cleaning-options');
    container.innerHTML = options.map(opt => `
        <div class="clean-option" id="clean-${opt.id}" onclick="toggleCleanOption('${opt.id}')" data-operation='${JSON.stringify(opt.operation)}'>
            <div class="clean-checkbox">✓</div>
            <span class="clean-icon">${opt.icon}</span>
            <h4>${opt.title}</h4>
            <p>${opt.desc}</p>
            <div class="clean-impact">📊 ${opt.impact}</div>
        </div>
    `).join('');

    state.selectedCleanOps.clear();
    updateCleanButton();
}

function toggleCleanOption(id) {
    const el = document.getElementById(`clean-${id}`);
    el.classList.toggle('selected');

    if (state.selectedCleanOps.has(id)) {
        state.selectedCleanOps.delete(id);
    } else {
        state.selectedCleanOps.add(id);
    }

    updateCleanButton();
}

function toggleAllCleaning() {
    const allOptions = document.querySelectorAll('.clean-option');
    const allSelected = state.selectedCleanOps.size === allOptions.length;

    allOptions.forEach(opt => {
        const id = opt.id.replace('clean-', '');
        if (allSelected) {
            opt.classList.remove('selected');
            state.selectedCleanOps.delete(id);
        } else {
            opt.classList.add('selected');
            state.selectedCleanOps.add(id);
        }
    });

    updateCleanButton();
    document.getElementById('btn-select-all-cleaning').textContent =
        allSelected ? 'Select All' : 'Deselect All';
}

function updateCleanButton() {
    const btn = document.getElementById('btn-apply-cleaning');
    btn.disabled = state.selectedCleanOps.size === 0;
    btn.innerHTML = state.selectedCleanOps.size > 0 ?
        `🧹 Apply ${state.selectedCleanOps.size} Operation${state.selectedCleanOps.size > 1 ? 's' : ''}` :
        '🧹 Select operations to apply';
}

async function applyCleaning() {
    const operations = [];
    state.selectedCleanOps.forEach(id => {
        const el = document.getElementById(`clean-${id}`);
        if (el) {
            operations.push(JSON.parse(el.dataset.operation));
        }
    });

    if (operations.length === 0) return;

    showLoading('Cleaning dataset...', `Applying ${operations.length} operation(s)`);

    try {
        const res = await fetch(`${API_BASE}/clean/${state.sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ operations }),
        });
        const data = await res.json();

        if (!res.ok) {
            showError(data.error || 'Cleaning failed');
            hideLoading();
            return;
        }

        state.cleaningResult = data;
        renderCleaningResults(data);
        enableExportButtons();
        hideLoading();
        showSuccess('Dataset cleaned successfully!');
    } catch (err) {
        showError('Cleaning failed: ' + err.message);
        hideLoading();
    }
}

function renderCleaningResults(data) {
    const resultsEl = document.getElementById('cleaning-results');
    resultsEl.classList.remove('hidden');

    // Before/After scores
    document.getElementById('before-score').textContent = data.before_score ?? '—';
    document.getElementById('after-score').textContent = data.after_score ?? '—';

    // Before details
    const beforeDetails = document.getElementById('before-details');
    beforeDetails.innerHTML = `
        <div style="font-size: 0.85rem; color: var(--text-muted);">
            <div>Rows: ${data.cleaning_result.original_rows.toLocaleString()}</div>
            <div>Issues: ${data.before_issues_count}</div>
        </div>
    `;

    // After details
    const afterDetails = document.getElementById('after-details');
    afterDetails.innerHTML = `
        <div style="font-size: 0.85rem; color: var(--text-muted);">
            <div>Rows: ${data.cleaning_result.cleaned_rows.toLocaleString()}</div>
            <div>Issues: ${data.after_issues_count}</div>
            <div>Rows removed: ${data.cleaning_result.rows_removed}</div>
        </div>
    `;

    // Operations log
    const opsLog = document.getElementById('ops-log');
    opsLog.innerHTML = '<h4 style="color: var(--text-primary); margin-bottom: var(--space-sm);">📝 Operations Log</h4>';
    data.cleaning_result.operations_applied.forEach(op => {
        opsLog.innerHTML += `
            <div class="ops-log-item">
                <span class="ops-icon">✓</span>
                <span><strong>${op.type.replace(/_/g, ' ')}</strong> on <em>${op.column}</em> — ${op.strategy}
                    ${op.filled_count ? ` (${op.filled_count} filled)` : ''}
                    ${op.rows_removed ? ` (${op.rows_removed} rows removed)` : ''}
                    ${op.affected_count ? ` (${op.affected_count} modified)` : ''}
                </span>
            </div>
        `;
    });

    // Data preview
    if (data.preview) {
        const previewEl = document.getElementById('cleaned-preview-table');
        previewEl.innerHTML = buildPreviewTable(data.preview.cleaned);
    }
}

function buildPreviewTable(preview) {
    if (!preview || !preview.columns) return '';
    let html = '<table class="preview-table"><thead><tr>';
    html += preview.columns.map(c => `<th>${c}</th>`).join('');
    html += '</tr></thead><tbody>';
    html += preview.rows.map(row =>
        '<tr>' + row.map(cell => `<td>${cell}</td>`).join('') + '</tr>'
    ).join('');
    html += '</tbody></table>';
    return html;
}

// ── Export ──────────────────────────────────────────────────────────
function enableExportButtons() {
    document.getElementById('btn-download-csv').disabled = false;
    document.getElementById('btn-download-xlsx').disabled = false;
}

function updateExportButtons() {
    document.getElementById('btn-download-report').disabled = !state.analysis;
}

async function downloadFile(type) {
    try {
        const res = await fetch(`${API_BASE}/download/${state.sessionId}/${type}`);
        if (!res.ok) {
            const data = await res.json();
            showError(data.error || 'Download failed');
            return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${state.filename.replace(/\.[^.]+$/, '')}_cleaned.${type}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showSuccess(`Downloaded as ${type.toUpperCase()}!`);
    } catch (err) {
        showError('Download failed: ' + err.message);
    }
}

async function downloadReport() {
    showLoading('Generating PDF report...', 'Creating comprehensive analysis document');

    try {
        const res = await fetch(`${API_BASE}/report/${state.sessionId}`);
        if (!res.ok) {
            const data = await res.json();
            showError(data.error || 'Report generation failed');
            hideLoading();
            return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${state.filename.replace(/\.[^.]+$/, '')}_quality_report.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        hideLoading();
        showSuccess('Report downloaded!');
    } catch (err) {
        showError('Report download failed: ' + err.message);
        hideLoading();
    }
}

// ── Reset ──────────────────────────────────────────────────────────
function resetApp() {
    state = {
        sessionId: null,
        filename: null,
        analysis: null,
        recommendations: null,
        cleaningResult: null,
        selectedCleanOps: new Set(),
        charts: {},
    };

    // Reset UI
    document.getElementById('header-actions').classList.add('hidden');
    document.getElementById('nav-tabs').classList.add('hidden');
    document.getElementById('issues-badge').classList.add('hidden');

    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('section-upload').classList.add('active');

    document.getElementById('file-input').value = '';
    document.getElementById('cleaning-results').classList.add('hidden');

    // Disable export buttons
    document.getElementById('btn-download-csv').disabled = true;
    document.getElementById('btn-download-xlsx').disabled = true;
    document.getElementById('btn-download-report').disabled = true;

    // Destroy charts
    Object.values(state.charts).forEach(c => { try { c.destroy(); } catch(e) {} });
}

// ── Loading / Toast ────────────────────────────────────────────────
function showLoading(text, subtext) {
    document.getElementById('loading-text').textContent = text || 'Processing...';
    document.getElementById('loading-subtext').textContent = subtext || '';
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

function showError(message) {
    const toast = document.getElementById('error-toast');
    document.getElementById('error-message').textContent = message;
    toast.classList.add('visible');
    setTimeout(() => toast.classList.remove('visible'), 6000);
}

function hideError() {
    document.getElementById('error-toast').classList.remove('visible');
}

function showSuccess(message) {
    const toast = document.getElementById('success-toast');
    document.getElementById('success-message').textContent = message;
    toast.classList.add('visible');
    setTimeout(() => toast.classList.remove('visible'), 4000);
}

// ── Utilities ──────────────────────────────────────────────────────
function truncate(str, len) {
    return str.length > len ? str.substring(0, len) + '…' : str;
}
