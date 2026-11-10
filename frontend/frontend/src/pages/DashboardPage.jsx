import React, { useState, useEffect } from 'react';
import { 
  AreaChart as Chart, 
  Area as AreaLine, 
  XAxis as X, YAxis as Y, 
  Tooltip as Tip, 
  ResponsiveContainer as Container, 
  CartesianGrid as Grid 
} from 'recharts';
import './DashboardPage.css';
import AlertsTab from './AlertsTab';
import ForecastTab from './ForecastTab';
import { overviewService, transactionService } from '../services/api';

const mockForecastData = [
  { time: '00:00', actual: 12, forecast: 14, upperBound: 20, lowerBound: 8 },
  { time: '04:00', actual: 45, forecast: 40, upperBound: 55, lowerBound: 30 },
  { time: '08:00', actual: 18, forecast: 22, upperBound: 32, lowerBound: 12 },
  { time: '12:00', actual: 18, forecast: 20, upperBound: 28, lowerBound: 10 },
  { time: '16:00', actual: 32, forecast: 30, upperBound: 42, lowerBound: 20 },
  { time: '20:00', actual: 19, forecast: 18, upperBound: 26, lowerBound: 10 },
  { time: '23:59', actual: 8,  forecast: 10, upperBound: 18, lowerBound: 2 }
];

const normalizeActivity = (tx) => ({
  id: tx.id,
  userId: tx.user_id || tx.userId || 'Unknown',
  userName: tx.user_name || tx.userName || 'Unknown account',
  amount: Number(tx.amount || 0),
  timestamp: tx.timestamp,
  ip: tx.ip_address || tx.ip || 'Unknown',
  score: Number(tx.risk_score ?? tx.score ?? 0),
  status: tx.action || tx.status || (tx.is_fraud ? 'Review' : 'Allowed'),
});

const mergeActivity = (existing, incoming) => {
  const byId = new Map(existing.map((tx) => [tx.id, tx]));
  incoming.forEach((tx) => byId.set(tx.id, tx));
  return Array.from(byId.values())
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 10);
};

