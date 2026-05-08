import React, { useEffect, useState } from 'react'
import { listAssessments, deleteAssessment } from '../lib/supabase'
import { fmtUSD, fmtPayback } from '../lib/calc'

export default function Dashboard({ t, onView, onNew }) {
  const [assessments, setAssessments] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try { setAssessments(await listAssessments()) } catch (e) { console.error(e) }
    setLoading(false)
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!window.confirm(t.deleteConfirm)) return
    await deleteAssessment(id)
    setAssessments(a => a.filter(x => x.id !== id))
  }

  const filtered = assessments.filter(a =>
    [(a.company_name || ''), (a.industry || ''), (a.state || '')]
      .some(v => v.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', letterSpacing: '-.3px' }}>{t.savedAssessments}</div>
        <button onClick={onNew} style={{
          padding: '9px 18px', borderRadius: 8, fontSize: 12, fontWeight: 600,
          background: '#1a6b4a', color: '#fff', border: 'none', cursor: 'pointer',
          fontFamily: 'inherit', boxShadow: '0 2px 8px rgba(26,107,74,.25)',
        }}>+ {t.newAssessment}</button>
      </div>

      <input type="text" placeholder={t.searchPlaceholder} value={search}
        onChange={e => setSearch(e.target.value)}
        style={{
          width: '100%', padding: '10px 14px',
          border: '1.5px solid #e5e7eb', borderRadius: 9,
          fontSize: 13, marginBottom: 16, fontFamily: 'inherit',
          color: '#111827', background: '#fff', outline: 'none',
          transition: 'border .15s',
        }}
        onFocus={e => (e.target.style.borderColor = '#1a6b4a')}
        onBlur={e => (e.target.style.borderColor = '#e5e7eb')}
      />

      {loading && (
        <div style={{ textAlign: 'center', color: '#9ca3af', padding: 50, fontSize: 13 }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
          {t.saving}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div style={{
          textAlign: 'center', padding: 50,
          background: '#f9fafb', borderRadius: 14,
          border: '1px dashed #e5e7eb',
        }}>
          <div style={{ fontSize: 32, marginBottom: 10 }}>📋</div>
          <div style={{ fontSize: 14, color: '#6b7280', fontWeight: 500 }}>{t.noSaved}</div>
        </div>
      )}

      {filtered.map(a => {
        const res = a.results || {}
        return (
          <div key={a.id} onClick={() => onView(a.id)} style={{
            background: '#fff', border: '1.5px solid #eaecef',
            borderRadius: 13, padding: '16px 20px', marginBottom: 10,
            cursor: 'pointer', transition: 'all .15s',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16,
            boxShadow: '0 1px 3px rgba(0,0,0,.05)',
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#1a6b4a'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(26,107,74,.1)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#eaecef'; e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,.05)' }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a', marginBottom: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {a.company_name || '—'}
              </div>
              <div style={{ fontSize: 11, color: '#9ca3af' }}>{a.industry}{a.state ? ` · ${a.state}` : ''}</div>
            </div>
            <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexShrink: 0 }}>
              {res.annualSavings != null && (
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#0f4c2a' }}>{fmtUSD(res.annualSavings)}/yr</div>
                  <div style={{ fontSize: 10, color: '#9ca3af', marginTop: 2 }}>{fmtPayback(res.paybackYears)} payback</div>
                </div>
              )}
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 11, color: '#b0b8c4' }}>{new Date(a.created_at).toLocaleDateString()}</div>
                <div style={{ fontSize: 10, color: '#c4cdd6', marginTop: 2 }}>{a.total_fleet} vehicles</div>
              </div>
              <button onClick={e => handleDelete(a.id, e)} style={{
                width: 30, height: 30, border: '1px solid #fecaca', borderRadius: 7,
                background: '#fff', color: '#dc2626', cursor: 'pointer', fontSize: 14,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all .15s', flexShrink: 0,
              }}
                onMouseEnter={e => { e.currentTarget.style.background = '#fee2e2' }}
                onMouseLeave={e => { e.currentTarget.style.background = '#fff' }}
              >×</button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
