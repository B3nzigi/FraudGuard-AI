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

const mockForecastData = [
  { time: '00:00', actual: 12, forecast: 14, upperBound: 20, lowerBound: 8 },
  { time: '04:00', actual: 45, forecast: 40, upperBound: 55, lowerBound: 30 },
  { time: '08:00', actual: 18, forecast: 22, upperBound: 32, lowerBound: 12 },
  { time: '12:00', actual: 18, forecast: 20, upperBound: 28, lowerBound: 10 },
  { time: '16:00', actual: 32, forecast: 30, upperBound: 42, lowerBound: 20 },
  { time: '20:00', actual: 19, forecast: 18, upperBound: 26, lowerBound: 10 },
  { time: '23:59', actual: 8,  forecast: 10, upperBound: 18, lowerBound: 2 }
];

//mock recent flagged activity feed
const mockRecentActivity = [
  {id: 'TX-9042', user: 'user_882', amount: '$1,250.00', ip: '192.168.1.42', score: '0.92', status: 'Blocked' },
  { id: 'TX-9041', user: 'user_104', amount: '$42.10', ip: '10.0.0.12', score: '0.08', status: 'Allowed' },
  { id: 'TX-9040', user: 'user_519', amount: '$890.00', ip: '172.16.0.8', score: '0.85', status: 'Review' },
];

export default function DashboardPage({ onLogout }) {
  const [activeTab, setActiveTab] = useState('Overview');
  const [stats, setStats] = useState({ totalInspected: 124500, totalFlagged: 341 });

  useEffect(() => {
    fetch('http://localhost:8080/api/v1/transactions')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          const flaggedCount = data.filter(t => t.is_fraud === 1).length;
          setStats({
            totalInspected: 124500 + data.length,
            totalFlagged: 341 + flaggedCount
          });
        }
      })
      .catch(err => console.error('Could not load live backend stats:', err));
  }, []);

  return (
    <div className="admin-container">
      {/* Top Glassmorphism Header */}
      <header className="admin-header">
        <h1>FraudGuard AI Admin Dashboard</h1>
        <div className="system-status">
          <span className="status-dot"></span>ML Engine Active
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
            <section className="chart-section">
              <h2>Predictive ML Forecast Module</h2>
              <p className="chart-subtext">Advanced time-series forecasting coming soon.</p>
            </section>
          ) : (
            /* Default: Render Overview Tab */
            <>
              {/* KPI Header Box */}
              <section className="kpi-card-section">
                <h2>KPI Cards Overview</h2>
                <div className="kpi-metrics">
                  <div className="metric-box">
                    <span className="metric-label">Total Inspected:</span>
                    <span className="metric-value">{stats.totalInspected.toLocaleString()}</span>
                  </div>
                  <div className="metric-divider">|</div>
                  <div className="metric-box flagged">
                    <span className="metric-label">Total Flagged:</span>
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
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0}/>
                        </linearGradient>
                      </defs>
                      <Grid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                      <X dataKey="time" stroke="#94a3b8" />
                      <Y stroke="#94a3b8" />
                      <Tip 
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', borderRadius: '8px', color: '#fff' }}
                      />
                      
                      {/* Confidence Interval Band */}
                      <AreaLine 
                        type="monotone" 
                        dataKey="upperBound" 
                        stroke="none" 
                        fill="#38bdf8" 
                        fillOpacity={0.12} 
                        name="Upper Confidence Band" 
                      />
                      <AreaLine 
                        type="monotone" 
                        dataKey="lowerBound" 
                        stroke="none" 
                        fill="#0f172a" 
                        fillOpacity={0.8} 
                        name="Lower Confidence Band" 
                      />

                      {/* Prophet Predictive & Actual Lines */}
                      <AreaLine 
                        type="monotone" 
                        dataKey="forecast" 
                        stroke="#a855f7" 
                        strokeDasharray="4 4" 
                        fill="none" 
                        strokeWidth={2} 
                        name="Prophet Forecast" 
                      />
                      <AreaLine 
                        type="monotone" 
                        dataKey="actual" 
                        stroke="#3b82f6" 
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
                      <th>User ID</th>
                      <th>Amount</th>
                      <th>IP Address</th>
                      <th>Risk Score</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mockRecentActivity.map((tx) => (
                      <tr key={tx.id}>
                        <td>{tx.id}</td>
                        <td>{tx.user}</td>
                        <td>{tx.amount}</td>
                        <td><code>{tx.ip}</code></td>
                        <td>
                          <span className={`risk-badge ${parseFloat(tx.score) > 0.5 ? 'high' : 'low'}`}>
                            {tx.score}
                          </span>
                        </td>
                        <td>
                          <span className={`status-tag ${tx.status.toLowerCase()}`}>
                            {tx.status}
                          </span>
                        </td>
                      </tr>
                    ))}
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