export default function DashboardPage({ onLogout, theme, onToggleTheme }) {
  const [activeTab, setActiveTab] = useState('Overview');
  const [stats, setStats] = useState({ totalInspected: 0, totalFlagged: 0 });
  const [recentActivity, setRecentActivity] = useState([]);
  const [activityLoading, setActivityLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const loadOverview = () => {
      overviewService.getOverview()
        .then((data) => {
          if (mounted) {
            setStats({
              totalInspected: Number(data.total_inspected || 0),
              totalFlagged: Number(data.total_flagged || 0),
            });
          }
        })
        .catch((err) => console.error('Could not load live model inspection stats:', err));
    };

    loadOverview();
    const refreshTimer = window.setInterval(loadOverview, 15000);
    return () => {
      mounted = false;
      window.clearInterval(refreshTimer);
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadRecentActivity = () => {
      transactionService.getTransactions(10)
        .then((data) => {
          if (mounted) {
            setRecentActivity((previous) => mergeActivity(previous, data.map(normalizeActivity)));
            setActivityLoading(false);
          }
        })
        .catch((err) => {
          console.error('Could not load recent model decisions:', err);
          if (mounted) setActivityLoading(false);
        });
    };

    loadRecentActivity();
    const refreshTimer = window.setInterval(loadRecentActivity, 10000);
    const token = localStorage.getItem('token');
    let socket;
    if (token) {
      try {
        socket = new WebSocket(`ws://localhost:8080/ws/alerts?token=${token}`);
        socket.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message.type === 'NEW_TRANSACTION' && message.data) {
            setRecentActivity((previous) => mergeActivity(previous, [normalizeActivity(message.data)]));
            setActivityLoading(false);
          }
        };
        socket.onerror = (error) => console.error('Transaction feed websocket error:', error);
      } catch (err) {
        console.error('Could not connect to the live transaction feed:', err);
      }
    }

    return () => {
      mounted = false;
      window.clearInterval(refreshTimer);
      if (socket) socket.close();
    };
  }, []);

  return (
    <div className="admin-container">
      {/* Top Glassmorphism Header */}
      <header className="admin-header">
        <h1>FraudGuard AI Admin Dashboard</h1>
        <div className="header-actions">
          <button
            type="button"
            className="theme-toggle"
            onClick={onToggleTheme}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            aria-pressed={theme === 'dark'}
          >
            <span className="theme-toggle-icon" aria-hidden="true">{theme === 'light' ? '☾' : '☀'}</span>
            <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
          </button>
          <div className="system-status">
            <span className="status-dot"></span>ML Engine Active
          </div>
        </div>
      </header>

      <div className="admin-body">
        {/* Sidebar */}
        <aside className="admin-sidebar">
        <div className="sidebar-top">
          <h3>Navigation</h3>
          <nav>
            <button 
              className={activeTab === 'Overview' ? 'active' : ''} 
              onClick={() => setActiveTab('Overview')}
            >
              Overview
            </button>
            <button 
              className={activeTab === 'Alerts' ? 'active' : ''} 
              onClick={() => setActiveTab('Alerts')}
            >
              Alerts
            </button>
            <button 
              className={activeTab === 'Forecast' ? 'active' : ''} 
              onClick={() => setActiveTab('Forecast')}
            >
              Forecast
            </button>
          </nav>
          </div>

          <div className="sidebar-bottom">
            <button className="logout-btn" onClick={onLogout}>
              Logout
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        {/* Main Content Area */}
        <main className="admin-main">
          {activeTab === 'Alerts' ? (
            /* Render Alerts Tab when activeTab === 'Alerts' */
            <AlertsTab />
          ) : activeTab === 'Forecast' ? (
            /* Render Forecast View Placeholder */
            <ForecastTab />
          ) : (
            /* Default: Render Overview Tab */
            <>
              {/* KPI Header Box */}
              <section className="kpi-card-section">
                <h2>KPI Cards Overview</h2>
                <div className="kpi-metrics">
                  <div className="metric-box">
                    <span className="metric-label">Model Inspected:</span>
                    <span className="metric-value">{stats.totalInspected.toLocaleString()}</span>
                  </div>
                  <div className="metric-divider">|</div>
                  <div className="metric-box flagged">
                    <span className="metric-label">Flagged by Model:</span>
                    <span className="metric-value">{stats.totalFlagged.toLocaleString()}</span>
                  </div>
                </div>
              </section>

              {/* Predictive Trend Chart */}
              <section className="chart-section">
                <h2>Predictive Trend Canvas</h2>
                <p className="chart-subtext">
                  Meta Prophet Line Charts (Upper/Lower Confidence Bands)
                </p>

                <div className="chart-wrapper">
                  <Container width="100%" height={320}>
                    <Chart data={mockForecastData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--chart-secondary)" stopOpacity={0.35}/>
                          <stop offset="95%" stopColor="var(--chart-secondary)" stopOpacity={0.0}/>
                        </linearGradient>
                      </defs>
                      <Grid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                      <X dataKey="time" stroke="var(--chart-axis)" />
                      <Y stroke="var(--chart-axis)" />
                      <Tip 
                        contentStyle={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-color)', borderRadius: '8px', color: 'var(--text-primary)' }}
                      />
                      
                      {/* Confidence Interval Band */}
                      <AreaLine 
                        type="monotone" 
                        dataKey="upperBound" 
                        stroke="none" 
                        fill="var(--chart-band)" 
                        fillOpacity={0.12} 
                        name="Upper Confidence Band" 
                      />
                      <AreaLine 
                        type="monotone" 
                        dataKey="lowerBound" 
                        stroke="none" 
                        fill="var(--chart-lower-bound)" 
                        fillOpacity={0.8} 
                        name="Lower Confidence Band" 
                      />

                      {/* Prophet Predictive & Actual Lines */}
                      <AreaLine 
                        type="monotone" 
                        dataKey="forecast" 
                        stroke="var(--chart-primary)" 
                        strokeDasharray="4 4" 
                        fill="none" 
                        strokeWidth={2} 
                        name="Prophet Forecast" 
                      />
                      <AreaLine 
                        type="monotone" 
                        dataKey="actual" 
                        stroke="var(--chart-secondary)" 
                        fill="url(#colorActual)" 
                        strokeWidth={3} 
                        name="Actual Fraud Attacks" 
                      />
                    </Chart>
                  </Container>
                </div>
              </section>

              {/* Live Recent Transaction Activity feed */}
              <section className="activity-section">
                <h2>Recent Threat Intelligence Feed</h2>
                <table className="activity-table">
                  <thead>
                    <tr>
                      <th>Transaction ID</th>
                      <th>Customer</th>
                      <th>Amount</th>
                      <th>Time</th>
                      <th>IP Address</th>
                      <th>Risk Score</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activityLoading ? (
                      <tr><td colSpan="7" className="activity-empty">Loading recent model decisions…</td></tr>
                    ) : recentActivity.length ? recentActivity.map((tx) => (
                        <tr key={tx.id}>
                          <td className="activity-id">{tx.id}</td>
                          <td className="activity-customer">
                            <strong>{tx.userName}</strong>
                            <small>{tx.userId}</small>
                          </td>
                          <td>KES {tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                          <td>{tx.timestamp ? new Date(tx.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}</td>
                          <td><code>{tx.ip}</code></td>
                          <td>
                            <span className={`risk-badge ${tx.score >= 0.75 ? 'high' : tx.score >= 0.35 ? 'medium' : 'low'}`}>
                              {tx.score.toFixed(2)}
                            </span>
                          </td>
                          <td>
                            <span className={`status-tag ${tx.status.toLowerCase()}`}>
                              {tx.status}
                            </span>
                          </td>
                        </tr>
                      )) : (
                        <tr><td colSpan="7" className="activity-empty">No transactions have been scored yet.</td></tr>
                      )}
                  </tbody>
                </table>
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
