import React, { useState } from 'react';
import {
  AreaChart as Chart,
  Area as AreaLine,
  XAxis as X,
  YAxis as Y,
  Tooltip as Tip,
  ResponsiveContainer as Container,
  CartesianGrid as Grid
} from 'recharts';
import './ForecastTab.css';

const forecast7Days = [
  { day: 'Mon', actual: 120, forecast: 115, upperBound: 140, lowerBound: 90 },
  { day: 'Tue', actual: 150, forecast: 145, upperBound: 175, lowerBound: 115 },
  { day: 'Wed', actual: 180, forecast: 190, upperBound: 220, lowerBound: 160 },
  { day: 'Thu', actual: 210, forecast: 205, upperBound: 240, lowerBound: 170 },
  { day: 'Fri', actual: 310, forecast: 340, upperBound: 400, lowerBound: 280 },
  { day: 'Sat', actual: null, forecast: 490, upperBound: 580, lowerBound: 410 },
  { day: 'Sun', actual: null, forecast: 420, upperBound: 510, lowerBound: 330 },
];

const forecast24Hours = [
  { day: '00:00', actual: 15, forecast: 14, upperBound: 22, lowerBound: 8 },
  { day: '04:00', actual: 42, forecast: 40, upperBound: 55, lowerBound: 30 },
  { day: '08:00', actual: 18, forecast: 22, upperBound: 32, lowerBound: 12 },
  { day: '12:00', actual: 28, forecast: 30, upperBound: 42, lowerBound: 20 },
  { day: '16:00', actual: 65, forecast: 70, upperBound: 90, lowerBound: 50 },
  { day: '20:00', actual: null, forecast: 110, upperBound: 140, lowerBound: 85 },
  { day: '23:59', actual: null, forecast: 45, upperBound: 60, lowerBound: 30 }
];

export default function ForecastTab() {
  const [timeframe, setTimeframe] = useState('7d');
  const [riskCutoff, setRiskCutoff] = useState(0.75);
  const [enforceMpesaPin, setEnforceMpesaPin] = useState(true);
  const [blockVpn, setBlockVpn] = useState(false);

  const activeData = timeframe === '7d' ? forecast7Days : forecast24Hours;

  const baseExposureKES = timeframe === '7d' ? 5450000 : 1250000;
  const adjustedExposure = Math.round(
    baseExposureKES * (1.5 - riskCutoff) * (enforceMpesaPin ? 0.75 : 1.0) * (blockVpn ? 0.85 : 1.0)
  );

  return (
    <div className="forecast-container">
      <div className="forecast-header-bar">
        <div>
          <h2>Predictive ML Engine (Prophet Model)</h2>
          <p className="forecast-subtitle">Time-series anomaly forecasting & KES financial loss projections</p>
        </div>
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
      </div>

      <section className="forecast-kpi-grid">
        <div className="forecast-kpi-card danger">
          <span className="kpi-label">Projected Attack Surge</span>
          <span className="kpi-val">+24.6%</span>
          <span className="kpi-sub">Expected over weekend Peak</span>
        </div>
        <div className="forecast-kpi-card warning">
          <span className="kpi-label">Risk at Stake (KES)</span>
          <span className="kpi-val">KES {adjustedExposure.toLocaleString()}</span>
          <span className="kpi-sub">Projected fraud exposure</span>
        </div>
        <div className="forecast-kpi-card info">
          <span className="kpi-label">Predicted Peak Window</span>
          <span className="kpi-val">Sat 02:00 - 06:00 EAT</span>
          <span className="kpi-sub">High velocity carding expected</span>
        </div>
        <div className="forecast-kpi-card success">
          <span className="kpi-label">Model Drift Index</span>
          <span className="kpi-val">0.03 (Stable)</span>
          <span className="kpi-sub">Retraining due in 12 days</span>
        </div>
      </section>

      <section className="forecast-chart-card">
        <div className="chart-card-header">
          <h3>Prophet Fraud Volume & Confidence Bands</h3>
          <span className="chart-badge">KES Value Scale (x1000)</span>
        </div>
        <div className="forecast-chart-wrapper">
          <Container width="100%" height={340}>
            <Chart data={activeData} margin={{ top: 15, right: 30, left: 10, bottom: 0}}>
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
                formatter={(value, name) => [`KES ${(value * 1000).toLocaleString()}`, name]}
              />

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
              
              <AreaLine
                type="monotone"
                dataKey="forecast"
                stroke="#a855f7"
                strokeDasharray="4 4"
                fill="url(#colorForecast)"
                strokeWidth={2}
                name="Predicted Fraud (KES)"
              />

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

        <section className="vectors-card">
          <h3>Predicted Attack Vectors</h3>
          <div className="vector-list">
            <div className="vector-item">
              <div className="vector-info">
                <span>M-pesa SIM Swap / Account takeover</span>
                <strong>54%</strong>
              </div>
              <div className="vector-bar"><div className="vector-fill danger" style={{width: '54%' }}></div></div>
            </div>

            <div className="vector-item">
              <div className="vector-info">
                <span>Carding & Bot Velocity Attacks</span>
                <strong>28%</strong>
              </div>
              <div className="vector-bar"><div className="vector-fill warning" style={{ width: '28%' }}></div></div>
            </div>

            <div className="vector-item">
              <div className="vector-info">
                <span>Promo Code / Referral Exploits</span>
                <strong>18%</strong>
              </div>
              <div className="vector-bar"><div className="vector-fill info" style={{ width: '18%' }}></div></div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}