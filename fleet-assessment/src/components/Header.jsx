import React from 'react'

export default function Header({ lang, setLang, t }) {
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 5, marginBottom: 14 }}>
        {['en', 'pt', 'es'].map(l => (
          <button key={l} onClick={() => setLang(l)} style={{
            padding: '5px 13px',
            border: `1.5px solid ${lang === l ? '#1a6b4a' : '#e5e7eb'}`,
            borderRadius: 7, fontSize: 11, fontWeight: 700, cursor: 'pointer',
            background: lang === l ? '#1a6b4a' : '#fff',
            color: lang === l ? '#fff' : '#9ca3af',
            fontFamily: 'inherit', letterSpacing: '.06em',
            transition: 'all .15s',
            boxShadow: lang === l ? '0 2px 8px rgba(26,107,74,.25)' : 'none',
          }}>{l.toUpperCase()}</button>
        ))}
      </div>

      <div style={{
        background: 'linear-gradient(135deg, #0b1f14 0%, #0f2a1a 50%, #0b1f14 100%)',
        borderRadius: 16, padding: '22px 28px', marginBottom: 22,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        border: '1px solid rgba(34,197,94,.12)',
        boxShadow: '0 8px 32px rgba(0,0,0,.12)',
      }}>
        <div>
          <div style={{
            color: '#fff', fontSize: 18, fontWeight: 700,
            letterSpacing: '-.3px', marginBottom: 5,
          }}>{t.appTitle}</div>
          <div style={{
            color: 'rgba(255,255,255,.38)', fontSize: 10,
            textTransform: 'uppercase', letterSpacing: '.12em', fontWeight: 500,
          }}>{t.appSub}</div>
        </div>
        <div style={{
          width: 44, height: 44, flexShrink: 0,
          background: 'rgba(34,197,94,.12)',
          borderRadius: 12, border: '1px solid rgba(34,197,94,.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            stroke="rgba(34,197,94,.85)" strokeWidth="1.5"
            strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
          </svg>
        </div>
      </div>
    </>
  )
}
