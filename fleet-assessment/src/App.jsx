import React, { useState } from 'react'
import { translations } from './i18n/translations'
import Header from './components/Header'
import AssessmentForm from './components/AssessmentForm'
import Results from './components/Results'
import Dashboard from './components/Dashboard'
import { getAssessment } from './lib/supabase'

export default function App() {
  const [lang, setLang] = useState('en')
  const [view, setView] = useState('form')
  const [completedForm, setCompletedForm] = useState(null)

  const t = translations[lang]

  const handleFormComplete = form => {
    setCompletedForm(form)
    setView('results')
    window.scrollTo(0, 0)
  }

  const handleViewSaved = async id => {
    try {
      const data = await getAssessment(id)
      const form = {
        hasEV: data.has_ev,
        companyName: data.company_name || '',
        industry: data.industry || '',
        state: data.state || '',
        totalFleet: data.total_fleet || '',
        vehicles: data.vehicles || [],
        milesDay: data.miles_day || '',
        opDays: data.op_days || '250',
        hoursParked: data.hours_parked || '10',
        monthlyFuel: data.monthly_fuel || '',
        kwRate: data.kw_rate || '0.16',
        iceMaint: data.ice_maint || '',
        insurance: data.insurance || '2400',
        evEfficiency: data.ev_efficiency || '0.35',
        evMaint: data.ev_maint || '',
        evVehicleCost: data.ev_vehicle_cost || '',
        evNext12: data.ev_next_12 || '',
        evNext36: data.ev_next_36 || '',
        installCostUs: data.install_cost_us || '',
        installPriceClient: data.install_price_client || '',
        maintFeeClient: data.maint_fee_client || '',
        hwCost: data.hw_cost || '1200',
        yourKwhRate: data.your_kwh_rate || 0.35,
        longTrips: 0, shifts: '1', routeType: 'mixed',
        fuelType: 'gasoline', voltage: '480', panelCap: 'unknown',
        parkingType: 'lot', existingInfra: 'none', hasSolar: 'no',
      }
      setCompletedForm(form)
      setView('results')
      window.scrollTo(0, 0)
    } catch (e) { console.error(e) }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '16px 16px 60px', minHeight: '100vh' }}>
      <Header lang={lang} setLang={setLang} t={t} />

      {/* Nav tabs */}
      <div style={{
        display: 'flex', border: '1.5px solid #e5e7eb',
        borderRadius: 11, overflow: 'hidden', marginBottom: 22,
        boxShadow: '0 1px 4px rgba(0,0,0,.05)',
      }} className="no-print">
        {[['form', t.navNew], ['dashboard', t.navSaved]].map(([key, label]) => (
          <button key={key} onClick={() => setView(key)} style={{
            flex: 1, padding: '10px 12px', textAlign: 'center',
            fontSize: 11, fontWeight: 700, cursor: 'pointer', border: 'none',
            borderRight: key === 'form' ? '1px solid #e5e7eb' : 'none',
            background: view === key ? '#f0fdf4' : '#fff',
            color: view === key ? '#0f4c2a' : '#9ca3af',
            fontFamily: 'inherit', textTransform: 'uppercase',
            letterSpacing: '.06em', transition: 'all .15s',
          }}>{label}</button>
        ))}
      </div>

      {view === 'form' && <AssessmentForm t={t} lang={lang} onComplete={handleFormComplete} />}
      {view === 'results' && completedForm && <Results form={completedForm} t={t} lang={lang} onNew={() => setView('form')} />}
      {view === 'dashboard' && <Dashboard t={t} onView={handleViewSaved} onNew={() => setView('form')} />}
    </div>
  )
}
