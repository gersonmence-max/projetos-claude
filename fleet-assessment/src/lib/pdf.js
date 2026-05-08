import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { fmtUSD, fmtPayback } from './calc'

export async function generatePDF(form, results, lang = 'en') {
  const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  const W = 210, M = 16
  const green = [26, 107, 74]
  const darkBg = [15, 31, 23]
  const gray = [100, 116, 139]
  const lightGray = [241, 245, 249]
  const red = [185, 28, 28]

  let y = 0

  // ── Header ─────────────────────────────────────────────────────────────────
  pdf.setFillColor(...darkBg)
  pdf.rect(0, 0, W, 40, 'F')
  pdf.setTextColor(255, 255, 255)
  pdf.setFontSize(18)
  pdf.setFont('helvetica', 'bold')
  pdf.text(lang === 'pt' ? 'Avaliação de Eletrificação de Frota' : lang === 'es' ? 'Evaluación de Electrificación de Flota' : 'Fleet Electrification Assessment', M, 16)
  pdf.setFontSize(9)
  pdf.setFont('helvetica', 'normal')
  pdf.setTextColor(180, 200, 190)
  pdf.text(lang === 'pt' ? 'Plataforma de Prontidão EV e ROI' : lang === 'es' ? 'Plataforma de Preparación EV y ROI' : 'EV Fleet Readiness & ROI Platform', M, 24)
  pdf.setTextColor(140, 170, 155)
  pdf.text(`${form.companyName || 'Fleet Assessment'} · ${new Date().toLocaleDateString()}`, M, 32)
  y = 50

  // ── ROI Hero ───────────────────────────────────────────────────────────────
  pdf.setFillColor(...green)
  pdf.roundedRect(M, y, W - M * 2, 28, 4, 4, 'F')
  pdf.setTextColor(255, 255, 255)
  pdf.setFontSize(22)
  pdf.setFont('helvetica', 'bold')
  pdf.text(fmtPayback(results.paybackYears), W / 2, y + 12, { align: 'center' })
  pdf.setFontSize(9)
  pdf.setFont('helvetica', 'normal')
  pdf.text(lang === 'pt' ? 'Período de Retorno Estimado' : lang === 'es' ? 'Período de Retorno Estimado' : 'Estimated Payback Period', W / 2, y + 20, { align: 'center' })
  pdf.setFontSize(8)
  pdf.setTextColor(200, 230, 215)
  pdf.text(`${lang === 'pt' ? 'Investimento total' : lang === 'es' ? 'Inversión total' : 'Total investment'}: ${fmtUSD(results.totalInstallClient)}   ·   ${lang === 'pt' ? 'Economia anual' : lang === 'es' ? 'Ahorro anual' : 'Annual savings'}: ${fmtUSD(results.annualSavings)}`, W / 2, y + 26, { align: 'center' })
  y += 36

  // ── Metrics row ────────────────────────────────────────────────────────────
  const metrics = [
    { label: lang === 'pt' ? 'Economia anual' : lang === 'es' ? 'Ahorro anual' : 'Annual savings', value: fmtUSD(results.annualSavings), sub: lang === 'pt' ? 'Combust. + manutenção' : lang === 'es' ? 'Comb. + mantenimiento' : 'Fuel + maintenance' },
    { label: lang === 'pt' ? 'Carregadores' : lang === 'es' ? 'Cargadores' : 'Chargers needed', value: String(results.chargersNeeded), sub: 'Level 2 AC' },
    { label: 'CO₂ reduced', value: results.co2Saved + 't', sub: lang === 'pt' ? 'Toneladas / ano' : lang === 'es' ? 'Toneladas / año' : 'Tons per year' },
  ]
  const mW = (W - M * 2 - 8) / 3
  metrics.forEach((m, i) => {
    const mx = M + i * (mW + 4)
    pdf.setFillColor(...lightGray)
    pdf.roundedRect(mx, y, mW, 22, 3, 3, 'F')
    pdf.setTextColor(...green)
    pdf.setFontSize(14)
    pdf.setFont('helvetica', 'bold')
    pdf.text(m.value, mx + mW / 2, y + 10, { align: 'center' })
    pdf.setTextColor(...gray)
    pdf.setFontSize(7)
    pdf.setFont('helvetica', 'normal')
    pdf.text(m.label, mx + mW / 2, y + 16, { align: 'center' })
    pdf.text(m.sub, mx + mW / 2, y + 20, { align: 'center' })
  })
  y += 30

  // ── Annual Cost Breakdown ──────────────────────────────────────────────────
  pdf.setFontSize(10)
  pdf.setFont('helvetica', 'bold')
  pdf.setTextColor(15, 23, 42)
  pdf.text(lang === 'pt' ? 'Custo Anual — ICE vs VE' : lang === 'es' ? 'Costo Anual — ICE vs VE' : 'Annual Cost Breakdown — ICE vs EV', M, y)
  y += 6

  const rows = [
    [lang === 'pt' ? 'Combustível / Energia' : lang === 'es' ? 'Combustible / Energía' : 'Fuel / Energy', fmtUSD(results.evEnergyCost), fmtUSD(results.iceFuelAnnual)],
    [lang === 'pt' ? 'Manutenção' : lang === 'es' ? 'Mantenimiento' : 'Maintenance', fmtUSD(results.evMaintAnnual), fmtUSD(results.iceMaintAnnual)],
    [lang === 'pt' ? 'Seguro' : 'Insurance', fmtUSD(results.annualIns), fmtUSD(results.annualIns)],
    [lang === 'pt' ? 'TOTAL ANUAL' : lang === 'es' ? 'TOTAL ANUAL' : 'TOTAL ANNUAL', fmtUSD(results.evAnnualTotal), fmtUSD(results.iceAnnualTotal)],
  ]

  // header
  pdf.setFillColor(240, 244, 248)
  pdf.rect(M, y, W - M * 2, 7, 'F')
  pdf.setFontSize(7.5)
  pdf.setFont('helvetica', 'bold')
  pdf.setTextColor(...gray)
  pdf.text(lang === 'pt' ? 'Categoria' : 'Category', M + 3, y + 5)
  pdf.setTextColor(...green)
  pdf.text('EV Fleet', M + 110, y + 5)
  pdf.setTextColor(...red)
  pdf.text('ICE Fleet', M + 148, y + 5)
  y += 8

  rows.forEach((r, i) => {
    if (i === rows.length - 1) {
      pdf.setFillColor(232, 248, 240)
      pdf.rect(M, y - 1, W - M * 2, 9, 'F')
    }
    pdf.setFontSize(i === rows.length - 1 ? 8.5 : 8)
    pdf.setFont('helvetica', i === rows.length - 1 ? 'bold' : 'normal')
    pdf.setTextColor(30, 41, 59)
    pdf.text(r[0], M + 3, y + 5)
    pdf.setTextColor(...green)
    pdf.text(r[1], M + 110, y + 5)
    pdf.setTextColor(...red)
    pdf.text(r[2], M + 148, y + 5)
    y += 9
  })
  y += 6

  // ── 5-Year TCO Chart (via canvas) ─────────────────────────────────────────
  try {
    const chartEl = document.getElementById('pdfChartCanvas')
    if (chartEl) {
      const canvas = await html2canvas(chartEl, { scale: 2, backgroundColor: '#ffffff' })
      const imgData = canvas.toDataURL('image/png')
      const chartH = 55
      pdf.setFontSize(10)
      pdf.setFont('helvetica', 'bold')
      pdf.setTextColor(15, 23, 42)
      pdf.text(lang === 'pt' ? 'Comparativo de Custo — 5 Anos' : lang === 'es' ? 'Comparativa de Costo — 5 Años' : '5-Year Cost Comparison', M, y)
      y += 5
      pdf.addImage(imgData, 'PNG', M, y, W - M * 2, chartH)
      y += chartH + 8
    }
  } catch (e) { /* skip chart if unavailable */ }

  // ── Infrastructure Recommendation ─────────────────────────────────────────
  pdf.setFontSize(10)
  pdf.setFont('helvetica', 'bold')
  pdf.setTextColor(15, 23, 42)
  pdf.text(lang === 'pt' ? 'Recomendação de Infraestrutura' : lang === 'es' ? 'Recomendación de Infraestructura' : 'Infrastructure Recommendation', M, y)
  y += 6

  pdf.setFillColor(...lightGray)
  pdf.roundedRect(M, y, W - M * 2, 30, 3, 3, 'F')
  pdf.setFontSize(9)
  pdf.setFont('helvetica', 'normal')
  pdf.setTextColor(30, 41, 59)
  const infraLines = [
    `${results.chargersNeeded} × Level 2 AC chargers (${results.chargerTypeKw} kW each)`,
    `${lang === 'pt' ? 'Carga adicional no local' : lang === 'es' ? 'Carga adicional en sitio' : 'Additional site load'}: ~${results.chargePowerKw} kW`,
    `${lang === 'pt' ? 'Janela de recarga' : lang === 'es' ? 'Ventana de carga' : 'Charging window'}: ${results.hoursParked}h — ${lang === 'pt' ? 'suficiente para' : lang === 'es' ? 'suficiente para' : 'sufficient for'} ${Math.round(results.milesDay)} ${lang === 'pt' ? 'km/dia' : lang === 'es' ? 'km/día' : 'mi/day'}`,
    results.hasLongTrips ? (lang === 'pt' ? '⚠ Alta quilometragem: considere 1–2 carregadores DC rápidos (50kW+)' : lang === 'es' ? '⚠ Alta kilometraje: considera 1–2 cargadores DC rápidos (50kW+)' : '⚠ High mileage: consider 1–2 DC fast chargers (50kW+)') : ''
  ].filter(Boolean)
  infraLines.forEach((line, i) => {
    pdf.text(`• ${line}`, M + 4, y + 7 + i * 6)
  })
  y += 36

  // ── Footer ─────────────────────────────────────────────────────────────────
  pdf.setFillColor(245, 248, 250)
  pdf.rect(0, 285, W, 12, 'F')
  pdf.setFontSize(7)
  pdf.setTextColor(...gray)
  pdf.text('Fleet Electrification Assessment · EV Fleet Readiness & ROI Platform', M, 292)
  pdf.text(new Date().toLocaleDateString(), W - M, 292, { align: 'right' })

  pdf.save(`fleet-assessment-${(form.companyName || 'report').replace(/\s+/g, '-').toLowerCase()}.pdf`)
}
