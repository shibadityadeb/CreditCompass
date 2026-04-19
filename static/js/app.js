(function() {
    'use strict';
    const CONFIG = {
        API_ENDPOINT: '/predict',
        HEALTH_ENDPOINT: '/health',
        ANIMATION_DURATION: 1000,
        DEBOUNCE_DELAY: 300
    };
    const elements = {
        form: null,
        submitBtn: null,
        resetBtn: null,
        resultCard: null,
        resultPlaceholder: null,
        resultLoading: null,
        resultError: null,
        resultSuccess: null,
        errorMessage: null,
        retryBtn: null,
        gaugeFill: null,
        gaugeValue: null,
        riskIndicator: null,
        riskBadge: null,
        riskLevel: null,
        resultMessage: null,
        riskClassification: null,
        confidenceLevel: null,
        newAssessmentBtn: null,
        systemStatus: null
    };
    function $(selector) {
        return document.querySelector(selector);
    }
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    function validateNumber(value, min, max) {
        const num = parseFloat(value);
        return !isNaN(num) && num >= min && num <= max;
    }
    function formatPercentage(value) {
        return `${(value * 100).toFixed(2)}%`;
    }
    function calculateGaugeOffset(probability) {
        const maxOffset = 251.2; 
        return maxOffset - (probability * maxOffset);
    }
    function getGaugeColor(riskClass) {
        const colors = {
            low: '#10b981',
            medium: '#f59e0b',
            high: '#ef4444'
        };
        return colors[riskClass] || colors.low;
    }
    const UIState = {
        IDLE: 'idle',
        LOADING: 'loading',
        SUCCESS: 'success',
        ERROR: 'error'
    };
    let currentState = UIState.IDLE;
    let lastSubmitData = null;
    function updateUIState(state, data = null) {
        currentState = state;
        elements.resultPlaceholder.classList.add('hidden');
        elements.resultLoading.classList.add('hidden');
        elements.resultError.classList.add('hidden');
        elements.resultSuccess.classList.add('hidden');
        elements.submitBtn.disabled = state === UIState.LOADING;
        elements.submitBtn.classList.toggle('loading', state === UIState.LOADING);
        switch (state) {
            case UIState.IDLE:
                elements.resultPlaceholder.classList.remove('hidden');
                break;
            case UIState.LOADING:
                elements.resultLoading.classList.remove('hidden');
                break;
            case UIState.SUCCESS:
                elements.resultSuccess.classList.remove('hidden');
                if (data) {
                    displayResults(data);
                }
                break;
            case UIState.ERROR:
                elements.resultError.classList.remove('hidden');
                if (data && data.error) {
                    elements.errorMessage.textContent = data.error;
                }
                break;
        }
    }
    async function predictRisk(formData) {
        const response = await fetch(CONFIG.API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Prediction failed');
        }
        if (!data.success) {
            throw new Error(data.error || 'Unknown error occurred');
        }
        return data;
    }
    async function checkHealth() {
        try {
            const response = await fetch(CONFIG.HEALTH_ENDPOINT);
            const data = await response.json();
            const statusDot = elements.systemStatus.querySelector('.status-dot');
            if (data.status === 'healthy' && data.model_loaded) {
                statusDot.style.background = '#10b981';
                elements.systemStatus.innerHTML = '<span class="status-dot" style="background: #10b981"></span> System Online';
            } else {
                statusDot.style.background = '#f59e0b';
                elements.systemStatus.innerHTML = '<span class="status-dot" style="background: #f59e0b"></span> System Degraded';
            }
        } catch (error) {
            console.error('Health check failed:', error);
            elements.systemStatus.innerHTML = '<span class="status-dot" style="background: #ef4444"></span> System Offline';
        }
    }
    function getFormData() {
        const formData = {};
        const inputs = elements.form.querySelectorAll('input[type="number"]');
        inputs.forEach(input => {
            const value = parseFloat(input.value);
            formData[input.name] = isNaN(value) ? 0 : value;
        });
        return formData;
    }
    function validateFormData(formData) {
        const validationRules = {
            rev_util: { min: 0, max: 10 },
            age: { min: 18, max: 120 },
            late_30_59: { min: 0, max: 50 },
            debt_ratio: { min: 0, max: 100 },
            monthly_inc: { min: 0, max: 10000000 },
            open_credit: { min: 0, max: 100 },
            late_90: { min: 0, max: 50 },
            real_estate: { min: 0, max: 50 },
            late_60_89: { min: 0, max: 50 },
            dependents: { min: 0, max: 20 }
        };
        const errors = [];
        for (const [field, rules] of Object.entries(validationRules)) {
            if (formData[field] === undefined || formData[field] === null) {
                errors.push(`${field} is required`);
                continue;
            }
            if (!validateNumber(formData[field], rules.min, rules.max)) {
                errors.push(`${field} must be between ${rules.min} and ${rules.max}`);
            }
        }
        return errors;
    }
    async function handleSubmit(event) {
        event.preventDefault();
        const formData = getFormData();
        const validationErrors = validateFormData(formData);
        if (validationErrors.length > 0) {
            updateUIState(UIState.ERROR, { error: validationErrors[0] });
            return;
        }
        lastSubmitData = formData;
        updateUIState(UIState.LOADING);
        try {
            const result = await predictRisk(formData);
            updateUIState(UIState.SUCCESS, result);
        } catch (error) {
            console.error('Prediction error:', error);
            updateUIState(UIState.ERROR, { error: error.message });
        }
    }
    function handleReset() {
        updateUIState(UIState.IDLE);
        lastSubmitData = null;
    }
    function displayResults(data) {
        const { probability, risk_level, risk_class, message } = data;
        animateGauge(probability, risk_class);
        elements.riskBadge.className = `risk-badge ${risk_class}`;
        elements.riskLevel.textContent = risk_level;
        elements.resultMessage.textContent = message;
        elements.riskClassification.textContent = risk_level;
        const confidence = calculateConfidence(probability);
        elements.confidenceLevel.textContent = confidence;
    }
    function animateGauge(probability, riskClass) {
        const targetOffset = calculateGaugeOffset(probability);
        const color = getGaugeColor(riskClass);
        elements.gaugeFill.style.stroke = color;
        let currentValue = 0;
        const targetValue = probability * 100;
        const startTime = performance.now();
        function updateValue(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / CONFIG.ANIMATION_DURATION, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            currentValue = targetValue * eased;
            elements.gaugeValue.textContent = `${currentValue.toFixed(1)}%`;
            const currentOffset = calculateGaugeOffset(probability * eased);
            elements.gaugeFill.style.strokeDashoffset = currentOffset;
            if (progress < 1) {
                requestAnimationFrame(updateValue);
            }
        }
        requestAnimationFrame(updateValue);
    }
    function calculateConfidence(probability) {
        const distFromMedium = Math.abs(probability - 0.4);
        const distFromHigh = Math.abs(probability - 0.7);
        const minDist = Math.min(distFromMedium, distFromHigh, probability, 1 - probability);
        if (minDist > 0.2) return 'Very High';
        if (minDist > 0.1) return 'High';
        if (minDist > 0.05) return 'Moderate';
        return 'Low';
    }
    function handleRetry() {
        if (lastSubmitData) {
            handleSubmit({ preventDefault: () => {} });
        } else {
            updateUIState(UIState.IDLE);
        }
    }
    function handleNewAssessment() {
        elements.form.reset();
        updateUIState(UIState.IDLE);
        lastSubmitData = null;
        elements.form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    function setupInputValidation() {
        const inputs = elements.form.querySelectorAll('input[type="number"]');
        inputs.forEach(input => {
            input.addEventListener('input', debounce(function() {
                const value = parseFloat(this.value);
                const min = parseFloat(this.min);
                const max = parseFloat(this.max);
                if (isNaN(value) || value < min || value > max) {
                    this.classList.add('invalid');
                } else {
                    this.classList.remove('invalid');
                }
            }, CONFIG.DEBOUNCE_DELAY));
        });
    }
    function cacheElements() {
        elements.form = $('#creditForm');
        elements.submitBtn = $('#submitBtn');
        elements.resetBtn = $('#resetBtn');
        elements.resultCard = $('#resultCard');
        elements.resultPlaceholder = $('#resultPlaceholder');
        elements.resultLoading = $('#resultLoading');
        elements.resultError = $('#resultError');
        elements.resultSuccess = $('#resultSuccess');
        elements.errorMessage = $('#errorMessage');
        elements.retryBtn = $('#retryBtn');
        elements.gaugeFill = $('#gaugeFill');
        elements.gaugeValue = $('#gaugeValue');
        elements.riskIndicator = $('#riskIndicator');
        elements.riskBadge = $('#riskBadge');
        elements.riskLevel = $('#riskLevel');
        elements.resultMessage = $('#resultMessage');
        elements.riskClassification = $('#riskClassification');
        elements.confidenceLevel = $('#confidenceLevel');
        elements.newAssessmentBtn = $('#newAssessmentBtn');
        elements.systemStatus = $('#systemStatus');
    }
    function bindEvents() {
        elements.form.addEventListener('submit', handleSubmit);
        elements.form.addEventListener('reset', handleReset);
        elements.retryBtn.addEventListener('click', handleRetry);
        elements.newAssessmentBtn.addEventListener('click', handleNewAssessment);
    }
    function init() {
        cacheElements();
        bindEvents();
        setupInputValidation();
        checkHealth();
        setInterval(checkHealth, 30000);
        console.log('CreditCompass initialized successfully');
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();


// =============================================================================
// Milestone 2: AI Lending Assessment Module
// Handles the "Get Full AI Lending Assessment" button and /assess API call
// =============================================================================

(function() {
    'use strict';

    const AI_ENDPOINT = '/assess';

    // ──────────────────────────────────────────────────────────────────────────
    // DOM Helpers
    // ──────────────────────────────────────────────────────────────────────────

    function $(id) { return document.getElementById(id); }

    function showEl(id)  { const el = $(id); if (el) el.classList.remove('hidden'); }
    function hideEl(id)  { const el = $(id); if (el) el.classList.add('hidden'); }
    function setText(id, text) { const el = $(id); if (el) el.textContent = text; }

    // ──────────────────────────────────────────────────────────────────────────
    // Read current form data
    // ──────────────────────────────────────────────────────────────────────────

    function getFormData() {
        const form = document.getElementById('creditForm');
        if (!form) return {};
        const data = {};
        form.querySelectorAll('input[type="number"]').forEach(input => {
            const val = parseFloat(input.value);
            data[input.name] = isNaN(val) ? null : val;
        });
        return data;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Animated loading steps (purely cosmetic — improves UX)
    // ──────────────────────────────────────────────────────────────────────────

    let stepTimer = null;

    function startLoadingSteps() {
        const steps = ['step1', 'step2', 'step3', 'step4'];
        let current = 0;

        // Reset all
        steps.forEach(id => {
            const el = $(id);
            if (el) {
                el.classList.remove('active', 'done');
            }
        });

        function advance() {
            if (current > 0) {
                const prev = $(steps[current - 1]);
                if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
            }
            if (current < steps.length) {
                const curr = $(steps[current]);
                if (curr) curr.classList.add('active');
                current++;
                // Steps 1-3 take ~1.5s each, step 4 stays active until response
                if (current < steps.length) {
                    stepTimer = setTimeout(advance, 1500);
                }
            }
        }
        advance();
    }

    function stopLoadingSteps() {
        if (stepTimer) clearTimeout(stepTimer);
        // Mark all as done
        ['step1', 'step2', 'step3', 'step4'].forEach(id => {
            const el = $(id);
            if (el) { el.classList.remove('active'); el.classList.add('done'); }
        });
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Decision badge rendering
    // ──────────────────────────────────────────────────────────────────────────

    const DECISION_CONFIG = {
        'APPROVE': { cls: 'approve', icon: '✅', label: 'APPROVE'  },
        'REVIEW':  { cls: 'review',  icon: '🔍', label: 'REVIEW'   },
        'REJECT':  { cls: 'reject',  icon: '❌', label: 'REJECT'   },
    };

    function renderDecision(decision) {
        const cfg = DECISION_CONFIG[decision.toUpperCase()] || DECISION_CONFIG['REVIEW'];
        const badge = $('decisionBadge');
        if (badge) {
            badge.className = `decision-badge ${cfg.cls}`;
        }
        setText('decisionIcon', cfg.icon);
        setText('decisionText', cfg.label);
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Render the full AI report
    // ──────────────────────────────────────────────────────────────────────────

    function renderReport(data) {
        const { recommendation, missing_fields } = data;

        // Decision badge
        renderDecision(recommendation.lending_decision || 'REVIEW');

        // Missing data alert
        if (missing_fields && missing_fields.length > 0) {
            showEl('missingDataAlert');
            setText('missingFieldsList',
                `Missing fields: ${missing_fields.join(', ')}. Default values were used.`
            );
        } else {
            hideEl('missingDataAlert');
        }

        // Report sections
        setText('rptBorrowerSummary', recommendation.borrower_summary || '—');
        setText('rptRiskAnalysis',    recommendation.credit_risk_analysis || '—');
        setText('rptRationale',       recommendation.decision_rationale || '—');
        setText('rptMitigation',      recommendation.risk_mitigation_suggestions || '—');
        setText('rptReferences',      recommendation.regulatory_references || '—');
        setText('rptDisclaimer',      recommendation.disclaimer || '—');
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Main: run assessment
    // ──────────────────────────────────────────────────────────────────────────

    async function runAIAssessment() {
        const formData = getFormData();
        const btn = $('aiAssessBtn');

        // Show section with loading card
        showEl('aiReportSection');
        showEl('aiLoadingCard');
        hideEl('aiReportCard');

        // Scroll to loading
        const section = $('aiReportSection');
        if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Disable button + show spinner
        if (btn) { btn.disabled = true; btn.classList.add('loading'); }

        startLoadingSteps();

        try {
            const response = await fetch(AI_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });

            const result = await response.json();

            stopLoadingSteps();
            hideEl('aiLoadingCard');

            if (!result.success) {
                alert('AI Assessment failed: ' + (result.error || 'Unknown error'));
                hideEl('aiReportSection');
                return;
            }

            renderReport(result);
            showEl('aiReportCard');

            // Scroll to report
            const card = $('aiReportCard');
            if (card) setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);

        } catch (err) {
            stopLoadingSteps();
            hideEl('aiLoadingCard');
            hideEl('aiReportSection');
            console.error('AI assessment error:', err);
            alert('AI Assessment failed. Please check your connection and try again.');
        } finally {
            if (btn) { btn.disabled = false; btn.classList.remove('loading'); }
        }
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Initialise event listeners
    // ──────────────────────────────────────────────────────────────────────────

    function initAI() {
        // Show AI button only after ML result is shown
        // We observe the result-success element visibility
        const mlSuccessEl = document.getElementById('resultSuccess');
        const aiWrapper   = document.getElementById('aiAssessBtnWrapper');

        if (mlSuccessEl && aiWrapper) {
            // Use MutationObserver to watch when ML result appears
            const observer = new MutationObserver(() => {
                const isVisible = !mlSuccessEl.classList.contains('hidden');
                if (isVisible) {
                    aiWrapper.style.display = 'block';
                } else {
                    aiWrapper.style.display = 'none';
                    // Also hide AI report if form is reset
                    hideEl('aiReportSection');
                }
            });
            observer.observe(mlSuccessEl, { attributes: true, attributeFilter: ['class'] });
            // Initial state: hidden until ML result appears
            aiWrapper.style.display = 'none';
        }

        // AI assess button click
        const aiBtn = document.getElementById('aiAssessBtn');
        if (aiBtn) aiBtn.addEventListener('click', runAIAssessment);

        // Close/new assessment buttons inside report
        const closeBtn = document.getElementById('closeReportBtn');
        if (closeBtn) closeBtn.addEventListener('click', () => hideEl('aiReportSection'));

        const newFullBtn = document.getElementById('newFullAssessmentBtn');
        if (newFullBtn) newFullBtn.addEventListener('click', () => {
            const form = document.getElementById('creditForm');
            if (form) form.reset();
            // Trigger reset event so Milestone 1 UI resets too
            form.dispatchEvent(new Event('reset'));
            hideEl('aiReportSection');
            form.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAI);
    } else {
        initAI();
    }

})();
