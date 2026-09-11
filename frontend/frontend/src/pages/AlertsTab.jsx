import React, { useState, useEffect } from 'react';
import { alertService } from '../services/api';
import { exportAlertsPdf } from '../utils/pdfExport';
import './AlertsTab.css';

export default function AlertsTab() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [selectedAlert, setSelectedAlert] = useState(null);

  // 1. Fetch live alerts from FastAPI on load
  const fetchAlerts = () => {
    setLoading(true);
    alertService
      .getAlerts()
      .then((data) => {
        setAlerts(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('API Error:', err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchAlerts();

    const token = localStorage.getItem('token');

    const ws = new WebSocket(`ws://localhost:8080/ws/alerts?token=${token}`);

    ws.onopen = () => {
      console.log('Connected to Live Alert Websocket')
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'NEW_ALERT') {
        //prepend incoming alert
        setAlerts((prevAlerts) => [message.data, ...prevAlerts]);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket Error: ', error)
    };

    return () => {
      ws.close();
    };
  }, []);

  // 2. Persist triage action to backend
  const handleUpdateStatus = (id, newStatus) => {
    alertService
      .updateStatus(id, newStatus)
      .then(() => {
        setAlerts((prev) =>
          prev.map((alert) => (alert.id === id ? { ...alert, status: newStatus } : alert))
        );
        if (selectedAlert && selectedAlert.id === id) {
          setSelectedAlert((prev) => ({ ...prev, status: newStatus }));
        }
      })
      .catch((err) => console.error('Status update failed:', err));
  };

  // Filter Logic
  const filteredAlerts = alerts.filter((alert) => {
    const matchesSearch =
      alert.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.userId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.ip.includes(searchQuery) ||
      alert.trigger.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSeverity = severityFilter === 'All' || alert.severity === severityFilter;
    const matchesStatus = statusFilter === 'All' || alert.status === statusFilter;

    return matchesSearch && matchesSeverity && matchesStatus;
  });

  // Metric calculations
  const criticalCount = alerts.filter(
    (a) => a.severity === 'Critical' && !a.status.startsWith('Resolved')
  ).length;
  const pendingCount = alerts.filter(
    (a) => a.status === 'New' || a.status === 'Under Investigation'
  ).length;
  const resolvedCount = alerts.filter((a) => a.status.startsWith('Resolved')).length;

  const exportToPDF = () => {
    exportAlertsPdf({
      alerts: filteredAlerts,
      criticalCount,
      pendingCount,
      resolvedCount,
    });
  };

  return (
    <div className="alerts-container">
      {/* 1. Alerts KPI Header */}
      <section className="alerts-kpi-grid">
        <div className="alert-kpi-card critical">
          <span className="kpi-title">Critical Threats</span>
          <span className="kpi-count">{criticalCount}</span>
          <span className="kpi-subtext">Requires immediate block</span>
        </div>
        <div className="alert-kpi-card pending">
          <span className="kpi-title">Pending Review</span>
          <span className="kpi-count">{pendingCount}</span>
          <span className="kpi-subtext">Active triage queue</span>
        </div>
        <div className="alert-kpi-card resolved">
          <span className="kpi-title">Resolved Today</span>
          <span className="kpi-count">{resolvedCount}</span>
          <span className="kpi-subtext">Cleared by analysts</span>
        </div>
        <div className="alert-kpi-card response-time">
          <span className="kpi-title">Avg Triage Speed</span>
          <span className="kpi-count">3.4m</span>
          <span className="kpi-subtext">Target: &lt; 5.0m</span>
        </div>
      </section>

      {/* 2. Controls & Search */}
      <section className="alerts-controls">
        <input
          type="text"
          placeholder="Search Alert ID, User, IP, or Trigger Rule..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="alerts-search-input"
        />

        <div className="alerts-filter-group">
          <label>Severity:</label>
          <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
            <option value="All">All Severities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>

        <div className="alerts-filter-group">
          <label>Status:</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="All">All Statuses</option>
            <option value="New">New</option>
            <option value="Under Investigation">Under Investigation</option>
            <option value="Resolved - Fraud">Resolved - Fraud</option>
            <option value="Resolved - Approved">Resolved - Approved</option>
          </select>
        </div>

        <button
            className='btn-export-csv'
            onClick={exportToPDF}
            title="Download filtered incident logs as a PDF"
        >
          Export Executive Report    
        </button>
      </section>

      {/* 3. Alerts Main Table */}
      <section className="alerts-table-wrapper">
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Alert ID</th>
              <th>Timestamp</th>
              <th>Rule Trigger</th>
              <th>User ID</th>
              <th>Amount</th>
              <th>IP & Location</th>
              <th>Risk Score</th>
              <th>Status</th>
              <th>Quick Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="9" className="no-data">Loading security alerts...</td>
              </tr>
            ) : filteredAlerts.length > 0 ? (
              filteredAlerts.map((alert) => (
                <tr key={alert.id} className={alert.severity.toLowerCase()}>
                  <td className="font-mono">{alert.id}</td>
                  <td className="text-muted">{alert.timestamp.split(' ')[1]}</td>
                  <td><strong>{alert.trigger}</strong></td>
                  <td className="font-mono">{alert.userId}</td>
                  <td>{alert.amount}</td>
                  <td>
                    <code>{alert.ip}</code>
                    <span className="location-tag">{alert.location}</span>
                  </td>
                  <td>
                    <span className={`risk-pill ${alert.score >= 0.8 ? 'critical' : alert.score >= 0.6 ? 'high' : 'medium'}`}>
                      {alert.score}
                    </span>
                  </td>
                  <td>
                    <span className={`status-pill ${alert.status.toLowerCase().replace(/\s+/g, '-')}`}>
                      {alert.status}
                    </span>
                  </td>
                  <td className="actions-cell">
                    <button
                      className="btn-action block"
                      title="Block User & Confirm Fraud"
                      onClick={() => handleUpdateStatus(alert.id, 'Resolved - Fraud')}
                    >
                      Block
                    </button>
                    <button
                      className="btn-action approve"
                      title="Approve Transaction"
                      onClick={() => handleUpdateStatus(alert.id, 'Resolved - Approved')}
                    >
                      Approve
                    </button>
                    <button
                      className="btn-action inspect"
                      onClick={() => setSelectedAlert(alert)}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="9" className="no-data">No matching security alerts found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {/* 4. Inspection Modal */}
      {selectedAlert && (
        <div className="modal-backdrop" onClick={() => setSelectedAlert(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <h3>Incident Deep Dive: {selectedAlert.id}</h3>
              <button className="modal-close" onClick={() => setSelectedAlert(null)}>&times;</button>
            </header>

            <div className="modal-body">
              <div className="modal-grid">
                <div>
                  <label>Triggering Rule</label>
                  <p className="modal-value">{selectedAlert.trigger}</p>
                </div>
                <div>
                  <label>Risk Score</label>
                  <p className="modal-value text-danger">{selectedAlert.score} (Severity: {selectedAlert.severity})</p>
                </div>
                <div>
                  <label>User ID</label>
                  <p className="modal-value font-mono">{selectedAlert.userId}</p>
                </div>
                <div>
                  <label>Transaction Amount</label>
                  <p className="modal-value">{selectedAlert.amount}</p>
                </div>
                <div>
                  <label>IP Address & Geo</label>
                  <p className="modal-value font-mono">{selectedAlert.ip} ({selectedAlert.location})</p>
                </div>
                <div>
                  <label>Client Device Fingerprint</label>
                  <p className="modal-value font-mono">{selectedAlert.device}</p>
                </div>
              </div>

              <div className="xai-section">
                <h4>ML Model Decision Breakdown (SHAP Feature Importance)</h4>
                <div className="shap-grid">
                  <div className="shap-item danger">
                    <span>TOR Exit Node Usage</span>
                    <div className="shap-bar"><div className="fill" style={{ width: '85%' }}></div></div>
                    <strong>+0.42 Risk</strong>
                  </div>
                  <div className="shap-item danger">
                    <span>High Velocity Pattern</span>
                    <div className="shap-bar"><div className="fill" style={{ width: '65%' }}></div></div>
                    <strong>+0.31 Risk</strong>
                  </div>
                  <div className="shap-item success">
                    <span>Known Device Fingerprint</span>
                    <div className="shap-bar"><div className="fill" style={{ width: '30%' }}></div></div>
                    <strong>-0.15 Risk</strong>
                  </div>
                </div>
              </div>

              <div className="raw-json-box">
                <label>Raw Payload Telemetry</label>
                <pre>{JSON.stringify(selectedAlert, null, 2)}</pre>
              </div>
            </div>

            <footer className="modal-footer">
              <button
                className="btn-modal danger"
                onClick={() => handleUpdateStatus(selectedAlert.id, 'Resolved - Fraud')}
              >
                Confirm Fraud & Blacklist IP
              </button>
              <button
                className="btn-modal success"
                onClick={() => handleUpdateStatus(selectedAlert.id, 'Resolved - Approved')}
              >
                Mark as False Positive
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}