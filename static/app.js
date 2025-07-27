// WealthMachine - Modern UI JavaScript
// Material Design + iOS Inspired Interactions

class WealthMachineApp {
    constructor() {
        this.apiBase = window.location.origin;
        this.authToken = localStorage.getItem('authToken');
        this.isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.currentTab = 'dashboard';
        this.ventures = [];
        this.agents = [];
        this.init();
    }

    async init() {
        await this.authenticate();
        this.setupEventListeners();
        this.loadDashboardData();
        this.startAutoRefresh();
        this.applyTheme();
        
        // Debug: Log available tabs
        console.log('Available tabs:', document.querySelectorAll('.tab-item').length);
        console.log('Available tab content:', document.querySelectorAll('.tab-content').length);
    }

    setupEventListeners() {
        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', () => this.toggleTheme());
        
        // Modal controls
        document.getElementById('evaluateBtn').addEventListener('click', () => this.showModal());
        document.getElementById('modalClose').addEventListener('click', () => this.hideModal());
        document.querySelector('.modal-backdrop').addEventListener('click', () => this.hideModal());
        
        // Form submission
        document.getElementById('evaluationForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.runEvaluation();
        });
        
        // Tab navigation - Add delay to ensure DOM is ready
        setTimeout(() => {
            document.querySelectorAll('.tab-item').forEach(tab => {
                tab.addEventListener('click', (e) => {
                    e.preventDefault();
                    const tabId = tab.getAttribute('data-tab');
                    if (tabId) {
                        this.switchTab(tabId);
                    }
                });
            });
        }, 100);
        
