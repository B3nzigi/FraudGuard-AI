import React, { useState, useEffect } from 'react';
import {
  AreaChart as Chart,
  Area as AreaLine,
  XAxis as X,
  YAxis as Y,
  Tooltip as Tip,
  ResponsiveContainer as Container,
  CartesianGrid as Grid
} from 'recharts';
import { fetchForecastData } from '../services/apiService';
import { exportForecastPdf } from '../utils/pdfExport';
import './ForecastTab.css';

export default function ForecastTab() {
  const [timeframe, setTimeframe] = useState('7d');
  const [riskCutoff, setRiskCutoff] = useState(0.75);
  const [enforceMpesaPin, setEnforceMpesaPin] = useState(true);
  const [blockVpn, setBlockVpn] = useState(false);

  // States for backend data and loading indicators
  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch live metrics from FastAPI whenever controls change
  useEffect(() => {
    setLoading(true);

    fetchForecastData({
      timeframe,
      cutoff: riskCutoff,
      enforceMpesa: enforceMpesaPin,
      blockVpn,
    })
      .then((data) => {
        setForecastData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('API Error:', err);
        setLoading(false);
      });
  }, [timeframe, riskCutoff, enforceMpesaPin, blockVpn]);

  // Fallback metrics while loading or if offline
  const activeChartData = forecastData?.chartData || [];
  const exposureKES = forecastData?.adjustedExposureKES ?? 0;
  const attackSurge = forecastData?.projectedSurge || '+0.0%';
  const peakWindow = forecastData?.peakWindow || 'N/A';
  const modelDrift = forecastData?.modelDrift || 'Stable';
  const attackVectors = forecastData?.attackVectors || [];

   return (
    <div className="forecast-container">
      {/* 1. Header & Timeframe selector */}
      <div className="forecast-header-bar">
        <div>
          <h2>Predictive ML Engine (Prophet Model)</h2>
          <p className="forecast-subtitle">Time-series anomaly forecasting & KES financial loss projections</p>
        </div>
        <div className="forecast-header-actions">
          <div className="timeframe-selector">
            <button
              className={timeframe === '24h' ? 'active' : ''}
              onClick={() => setTimeframe('24h')}
            >
              Next 24 Hours
            </button>
            <button
              className={timeframe === '7d' ? 'active' : ''}
              onClick={() => setTimeframe('7d')}
            >
              Next 7 Days
            </button>
          </div>
          <button
            type="button"
            className="btn-export-pdf"
            onClick={() =>
              exportForecastPdf({
                timeframe,
                riskCutoff,
                enforceMpesaPin,
                blockVpn,
                attackSurge,
                exposureKES,
                peakWindow,
                modelDrift,
                chartData: activeChartData,
                attackVectors,
              })
            }
            title="Download forecast metrics as a PDF"
          >
            Export PDF
          </button>
        </div>
      </div>

      {/* 2. Dynamic Summary KPIs */}
      <section className="forecast-kpi-grid">
        <div className="forecast-kpi-card danger">
          <span className="kpi-label">Projected Attack Surge</span>
          <span className="kpi-val">{attackSurge}</span>
          <span className="kpi-sub">Expected over peak window</span>
        </div>
        <div className="forecast-kpi-card warning">
          <span className="kpi-label">Risk at Stake (KES)</span>
          <span className="kpi-val">KES {exposureKES.toLocaleString()}</span>
          <span className="kpi-sub">Projected fraud exposure</span>
        </div>
        <div className="forecast-kpi-card info">
          <span className="kpi-label">Predicted Peak Window</span>
          <span className="kpi-val">{peakWindow}</span>
          <span className="kpi-sub">High velocity carding expected</span>
        </div>
        <div className="forecast-kpi-card success">
          <span className="kpi-label">Model Drift Index</span>
          <span className="kpi-val">{modelDrift}</span>
          <span className="kpi-sub">Retraining due in 12 days</span>
        </div>
      </section>

      {/* 3. Recharts Prophet Area Chart */}
      <section className="forecast-chart-card">
        <div className="chart-card-header">
          <h3>Prophet Fraud Volume & Confidence Bands</h3>
          <span className="chart-badge">
            {loading ? 'Updating live metrics...' : 'KES Value Scale (x1000)'}
          </span>
        </div>
        <div className="forecast-chart-wrapper">
          <Container width="100%" height={340}>
            <Chart data={activeChartData} margin={{ top: 15, right: 30, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.6}/>
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              <Grid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
              <X dataKey="day" stroke="#94a3b8" />
              <Y stroke="#94a3b8" unit="k" />
              <Tip
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', borderRadius: '8px', color: '#fff' }}
                formatter={(value, name) => [value !== null ? `KES ${(value * 1000).toLocaleString()}` : 'N/A', name]}
              />

              {/* Upper & Lower Confidence Area */}
              <AreaLine
                type="monotone"
                dataKey="upperBound"
                stroke="none"
                fill="#38bdf8"
                fillOpacity={0.12}
                name="Upper Bound (KES)"
              />
              <AreaLine
                type="monotone"
                dataKey="lowerBound"
                stroke="none"
                fill="#0f172a"
                fillOpacity={0.8}
                name="Lower Bound (KES)"
              />
              
              {/* Forecast Line */}
              <AreaLine
                type="monotone"
                dataKey="forecast"
                stroke="#a855f7"
                strokeDasharray="4 4"
                fill="url(#colorForecast)"
                strokeWidth={2}
                name="Predicted Fraud (KES)"
              />

              {/* Actual Line */}
              <AreaLine 
                type="monotone"
                dataKey="actual"
                stroke="#3b82f6"
                fill="none"
                strokeWidth={3}
                name="Actual Fraud (KES)"
              />
            </Chart>
          </Container>
        </div>
      </section>

      {/* 4. Interactive Simulation & Vector Breakdown */}
      <div className="forecast-bottom-grid">
        <section className="simulation-card">
          <h3>"What If?" Mitigation Simulator</h3>
          <p className="sim-subtext">Adjust rules to see real-time impact on KES risk exposure</p>

          <div className="slider-control">
            <div className="slider-label">
              <span>Risk Score Cutoff Threshold:</span>
              <strong className="text-highlight">{riskCutoff}</strong>
            </div>
            <input
              type="range"
              min="0.50"
              max="0.95"
              step="0.05"
              value={riskCutoff}
              onChange={(e) => setRiskCutoff(parseFloat(e.target.value))}
            />
          </div>

          <div className="toggle-group">
            <label className="toggle-item">
              <input
                type="checkbox"
                checked={enforceMpesaPin}
                onChange={(e) => setEnforceMpesaPin(e.target.checked)}
              />
              <span>Require M-pesa STK re-Auth on &gt; KES 50,000</span>
            </label>

            <label className="toggle-item">
              <input
                type="checkbox"
                checked={blockVpn}
                onChange={(e) => setBlockVpn(e.target.checked)}
              />
              <span>Auto-block VPN & Proxy Transactions</span>
            </label>
          </div>
        </section>

        {/* Vector Distribution */}
        <section className="vectors-card">
          <h3>Predicted Attack Vectors</h3>
          <div className="vector-list">
            {attackVectors.map((vector, idx) => (
              <div className="vector-item" key={idx}>
                <div className="vector-info">
                  <span>{vector.label}</span>
                  <strong>{vector.percentage}%</strong>
                </div>
                <div className="vector-bar">
                  <div className={`vector-fill ${vector.level}`} style={{ width: `${vector.percentage}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}