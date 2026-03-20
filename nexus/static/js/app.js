/**
 * Core Application Logic for NEXUS
 */

// Debounce helper
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

class NexusApp {
    constructor() {
        // DOM Elements
        this.form = document.getElementById('analyze-form');
        this.input = document.getElementById('emergency-input');
        this.charCounter = document.getElementById('char-counter');
        this.uploadBtn = document.getElementById('upload-btn');
        this.fileInput = document.getElementById('image-upload-input');
        this.imagePreviewZone = document.getElementById('image-preview-zone');
        this.imageThumb = document.getElementById('image-thumb');
        this.filenameSpan = document.getElementById('image-filename');
        this.filesizeSpan = document.getElementById('image-size');
        this.clearImageBtn = document.getElementById('clear-image-btn');
        
        this.submitBtn = document.getElementById('analyze-btn');
        this.errorAlert = document.getElementById('error-message');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.resultsPanel = document.getElementById('results-panel');
        
        // State
        this.currentImageB64 = null;
        this.scenarios = [];

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDemoScenarios();
    }

    bindEvents() {
        // Textarea limit & counter
        const debouncedCount = debounce(() => {
            const count = this.input.value.length;
            this.charCounter.textContent = `${count.toLocaleString()} / 10,000`;
            if (count >= 10000) {
                this.charCounter.style.color = 'var(--color-critical)';
            } else {
                this.charCounter.style.color = '';
            }
        }, 300);
        
        this.input.addEventListener('input', debouncedCount);

        // Upload handlers
        this.uploadBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.clearImageBtn.addEventListener('click', () => this.clearImage());

        // Form Submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.analyze();
        });

        // Keyboard Shortcut Control+Enter or Cmd+Enter
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                if (!this.submitBtn.disabled) {
                    this.analyze();
                }
            }
        });
    }

    async loadDemoScenarios() {
        try {
            const response = await fetch('/api/demo');
            if (response.ok) {
                const data = await response.json();
                this.scenarios = data.scenarios || [];
                this.renderScenarios();
            }
        } catch (error) {
            console.error("Failed to load demo scenarios:", error);
        }
    }

    renderScenarios() {
        const container = document.getElementById('scenarios-container');
        container.innerHTML = '';

        this.scenarios.forEach((scenario, index) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'scenario-card';
            btn.setAttribute('role', 'button');
            btn.setAttribute('aria-pressed', 'false');
            btn.setAttribute('aria-label', `Select ${scenario.title} scenario`);
            
            btn.innerHTML = `
                <div class="card-header">
                    <span class="card-icon" aria-hidden="true">${scenario.icon}</span>
                    <span class="card-category">${scenario.category}</span>
                </div>
                <h3>${scenario.title}</h3>
            `;

            btn.addEventListener('click', () => {
                // Focus styling
                document.querySelectorAll('.scenario-card').forEach(c => c.setAttribute('aria-pressed', 'false'));
                btn.setAttribute('aria-pressed', 'true');
                
                // Populate input
                this.input.value = scenario.input;
                this.input.dispatchEvent(new Event('input')); // Trigger char counter
            });

            // Keyboard navigation between scenario cards
            btn.addEventListener('keydown', (e) => {
                let target = null;
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    target = btn.nextElementSibling || container.firstElementChild;
                } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    target = btn.previousElementSibling || container.lastElementChild;
                }
                
                if (target) {
                    e.preventDefault();
                    target.focus();
                }
            });

            container.appendChild(btn);
        });
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validations
        const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            this.showError("Please upload a valid JPEG, PNG, or WebP image.");
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            this.showError("Image size must be less than 5MB.");
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.currentImageB64 = e.target.result;
            this.imageThumb.src = this.currentImageB64;
            this.filenameSpan.textContent = file.name;
            this.filesizeSpan.textContent = (file.size / 1024).toFixed(1) + " KB";
            this.imagePreviewZone.classList.remove('hidden');
            this.hideError();
        };
        reader.readAsDataURL(file);
    }

    clearImage() {
        this.currentImageB64 = null;
        this.fileInput.value = '';
        this.imagePreviewZone.classList.add('hidden');
    }

    showError(msg) {
        this.errorAlert.textContent = msg;
        this.errorAlert.classList.remove('hidden');
    }

    hideError() {
        this.errorAlert.classList.add('hidden');
    }

    setLoading(isLoading) {
        this.submitBtn.disabled = isLoading;
        if (isLoading) {
            this.submitBtn.innerHTML = `
                <span class="spinner" style="width:20px;height:20px;border-width:2px;margin:0"></span>
                <span class="btn-text">Analyzing...</span>
            `;
            this.loadingOverlay.classList.remove('hidden');
            this.resultsPanel.setAttribute('aria-busy', 'true');
        } else {
            this.submitBtn.innerHTML = `
                <span class="btn-text">Analyze Emergency</span>
                <span class="material-symbols-rounded">bolt</span>
            `;
            this.loadingOverlay.classList.add('hidden');
            this.resultsPanel.setAttribute('aria-busy', 'false');
        }
    }

    async analyze() {
        const text = this.input.value.trim();
        if (!text && !this.currentImageB64) {
            this.showError("Please enter text or upload an image to analyze.");
            return;
        }

        this.hideError();
        this.setLoading(true);

        try {
            // Check geolocation context
            let context = "";
            if ("geolocation" in navigator) {
                try {
                    const pos = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 3000 });
                    });
                    context = `User Location: Lat ${pos.coords.latitude}, Lng ${pos.coords.longitude}`;
                } catch (e) {
                    console.warn("Geolocation denied or timed out.");
                }
            }

            const payload = {
                text: text,
                image: this.currentImageB64,
                context: context
            };

            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP Error ${response.status}`);
            }

            const data = await response.json();
            
            // Render the results
            this.renderResults(data);

        } catch (error) {
            this.showError("Analysis failed: " + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    renderResults(plan) {
        document.getElementById('empty-state').classList.add('hidden');
        document.getElementById('analysis-results').classList.remove('hidden');

        // 1. Severity Banner
        const banner = document.getElementById('severity-banner');
        banner.className = `severity-banner severity-${plan.severity}`;
        
        const severityIcons = {
            'CRITICAL': 'warning',
            'HIGH': 'error',
            'MEDIUM': 'info',
            'LOW': 'check_circle'
        };
        document.getElementById('severity-icon').textContent = severityIcons[plan.severity] || 'warning';
        document.getElementById('severity-label').textContent = plan.severity;
        document.getElementById('severity-label').setAttribute('aria-label', `Severity level: ${plan.severity}`);
        document.getElementById('confidence-percentage').textContent = `${(plan.confidence * 100).toFixed(0)}% confidence`;

        // 2. Intent & Metrics
        document.getElementById('intent-text').textContent = plan.intent;
        document.getElementById('location-text').textContent = plan.location || "Unknown Location";
        document.getElementById('people-text').textContent = plan.affected_people || "Unknown Casualties";

        // 3. Action Cards
        const cardsContainer = document.getElementById('action-cards');
        cardsContainer.innerHTML = '';

        if (plan.immediate_actions && plan.immediate_actions.length > 0) {
            plan.immediate_actions.forEach((action, index) => {
                const card = document.createElement('article');
                card.className = 'action-card';
                card.setAttribute('role', 'article');
                card.setAttribute('aria-label', `Action ${action.priority}: ${action.title}`);

                const verifiedHtml = action.verified ? 
                    `<span class="meta-tag"><span class="material-symbols-rounded verified-icon">verified</span> Verified</span>` : 
                    `<span class="meta-tag"><span class="material-symbols-rounded" style="color:var(--color-medium)">help</span> Unverified</span>`;
                
                const phoneHtml = action.phone_number ? 
                    `<span class="meta-tag"><span class="material-symbols-rounded" style="font-size:1rem">call</span> ${action.phone_number}</span>` : '';

                card.innerHTML = `
                    <div class="card-top">
                        <div class="priority-badge priority-${action.priority}" aria-hidden="true">${action.priority}</div>
                        <div class="action-content">
                            <h4>${action.title}</h4>
                            <p class="action-desc">${action.description}</p>
                            <div class="action-meta">
                                <span class="meta-tag"><span class="material-symbols-rounded" style="font-size:1rem">business</span> ${action.agency}</span>
                                <span class="meta-tag"><span class="material-symbols-rounded" style="font-size:1rem">timer</span> ${action.estimated_time}</span>
                                ${phoneHtml}
                                ${verifiedHtml}
                            </div>
                        </div>
                    </div>
                `;
                cardsContainer.appendChild(card);

                // Animate in with staggered delay using requestAnimationFrame
                requestAnimationFrame(() => {
                    setTimeout(() => {
                        card.classList.add('visible');
                    }, index * 60);
                });
            });
        }

        // 4. Secondary Sections (Medical)
        const medSection = document.getElementById('medical-summary-section');
        if (plan.medical_summary) {
            document.getElementById('medical-summary-text').textContent = plan.medical_summary;
            medSection.classList.remove('hidden');
        } else {
            medSection.classList.add('hidden');
        }

        // 5. External Integrations
        if (window.mapsManager) {
            window.mapsManager.initMap(plan.location);
        }
        
        if (window.chartsManager) {
            document.getElementById('charts-section').classList.remove('hidden');
            window.chartsManager.drawCharts(plan);
        }

        // Screen reader announcement
        let announcement = `Analysis complete. ${plan.severity} severity. ${plan.immediate_actions.length} actions generated.`;
        
        // Use a temporary live region to assure it gets read
        const a11yLogger = document.createElement('div');
        a11yLogger.setAttribute('role', 'status');
        a11yLogger.setAttribute('aria-live', 'polite');
        a11yLogger.className = 'visually-hidden';
        a11yLogger.textContent = announcement;
        document.body.appendChild(a11yLogger);
        setTimeout(() => a11yLogger.remove(), 3000);
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.nexusApp = new NexusApp();
});
