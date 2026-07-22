import React, { useState, useEffect} from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import './DashboardPage.css';

//mock meta prophet predictive data with upper and lower confidence bounds
const mockForecastData = [
    { time: '00:00', actual: 12, forecast: 14, upperBound: 20, lowerBound: 8},
    { time: '04:00', actual: 45, forecast: 40, upperBound: 55, lowerBound: 30},
    { time: '08:00', actual: 18, forecast: 22, upperBound: 32, lowerBound: 12},
    { time: '12:00', actual: 18, forecast: 20, upperBound: 28, lowerBound: 10},
    { time: '16:00', actual: 32, forecast: 30, upperBound: 42, lowerBound: 20},
    { time: '20:00', actual: 19, forecast: 18, upperBound: 26, lowerBound: 10},
    { time: '23:59', actual: 8, forecast: 10, upperBound: 18, lowerBound: 2},
];

export default function DashboardPage() {
    const [activeTab, setActiveTab] = useState('Overview');
    const [stats, setStats] = useState({totalInspected: 124500, totalFlagged: 341});

    useEffect(() => {
        //Fetch live transactions summary from FastAPI backend
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
        .catch(err => console.error('Could not load live backend stats: ', err));
    }, []);

    return (
        <div className="admin-container">
            {/* 1.Header */}
            <header className="admin-header">
                <h1>FraudGuard AI Admin Dashboard</h1>
            </header>

            <div className="admin-body">
                {/*2.SideBar */}
                <aside className="admin-sidebar">
                    <h3>[SideBar]</h3>
                    <nav>
                        <button 
                        className={activeTab === 'Overview' ? 'active' : ''}
                        onclock={() => setActiveTab('Overview')}>
                            Overview
                        </button>
                        <button
                        className={activeTab === 'Alerts' ? 'active' : ''}
                        onClick={() => setActiveTab('Alerts')}>
                            Alerts
                        </button>
                        <button
                        className={activeTab === 'Forecast' ? 'active' : ''}
                        onClick={() => setActiveTab('Forecast')}>
                            Forecast
                        </button>
                    </nav>
                </aside>

                {/* Right main Panel*/}
                <main className="admin-main">
                    {/* 3. KPI Cards Overview */}
                    <section className="kpi-card-section">
                        <h2>[KPI Cards Overview]</h2>
                        <div className="kpi-metrics">
                            <div className="metric-box">
                                <span className="metric-label">Total Inspected</span>
                                <span className="metric-value">{stats.totalInspected.toLocaleString()}</span>
                            </div>
                            <div className="metric-divider">|</div>
                            <div classname="metric-box flagged">
                                <span className="metric-label">Total Flagged</span>
                                <span classname="metric-value">{stats.totalFlagged.toLocaleString()}</span>
                            </div>
                        </div>
                    </section>

                    {/* 4. Predictive Trend canvas */}
                    <section className="chart-section">
                        <h2>Predictive Trend Canvas</h2>
                        <p className="chart-subtext">
                            Meta Prophet Line Charts (Upper/Lower Confidence Bands)
                        </p>

                        <div className="chart-wrapper">
                            <ResponsiveContainer width="100%" height="{280}">
                                <AreaChart data={mockForecastData} margin={{top: 10, right: 30, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                <XAxis dataKey="time" />
                                <YAxis />
                                <Tooltip />

                                {/* Confidence interval Band (Lower to Upper) */}
                                <Area
                                type="monotype"
                                dataKey="upperBound"
                                stroke="none"
                                fill="#3b82f6"
                                fillOpacity={0.15}
                                name="Upper Confidence Band"
                                />
                                <Area
                                type="monotone"
                                dataKey="lowerBound"
                                stroke="none"
                                fill="#ffffff"
                                fillOpacity={1}
                                name="Lower Confidence Band"
                                />

                                {/* Prophet predictive & Actual Lines */}
                                <Area
                                type="monotone"
                                dataKey="forecast"
                                stroke="#9333ea"
                                strokeDasharray="5 5"
                                fill="none"
                                strokeWidth={2}
                                name="Prophet Forecast"
                                />
                                <Area
                                type="monotone"
                                dataKey="actual"
                                stroke="#2563eb"
                                fill="none"
                                strokeWidth={3}
                                name="Actual Fraud Attacks"
                                />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </section>
                </main>
            </div>
        </div>
    );
}