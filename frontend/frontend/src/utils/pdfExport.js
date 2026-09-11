import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

const BRAND = [37, 99, 235];
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