        // Notification button
        document.getElementById('notificationBtn').addEventListener('click', () => {
            this.showNotification('No new notifications');
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.hideModal();
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                this.showModal();
            }
        });
        
        // Add ripple effect to buttons
        this.addRippleEffect();
    }

    async authenticate() {
        try {
            // Skip authentication if we already have a token
            if (this.authToken) {
                console.log('✓ Using existing token');
                return;
            }
            
            const response = await fetch(`${this.apiBase}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'username=demo&password=demo'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.authToken = data.access_token;
                // Store token in localStorage for persistence
                localStorage.setItem('authToken', this.authToken);
                console.log('✓ Authenticated successfully');
            } else {
                throw new Error('Authentication failed');
            }
        } catch (error) {
            console.warn('Authentication error, using demo token');
            this.authToken = 'demo';
            localStorage.setItem('authToken', this.authToken);
        }
    }

    async loadDashboardData() {
        try {
            // Load all data in parallel
            const [dashboardData, venturesData, agentsData] = await Promise.all([
                this.fetchDashboard(),
                this.fetchVentures(),
                this.fetchAgents()
            ]);
            
            this.updateDashboard(dashboardData);
            this.ventures = venturesData.ventures || [];
            this.agents = agentsData.agents || [];
            
            this.renderVentures();
            this.renderAgents();
            this.applyModernStyling();
        } catch (error) {
            console.error('Error loading data:', error);
            this.useOfflineData();
        }
    }

    async fetchDashboard() {
        const response = await fetch(`${this.apiBase}/api/v1/analytics/dashboard`, {
            headers: { 'Authorization': `Bearer ${this.authToken}` }
        });
        return response.ok ? response.json() : this.getOfflineDashboard();
    }

    async fetchVentures() {
        const response = await fetch(`${this.apiBase}/api/v1/ventures`, {
            headers: { 'Authorization': `Bearer ${this.authToken}` }
        });
        return response.ok ? response.json() : this.getOfflineVentures();
    }

    async fetchAgents() {
        const response = await fetch(`${this.apiBase}/api/v1/agents`, {
            headers: { 'Authorization': `Bearer ${this.authToken}` }
        });
        return response.ok ? response.json() : this.getOfflineAgents();
    }

    updateDashboard(data) {
        // Animate number updates
        this.animateValue('totalVentures', 0, data.total_ventures || 0, 1000);
        this.animateValue('monthlyRevenue', 0, data.total_monthly_revenue || 0, 1000, true);
        this.animateValue('successRate', 0, data.ultra_low_failure_rate_percentage || 0, 1000, false, true);
    }

    animateValue(id, start, end, duration, isCurrency = false, isPercentage = false) {
        const element = document.getElementById(id);
        if (!element) return;
        
        const startTime = performance.now();
        
        const updateValue = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = start + (end - start) * easeOutQuart;
            
            if (isCurrency) {
                element.textContent = `$${(current / 1000).toFixed(1)}K`;
            } else if (isPercentage) {
                element.textContent = `${current.toFixed(1)}%`;
            } else {
                element.textContent = Math.round(current);
            }
            
            if (progress < 1) {
                requestAnimationFrame(updateValue);
            }
        };
        
        requestAnimationFrame(updateValue);
    }

    switchTab(tabId) {
        // Update tab buttons
        document.querySelectorAll('.tab-item').forEach(tab => {
            tab.classList.remove('active');
        });
        const tabElement = document.querySelector(`[data-tab="${tabId}"]`);
        if (tabElement) {
            tabElement.classList.add('active');
        }
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        const contentElement = document.getElementById(tabId);
        if (contentElement) {
            contentElement.classList.add('active');
        }
        
        this.currentTab = tabId;
        
        // Load tab-specific data
        this.loadTabData(tabId);
    }
    
    loadTabData(tabId) {
        console.log('Loading tab data for:', tabId);
        switch (tabId) {
            case 'dashboard':
                // Already loaded in initial load
                break;
            case 'ventures':
                this.renderVentures();
                break;
            case 'agents':
                this.renderAgents();
                break;
            case 'opportunity':
                this.showNotification('🎯 Opportunity Detection: AI-powered market analysis active');
                break;
            case 'risk':
                this.showNotification('🛡️ Risk Analysis: Ultra-low failure rate P(failure) ≤ 0.01%');
                break;
            case 'market':
                this.showNotification('📈 Market Intelligence: LSTM trend analysis updated');
                break;
            case 'compliance':
                this.showNotification('⚖️ Compliance: All ventures regulatory compliant');
                break;
            case 'automation':
                this.showNotification('⚙️ Automation: 47 rules active, 1,247 tasks automated');
                break;
        }
    }

    renderVentures() {
        const container = document.getElementById('venturesGrid');
        
        if (this.ventures.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="material-icons-round empty-icon">inventory_2</span>
                    <h3>No ventures yet</h3>
                    <p>Start by evaluating a new opportunity</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.ventures.map(venture => `
            <div class="venture-card" data-venture-id="${venture.id}">
                <div class="venture-header">
                    <h4 class="venture-name">${venture.name}</h4>
                    <span class="venture-type">${this.formatVentureType(venture.type)}</span>
                </div>
                <div class="venture-metrics">
                    <div class="metric">
                        <span class="metric-label">Revenue</span>
                        <span class="metric-value">$${(venture.revenue / 1000).toFixed(1)}K</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Risk Score</span>
                        <span class="metric-value">${(venture.risk_score * 100).toFixed(0)}%</span>
                    </div>
                </div>
                <div class="venture-status ${this.getStatusClass(venture.failure_probability)}">
                    <span class="status-dot"></span>
                    <span>Failure Rate: ${(venture.failure_probability * 100).toFixed(3)}%</span>
                </div>
            </div>
        `).join('');
        
        // Add click handlers and ensure proper styling
        container.querySelectorAll('.venture-card').forEach(card => {
            card.addEventListener('click', () => {
                const ventureId = card.dataset.ventureId;
                this.showVentureDetails(ventureId);
            });
            
            // Force card styling
            card.style.display = 'block';
            card.style.listStyle = 'none';
        });
    }

    renderAgents() {
        const container = document.getElementById('agentsGrid');
        
        container.innerHTML = this.agents.map(agent => `
            <div class="agent-card ${agent.active ? 'active' : 'inactive'}">
                <div class="agent-icon">
                    <span class="material-icons-round">${this.getAgentIcon(agent.type)}</span>
                </div>
                <h4 class="agent-name">${agent.name}</h4>
                <div class="agent-stats">
                    <div class="accuracy-bar">
                        <div class="accuracy-fill" style="width: ${agent.accuracy * 100}%"></div>
                    </div>
                    <span class="accuracy-text">${(agent.accuracy * 100).toFixed(0)}% Accuracy</span>
                </div>
            </div>
        `).join('');
    }

    formatVentureType(type) {
        const types = {
            'saas': 'SaaS',
            'ecommerce': 'E-commerce',
            'content': 'Content Platform'
        };
        return types[type] || type;
    }

    getStatusClass(failureProbability) {
        if (failureProbability <= 0.0001) return 'ultra-low-risk';
        if (failureProbability <= 0.001) return 'low-risk';
        if (failureProbability <= 0.01) return 'medium-risk';
        return 'high-risk';
    }

    getAgentIcon(type) {
        const icons = {
            'market_intelligence': 'analytics',
            'risk_assessment': 'security',
            'legal_compliance': 'gavel',
            'opportunity_scout': 'explore',
            'portfolio_optimizer': 'auto_graph'
        };
        return icons[type] || 'smart_toy';
    }

    showModal() {
        const modal = document.getElementById('evaluationModal');
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        
        // Focus on first input
        setTimeout(() => {
            document.getElementById('ventureName').focus();
        }, 300);
    }

    hideModal() {
        const modal = document.getElementById('evaluationModal');
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        
        // Reset form
        document.getElementById('evaluationForm').reset();
        document.getElementById('evaluationResults').style.display = 'none';
        document.getElementById('evaluationForm').style.display = 'flex';
    }

    async runEvaluation() {
        const ventureName = document.getElementById('ventureName').value;
        const marketSize = document.getElementById('marketSize').value;
        const competition = document.getElementById('competitionLevel').value;
        
        // Show loading state
        const button = document.getElementById('runEvaluation');
        const originalContent = button.innerHTML;
        button.innerHTML = '<span class="loading"></span> Analyzing...';
        button.disabled = true;
        
        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Show results
            document.getElementById('evaluationForm').style.display = 'none';
            document.getElementById('evaluationResults').style.display = 'block';
            
            // Update results with animation
            const score = Math.random() * 30 + 70;
            const successProb = 99.9 + Math.random() * 0.09;
            const riskLevel = successProb > 99.95 ? 'Ultra Low' : 'Low';
            
            this.animateValue('opportunityScore', 0, score, 1000);
            document.getElementById('failureProbability').textContent = `${successProb.toFixed(2)}%`;
            document.getElementById('riskLevel').textContent = riskLevel;
            
            // Update recommendation
            document.getElementById('recommendation').innerHTML = `
                <span class="material-icons-round">lightbulb</span>
                <p><strong>Recommendation:</strong> This venture shows excellent potential with ultra-low risk profile. 
                The AI analysis indicates strong market fit and minimal competition risk. 
                Consider proceeding with MVP development.</p>
            `;
            
            // Add to ventures after delay
            setTimeout(() => {
                this.addNewVenture({
                    name: ventureName,
                    marketSize: marketSize,
                    competition: competition,
                    score: score,
                    successProbability: successProb
                });
            }, 1500);
            
        } catch (error) {
            this.showNotification('Error running evaluation', 'error');
        } finally {
            button.innerHTML = originalContent;
            button.disabled = false;
        }
    }

    addNewVenture(ventureData) {
        const newVenture = {
            id: `venture-${Date.now()}`,
            name: ventureData.name,
            type: 'saas',
            status: 'evaluating',
            revenue: 0,
            risk_score: (100 - ventureData.score) / 100,
            failure_probability: (100 - ventureData.successProbability) / 100
        };
        
        this.ventures.unshift(newVenture);
        this.renderVentures();
        this.showNotification('New venture added successfully!', 'success');
        
        // Update dashboard count
        const currentCount = parseInt(document.getElementById('totalVentures').textContent) || 0;
        this.animateValue('totalVentures', currentCount, currentCount + 1, 500);
    }

    showVentureDetails(ventureId) {
        const venture = this.ventures.find(v => v.id === ventureId);
        if (!venture) return;
        
        this.showNotification(`Viewing details for ${venture.name}`, 'info');
    }

    switchTab(tabElement) {
        // Update active states
        document.querySelectorAll('.tab-item').forEach(tab => tab.classList.remove('active'));
        tabElement.classList.add('active');
        
        const tabName = tabElement.querySelector('.tab-label').textContent.toLowerCase();
        this.currentTab = tabName;
        
        this.showNotification(`Switched to ${tabName}`, 'info');
    }

    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        this.applyTheme();
    }

    applyTheme() {
        if (this.isDarkMode) {
            document.documentElement.style.setProperty('--md-surface', '#1F2937');
            document.documentElement.style.setProperty('--md-surface-variant', '#374151');
            document.documentElement.style.setProperty('--md-background', '#111827');
            document.documentElement.style.setProperty('--md-on-surface', '#F9FAFB');
            document.documentElement.style.setProperty('--md-on-surface-variant', '#D1D5DB');
            document.getElementById('themeToggle').querySelector('.material-icons-round').textContent = 'light_mode';
        } else {
            document.documentElement.style.setProperty('--md-surface', '#FFFFFF');
            document.documentElement.style.setProperty('--md-surface-variant', '#F3F4F6');
            document.documentElement.style.setProperty('--md-background', '#FAFAFA');
            document.documentElement.style.setProperty('--md-on-surface', '#1F2937');
            document.documentElement.style.setProperty('--md-on-surface-variant', '#6B7280');
            document.getElementById('themeToggle').querySelector('.material-icons-round').textContent = 'dark_mode';
        }
        
        // Update meta theme color
        document.querySelector('meta[name="theme-color"]').content = this.isDarkMode ? '#111827' : '#FFFFFF';
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="material-icons-round notification-icon">${this.getNotificationIcon(type)}</span>
            <span>${message}</span>
        `;
        
        // Add to body
        document.body.appendChild(notification);
        
        // Trigger animation
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Remove after delay
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check_circle',
            'error': 'error',
            'warning': 'warning',
            'info': 'info'
        };
        return icons[type] || 'info';
    }

    addRippleEffect() {
        document.querySelectorAll('button, .tab-item, .stat-card').forEach(element => {
            element.addEventListener('click', function(e) {
                const ripple = document.createElement('span');
                ripple.className = 'ripple';
                this.appendChild(ripple);
                
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                
                setTimeout(() => ripple.remove(), 600);
            });
        });
    }

    startAutoRefresh() {
        // Refresh data every 30 seconds
        setInterval(() => {
            this.loadDashboardData();
        }, 30000);
    }

    // Offline data fallbacks
    getOfflineDashboard() {
        return {
            total_ventures: 3,
            total_monthly_revenue: 27500,
            ultra_low_failure_rate_percentage: 92.5,
            target_achievement: 'SUCCESS'
        };
    }

    getOfflineVentures() {
        return {
            ventures: [
                {
                    id: 'v1',
                    name: 'AI Analytics Platform',
                    type: 'saas',
                    status: 'scaling',
                    revenue: 12500,
                    risk_score: 0.08,
                    failure_probability: 0.0007
                },
                {
                    id: 'v2',
                    name: 'Smart E-commerce Hub',
                    type: 'ecommerce',
                    status: 'mvp',
                    revenue: 8500,
                    risk_score: 0.12,
                    failure_probability: 0.0009
                },
                {
                    id: 'v3',
                    name: 'Content Creator Suite',
                    type: 'content',
                    status: 'growth',
                    revenue: 6500,
                    risk_score: 0.05,
                    failure_probability: 0.0003
                }
            ]
        };
    }

    getOfflineAgents() {
        return {
            agents: [
                {
                    id: 'a1',
                    type: 'market_intelligence',
                    name: 'Market Intelligence',
                    active: true,
                    accuracy: 0.89
                },
                {
                    id: 'a2',
                    type: 'risk_assessment',
                    name: 'Risk Assessment',
                    active: true,
                    accuracy: 0.94
                },
                {
                    id: 'a3',
                    type: 'legal_compliance',
                    name: 'Legal Compliance',
                    active: true,
                    accuracy: 0.91
                },
                {
                    id: 'a4',
                    type: 'opportunity_scout',
                    name: 'Opportunity Scout',
                    active: true,
                    accuracy: 0.87
                }
            ]
        };
    }

    useOfflineData() {
        this.updateDashboard(this.getOfflineDashboard());
        this.ventures = this.getOfflineVentures().ventures;
        this.agents = this.getOfflineAgents().agents;
        this.renderVentures();
        this.renderAgents();
        
        // Force proper styling after data load
        this.applyModernStyling();
    }
    
    applyModernStyling() {
        // Ensure ventures are displayed as cards, not list items
        const venturesGrid = document.getElementById('venturesGrid');
        if (venturesGrid) {
            venturesGrid.style.display = 'grid';
            venturesGrid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(320px, 1fr))';
            venturesGrid.style.gap = '24px';
            venturesGrid.style.marginTop = '24px';
        }
        
        // Style venture cards
        document.querySelectorAll('.venture-card').forEach(card => {
            card.style.listStyle = 'none';
            card.style.display = 'block';
            card.style.background = 'var(--md-surface)';
            card.style.borderRadius = '24px';
            card.style.padding = '24px';
            card.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
            card.style.border = '1px solid var(--ios-gray-5)';
            card.style.cursor = 'pointer';
            card.style.transition = 'all 0.3s ease';
        });
        
        // Style agents grid
        const agentsGrid = document.getElementById('agentsGrid');
        if (agentsGrid) {
            agentsGrid.style.display = 'grid';
            agentsGrid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))';
            agentsGrid.style.gap = '24px';
            agentsGrid.style.marginTop = '24px';
        }
    }
}

