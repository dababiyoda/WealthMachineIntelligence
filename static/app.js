/* UAT governed preview operator console.
 *
 * The console renders authoritative API state when authenticated. Its offline
 * simulation contains no fabricated ventures, agents, revenue, or outcomes.
 */

class UATPreviewApp {
    constructor() {
        this.apiBase = window.location.origin;
        this.authToken = sessionStorage.getItem('uatAuthToken');
        this.isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.ventures = [];
        this.agents = [];
        this.governance = null;
        this.refreshTimer = null;
    }

    async init() {
        this.setupEventListeners();
        this.applyTheme();
        await this.loadCapabilities();
        if (this.authToken) {
            await this.loadProtectedData();
        } else {
            this.renderLoggedOut();
        }
    }

    setupEventListeners() {
        document.getElementById('themeToggle')?.addEventListener('click', () => this.toggleTheme());
        document.getElementById('notificationBtn')?.addEventListener('click', () => {
            this.showNotification('No verified notifications are connected.');
        });
        document.getElementById('loginForm')?.addEventListener('submit', async (event) => {
            event.preventDefault();
            await this.login();
        });
        document.getElementById('logoutButton')?.addEventListener('click', () => this.logout());
        document.getElementById('evaluateBtn')?.addEventListener('click', () => this.showModal());
        document.getElementById('modalClose')?.addEventListener('click', () => this.hideModal());
        document.querySelector('.modal-backdrop')?.addEventListener('click', () => this.hideModal());
        document.getElementById('evaluationForm')?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.runEvaluation();
        });
        document.querySelectorAll('.tab-item').forEach((tab) => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') this.hideModal();
        });
    }

    async login() {
        const username = document.getElementById('loginUsername')?.value.trim() || '';
        const password = document.getElementById('loginPassword')?.value || '';
        const status = document.getElementById('authStatus');
        if (status) status.textContent = 'Authenticating…';
        try {
            const body = new URLSearchParams({ username, password });
            const response = await fetch(`${this.apiBase}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body,
            });
            if (!response.ok) throw new Error('Invalid credentials');
            const data = await response.json();
            this.authToken = data.access_token;
            sessionStorage.setItem('uatAuthToken', this.authToken);
            if (status) status.textContent = `Signed in as ${data.user.username}`;
            this.setAuthVisibility(true);
            await this.loadProtectedData();
        } catch (error) {
            this.authToken = null;
            sessionStorage.removeItem('uatAuthToken');
            if (status) status.textContent = error.message;
            this.renderLoggedOut();
        }
    }

    logout() {
        this.authToken = null;
        sessionStorage.removeItem('uatAuthToken');
        if (this.refreshTimer) window.clearInterval(this.refreshTimer);
        this.renderLoggedOut();
        this.showNotification('Operator session cleared.');
    }

    setAuthVisibility(authenticated) {
        document.getElementById('loginForm')?.classList.toggle('hidden', authenticated);
        document.getElementById('logoutButton')?.classList.toggle('hidden', !authenticated);
    }

    authHeaders() {
        return this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {};
    }

    async fetchJson(path, authenticated = false) {
        const response = await fetch(`${this.apiBase}${path}`, {
            headers: authenticated ? this.authHeaders() : {},
        });
        if (response.status === 401) {
            this.logout();
            throw new Error('Operator session expired');
        }
        if (!response.ok) throw new Error(`${path} returned ${response.status}`);
        return response.json();
    }

    async loadCapabilities() {
        try {
            const capability = await this.fetchJson('/api/v1/system/capabilities');
            this.renderCapabilities(capability);
        } catch (_error) {
            this.renderCapabilities(this.offlineState().capability);
        }
    }

    async loadProtectedData() {
        try {
            const [dashboard, ventures, agents, governance] = await Promise.all([
                this.fetchJson('/api/v1/analytics/dashboard', true),
                this.fetchJson('/api/v1/ventures/', true),
                this.fetchJson('/api/v1/agents/', true),
                this.fetchJson('/api/v1/governance/status', true),
            ]);
            this.ventures = Array.isArray(ventures.ventures) ? ventures.ventures : [];
            this.agents = Array.isArray(agents) ? agents : [];
            this.governance = governance;
            this.renderDashboard(dashboard);
            this.renderVentures();
            this.renderAgents();
            this.renderGovernance(governance);
            this.setAuthVisibility(true);
            const status = document.getElementById('authStatus');
            if (status && !status.textContent.startsWith('Signed in')) {
                status.textContent = 'Authenticated operator session';
            }
            this.startRefresh();
        } catch (error) {
            console.warn('Protected data unavailable:', error.message);
            this.useOfflineData();
        }
    }

    startRefresh() {
        if (this.refreshTimer) window.clearInterval(this.refreshTimer);
        this.refreshTimer = window.setInterval(() => {
            if (document.visibilityState === 'visible' && this.authToken) this.loadProtectedData();
        }, 60000);
    }

    renderCapabilities(capability) {
        const mode = document.getElementById('operatingMode');
        const stage = document.getElementById('capabilityStage');
        if (mode) mode.textContent = `${capability.operating_mode || 'restricted'} — external autonomy: none`;
        if (stage) stage.textContent = this.humanize(capability.declared_stage || 'unknown_restricted');
    }

    renderDashboard(data) {
        this.setText('totalVentures', Number(data.total_ventures || 0));
        const revenue = Number(data.total_revenue ?? data.total_monthly_revenue ?? 0);
        this.setText('monthlyRevenue', this.formatMoney(revenue));
        const coverage = Number(data.modeled_low_risk_coverage ?? data.modeled_risk_threshold_coverage ?? 0);
        this.setText('modeledCoverage', `${coverage.toFixed(1)}%`);
    }

    renderVentures() {
        const container = document.getElementById('venturesGrid');
        if (!container) return;
        if (!this.ventures.length) {
            container.innerHTML = this.emptyState('No authoritative ventures', 'A governed venture record has not been created.');
            return;
        }
        container.innerHTML = this.ventures.map((venture) => {
            const name = this.escape(venture.name || 'Unnamed venture');
            const type = this.escape(venture.venture_type || venture.type || 'unclassified');
            const revenue = Number(venture.monthly_revenue ?? venture.revenue ?? 0);
            const risk = Number(venture.risk_score ?? venture.heuristic_risk_index ?? 0);
            return `<article class="venture-card">
                <div class="venture-header"><h4 class="venture-name">${name}</h4><span class="venture-type">${type}</span></div>
                <div class="venture-metrics">
                    <div class="metric"><span class="metric-label">Recorded revenue — unverified</span><span class="metric-value">${this.formatMoney(revenue)}</span></div>
                    <div class="metric"><span class="metric-label">Heuristic review index</span><span class="metric-value">${risk.toFixed(2)}</span></div>
                </div>
                <div class="venture-status"><span class="status-dot"></span><span>No execution authority</span></div>
            </article>`;
        }).join('');
    }

    renderAgents() {
        const container = document.getElementById('agentsGrid');
        if (!container) return;
        if (!this.agents.length) {
            container.innerHTML = this.emptyState('No evaluated agents', 'No versioned performance evaluation is linked.');
            return;
        }
        container.innerHTML = this.agents.map((agent) => `<article class="agent-card">
            <div class="agent-icon">◇</div>
            <h4 class="agent-name">${this.escape(agent.name || 'Unnamed agent')}</h4>
            <div class="agent-stats"><span class="accuracy-text">Performance unverified</span></div>
        </article>`).join('');
    }

    renderGovernance(data) {
        const values = {
            governanceControlStage: data.control_plane || 'unknown',
            governanceEvidenceStage: data.evidence_plane || 'unknown',
            governanceActions: Number(data.actions || 0),
            governanceApprovals: Number(data.pending_approvals || 0),
            governanceKills: Number(data.active_kill_switches || 0),
            governanceAudit: data.audit_chain_valid ? 'Valid' : 'Invalid — hold',
        };
        Object.entries(values).forEach(([id, value]) => this.setText(id, this.humanize(String(value))));
        const audit = document.getElementById('governanceAudit');
        audit?.classList.toggle('danger-text', !data.audit_chain_valid);
    }

    renderLoggedOut() {
        this.setAuthVisibility(false);
        this.ventures = [];
        this.agents = [];
        this.governance = null;
        this.useOfflineData();
        const status = document.getElementById('authStatus');
        if (status) status.textContent = 'Sign in to load authoritative local records';
    }

    useOfflineData() {
        const state = this.offlineState();
        this.ventures = state.ventures;
        this.agents = state.agents;
        this.renderDashboard(state.dashboard);
        this.renderVentures();
        this.renderAgents();
        this.renderGovernance(state.governance);
    }

    offlineState() {
        return {
            mode: 'offline simulation',
            capability: {
                declared_stage: 'unknown_restricted',
                operating_mode: 'restricted',
                authorized_external_autonomy: 'none',
            },
            dashboard: { total_ventures: 0, total_revenue: 0, modeled_low_risk_coverage: 0 },
            ventures: [],
            agents: [],
            governance: {
                control_plane: 'not_loaded',
                evidence_plane: 'not_loaded',
                actions: 0,
                pending_approvals: 0,
                active_kill_switches: 0,
                audit_chain_valid: false,
            },
        };
    }

    switchTab(tabId) {
        if (!tabId) return;
        document.querySelectorAll('.tab-item').forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === tabId));
        document.querySelectorAll('.tab-content').forEach((content) => {
            const active = content.id === tabId;
            content.classList.toggle('active', active);
            content.style.display = active ? 'block' : 'none';
        });
    }

    showModal() {
        const modal = document.getElementById('evaluationModal');
        modal?.classList.add('active');
        modal?.setAttribute('aria-hidden', 'false');
        document.getElementById('ventureName')?.focus();
    }

    hideModal() {
        const modal = document.getElementById('evaluationModal');
        modal?.classList.remove('active');
        modal?.setAttribute('aria-hidden', 'true');
        document.getElementById('evaluationForm')?.reset();
        const results = document.getElementById('evaluationResults');
        const form = document.getElementById('evaluationForm');
        if (results) results.style.display = 'none';
        if (form) form.style.display = 'flex';
    }

    runEvaluation() {
        const name = document.getElementById('ventureName')?.value.trim() || '';
        const market = document.getElementById('marketSize')?.value || '';
        const competition = document.getElementById('competitionLevel')?.value || '';
        const seed = `${name}|${market}|${competition}`;
        const hash = [...seed].reduce((value, character) => ((value * 31) + character.charCodeAt(0)) >>> 0, 7);
        const score = 40 + (hash % 41);
        const risk = 0.2 + ((hash % 61) / 100);
        document.getElementById('evaluationForm').style.display = 'none';
        document.getElementById('evaluationResults').style.display = 'block';
        this.setText('opportunityScore', score);
        this.setText('heuristicRiskIndex', risk.toFixed(2));
        this.setText('riskLevel', 'Uncalibrated');
        document.getElementById('recommendation').innerHTML = `<p><strong>Simulation only:</strong> this deterministic score is not market proof or permission to build. Record the claim, collect external evidence, and submit any proposed action through the governance workflow.</p>`;
    }

    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        this.applyTheme();
    }

    applyTheme() {
        document.documentElement.dataset.theme = this.isDarkMode ? 'dark' : 'light';
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.content = this.isDarkMode ? '#111827' : '#FFFFFF';
    }

    showNotification(message, type = 'info') {
        document.querySelector('.notification-toast')?.remove();
        const toast = document.createElement('div');
        toast.className = `notification-toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        window.setTimeout(() => toast.remove(), 3500);
    }

    emptyState(title, text) {
        return `<div class="empty-state"><div class="empty-icon">◇</div><h3>${this.escape(title)}</h3><p>${this.escape(text)}</p></div>`;
    }

    setText(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = String(value);
    }

    formatMoney(value) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0);
    }

    humanize(value) {
        return value.replaceAll('_', ' ');
    }

    escape(value) {
        const node = document.createElement('span');
        node.textContent = String(value);
        return node.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new UATPreviewApp();
    app.init();
    window.uatPreview = app;
});
