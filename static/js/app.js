/**
 * CreditCompass - Credit Risk Assessment Application
 * Frontend JavaScript for API interaction and UI management
 */

(function() {
    'use strict';

    // ==========================================================================
    // Configuration
    // ==========================================================================

    const CONFIG = {
        API_ENDPOINT: '/predict',
        HEALTH_ENDPOINT: '/health',
        ANIMATION_DURATION: 1000,
        DEBOUNCE_DELAY: 300
    };

    // ==========================================================================
    // DOM Elements
    // ==========================================================================

    const elements = {
        // Form
        form: null,
        submitBtn: null,
        resetBtn: null,
        
        // Result states
        resultCard: null,
        resultPlaceholder: null,
        resultLoading: null,
        resultError: null,
        resultSuccess: null,
        
        // Error elements
        errorMessage: null,
        retryBtn: null,
        
        // Success elements
        gaugeFill: null,
        gaugeValue: null,
        riskIndicator: null,
        riskBadge: null,
        riskLevel: null,
        resultMessage: null,
        riskClassification: null,
        confidenceLevel: null,
        newAssessmentBtn: null,
        
        // System status
        systemStatus: null
    };

    // ==========================================================================
    // Utility Functions
    // ==========================================================================

    /**
     * Safely query DOM element
     */
    function $(selector) {
        return document.querySelector(selector);
    }

    /**
     * Debounce function to limit rapid calls
     */
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

    /**
     * Validate numeric input
     */
    function validateNumber(value, min, max) {
        const num = parseFloat(value);
        return !isNaN(num) && num >= min && num <= max;
    }

    /**
     * Format percentage for display
     */
    function formatPercentage(value) {
        return `${(value * 100).toFixed(2)}%`;
    }

    /**
     * Calculate gauge arc offset based on probability
     */
    function calculateGaugeOffset(probability) {
        const maxOffset = 251.2; // Full arc length
        return maxOffset - (probability * maxOffset);
    }

    /**
     * Get gauge color based on risk class
     */
    function getGaugeColor(riskClass) {
        const colors = {
            low: '#10b981',
            medium: '#f59e0b',
            high: '#ef4444'
        };
        return colors[riskClass] || colors.low;
    }

    // ==========================================================================
    // State Management
    // ==========================================================================

    const UIState = {
        IDLE: 'idle',
        LOADING: 'loading',
        SUCCESS: 'success',
        ERROR: 'error'
    };

    let currentState = UIState.IDLE;
    let lastSubmitData = null;

    /**
     * Update UI based on current state
     */
    function updateUIState(state, data = null) {
        currentState = state;
        
        // Hide all states first
        elements.resultPlaceholder.classList.add('hidden');
        elements.resultLoading.classList.add('hidden');
        elements.resultError.classList.add('hidden');
        elements.resultSuccess.classList.add('hidden');
        
        // Update button states
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

    // ==========================================================================
    // API Communication
    // ==========================================================================

    /**
     * Send prediction request to backend
     */
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

    /**
     * Check system health
     */
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

    // ==========================================================================
    // Form Handling
    // ==========================================================================

    /**
     * Extract form data
     */
    function getFormData() {
        const formData = {};
        const inputs = elements.form.querySelectorAll('input[type="number"]');
        
        inputs.forEach(input => {
            const value = parseFloat(input.value);
            formData[input.name] = isNaN(value) ? 0 : value;
        });
        
        return formData;
    }

    /**
     * Validate form data
     */
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

    /**
     * Handle form submission
     */
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

    /**
     * Handle form reset
     */
    function handleReset() {
        updateUIState(UIState.IDLE);
        lastSubmitData = null;
    }

    // ==========================================================================
    // Results Display
    // ==========================================================================

    /**
     * Display prediction results with animations
     */
    function displayResults(data) {
        const { probability, risk_level, risk_class, message } = data;
        
        // Update gauge
        animateGauge(probability, risk_class);
        
        // Update risk badge
        elements.riskBadge.className = `risk-badge ${risk_class}`;
        elements.riskLevel.textContent = risk_level;
        
        // Update details
        elements.resultMessage.textContent = message;
        elements.riskClassification.textContent = risk_level;
        
        // Calculate confidence based on how far from threshold
        const confidence = calculateConfidence(probability);
        elements.confidenceLevel.textContent = confidence;
    }

    /**
     * Animate the gauge to show probability
     */
    function animateGauge(probability, riskClass) {
        const targetOffset = calculateGaugeOffset(probability);
        const color = getGaugeColor(riskClass);
        
        // Set color
        elements.gaugeFill.style.stroke = color;
        
        // Animate value
        let currentValue = 0;
        const targetValue = probability * 100;
        const startTime = performance.now();
        
        function updateValue(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / CONFIG.ANIMATION_DURATION, 1);
            
            // Easing function (ease-out)
            const eased = 1 - Math.pow(1 - progress, 3);
            
            currentValue = targetValue * eased;
            elements.gaugeValue.textContent = `${currentValue.toFixed(1)}%`;
            
            // Update gauge fill
            const currentOffset = calculateGaugeOffset(probability * eased);
            elements.gaugeFill.style.strokeDashoffset = currentOffset;
            
            if (progress < 1) {
                requestAnimationFrame(updateValue);
            }
        }
        
        requestAnimationFrame(updateValue);
    }

    /**
     * Calculate confidence level based on probability distance from thresholds
     */
    function calculateConfidence(probability) {
        // Distance from nearest threshold (0.4 or 0.7)
        const distFromMedium = Math.abs(probability - 0.4);
        const distFromHigh = Math.abs(probability - 0.7);
        const minDist = Math.min(distFromMedium, distFromHigh, probability, 1 - probability);
        
        if (minDist > 0.2) return 'Very High';
        if (minDist > 0.1) return 'High';
        if (minDist > 0.05) return 'Moderate';
        return 'Low';
    }

    // ==========================================================================
    // Event Handlers
    // ==========================================================================

    /**
     * Handle retry button click
     */
    function handleRetry() {
        if (lastSubmitData) {
            handleSubmit({ preventDefault: () => {} });
        } else {
            updateUIState(UIState.IDLE);
        }
    }

    /**
     * Handle new assessment button click
     */
    function handleNewAssessment() {
        elements.form.reset();
        updateUIState(UIState.IDLE);
        lastSubmitData = null;
        
        // Scroll to form
        elements.form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Add input validation feedback
     */
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

    // ==========================================================================
    // Initialization
    // ==========================================================================

    /**
     * Cache DOM elements
     */
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

    /**
     * Bind event listeners
     */
    function bindEvents() {
        elements.form.addEventListener('submit', handleSubmit);
        elements.form.addEventListener('reset', handleReset);
        elements.retryBtn.addEventListener('click', handleRetry);
        elements.newAssessmentBtn.addEventListener('click', handleNewAssessment);
    }

    /**
     * Initialize the application
     */
    function init() {
        cacheElements();
        bindEvents();
        setupInputValidation();
        checkHealth();
        
        // Periodic health check
        setInterval(checkHealth, 30000);
        
        console.log('CreditCompass initialized successfully');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