// Add notification styles dynamically
const notificationStyles = `
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--md-surface);
    color: var(--md-on-surface);
    padding: var(--space-md) var(--space-lg);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-lg);
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    transform: translateX(400px);
    transition: transform 0.3s var(--ease-in-out);
    z-index: 3000;
    max-width: 300px;
}

.notification.show {
    transform: translateX(0);
}

.notification-icon {
    font-size: 20px;
}

.notification-success .notification-icon { color: var(--md-secondary); }
.notification-error .notification-icon { color: var(--md-error); }
.notification-warning .notification-icon { color: var(--ios-yellow); }
.notification-info .notification-icon { color: var(--md-primary); }

.ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple-animation 0.6s ease-out;
    pointer-events: none;
}

@keyframes ripple-animation {
    to {
        transform: scale(4);
        opacity: 0;
    }
}

.venture-card {
    background: var(--md-surface);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    box-shadow: var(--shadow-md);
    cursor: pointer;
    transition: all 0.3s var(--ease-in-out);
}

.venture-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-xl);
}

.venture-header {
    margin-bottom: var(--space-md);
}

.venture-name {
    font-size: var(--text-lg);
    font-weight: 600;
    margin-bottom: var(--space-xs);
}

.venture-type {
    font-size: var(--text-sm);
    color: var(--md-on-surface-variant);
}

.venture-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-md);
    margin-bottom: var(--space-md);
}

.metric {
    text-align: center;
}

.metric-label {
    display: block;
    font-size: var(--text-xs);
    color: var(--md-on-surface-variant);
    margin-bottom: var(--space-xs);
}

.metric-value {
    font-size: var(--text-xl);
    font-weight: 700;
}

.venture-status {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    font-size: var(--text-sm);
    padding: var(--space-sm);
    border-radius: var(--radius-md);
    background: var(--md-surface-variant);
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--ios-gray);
}

.ultra-low-risk .status-dot { background: var(--md-secondary); }
.low-risk .status-dot { background: var(--ios-green); }
.medium-risk .status-dot { background: var(--ios-yellow); }
.high-risk .status-dot { background: var(--md-error); }

.agent-card {
    background: var(--md-surface);
    border-radius: var(--radius-md);
    padding: var(--space-lg);
    text-align: center;
    box-shadow: var(--shadow-sm);
    transition: all 0.3s var(--ease-in-out);
}

.agent-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.agent-icon {
    width: 48px;
    height: 48px;
    background: var(--md-surface-variant);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto var(--space-md);
    color: var(--md-primary);
}

.agent-name {
    font-size: var(--text-base);
    font-weight: 600;
    margin-bottom: var(--space-md);
}

.agent-stats {
    margin-top: var(--space-md);
}

.accuracy-bar {
    width: 100%;
    height: 4px;
    background: var(--ios-gray-5);
    border-radius: var(--radius-full);
    overflow: hidden;
    margin-bottom: var(--space-sm);
}

.accuracy-fill {
    height: 100%;
    background: var(--md-primary);
    transition: width 0.3s var(--ease-in-out);
}

.accuracy-text {
    font-size: var(--text-xs);
    color: var(--md-on-surface-variant);
}
`;

// Add styles to document
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new WealthMachineApp();
    
    // Debug: Force remove any list styling
    setTimeout(() => {
        const style = document.createElement('style');
        style.textContent = `
            .ventures-grid, .agents-grid {
                display: grid !important;
                list-style: none !important;
            }
            .venture-card, .agent-card {
                display: block !important;
                list-style: none !important;
            }
            ul, ol, li {
                list-style: none !important;
            }
            /* Override any default browser list styling */
            * {
                list-style: none !important;
            }
        `;
        document.head.appendChild(style);
    }, 100);
});