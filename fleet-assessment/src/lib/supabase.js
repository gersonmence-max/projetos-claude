import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseKey)

// ─── Assessments CRUD ────────────────────────────────────────────────────────

export async function saveAssessment(data) {
  const { data: result, error } = await supabase
    .from('assessments')
    .insert([{
      company_name: data.companyName,
      industry: data.industry,
      state: data.state,
      total_fleet: data.totalFleet,
      vehicles: data.vehicles,
      has_ev: data.hasEV,
      miles_day: data.milesDay,
      op_days: data.opDays,
      hours_parked: data.hoursParked,
      monthly_fuel: data.monthlyFuel,
      kw_rate: data.kwRate,
      ice_maint: data.iceMaint,
      insurance: data.insurance,
      ev_efficiency: data.evEfficiency,
      ev_maint: data.evMaint,
      ev_vehicle_cost: data.evVehicleCost,
      ev_next_12: data.evNext12,
      ev_next_36: data.evNext36,
      install_cost_us: data.installCostUs,
      install_price_client: data.installPriceClient,
      maint_fee_client: data.maintFeeClient,
      hw_cost: data.hwCost,
      your_kwh_rate: data.yourKwhRate,
      results: data.results,
      created_at: new Date().toISOString(),
    }])
    .select()
  if (error) throw error
  return result[0]
}

export async function listAssessments() {
  const { data, error } = await supabase
    .from('assessments')
    .select('id, company_name, industry, state, total_fleet, created_at, results')
    .order('created_at', { ascending: false })
  if (error) throw error
  return data
}

export async function getAssessment(id) {
  const { data, error } = await supabase
    .from('assessments')
    .select('*')
    .eq('id', id)
    .single()
  if (error) throw error
  return data
}

export async function deleteAssessment(id) {
  const { error } = await supabase.from('assessments').delete().eq('id', id)
  if (error) throw error
}
