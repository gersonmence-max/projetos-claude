import React, { useEffect, useRef, useState } from 'react'
import { Chart, registerables } from 'chart.js'
import { calcResults, fmtUSD, fmtPayback } from '../lib/calc'
import { generatePDF } from '../lib/pdf'
import { saveAssessment } from '../lib/supabase'
import { Card, Metric, DarkBox } from './UI'

Chart.register(...registerables)

export default function Results({ form, t, lang, onNew }) {
  const [tab, setTab] = useState('client')
  const [adjKwh, setAdjKwh] = useState(parseFloat(form.yourKwhRate) || 0.35)
  const [saving, setSaving] = useState(false)
  const [savedId, setSavedId] = useState(null)
  const chartRef = useRef(null)
  const chartInst = useRef(null)
  const r = calcResults(form)

  const yearLabels = lang === 'pt'
    ? ['Ano 1','Ano 2','Ano 3','Ano 4','Ano 5']
    : lang === 'es'
      ? ['Año 1','Año 2','Año 3','Año 4','Año 5']
      : ['Year 1','Year 2','Year 3','Year 4','Year 5']

  useEffect(() => {
    chartInst.current?.destroy()
    if (!chartRef.current) return
    chartInst.current = new Chart(chartRef.current, {
      type: 'line',
      data: {
        labels: yearLabels,
        datasets: [
          {
            label: t.evFleetCum, data: r.tcoEV,
            borderColor: '#1a6b4a', backgroundColor: 'rgba(26,107,74,.08)',
            tension: 0.4, fill: true, pointBackgroundColor: '#1a6b4a',
            pointRadius: 5, pointHoverRadius: 7, borderWidth: 2,
          },
          {
            label: t.iceFleetCum, data: r.tcoICE,
            borderColor: '#dc2626', backgroundColor: 'rgba(220,38,38,.05)',
            tension: 0.4, fill: true, pointBackgroundColor: '#dc2626',
            pointRadius: 5, pointHoverRadius: 7, borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: {
            display: true, position: 'top',
            labels: { font: { size: 11, family: 'Inter, sans-serif' }, boxWidth: 12, padding: 18 },
          },
          tooltip: {
            backgroundColor: '#0f172a', titleFont: { size: 12 },
            bodyFont: { size: 11 }, padding: 12, cornerRadius: 9,
            callbacks: { label: ctx => ` ${ctx.dataset.label}: $${Math.round(ctx.raw / 1000)}k` },
          },
        },
        scales: {
          y: {
            ticks: { callback: v => '$' + (v / 1000).toFixed(0) + 'k', font: { size: 10 } },
            grid: { color: 'rgba(0,0,0,.04)' },
          },
          x: { ticks: { font: { size: 10 } }, grid: { display: false } },
        },
      },
    })
    return () => chartInst.current?.destroy()
  }, [lang])

  const handleSave = async () => {
    setSaving(true)
    try {
      const saved = await saveAssessment({ ...form, results: r })
      setSavedId(saved.id)
    } catch (e) { console.error(e) }
    setSaving(false)
  }

  const adjPayback = () => {
    const s = (r.iceFuelAnnual + r.iceMaintAnnual) - (r.annualKwh * adjKwh + r.evMaintAnnual)
    return s > 0 ? fmtPayback(r.totalInstallClient / s, t) : 'N/A'
  }
  const adjProfit = () => fmtUSD(r.annualKwh * (adjKwh - (parseFloat(form.kwRate) || 0.16)))

  const Row = ({ label, ev, ice, bold }) => (
    <div style={{
      display: 'flex', alignItems: 'center', padding: '10px 4px',
      borderBottom: '1px solid #f9fafb',
      background: bold ? '#f0fdf4' : 'transparent',
      borderRadius: bold ? 8 : 0,
      marginTop: bold ? 6 : 0,
    }}>
      <div style={{ flex: 1.4, fontSize: bold ? 13 : 12, fontWeight: bold ? 700 : 400, color: bold ? '#0f4c2a' : '#374151', paddingLeft: bold ? 8 : 0 }}>{label}</div>
      <div style={{ flex: 1, textAlign: 'center', fontSize: bold ? 14 : 12, fontWeight: 700, color: '#0f4c2a' }}>{ev}</div>
      <div style={{ flex: 1, textAlign: 'center', fontSize: bold ? 14 : 12, fontWeight: 700, color: '#b91c1c' }}>{ice}</div>
    </div>
  )

  return (
    <div>
      <div style={{ marginBottom: 22 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 8 }}>
          <span style={{ fontWeight: 700, color: '#374151', textTransform: 'uppercase', letterSpacing: '.05em' }}>{t.resultsLabel}</span>
          <span style={{ color: '#9ca3af' }}>{t.complete}</span>
        </div>
        <div style={{ height: 4, background: 'linear-gradient(90deg, #1a6b4a, #22c55e, #86efac)', borderRadius: 100 }} />
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex', border: '1.5px solid #e5e7eb',
        borderRadius: 11, overflow: 'hidden', marginBottom: 18,
        boxShadow: '0 1px 3px rgba(0,0,0,.05)',
      }}>
        {[['client', t.clientReport], ['margin', t.myMargins]].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} style={{
            flex: 1, padding: '11px 12px', textAlign: 'center',
            fontSize: 11, fontWeight: 700, cursor: 'pointer', border: 'none',
            borderRight: key === 'client' ? '1px solid #e5e7eb' : 'none',
            background: tab === key ? '#f0fdf4' : '#fff',
            color: tab === key ? '#0f4c2a' : '#9ca3af',
            fontFamily: 'inherit', textTransform: 'uppercase', letterSpacing: '.06em',
            transition: 'all .15s',
          }}>{label}</button>
        ))}
      </div>

      {tab === 'client' && (
        <div>
          {/* Hero */}
          <div style={{
            background: 'linear-gradient(135deg, #0b1f14 0%, #0f2a1a 60%, #0b1f14 100%)',
            borderRadius: 18, padding: '30px 24px', textAlign: 'center', marginBottom: 16,
            border: '1px solid rgba(34,197,94,.12)',
            boxShadow: '0 8px 32px rgba(0,0,0,.15)',
          }}>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,.35)', textTransform: 'uppercase', letterSpacing: '.14em', marginBottom: 12, fontWeight: 600 }}>{t.estimatedPayback}</div>
            <div style={{ fontSize: 52, fontWeight: 800, letterSpacing: '-2.5px', color: '#fff', lineHeight: 1 }}>{fmtPayback(r.paybackYears, t)}</div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 32, marginTop: 20, paddingTop: 20, borderTop: '1px solid rgba(255,255,255,.08)' }}>
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#22c55e' }}>{fmtUSD(r.annualSavings)}</div>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,.3)', textTransform: 'uppercase', letterSpacing: '.07em', marginTop: 3, fontWeight: 500 }}>{t.annualSavings}</div>
              </div>
              <div style={{ width: 1, background: 'rgba(255,255,255,.08)' }} />
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'rgba(255,255,255,.65)' }}>{fmtUSD(r.totalInstallClient)}</div>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,.3)', textTransform: 'uppercase', letterSpacing: '.07em', marginTop: 3, fontWeight: 500 }}>{t.totalInvestment}</div>
              </div>
            </div>
          </div>

          {/* Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
            <Metric value={fmtUSD(r.annualSavings)} label={t.annualSavings} sub={t.annualSavingsSub} accent />
            <Metric value={r.chargersNeeded} label={t.chargersNeeded} sub="Level 2 AC" />
            <Metric value={r.co2Saved + 't'} label={t.co2Reduced} sub={t.tonsYear} />
          </div>

          {/* Chart */}
          <Card head={t.fiveYearComp}>
            <div style={{ position: 'relative', height: 265 }} id="pdfChartCanvas">
              <canvas ref={chartRef} />
            </div>
          </Card>

          {/* Comparison */}
          <Card head={t.annualBreakdown}>
            <div style={{ display: 'flex', paddingBottom: 10, marginBottom: 4, borderBottom: '2px solid #f3f4f6' }}>
              <div style={{ flex: 1.4 }} />
              <div style={{ flex: 1, textAlign: 'center', fontSize: 10, fontWeight: 700, color: '#1a6b4a', textTransform: 'uppercase', letterSpacing: '.07em' }}>{t.evFleetLabel}</div>
              <div style={{ flex: 1, textAlign: 'center', fontSize: 10, fontWeight: 700, color: '#b91c1c', textTransform: 'uppercase', letterSpacing: '.07em' }}>{t.iceFleetLabel}</div>
            </div>
            <Row label={t.catFuel} ev={fmtUSD(r.evEnergyCost)} ice={fmtUSD(r.iceFuelAnnual)} />
            <Row label={t.catMaint} ev={fmtUSD(r.evMaintAnnual)} ice={fmtUSD(r.iceMaintAnnual)} />
            <Row label={t.catIns} ev={fmtUSD(r.annualIns)} ice={fmtUSD(r.annualIns)} />
            <Row label={t.catTotal} ev={fmtUSD(r.evAnnualTotal)} ice={fmtUSD(r.iceAnnualTotal)} bold />
          </Card>

          {/* Infrastructure */}
          <Card head={t.infraRec}>
            {[
              `${r.chargersNeeded} × ${t.levelTwoChargers} (${r.chargerTypeKw} kW)`,
              `${t.additionalLoad}: ~${r.chargePowerKw} kW`,
              `${t.chargingWindow}: ${r.hoursParked}h — ${t.sufficientFor} ${Math.round(r.milesDay)} ${t.miDay}`,
            ].map((line, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, padding: '9px 0', borderBottom: i < 2 ? '1px solid #f9fafb' : 'none', alignItems: 'flex-start' }}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#1a6b4a', flexShrink: 0, marginTop: 5 }} />
                <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.55 }}>{line}</div>
              </div>
            ))}
            {r.hasLongTrips && (
              <div style={{
                background: '#fffbeb', border: '1px solid #fde68a',
                borderRadius: 10, padding: '12px 16px',
                fontSize: 12, marginTop: 12, color: '#92400e', lineHeight: 1.6,
              }}>{t.dcWarning}</div>
            )}
          </Card>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, marginTop: 18, flexWrap: 'wrap' }}>
            <button onClick={() => generatePDF(form, r, lang)} style={{
              padding: '11px 24px', borderRadius: 9, fontSize: 13, fontWeight: 600,
              cursor: 'pointer', border: 'none',
              background: 'linear-gradient(135deg, #1a6b4a, #0f4c2a)',
              color: '#fff', fontFamily: 'inherit', letterSpacing: '.02em',
              boxShadow: '0 4px 14px rgba(26,107,74,.3)',
              transition: 'all .15s',
            }}>{t.exportPdf}</button>
            <button onClick={handleSave} style={{
              padding: '11px 22px', borderRadius: 9, fontSize: 13, fontWeight: 600,
              cursor: 'pointer', border: '1.5px solid #e5e7eb',
              background: savedId ? '#f0fdf4' : '#fff',
              color: savedId ? '#1a6b4a' : '#6b7280',
              fontFamily: 'inherit', minWidth: 140, transition: 'all .15s',
            }}>
              {saving ? t.saving : savedId ? t.saved : t.saveAssessment}
            </button>
            <button onClick={onNew} style={{
              padding: '11px 22px', borderRadius: 9, fontSize: 13, fontWeight: 500,
              cursor: 'pointer', border: '1.5px solid #e5e7eb',
              background: '#fff', color: '#6b7280', fontFamily: 'inherit',
            }}>{t.newAssessment}</button>
          </div>
        </div>
      )}

      {tab === 'margin' && (
        <div>
          <DarkBox>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <div style={{
                background: '#162019', border: '1px solid #1e3024',
                borderRadius: 5, padding: '3px 10px',
                fontSize: 9, fontWeight: 700, color: '#4b6b58', letterSpacing: '.08em',
              }}>🔒 {t.confidential}</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
              {[
                { v: fmtUSD(r.installMargin), l: t.installProfit },
                { v: fmtUSD(r.kwhMarginAnnual), l: t.kwhYear },
                { v: fmtUSD(r.maintAnnual), l: t.maintYear },
                { v: fmtUSD(r.yr1Profit), l: t.yr1Total },
                { v: fmtUSD(r.yr3Profit), l: t.yr3Cumul },
                { v: fmtUSD(r.yr5Profit), l: t.yr5Cumul },
              ].map(m => (
                <div key={m.l} style={{
                  background: '#162019', border: '1px solid #1e3024',
                  borderRadius: 10, padding: '15px 10px', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#fff', letterSpacing: '-.4px' }}>{m.v}</div>
                  <div style={{ fontSize: 9, color: '#3d5e4a', marginTop: 5, textTransform: 'uppercase', letterSpacing: '.07em' }}>{m.l}</div>
                </div>
              ))}
            </div>
          </DarkBox>

          <Card head={t.adjustKwh}>
            <div style={{ marginBottom: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#4b5563', textTransform: 'uppercase', letterSpacing: '.06em' }}>{t.clientKwhRate}</span>
                <span style={{ fontSize: 16, fontWeight: 700, color: '#1a6b4a' }}>${adjKwh.toFixed(2)}</span>
              </div>
              <input type="range" min="0.10" max="0.80" step="0.01" value={adjKwh}
                onChange={e => setAdjKwh(parseFloat(e.target.value))}
                style={{ width: '100%', accentColor: '#1a6b4a', cursor: 'pointer' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#b0b8c4', marginTop: 5 }}>
                <span>$0.10</span><span>$0.45</span><span>$0.80</span>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <Metric value={adjPayback()} label={t.clientPayback} />
              <Metric value={adjProfit()} label={t.yourKwhProfit} accent />
            </div>
          </Card>

          <div style={{ marginTop: 16 }}>
            <button onClick={onNew} style={{
              padding: '11px 22px', borderRadius: 9, fontSize: 13, fontWeight: 500,
              cursor: 'pointer', border: '1.5px solid #e5e7eb',
              background: '#fff', color: '#6b7280', fontFamily: 'inherit',
            }}>{t.newAssessment}</button>
          </div>
        </div>
      )}
    </div>
  )
}
