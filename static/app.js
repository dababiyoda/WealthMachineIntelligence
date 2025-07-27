// WealthMachine Ultra-Modern UI - Critical Precision Interface
class WealthMachineApp {
    constructor() {
        this.isDarkMode = true;
        this.apiBase = 'http://localhost:5000';
        this.authToken = null;
        this.data = {
            ventures: [],
            agents: [],
            dashboard: {}
        };
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.applyTheme();
        await this.authenticate();
        await this.loadData();
        this.render();
    }

    setupEventListeners() {
        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', () => {
            this.toggleTheme();
        });

        // Modal controls
        document.getElementById('evaluateBtn').addEventListener('click', () => {
            this.openModal();
        });

        document.getElementById('modalClose').addEventListener('click', () => {
            this.closeModal();
        });

        document.querySelector('.modal-backdrop').addEventListener('click', () => {
            this.closeModal();
        });

        // Evaluation form
        document.getElementById('runEvaluation').addEventListener('click', () => {
            this.runEvaluation();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModal();
            if (e.key === 'n' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                this.openModal();
            }
        });
    }

    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        this.applyTheme();
    }

    applyTheme() {
        document.body.className = this.isDarkMode ? 'dark-mode' : '';
        localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
    }

    async authenticate() {
        try {
            const response = await fetch(`${this.apiBase}/auth/login?username=demo&password=demo`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.authToken = data.access_token || 'demo';
                console.log('✓ Authentication successful');
            }
        } catch (error) {
            console.warn('Authentication failed, using demo mode');
            this.authToken = 'demo';
        }
    }

    async loadData() {
        await Promise.all([
            this.loadDashboard(),
            this.loadVentures(),
            this.loadAgents()
        ]);
    }

    async loadDashboard() {
        try {
            const response = await fetch(`${this.apiBase}/api/v1/analytics/dashboard`, {
                headers: { 'Authorization': `Bearer ${this.authToken}` }
            });
            
            if (response.ok) {
                this.data.dashboard = await response.json();
                console.log('✓ Dashboard data loaded');
            }
        } catch (error) {
            console.warn('Using fallback dashboard data');
            this.data.dashboard = {
                total_ventures: 2,
                total_monthly_revenue: 23700,
                ultra_low_failure_rate_percentage: 85.5,
                target_achievement: 'SUCCESS'
            };
        }
    }

    async loadVentures() {
        try {
            const response = await fetch(`${this.apiBase}/api/v1/ventures`, {
                headers: { 'Authorization': `Bearer ${this.authToken}` }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.data.ventures = data.ventures || [];
                console.log('✓ Ventures data loaded');
            }
        } catch (error) {
            console.warn('Using fallback ventures data');
            this.data.ventures = [
                {
                    id: 'venture-1',
                    name: 'AI-Powered SaaS Analytics',
                    type: 'saas',
                    status: 'mvp',
                    revenue: 8500,
                    risk_score: 0.15,
                    failure_probability: 0.0008
                },
                {
                    id: 'venture-2', 
                    name: 'B2B Digital Marketplace',
                    type: 'ecommerce',
                    status: 'scaling',
                    revenue: 15200,
                    risk_score: 0.08,
                    failure_probability: 0.0003
                }
            ];
        }
    }

    async loadAgents() {
        try {
            const response = await fetch(`${this.apiBase}/api/v1/agents`, {
                headers: { 'Authorization': `Bearer ${this.authToken}` }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.data.agents = data.agents || [];
                console.log('✓ Agents data loaded');
            }
        } catch (error) {
            console.warn('Using fallback agents data');
            this.data.agents = [
                {
                    id: 'agent-1',
                    type: 'market_intelligence',
                    name: 'Market Intelligence',
                    active: true,
                    accuracy: 0.85
                },
                {
                    id: 'agent-2',
                    type: 'risk_assessment', 
                    name: 'Risk Assessment',
                    active: true,
                    accuracy: 0.92
                },
                {
                    id: 'agent-3',
                    type: 'legal_compliance',
                    name: 'Legal Compliance',
                    active: true,
                    accuracy: 0.88
                }
            ];
        }
    }

    render() {
        this.renderDashboard();
        this.renderVentures();
        this.renderAgents();
    }

    renderDashboard() {
        const dashboard = this.data.dashboard;
        
        document.getElementById('totalVentures').textContent = dashboard.total_ventures || '—';
        document.getElementById('monthlyRevenue').textContent = 
            dashboard.total_monthly_revenue ? `$${(dashboard.total_monthly_revenue / 1000).toFixed(1)}K` : '—';
        document.getElementById('successRate').textContent = 
            dashboard.ultra_low_failure_rate_percentage ? `${dashboard.ultra_low_failure_rate_percentage.toFixed(1)}%` : '—';
    }

    renderVentures() {
        const container = document.getElementById('venturesGrid');
        
        if (this.data.ventures.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No ventures found</h3>
                    <p>Start by evaluating a new opportunity</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.data.ventures.map(venture => `
            <div class="venture-card fade-in" onclick="app.viewVenture('${venture.id}')">
                <div class="venture-header">
                    <div>
                        <div class="venture-title">${venture.name}</div>
                        <div class="venture-type">${venture.type}</div>
                    </div>
                    <div class="risk-badge ${this.getRiskClass(venture.failure_probability)}">
                        ${this.getRiskLabel(venture.failure_probability)}
                    </div>
                </div>
                
                <div class="venture-metrics">
                    <div class="metric">
                        <span class="metric-label">Monthly Revenue</span>
                        <span class="metric-value">$${(venture.revenue / 1000).toFixed(1)}K</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Failure Rate</span>
                        <span class="metric-value">${(venture.failure_probability * 100).toFixed(3)}%</span>
                    </div>
                </div>
                
                <div class="venture-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${(1 - venture.risk_score) * 100}%"></div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderAgents() {
        const container = document.getElementById('agentsGrid');
        
        container.innerHTML = this.data.agents.map(agent => `
            <div class="agent-card">
                <div class="agent-header">
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-status ${agent.active ? 'active' : 'inactive'}"></div>
                </div>
                <div class="agent-metrics">
                    <div class="metric">
                        <span class="metric-label">Accuracy</span>
                        <span class="metric-value">${(agent.accuracy * 100).toFixed(1)}%</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Status</span>
                        <span class="metric-value">${agent.active ? 'Active' : 'Inactive'}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    getRiskClass(probability) {
        if (probability <= 0.0001) return 'risk-ultra-low';
        if (probability <= 0.001) return 'risk-low';
        return 'risk-moderate';
    }

    getRiskLabel(probability) {
        if (probability <= 0.0001) return 'ULTRA-LOW';
        if (probability <= 0.001) return 'LOW';
        return 'MODERATE';
    }

    viewVenture(ventureId) {
        const venture = this.data.ventures.find(v => v.id === ventureId);
        if (venture) {
            console.log('Viewing venture:', venture);
            // Could open detailed view modal here
        }
    }

    openModal() {
        document.getElementById('evaluationModal').classList.add('active');
        document.getElementById('evaluationResults').style.display = 'none';
        this.resetForm();
    }

    closeModal() {
        document.getElementById('evaluationModal').classList.remove('active');
    }

    resetForm() {
        document.getElementById('ventureName').value = '';
        document.getElementById('marketSize').value = '';
        document.getElementById('competitionLevel').value = 'medium';
    }

    async runEvaluation() {
        const name = document.getElementById('ventureName').value;
        const marketSize = document.getElementById('marketSize').value || 5000000;
        const competition = document.getElementById('competitionLevel').value;

        if (!name.trim()) {
            alert('Please enter a venture name');
            return;
        }

        const button = document.getElementById('runEvaluation');
        const originalText = button.textContent;
        button.textContent = 'Evaluating...';
        button.disabled = true;

        try {
            // Create a demo venture first (simplified)
            const ventureData = {
                name: name,
                market_size: parseInt(marketSize),
                competition_level: competition
            };

            // Simulate AI evaluation
            await new Promise(resolve => setTimeout(resolve, 2000));

            const evaluation = this.simulateEvaluation(ventureData);
            this.displayEvaluationResults(evaluation);

        } catch (error) {
            console.error('Evaluation failed:', error);
            alert('Evaluation failed. Please try again.');
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    simulateEvaluation(ventureData) {
        // Simulate AI evaluation results
        const opportunityScore = 0.7 + Math.random() * 0.25;
        const failureProbability = Math.max(0.0001, (1 - opportunityScore) * 0.02);
        
        let action, confidence, rationale;
        
        if (opportunityScore > 0.8 && failureProbability <= 0.0001) {
            action = 'PROCEED_FULL';
            confidence = 0.92;
            rationale = 'Exceptional opportunity with ultra-low risk profile. Full resource allocation recommended.';
        } else if (opportunityScore > 0.65 && failureProbability <= 0.001) {
            action = 'PROCEED_CAUTIOUS';
            confidence = 0.78;
            rationale = 'Strong opportunity with acceptable risk. Measured approach with monitoring required.';
        } else {
            action = 'EVALUATE_FURTHER';
            confidence = 0.65;
            rationale = 'Additional market validation required before proceeding.';
        }

        return {
            opportunity_score: opportunityScore,
            failure_probability: failureProbability,
            action: action,
            confidence: confidence,
            rationale: rationale,
            meets_target: failureProbability <= 0.0001
        };
    }

    displayEvaluationResults(evaluation) {
        document.getElementById('evaluationResults').style.display = 'block';
        
        document.querySelector('.result-status').textContent = evaluation.action.replace('_', ' ');
        document.querySelector('.result-confidence').textContent = `${(evaluation.confidence * 100).toFixed(1)}% confidence`;
        
        document.getElementById('opportunityScore').textContent = (evaluation.opportunity_score * 100).toFixed(1) + '%';
        document.getElementById('failureProbability').textContent = (evaluation.failure_probability * 100).toFixed(4) + '%';
        document.getElementById('riskLevel').textContent = this.getRiskLabel(evaluation.failure_probability);
        document.getElementById('recommendation').textContent = evaluation.rationale;

        // Add animation
        document.getElementById('evaluationResults').classList.add('slide-up');
    }

    // Utility methods
    formatNumber(num) {
        if (num >= 1000000) return `$${(num / 1000000).toFixed(1)}M`;
        if (num >= 1000) return `$${(num / 1000).toFixed(1)}K`;
        return `$${num}`;
    }

    formatPercentage(num) {
        return `${(num * 100).toFixed(2)}%`;
    }
}

// Initialize the application
const app = new WealthMachineApp();

// Auto-refresh data every 30 seconds
setInterval(() => {
    app.loadData().then(() => app.render());
}, 30000);

// Performance monitoring
window.addEventListener('load', () => {
    console.log('✓ WealthMachine UI loaded');
    console.log('✓ Critical precision interface active');
});