import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

const BRAND = [232, 102, 67];
const INK = [15, 23, 42];
const MUTED = [100, 116, 139];

function todayStamp() {
  return new Date().toISOString().slice(0, 10);
}

function addReportHeader(doc, title, subtitle) {
  const pageWidth = doc.internal.pageSize.getWidth();

  doc.setFillColor(...BRAND);
  doc.rect(0, 0, pageWidth, 28, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.text('FraudGuard AI', 14, 12);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.text(title, 14, 20);

  doc.setFontSize(8);
  doc.text(subtitle, pageWidth - 14, 12, { align: 'right' });
  doc.text(`Generated ${new Date().toLocaleString()}`, pageWidth - 14, 20, { align: 'right' });

  doc.setTextColor(...INK);
}

function addFooter(doc) {
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i += 1) {
    doc.setPage(i);
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    doc.setFontSize(8);
    doc.setTextColor(...MUTED);
    doc.text(`Confidential — FraudGuard AI executive report  ·  page ${i} of ${pageCount}`, 14, pageHeight - 8);
    doc.text('Not for external distribution', pageWidth - 14, pageHeight - 8, { align: 'right' });
  }
}

export function exportAlertsPdf({
  alerts,
  criticalCount,
  pendingCount,
  resolvedCount,
}) {
  if (!alerts || alerts.length === 0) {
    window.alert('No security alerts available to export.');
    return;
  }

  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
  addReportHeader(doc, 'Executive Fraud Incident Report', `Alerts export · ${todayStamp()}`);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(...INK);
  doc.text('Triage snapshot', 14, 40);

  autoTable(doc, {
    startY: 44,
    theme: 'grid',
    head: [['Critical threats', 'Pending review', 'Resolved', 'Incidents in this export']],
    body: [[String(criticalCount), String(pendingCount), String(resolvedCount), String(alerts.length)]],
    headStyles: { fillColor: BRAND, textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 9, cellPadding: 3 },
  });

  autoTable(doc, {
    startY: doc.lastAutoTable.finalY + 10,
    theme: 'striped',
    head: [[
      'Alert ID',
      'Timestamp',
      'Rule trigger',
      'User ID',
      'Amount',
      'IP',
      'Location',
      'Score',
      'Severity',
      'Status',
    ]],
    body: alerts.map((alert) => [
      alert.id,
      alert.timestamp,
      alert.trigger,
      alert.userId,
      alert.amount,
      alert.ip,
      alert.location,
      alert.score,
      alert.severity,
      alert.status,
    ]),
    headStyles: { fillColor: BRAND, textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 8, cellPadding: 2.2, overflow: 'linebreak' },
    columnStyles: {
      2: { cellWidth: 48 },
    },
  });

  addFooter(doc);
  doc.save(`FraudGuard_Alerts_Report_${todayStamp()}.pdf`);
}

