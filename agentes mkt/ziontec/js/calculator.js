// ============================================
// ZIONTEC — Energy Savings Calculator
// ============================================

// State solar irradiance factors (relative to avg)
const stateSolarFactor = {
  MA: 0.92, CT: 0.94, RI: 0.95, NH: 0.88, VT: 0.85, ME: 0.83
};

// State incentives info
const stateIncentives = {
  MA: 'Massachusetts SMART Program + 15% state tax credit + net metering. Average additional value: $2,000–$5,000.',
  CT: 'Connecticut Residential Solar Investment Program (RSIP) + utility rebates. Net metering included.',
  RI: 'Rhode Island Renewable Energy Growth (REG) Program + net metering + 25% state tax credit.',
  NH: 'NH Electric Co-op rebates + net metering. No state income tax credit, but strong utility programs.',
  VT: 'Vermont Green Mountain Power incentives + net metering + standard offer program.',
  ME: 'Maine net metering + community solar options. Efficiency Maine Trust rebates available.'
};

// Public charging costs per kWh
const publicChargingCost = {
  public_fast: 0.55,
  public_l2: 0.42,
  home_120: 0.28
};

// Home Level 2 off-peak rate (New England average)
const homeChargingRate = 0.14;

// Installation costs (after 30% ITC)
const evInstallCost = 2000;
const solarInstallCostBase = 18000; // after federal 30% ITC

function formatCurrency(value) {
  return '$' + Math.round(value).toLocaleString('en-US');
}

function calculate() {
  // Get inputs
  const miles = parseInt(document.getElementById('miles').value);
  const efficiency = parseFloat(document.getElementById('efficiency').value);
  const chargingMethod = document.getElementById('chargingMethod').value;
  const electricBill = parseInt(document.getElementById('electricBill').value);
  const state = document.getElementById('state').value;
  const wantSolar = document.getElementById('wantSolar').value;

  // Update display values
  document.getElementById('milesVal').textContent = miles.toLocaleString();
  document.getElementById('effVal').textContent = efficiency.toFixed(1);
  document.getElementById('billVal').textContent = '$' + electricBill;

  // ─── EV SAVINGS CALCULATION ───────────────────────────────────────────────
  const monthlyKwh = miles / efficiency;
  const currentCostPerKwh = publicChargingCost[chargingMethod];
  const monthlyCostCurrent = monthlyKwh * currentCostPerKwh;
  const monthlyCostHome = monthlyKwh * homeChargingRate;
  const monthlyEvSavings = monthlyCostCurrent - monthlyCostHome;
  const annualEvSavings = monthlyEvSavings * 12;

  // ─── SOLAR SAVINGS CALCULATION ────────────────────────────────────────────
  let annualSolarSavings = 0;
  let solarInstallCost = 0;

  if (wantSolar === 'yes') {
    const solarFactor = stateSolarFactor[state] || 0.90;
    // Assume solar covers 80% of bill, adjusted by state factor
    const solarOffset = 0.80 * solarFactor;
    annualSolarSavings = electricBill * 12 * solarOffset;
    // Scale install cost by bill size (bigger bill = bigger system needed)
    solarInstallCost = solarInstallCostBase * (electricBill / 200);
    solarInstallCost = Math.max(12000, Math.min(solarInstallCost, 40000));
    document.getElementById('solarRow').style.display = 'block';
  } else {
    document.getElementById('solarRow').style.display = 'none';
  }

  // ─── TOTALS ───────────────────────────────────────────────────────────────
  const totalAnnualSavings = annualEvSavings + annualSolarSavings;
  const totalInstallCost = evInstallCost + solarInstallCost;
  const paybackYears = totalInstallCost / totalAnnualSavings;
  const tenYearSavings = (totalAnnualSavings * 10) - totalInstallCost;

  // ─── UPDATE UI ────────────────────────────────────────────────────────────
  document.getElementById('evSavings').textContent = formatCurrency(annualEvSavings) + '/yr';
  document.getElementById('solarSavings').textContent = wantSolar === 'yes' ? formatCurrency(annualSolarSavings) + '/yr' : 'N/A';
  document.getElementById('totalSavings').textContent = formatCurrency(totalAnnualSavings) + '/yr';

  if (paybackYears < 20 && paybackYears > 0) {
    document.getElementById('payback').textContent = paybackYears.toFixed(1) + ' yrs';
  } else {
    document.getElementById('payback').textContent = '—';
  }

  if (tenYearSavings > 0) {
    document.getElementById('tenYear').textContent = formatCurrency(tenYearSavings);
  } else {
    document.getElementById('tenYear').textContent = '—';
  }

  // State incentives
  document.getElementById('incentiveText').textContent = stateIncentives[state] || 'Contact us for available incentives in your state.';
}

// Initialize on load
document.addEventListener('DOMContentLoaded', calculate);
