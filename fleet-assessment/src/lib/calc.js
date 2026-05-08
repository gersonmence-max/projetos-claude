export function calcResults(form) {
  const totalVeh = form.vehicles?.reduce((a, v) => a + (v.count || 0), 0) || form.totalFleet || 10
  const milesDay = parseFloat(form.milesDay) || 80
  const opDays = parseFloat(form.opDays) || 250
  const evEff = parseFloat(form.evEfficiency) || 0.35
  const clientKwh = parseFloat(form.kwRate) || 0.12
  const yourKwh = parseFloat(form.yourKwhRate) || 0.22
  const monthlyFuel = parseFloat(form.monthlyFuel) || 8000
  const iceMaintM = parseFloat(form.iceMaint) || 3000
  const evMaintM = parseFloat(form.evMaint) || Math.round(iceMaintM * 0.2)
  const insurance = parseFloat(form.insurance) || 2400
  const installUs = parseFloat(form.installCostUs) || 18000
  const installClient = parseFloat(form.installPriceClient) || 28000
  const maintFeeClient = parseFloat(form.maintFeeClient) || 200
  const hwCost = parseFloat(form.hwCost) || 1200
  const hoursParked = parseFloat(form.hoursParked) || 10

  const annualMiles = totalVeh * milesDay * opDays
  const annualKwh = annualMiles * evEff
  const evEnergyCost = annualKwh * clientKwh
  const iceFuelAnnual = monthlyFuel * 12
  const iceMaintAnnual = iceMaintM * 12
  const evMaintAnnual = evMaintM * 12
  const annualIns = insurance * totalVeh
  const annualSavings = (iceFuelAnnual + iceMaintAnnual) - (evEnergyCost + evMaintAnnual)
  const chargersNeeded = Math.ceil(totalVeh * 1.15)
  const co2Saved = Math.round(annualMiles * 0.000404)
  const chargePowerKw = hoursParked > 0 ? Math.ceil((totalVeh * evEff * milesDay) / hoursParked * 1.1) : 22
  const chargerTypeKw = (chargePowerKw / totalVeh) > 7 ? 11 : 7.2
  const totalInstallClient = installClient + chargersNeeded * hwCost
  const paybackYears = annualSavings > 0 ? totalInstallClient / annualSavings : 99

  const installMargin = installClient - installUs
  const kwhMarginAnnual = annualKwh * (yourKwh - clientKwh)
  const maintAnnual = maintFeeClient * 12 * totalVeh
  const yr1Profit = installMargin + kwhMarginAnnual + maintAnnual
  const yr3Profit = installMargin + (kwhMarginAnnual + maintAnnual) * 3
  const yr5Profit = installMargin + (kwhMarginAnnual + maintAnnual) * 5

  const evAnnualTotal = evEnergyCost + evMaintAnnual + annualIns
  const iceAnnualTotal = iceFuelAnnual + iceMaintAnnual + annualIns
  const tcoEV = [1,2,3,4,5].map(y => Math.round(totalInstallClient + evAnnualTotal * y))
  const tcoICE = [1,2,3,4,5].map(y => Math.round(iceAnnualTotal * y))

  return {
    totalVeh, annualMiles, annualKwh, evEnergyCost, iceFuelAnnual,
    iceMaintAnnual, evMaintAnnual, annualIns, annualSavings,
    chargersNeeded, co2Saved, chargePowerKw, chargerTypeKw,
    totalInstallClient, paybackYears,
    installMargin, kwhMarginAnnual, maintAnnual,
    yr1Profit, yr3Profit, yr5Profit,
    evAnnualTotal, iceAnnualTotal, tcoEV, tcoICE,
    milesDay, hoursParked,
    hasLongTrips: (parseFloat(form.longTrips) || 0) > 3,
  }
}

export function fmtUSD(n) {
  return '$' + Math.round(n).toLocaleString('en-US')
}

export function fmtPayback(years, t) {
  if (years >= 99) return 'N/A'
  if (years < 1) return t?.paybackLess || '< 1 year'
  if (years < 1.5) return t?.paybackAbout || '~1 year'
  return years.toFixed(1) + ' ' + (t?.paybackUnit || 'yrs')
}
