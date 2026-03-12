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
                    return;
                }
                
                listContainer.innerHTML = `
                    <ul class="tunnel-list">
                        ${data.subdomains.map(subdomain => `
                            <li class="tunnel-item">
                                <div class="tunnel-info">
                                    <span class="tunnel-subdomain">${subdomain}</span>
                                    <span class="tunnel-url">http://${subdomain}.tunnel.dev</span>
                                </div>
                                <span class="status-badge status-active">Active</span>
                            </li>
                        `).join('')}
                    </ul>
                `;
            } catch (error) {
                console.error('Failed to load data:', error);
                document.getElementById('tunnel-list').innerHTML = `
                    <div class="empty-state">
                        <p>Failed to load data</p>
                    </div>
                `;
            }
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
