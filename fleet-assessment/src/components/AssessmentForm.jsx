import React, { useState } from 'react'
import { Card, Field, Input, Select, RadioGroup, Grid, BtnPrimary, BtnSecondary, BtnRow, SectionTitle, ProgressBar } from './UI'

const VEHICLE_TYPES = ['Cargo Van','Pickup Truck','Box Truck','Semi Truck','Passenger Car','Shuttle Bus','SUV']

export default function AssessmentForm({ t, onComplete }) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    hasEV: null,
    companyName: '', industry: '', state: '', totalFleet: '',
    vehicles: [],
    milesDay: '', tripsDay: '', shifts: '1', opDays: '250', routeType: 'mixed',
    returnBase: '', hoursParked: '10', takesHome: '',
    maxMiles: '', longTrips: '0',
    voltage: '480', contractedKw: '', panelCap: 'unknown', energyBill: '',
    parkingType: 'lot', parkingSpots: '', existingInfra: 'none', hasSolar: 'no',
    fuelType: 'gasoline', fuelCost: '3.80', mpg: '18', monthlyFuel: '', kwRate: '0.16',
    iceMaint: '', vehAge: '', insurance: '2400',
    evEfficiency: '0.35', evMaint: '', evVehicleCost: '',
    evNext12: '', evNext36: '', esg: '', driverReports: '', costCenter: '', telematics: '',
    locations: '1', decisionMaker: '',
    yourKwhRate: 0.35, installCostUs: '', installPriceClient: '', maintFeeClient: '', hwCost: '1200',
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const gn = k => parseFloat(form[k]) || 0

  const addVehicle = () => set('vehicles', [...form.vehicles, { type: 'Cargo Van', count: 1, dailyMiles: 80, batteryKwh: 100 }])
  const removeVehicle = i => set('vehicles', form.vehicles.filter((_, idx) => idx !== i))
  const updateVehicle = (i, k, v) => {
    const arr = [...form.vehicles]
    arr[i] = { ...arr[i], [k]: v }
    set('vehicles', arr)
  }

  const liveMargins = () => {
    const iu = gn('installCostUs') || 18000
    const ic = gn('installPriceClient') || 28000
    const yk = form.yourKwhRate || 0.35
    const ck = gn('kwRate') || 0.16
    const tv = form.vehicles.reduce((a, v) => a + (v.count || 0), 0) || gn('totalFleet') || 10
    const md = gn('milesDay') || 80
    const od = gn('opDays') || 250
    const ee = gn('evEfficiency') || 0.35
    const akwh = tv * md * od * ee
    const km = (yk - ck) * akwh
    const mf = gn('maintFeeClient') || 200
    return { installM: ic - iu, kwhM: km, yr1: (ic - iu) + km + (mf * 12 * tv) }
  }

  const fmt = n => '$' + Math.round(n).toLocaleString('en-US')
  const next = () => { setStep(s => s + 1); window.scrollTo(0, 0) }
  const back = () => { setStep(s => s - 1); window.scrollTo(0, 0) }

  const choiceStyle = (selected) => ({
    background: selected ? '#f0fdf4' : '#fff',
    border: `1.5px solid ${selected ? '#1a6b4a' : '#e5e7eb'}`,
    borderRadius: 12, padding: '18px 20px', cursor: 'pointer', marginBottom: 10,
    display: 'flex', alignItems: 'center', gap: 16,
    transition: 'all .2s',
    boxShadow: selected ? '0 2px 12px rgba(26,107,74,.12)' : '0 1px 3px rgba(0,0,0,.04)',
  })

  if (step === 0) return (
    <div>
      <ProgressBar step={1} total={8} label={t.gettingStarted} t={t} />
      <Card style={{ padding: '28px 26px' }}>
        <div style={{ fontSize: 21, fontWeight: 700, color: '#0f172a', lineHeight: 1.35, marginBottom: 6, letterSpacing: '-.4px' }}>{t.q0Title}</div>
        <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 24, lineHeight: 1.6 }}>{t.q0Sub}</div>
        {[
          { val: true, title: t.hasEVYes, sub: t.hasEVYesSub, icon: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z' },
          { val: false, title: t.hasEVNo, sub: t.hasEVNoSub, icon: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01' },
        ].map(opt => (
          <div key={String(opt.val)} onClick={() => { set('hasEV', opt.val); setTimeout(next, 220) }} style={choiceStyle(form.hasEV === opt.val)}>
            <div style={{
              width: 38, height: 38, borderRadius: '50%', flexShrink: 0,
              border: `1.5px solid ${form.hasEV === opt.val ? '#1a6b4a' : '#e5e7eb'}`,
              background: form.hasEV === opt.val ? '#dcfce7' : '#f9fafb',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all .2s',
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke={form.hasEV === opt.val ? '#1a6b4a' : '#9ca3af'}
                strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d={opt.icon}/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a', marginBottom: 3 }}>{opt.title}</div>
              <div style={{ fontSize: 12, color: '#9ca3af', lineHeight: 1.5 }}>{opt.sub}</div>
            </div>
          </div>
        ))}
      </Card>
    </div>
  )

  if (step === 1) return (
    <div>
      <ProgressBar step={2} total={8} label={t.companyProfile} t={t} />
      <SectionTitle title={t.companyProfile} />
      <Card head={t.companyInfo}>
        <Grid cols={2}>
          <Field label={t.companyName}><Input value={form.companyName} onChange={e => set('companyName', e.target.value)} placeholder="Acme Logistics Inc." /></Field>
          <Field label={t.industry}>
            <Select value={form.industry} onChange={e => set('industry', e.target.value)}>
              <option value="">{t.selectOpt}</option>
              {t.industryOpts.map(o => <option key={o}>{o}</option>)}
            </Select>
          </Field>
        </Grid>
        <Grid cols={2}>
          <Field label={t.stateLocation}><Input value={form.state} onChange={e => set('state', e.target.value)} placeholder="Massachusetts" /></Field>
          <Field label={t.totalFleet}><Input type="number" value={form.totalFleet} onChange={e => set('totalFleet', e.target.value)} placeholder="40" /></Field>
        </Grid>
      </Card>
      <Card head={t.fleetComp}>
        {form.vehicles.length === 0
          ? <div style={{ color: '#b0b8c4', fontSize: 12, paddingBottom: 8 }}>{t.noVehicles}</div>
          : <>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 30px', gap: 8, marginBottom: 8 }}>
              {[t.vType, t.vCount, t.vMiles, t.vBattery, ''].map((h, i) => (
                <div key={i} style={{ fontSize: 9, fontWeight: 700, color: '#a0a9b4', textTransform: 'uppercase', letterSpacing: '.07em' }}>{h}</div>
              ))}
            </div>
            {form.vehicles.map((v, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 30px', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                <Select value={v.type} onChange={e => updateVehicle(i, 'type', e.target.value)} style={{ fontSize: 12 }}>
                  {VEHICLE_TYPES.map(t2 => <option key={t2}>{t2}</option>)}
                </Select>
                <Input type="number" value={v.count} style={{ fontSize: 12 }} onChange={e => updateVehicle(i, 'count', parseInt(e.target.value) || 1)} />
                <Input type="number" value={v.dailyMiles} style={{ fontSize: 12 }} onChange={e => updateVehicle(i, 'dailyMiles', parseFloat(e.target.value) || 80)} />
                <Input type="number" value={v.batteryKwh} style={{ fontSize: 12 }} onChange={e => updateVehicle(i, 'batteryKwh', parseFloat(e.target.value) || 100)} />
                <button onClick={() => removeVehicle(i)} style={{
                  width: 28, height: 28, border: '1px solid #fecaca', borderRadius: 6,
                  background: '#fff', color: '#dc2626', cursor: 'pointer', fontSize: 15,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>×</button>
              </div>
            ))}
          </>
        }
        <button onClick={addVehicle} style={{
          width: '100%', padding: 10, marginTop: 6,
          background: '#fff', border: '1.5px dashed #d1d5db',
          borderRadius: 9, fontSize: 12, fontWeight: 600, color: '#9ca3af',
          cursor: 'pointer', transition: 'all .15s',
        }}
          onMouseEnter={e => { e.target.style.borderColor = '#1a6b4a'; e.target.style.color = '#1a6b4a' }}
          onMouseLeave={e => { e.target.style.borderColor = '#d1d5db'; e.target.style.color = '#9ca3af' }}
        >{t.addVehicle}</button>
      </Card>
      <BtnRow><BtnSecondary onClick={back}>{t.back}</BtnSecondary><BtnPrimary onClick={next}>{t.continue}</BtnPrimary></BtnRow>
    </div>
  )

  if (step === 2) return (
    <div>
      <ProgressBar step={3} total={8} label={t.dailyOps} t={t} />
      <SectionTitle title={t.dailyOps} />
      <Card head={t.mileageShifts}>
        <Grid cols={3}>
          <Field label={t.avgMilesDay}><Input type="number" value={form.milesDay} onChange={e => set('milesDay', e.target.value)} placeholder="80" /></Field>
          <Field label={t.tripsDay}><Input type="number" value={form.tripsDay} onChange={e => set('tripsDay', e.target.value)} placeholder="3" /></Field>
          <Field label={t.shiftsDay}>
            <Select value={form.shifts} onChange={e => set('shifts', e.target.value)}>
              <option value="1">{t.shift1}</option>
              <option value="2">{t.shift2}</option>
              <option value="3">{t.shift3}</option>
            </Select>
          </Field>
        </Grid>
        <Grid cols={2}>
          <Field label={t.opDaysYear}><Input type="number" value={form.opDays} onChange={e => set('opDays', e.target.value)} placeholder="250" /></Field>
          <Field label={t.routeType}>
            <Select value={form.routeType} onChange={e => set('routeType', e.target.value)}>
              <option value="city">{t.routeCity}</option>
              <option value="mixed">{t.routeMixed}</option>
              <option value="highway">{t.routeHwy}</option>
              <option value="offroad">{t.routeOffroad}</option>
            </Select>
          </Field>
        </Grid>
      </Card>
      <Card head={t.baseReturn}>
        <Field label={t.returnBase}>
          <RadioGroup value={form.returnBase} onChange={v => set('returnBase', v)} options={[
            { value: 'always', label: t.always }, { value: 'mostly', label: t.mostly },
            { value: 'sometimes', label: t.sometimes }, { value: 'rarely', label: t.rarely },
          ]} />
        </Field>
        <Grid cols={2} style={{ marginTop: 14 }}>
          <Field label={t.hoursParked} hint={t.hoursParkedHint}><Input type="number" value={form.hoursParked} onChange={e => set('hoursParked', e.target.value)} placeholder="10" /></Field>
          <Field label={t.takesHome}>
            <RadioGroup value={form.takesHome} onChange={v => set('takesHome', v)} options={[
              { value: 'no', label: t.no }, { value: 'some', label: t.someDo }, { value: 'all', label: t.mostDo },
            ]} />
          </Field>
        </Grid>
      </Card>
      <Card head={t.longDist}>
        <Grid cols={2}>
          <Field label={t.maxMiles}><Input type="number" value={form.maxMiles} onChange={e => set('maxMiles', e.target.value)} placeholder="150" /></Field>
          <Field label={t.longTripsMonth} hint={t.longTripsHint}><Input type="number" value={form.longTrips} onChange={e => set('longTrips', e.target.value)} placeholder="0" /></Field>
        </Grid>
      </Card>
      <BtnRow><BtnSecondary onClick={back}>{t.back}</BtnSecondary><BtnPrimary onClick={next}>{t.continue}</BtnPrimary></BtnRow>
    </div>
  )

  if (step === 3) return (
    <div>
      <ProgressBar step={4} total={8} label={t.electrical} t={t} />
      <SectionTitle title={t.electrical} />
      <Card head={t.powerSupply}>
        <Grid cols={2}>
          <Field label={t.serviceVoltage}>
            <Select value={form.voltage} onChange={e => set('voltage', e.target.value)}>
              <option value="240">240V single-phase</option>
              <option value="208">208V three-phase</option>
              <option value="480">480V three-phase</option>
              <option value="unknown">{t.voltUnk}</option>
            </Select>
          </Field>
          <Field label={t.contractedKw} hint={t.contractedHint}><Input type="number" value={form.contractedKw} onChange={e => set('contractedKw', e.target.value)} placeholder="200" /></Field>
        </Grid>
        <Grid cols={2}>
          <Field label={t.panelCap}>
            <Select value={form.panelCap} onChange={e => set('panelCap', e.target.value)}>
              <option value="ample">{t.panelAmple}</option>
              <option value="moderate">{t.panelMod}</option>
              <option value="tight">{t.panelTight}</option>
              <option value="unknown">{t.panelUnk}</option>
            </Select>
          </Field>
          <Field label={t.energyBill}><Input type="number" value={form.energyBill} onChange={e => set('energyBill', e.target.value)} placeholder="2500" /></Field>
        </Grid>
      </Card>
      <Card head={t.siteCond}>
        <Grid cols={2}>
          <Field label={t.parkingType}>
            <Select value={form.parkingType} onChange={e => set('parkingType', e.target.value)}>
              <option value="lot">{t.parkLot}</option>
              <option value="covered">{t.parkCovered}</option>
              <option value="garage">{t.parkGarage}</option>
              <option value="street">{t.parkStreet}</option>
            </Select>
          </Field>
          <Field label={t.parkingSpots}><Input type="number" value={form.parkingSpots} onChange={e => set('parkingSpots', e.target.value)} placeholder="30" /></Field>
        </Grid>
        <Field label={t.existingInfra}>
          <RadioGroup value={form.existingInfra} onChange={v => set('existingInfra', v)} options={[
            { value: 'none', label: t.infraNone }, { value: 'partial', label: t.infraSome }, { value: 'yes', label: t.infraYes },
          ]} />
        </Field>
        <Field label={t.hasSolar} style={{ marginTop: 14 }}>
          <RadioGroup value={form.hasSolar} onChange={v => set('hasSolar', v)} options={[
            { value: 'no', label: t.solNo }, { value: 'planned', label: t.solPlan }, { value: 'yes', label: t.solYes },
          ]} />
        </Field>
      </Card>
      <BtnRow><BtnSecondary onClick={back}>{t.back}</BtnSecondary><BtnPrimary onClick={next}>{t.continue}</BtnPrimary></BtnRow>
    </div>
  )

  if (step === 4) return (
    <div>
      <ProgressBar step={5} total={8} label={t.currentCosts} t={t} />
      <SectionTitle title={t.currentCosts} />
      <Card head={t.fuelCosts}>
        <Grid cols={3}>
          <Field label={t.fuelType}>
            <Select value={form.fuelType} onChange={e => set('fuelType', e.target.value)}>
              <option value="gasoline">{t.gasoline}</option>
              <option value="diesel">{t.diesel}</option>
              <option value="cng">{t.cng}</option>
              <option value="mixed">{t.mixed}</option>
            </Select>
          </Field>
          <Field label={t.fuelCostGal}><Input type="number" value={form.fuelCost} onChange={e => set('fuelCost', e.target.value)} placeholder="3.80" step="0.01" /></Field>
          <Field label={t.avgMpg}><Input type="number" value={form.mpg} onChange={e => set('mpg', e.target.value)} placeholder="18" /></Field>
        </Grid>
        <Grid cols={2}>
          <Field label={t.monthlyFuel} hint={t.monthlyFuelHint}><Input type="number" value={form.monthlyFuel} onChange={e => set('monthlyFuel', e.target.value)} placeholder="8000" /></Field>
          <Field label={t.elecRate} hint={t.elecRateHint}><Input type="number" value={form.kwRate} onChange={e => set('kwRate', e.target.value)} placeholder="0.16" step="0.001" /></Field>
        </Grid>
      </Card>
      <Card head={t.maintICE}>
        <Grid cols={3}>
          <Field label={t.monthlyMaint} hint={t.maintHint}><Input type="number" value={form.iceMaint} onChange={e => set('iceMaint', e.target.value)} placeholder="3000" /></Field>
          <Field label={t.avgVehAge}><Input type="number" value={form.vehAge} onChange={e => set('vehAge', e.target.value)} placeholder="5" /></Field>
          <Field label={t.annualIns}><Input type="number" value={form.insurance} onChange={e => set('insurance', e.target.value)} placeholder="2400" /></Field>
        </Grid>
      </Card>
      <Card head={t.evBench}>
        <Grid cols={3}>
          <Field label={t.evEnergyUse} hint={t.evEnergyHint}><Input type="number" value={form.evEfficiency} onChange={e => set('evEfficiency', e.target.value)} placeholder="0.35" step="0.01" /></Field>
          <Field label={t.evMonthlyMaint} hint={t.evMaintHint}><Input type="number" value={form.evMaint} onChange={e => set('evMaint', e.target.value)} placeholder="600" /></Field>
          <Field label={t.avgEvCost}><Input type="number" value={form.evVehicleCost} onChange={e => set('evVehicleCost', e.target.value)} placeholder="65000" /></Field>
        </Grid>
      </Card>
      <BtnRow><BtnSecondary onClick={back}>{t.back}</BtnSecondary><BtnPrimary onClick={next}>{t.continue}</BtnPrimary></BtnRow>
    </div>
  )

  if (step === 5) return (
    <div>
      <ProgressBar step={6} total={8} label={t.businessCtx} t={t} />
      <SectionTitle title={t.businessCtx} />
      <Card head={t.evAdoption}>
        <Grid cols={2}>
          <Field label={t.evNext12}><Input type="number" value={form.evNext12} onChange={e => set('evNext12', e.target.value)} placeholder="10" /></Field>
          <Field label={t.evNext36}><Input type="number" value={form.evNext36} onChange={e => set('evNext36', e.target.value)} placeholder="20" /></Field>
        </Grid>
        <Field label={t.esgMandate}>
          <RadioGroup value={form.esg} onChange={v => set('esg', v)} options={[
            { value: 'no', label: t.esgNo }, { value: 'soft', label: t.esgSoft }, { value: 'hard', label: t.esgHard },
          ]} />
        </Field>
      </Card>
      <Card head={t.chargingMgmt}>
        <Field label={t.driverReports}>
          <RadioGroup value={form.driverReports} onChange={v => set('driverReports', v)} options={[{ value: 'no', label: t.no }, { value: 'yes', label: t.yes }]} />
        </Field>
        <Field label={t.costCenterBilling} style={{ marginTop: 14 }}>
          <RadioGroup value={form.costCenter} onChange={v => set('costCenter', v)} options={[{ value: 'no', label: t.no }, { value: 'yes', label: t.yes }]} />
        </Field>
        <Field label={t.telematicsUsed} style={{ marginTop: 14 }}>
          <RadioGroup value={form.telematics} onChange={v => set('telematics', v)} options={[{ value: 'no', label: t.no }, { value: 'yes', label: t.telematicsYes }]} />
        </Field>
      </Card>
      <Card head={t.multiSite}>
        <Grid cols={2}>
          <Field label={t.numLocations}><Input type="number" value={form.locations} onChange={e => set('locations', e.target.value)} placeholder="1" /></Field>
          <Field label={t.decisionMaker}>
            <Select value={form.decisionMaker} onChange={e => set('decisionMaker', e.target.value)}>
              <option value="">{t.selectOpt}</option>
              {[t.dmFleet, t.dmOps, t.dmCFO, t.dmFacilities, t.dmOwner].map(o => <option key={o}>{o}</option>)}
            </Select>
          </Field>
        </Grid>
      </Card>
      <BtnRow><BtnSecondary onClick={back}>{t.back}</BtnSecondary><BtnPrimary onClick={next}>{t.continue}</BtnPrimary></BtnRow>
    </div>
  )

  if (step === 6) {
    const mg = liveMargins()
    return (
      <div>
        <ProgressBar step={7} total={8} label={t.yourPricing} t={t} />
        <div style={{
          background: 'linear-gradient(160deg, #0b1f14 0%, #0f2a1a 100%)',
          borderRadius: 16, padding: 24, marginBottom: 14,
          border: '1px solid rgba(34,197,94,.12)',
          boxShadow: '0 8px 32px rgba(0,0,0,.15)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <div style={{
              background: '#162019', border: '1px solid #1e3024',
              borderRadius: 5, padding: '3px 10px',
              fontSize: 9, fontWeight: 700, color: '#4b6b58', letterSpacing: '.08em',
            }}>🔒 {t.internalOnly}</div>
          </div>
          <div style={{ fontSize: 12, color: '#3d5e4a', marginBottom: 22, lineHeight: 1.65 }}>{t.privateDesc}</div>

          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#7a9e8a', textTransform: 'uppercase', letterSpacing: '.07em' }}>{t.kwhRateClient}</span>
              <span style={{ fontSize: 16, fontWeight: 700, color: '#22c55e' }}>${form.yourKwhRate.toFixed(2)}/kWh</span>
            </div>
            <input type="range" min="0.10" max="0.80" step="0.01" value={form.yourKwhRate}
              onChange={e => set('yourKwhRate', parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#22c55e', cursor: 'pointer' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#3d5e4a', marginTop: 6 }}>
              <span>$0.10</span>
              <span style={{ color: '#5a8a6a' }}>{t.clientRate}: ${(gn('kwRate') || 0.16).toFixed(2)} &nbsp;·&nbsp; {t.yourMargin}: ${(form.yourKwhRate - (gn('kwRate') || 0.16)).toFixed(2)}/kWh</span>
              <span>$0.80</span>
            </div>
          </div>

          <Grid cols={2} gap={10}>
            <Field label={<span style={{ color: '#7a9e8a', fontSize: 10, textTransform: 'uppercase', letterSpacing: '.07em' }}>{t.installCostYou}</span>}>
              <Input type="number" value={form.installCostUs} onChange={e => set('installCostUs', e.target.value)} placeholder="18000"
                style={{ background: '#162019', color: '#e2ead6', borderColor: '#1e3024', borderWidth: 1 }} />
            </Field>
            <Field label={<span style={{ color: '#7a9e8a', fontSize: 10, textTransform: 'uppercase', letterSpacing: '.07em' }}>{t.installPriceClient}</span>}>
              <Input type="number" value={form.installPriceClient} onChange={e => set('installPriceClient', e.target.value)} placeholder="28000"
                style={{ background: '#162019', color: '#e2ead6', borderColor: '#1e3024', borderWidth: 1 }} />
            </Field>
            <Field label={<span style={{ color: '#7a9e8a', fontSize: 10, textTransform: 'uppercase', letterSpacing: '.07em' }}>{t.maintFeeClient}</span>}>
              <Input type="number" value={form.maintFeeClient} onChange={e => set('maintFeeClient', e.target.value)} placeholder="200"
                style={{ background: '#162019', color: '#e2ead6', borderColor: '#1e3024', borderWidth: 1 }} />
            </Field>
            <Field label={<span style={{ color: '#7a9e8a', fontSize: 10, textTransform: 'uppercase', letterSpacing: '.07em' }}>{t.hwCostCharger}</span>}>
              <Input type="number" value={form.hwCost} onChange={e => set('hwCost', e.target.value)} placeholder="1200"
                style={{ background: '#162019', color: '#e2ead6', borderColor: '#1e3024', borderWidth: 1 }} />
            </Field>
          </Grid>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginTop: 6 }}>
            {[
              { v: fmt(mg.installM), l: t.installMargin },
              { v: fmt(mg.kwhM), l: t.kwhAnnualProfit },
              { v: fmt(mg.yr1), l: t.yr1TotalProfit },
            ].map(m => (
              <div key={m.l} style={{
                background: '#162019', border: '1px solid #1e3024',
                borderRadius: 10, padding: '14px 10px', textAlign: 'center',
              }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#fff', letterSpacing: '-.4px' }}>{m.v}</div>
                <div style={{ fontSize: 9, color: '#3d5e4a', marginTop: 4, textTransform: 'uppercase', letterSpacing: '.07em' }}>{m.l}</div>
              </div>
            ))}
          </div>
        </div>
        <BtnRow>
          <BtnSecondary onClick={back}>{t.back}</BtnSecondary>
          <BtnPrimary onClick={() => onComplete(form)}>{t.calculate}</BtnPrimary>
        </BtnRow>
      </div>
    )
  }

  return null
}
