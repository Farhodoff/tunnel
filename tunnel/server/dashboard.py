"""
Dashboard - Web UI for tunnel management
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tunnel Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        header {
            text-align: center;
            padding: 2rem 0;
            border-bottom: 1px solid #334155;
            margin-bottom: 2rem;
        }
        
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            color: #94a3b8;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
        }
        
        .stat-card h3 {
            color: #94a3b8;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #f8fafc;
        }
        
        .tunnels-section {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
        }
        
        .tunnels-section h2 {
            margin-bottom: 1rem;
            color: #f8fafc;
        }
        
        .tunnel-list {
            list-style: none;
        }
        
        .tunnel-item {
            background: #0f172a;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #334155;
        }
        
        .tunnel-info {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
        
        .tunnel-subdomain {
            font-weight: 600;
            color: #667eea;
        }
        
        .tunnel-url {
            font-size: 0.875rem;
            color: #94a3b8;
        }
        
        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-active {
            background: #065f46;
            color: #34d399;
        }
        
        .status-inactive {
            background: #7f1d1d;
            color: #f87171;
        }
        
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            margin-bottom: 1rem;
        }
        
        .refresh-btn:hover {
            background: #5a67d8;
        }
        
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #64748b;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #64748b;
        }

        .logs-section {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
            margin-top: 2rem;
        }

        .log-item {
            border-top: 1px solid #334155;
            padding: 0.9rem 0;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: center;
        }

        .log-meta {
            color: #94a3b8;
            font-size: 0.875rem;
        }

        .inspect-btn {
            background: #475569;
            color: white;
            border: none;
            padding: 0.4rem 0.7rem;
            border-radius: 6px;
            cursor: pointer;
        }

        .filters {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin: 1rem 0;
        }

        .filters input, .filters select {
            background: #0f172a;
            color: #e2e8f0;
            border: 1px solid #475569;
            border-radius: 6px;
            padding: 0.45rem;
        }

        .metric-bars {
            display: grid;
            gap: 0.5rem;
            color: #cbd5e1;
        }

        .metric-bar {
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
        }

        .metric-bar span {
            display: block;
            background: #667eea;
            padding: 0.25rem 0.5rem;
            min-width: 5rem;
        }

        .modal {
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.8);
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }

        .modal-content {
            background: #1e293b;
            border: 1px solid #475569;
            border-radius: 10px;
            max-width: 760px;
            width: 100%;
            padding: 1.5rem;
        }

        .modal pre {
            white-space: pre-wrap;
            max-height: 60vh;
            overflow: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔒 Tunnel Dashboard</h1>
            <p class="subtitle">Monitor and manage your tunnels</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Tunnels</h3>
                <div class="stat-value" id="total-tunnels">-</div>
            </div>
            <div class="stat-card">
                <h3>Active Tunnels</h3>
                <div class="stat-value" id="active-tunnels">-</div>
            </div>
            <div class="stat-card">
                <h3>Server Status</h3>
                <div class="stat-value" style="color: #34d399;">Online</div>
            </div>
        </div>
        
        <div class="tunnels-section">
            <h2>Active Tunnels</h2>
            <button class="refresh-btn" onclick="loadData()">Refresh</button>
            <div id="tunnel-list">
                <div class="loading">Loading...</div>
            </div>

            <div class="logs-section">
                <h2>Recent Requests</h2>
                <div class="filters">
                    <input id="filter-subdomain" placeholder="Subdomain">
                    <input id="filter-path" placeholder="Path contains">
                    <select id="filter-since">
                        <option value="3600">Last hour</option>
                        <option value="86400">Last 24 hours</option>
                        <option value="">All retained</option>
                    </select>
                    <button class="inspect-btn" onclick="loadLogs()">Apply filters</button>
                </div>

                <div class="logs-section">
                    <h2>Webhook Tester</h2>
                    <button class="inspect-btn" onclick="createWebhook()">Create endpoint</button>
                    <div id="webhook-list" class="log-meta">No endpoint created in this session.</div>
                </div>
                <div id="metric-summary" class="log-meta"></div>
                <div id="metric-bars" class="metric-bars"></div>
                <div id="log-list"><div class="loading">Loading...</div></div>
            </div>
        </div>
    </div>
    <div id="replay-modal" class="modal" onclick="if(event.target===this) closeReplay()">
        <div class="modal-content">
            <button class="inspect-btn" onclick="closeReplay()">Close</button>
            <h2 id="replay-title">Replay result</h2>
            <pre id="replay-result"></pre>
        </div>
    </div>
    
    <script>
        async function loadData() {
            try {
                const response = await fetch('/api/tunnels');
                const data = await response.json();
                
                // Update stats
                document.getElementById('total-tunnels').textContent = data.total_tunnels;
                document.getElementById('active-tunnels').textContent = data.active_tunnels;
                
                // Update tunnel list
                const listContainer = document.getElementById('tunnel-list');
                
                if (data.subdomains.length === 0) {
                    listContainer.innerHTML = `
                        <div class="empty-state">
                            <p>No active tunnels</p>
                            <p style="font-size: 0.875rem; margin-top: 0.5rem;">
                                Use the CLI client to create a tunnel
                            </p>
                        </div>
                    `;
                }
                if (data.subdomains.length > 0) {
                    const baseDomain = window.location.hostname.split('.').slice(-2).join('.') || 'tunnel.dev';
                    const scheme = window.location.protocol === 'https:' ? 'https' : 'http';
                    listContainer.innerHTML = `
                    <ul class="tunnel-list">
                        ${data.subdomains.map(subdomain => `
                            <li class="tunnel-item">
                                <div class="tunnel-info">
                                    <span class="tunnel-subdomain">${subdomain}</span>
                                    <span class="tunnel-url">${scheme}://${subdomain}.${data.base_domain || baseDomain}</span>
                                </div>
                                <span class="status-badge status-active">Active</span>
                            </li>
                        `).join('')}
                    </ul>
                    `;
                }
                await loadLogs();
            } catch (error) {
                console.error('Failed to load data:', error);
                document.getElementById('tunnel-list').innerHTML = `
                    <div class="empty-state">
                        <p>Failed to load data</p>
                    </div>
                `;
            }
        }

        async function loadLogs() {
            const container = document.getElementById('log-list');
            try {
                const params = new URLSearchParams({limit: '20'});
                const subdomain = document.getElementById('filter-subdomain').value;
                const path = document.getElementById('filter-path').value;
                const since = document.getElementById('filter-since').value;
                if (subdomain) params.set('subdomain', subdomain);
                if (path) params.set('path', path);
                if (since) params.set('since', since);
                const response = await fetch('/api/logs?' + params.toString());
                const data = await response.json();
                const stats = data.stats;
                document.getElementById('metric-summary').textContent =
                    `${stats.total_requests} requests · avg ${stats.avg_duration_ms} ms · ` +
                    `${formatBytes(stats.request_bytes)} in / ${formatBytes(stats.response_bytes)} out`;
                const maxStatus = Math.max(...Object.values(stats.status_codes), 1);
                document.getElementById('metric-bars').innerHTML = Object.entries(stats.status_codes)
                    .map(([status, count]) => `<div class="metric-bar"><span style="width:${Math.max(8, count / maxStatus * 100)}%">HTTP ${status}: ${count}</span></div>`)
                    .join('');
                if (!data.logs.length) {
                    container.innerHTML = '<div class="empty-state">No requests captured</div>';
                    return;
                }
                container.innerHTML = data.logs.slice().reverse().map(log => `
                    <div class="log-item">
                        <div>
                            <strong>${escapeHtml(log.method)} ${escapeHtml(log.path)}</strong>
                            <div class="log-meta">${escapeHtml(log.subdomain)} · ${log.status_code} · ${log.duration_ms} ms</div>
                            <details>
                                <summary class="log-meta">Inspect</summary>
                                <pre>${escapeHtml(JSON.stringify({headers: log.headers, body: log.body, body_b64: log.body_b64}, null, 2))}</pre>
                            </details>
                        </div>
                        <button class="inspect-btn" onclick="replayRequest('${encodeURIComponent(log.request_id)}')">Replay</button>
                    </div>
                `).join('');
            } catch (error) {
                container.innerHTML = '<div class="empty-state">Failed to load request logs</div>';
            }
        }

        function formatBytes(bytes) {
            if (!bytes) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB'];
            const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
            return (bytes / Math.pow(1024, index)).toFixed(index ? 1 : 0) + ' ' + units[index];
        }

        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, c => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            }[c]));
        }

        async function replayRequest(requestId) {
            const token = window.localStorage.getItem('tunnel_api_key');
            const headers = token ? {'X-API-Key': token} : {};
            const response = await fetch('/api/logs/' + requestId + '/replay', { method: 'POST', headers });
            const result = await response.json();
            if (!response.ok) {
                showReplay(result.error || 'Replay failed', response.status);
                return;
            }
            showReplay(JSON.stringify(result, null, 2), result.status_code);
            loadLogs();
        }

        function showReplay(value, status) {
            document.getElementById('replay-title').textContent = 'Replay result (HTTP ' + status + ')';
            document.getElementById('replay-result').textContent = value;
            document.getElementById('replay-modal').style.display = 'flex';
        }

        function closeReplay() {
            document.getElementById('replay-modal').style.display = 'none';
        }

        async function createWebhook() {
            const token = window.localStorage.getItem('tunnel_api_key');
            const headers = token ? {'X-API-Key': token} : {};
            const response = await fetch('/webhooks/create', {method: 'POST', headers});
            const result = await response.json();
            if (!response.ok) {
                showReplay(result.detail || result.error || 'Webhook creation failed', response.status);
                return;
            }
            document.getElementById('webhook-list').innerHTML =
                '<p>Capture URL: <code>' + escapeHtml(result.full_url) + '</code></p>' +
                '<button class="inspect-btn" onclick="loadWebhookRequests(\'' +
                escapeHtml(result.endpoint_id) + '\')">View captured requests</button>';
        }

        async function loadWebhookRequests(endpointId) {
            const token = window.localStorage.getItem('tunnel_api_key');
            const headers = token ? {'X-API-Key': token} : {};
            const response = await fetch('/webhooks/requests/' + encodeURIComponent(endpointId), {headers});
            const result = await response.json();
            showReplay(JSON.stringify(result, null, 2), response.status);
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 5 seconds
        setInterval(loadData, 5000);
    </script>
</body>
</html>
"""


@router.get("", response_class=HTMLResponse)
async def dashboard():
    """Serve dashboard HTML"""
    return DASHBOARD_HTML


@router.get("/")
async def dashboard_root():
    """Redirect to dashboard"""
    return HTMLResponse(content=DASHBOARD_HTML)