export function exportAlertPdf(alert) {
  if (!alert) return;

  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  addReportHeader(doc, 'Individual Fraud Alert Report', `Alert · ${todayStamp()}`);

  autoTable(doc, {
    startY: 34,
    theme: 'grid',
    head: [['Incident field', 'Recorded details']],
    body: [
      ['Alert ID', alert.id],
      ['Detected at', alert.timestamp || 'Unknown'],
      ['Customer', alert.userName || 'Unknown account'],
      ['User ID', alert.userId || 'Unknown'],
      ['Transaction ID', alert.transaction_id || alert.transactionId || 'Unknown'],
      ['Transaction time', alert.transactionTimestamp || 'Unknown'],
      ['Amount', alert.amount || 'Unknown'],
      ['Severity / model score', `${alert.severity || 'Unknown'} / ${alert.score ?? 'Unknown'}`],
      ['Review status', alert.status || 'Unknown'],
      ['IP address', `${alert.ip || 'Unknown'} · ${alert.location || 'Location unavailable'}`],
      ['Device fingerprint', alert.device || 'Unknown'],
      ['Trigger', alert.trigger || 'Unknown'],
    ],
    headStyles: { fillColor: BRAND, textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 8.5, cellPadding: 2.5, overflow: 'linebreak' },
    columnStyles: { 0: { cellWidth: 48, fontStyle: 'bold' } },
  });

  let sectionY = doc.lastAutoTable.finalY + 9;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(...INK);
  doc.text('Reason for flagging', 14, sectionY);
  sectionY += 6;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  const reasonLines = doc.splitTextToSize(alert.reason || 'No model explanation was provided for this alert.', 182);
  doc.text(reasonLines, 14, sectionY);
  sectionY += reasonLines.length * 4.5 + 5;

  if (alert.modelFeatures?.length) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.text('Model inputs at detection', 14, sectionY);
    autoTable(doc, {
      startY: sectionY + 4,
      theme: 'striped',
      head: [['Input', 'Value']],
      body: alert.modelFeatures.map((feature) => [feature.label, String(feature.value)]),
      headStyles: { fillColor: BRAND, textColor: 255, fontStyle: 'bold' },
      styles: { fontSize: 8.5, cellPadding: 2.5 },
      columnStyles: { 0: { cellWidth: 82 } },
    });
  }

  addFooter(doc);
  const fileId = String(alert.id || 'alert').replace(/[^a-z0-9-]/gi, '').slice(-24);
  doc.save(`FraudGuard_Alert_${fileId || todayStamp()}.pdf`);
}

export function exportForecastPdf({
  timeframe,
  riskCutoff,
  enforceMpesaPin,
  blockVpn,
  attackSurge,
  exposureKES,
  peakWindow,
  modelDrift,
  chartData,
  attackVectors,
}) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const horizon = timeframe === '24h' ? 'Next 24 hours' : 'Next 7 days';

  addReportHeader(doc, 'Predictive ML Forecast Report (Prophet)', `${horizon} · ${todayStamp()}`);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(...INK);
  doc.text('Key projections', 14, 40);

  autoTable(doc, {
    startY: 44,
    theme: 'grid',
    head: [['Projected attack surge', 'Risk at stake (KES)', 'Peak window', 'Model drift']],
    body: [[
      attackSurge,
      `KES ${Number(exposureKES || 0).toLocaleString()}`,
      peakWindow,
      modelDrift,
    ]],
    headStyles: { fillColor: BRAND, textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 9, cellPadding: 3 },
  });

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.text('Mitigation simulator settings', 14, doc.lastAutoTable.finalY + 12);

  autoTable(doc, {
    startY: doc.lastAutoTable.finalY + 16,
    theme: 'plain',
    body: [
      ['Horizon', horizon],
      ['Risk score cutoff', String(riskCutoff)],
      ['M-Pesa STK re-auth on > KES 50,000', enforceMpesaPin ? 'Enabled' : 'Disabled'],
      ['Auto-block VPN & proxy transactions', blockVpn ? 'Enabled' : 'Disabled'],
    ],
    styles: { fontSize: 9, cellPadding: 2.5 },
    columnStyles: {
      0: { fontStyle: 'bold', cellWidth: 70, textColor: MUTED },
      1: { textColor: INK },
    },
  });

  autoTable(doc, {
    startY: doc.lastAutoTable.finalY + 10,
    theme: 'striped',
    head: [['Period', 'Actual (KES x1000)', 'Forecast (KES x1000)', 'Lower bound', 'Upper bound']],
    body: (chartData || []).map((row) => [
      row.day,
      row.actual ?? '—',
      row.forecast ?? '—',
      row.lowerBound ?? '—',
      row.upperBound ?? '—',
    ]),
    headStyles: { fillColor: BRAND, textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 9, cellPadding: 3 },
  });

  autoTable(doc, {
    startY: doc.lastAutoTable.finalY + 10,
    theme: 'striped',
    head: [['Predicted attack vector', 'Share', 'Level']],
    body: (attackVectors || []).map((vector) => [
      vector.label,
      `${vector.percentage}%`,
      vector.level,
    ]),
    headStyles: { fillColor: BRAND, textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 9, cellPadding: 3 },
  });

  addFooter(doc);
  doc.save(`FraudGuard_Forecast_Report_${todayStamp()}.pdf`);
}
