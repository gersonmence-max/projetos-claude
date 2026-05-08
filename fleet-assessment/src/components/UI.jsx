import React from 'react'

const G = '#1a6b4a'
const GD = '#0f4c2a'

export function Card({ head, children, style }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #eaecef',
      borderRadius: 14, padding: '20px 22px', marginBottom: 14,
      boxShadow: '0 1px 3px rgba(0,0,0,.05), 0 1px 2px rgba(0,0,0,.03)',
      ...style,
    }}>
      {head && (
        <div style={{
          fontSize: 10, fontWeight: 700, color: '#a0a9b4',
          textTransform: 'uppercase', letterSpacing: '.1em', marginBottom: 16,
          paddingBottom: 10, borderBottom: '1px solid #f3f4f6',
        }}>{head}</div>
      )}
      {children}
    </div>
  )
}

export function Field({ label, hint, children, style }) {
  return (
    <div style={{ marginBottom: 14, ...style }}>
      {label && (
        <label style={{
          fontSize: 11, fontWeight: 600, color: '#4b5563',
          display: 'block', marginBottom: 6,
          textTransform: 'uppercase', letterSpacing: '.04em',
        }}>{label}</label>
      )}
      {children}
      {hint && <div style={{ fontSize: 11, color: '#b0b8c4', marginTop: 4, lineHeight: 1.4 }}>{hint}</div>}
    </div>
  )
}

export function Input({ style, ...props }) {
  const [focused, setFocused] = React.useState(false)
  return (
    <input
      style={{
        width: '100%', padding: '9px 12px',
        border: `1.5px solid ${focused ? G : '#e5e7eb'}`,
        borderRadius: 8, fontSize: 13, color: '#111827',
        background: focused ? '#fafffe' : '#fff',
        outline: 'none', fontFamily: 'inherit',
        transition: 'all .15s',
        boxShadow: focused ? `0 0 0 3px rgba(26,107,74,.08)` : 'none',
        ...style,
      }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      {...props}
    />
  )
}

export function Select({ children, style, ...props }) {
  return (
    <select style={{
      width: '100%', padding: '9px 12px',
      border: '1.5px solid #e5e7eb', borderRadius: 8,
      fontSize: 13, color: '#111827', background: '#fff',
      outline: 'none', fontFamily: 'inherit', cursor: 'pointer',
      transition: 'border .15s',
      ...style,
    }}
      onFocus={e => (e.target.style.borderColor = G)}
      onBlur={e => (e.target.style.borderColor = '#e5e7eb')}
      {...props}
    >
      {children}
    </select>
  )
}

export function RadioGroup({ options, value, onChange }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
      {options.map(opt => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          style={{
            border: `1.5px solid ${value === opt.value ? G : '#e5e7eb'}`,
            borderRadius: 8, padding: '7px 14px', fontSize: 12, fontWeight: 500,
            background: value === opt.value ? '#f0fdf4' : '#fff',
            color: value === opt.value ? GD : '#4b5563',
            cursor: 'pointer', fontFamily: 'inherit', transition: 'all .15s',
            boxShadow: value === opt.value ? '0 1px 3px rgba(26,107,74,.15)' : 'none',
          }}
        >{opt.label}</button>
      ))}
    </div>
  )
}

export function Grid({ cols = 2, gap = 12, children }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap }}>
      {children}
    </div>
  )
}

export function BtnPrimary({ children, onClick, style, disabled }) {
  const [hov, setHov] = React.useState(false)
  return (
    <button onClick={onClick} disabled={disabled}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        padding: '10px 24px', borderRadius: 9, fontSize: 13, fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer', border: 'none',
        background: disabled ? '#9ca3af' : hov ? GD : G,
        color: '#fff', fontFamily: 'inherit', letterSpacing: '.02em',
        transition: 'all .15s',
        transform: hov && !disabled ? 'translateY(-1px)' : 'none',
        boxShadow: hov && !disabled ? '0 4px 14px rgba(26,107,74,.35)' : 'none',
        ...style,
      }}>{children}</button>
  )
}

export function BtnSecondary({ children, onClick, style }) {
  const [hov, setHov] = React.useState(false)
  return (
    <button onClick={onClick}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        padding: '10px 22px', borderRadius: 9, fontSize: 13, fontWeight: 500,
        cursor: 'pointer', border: '1.5px solid #e5e7eb',
        background: hov ? '#f9fafb' : '#fff', color: '#6b7280',
        fontFamily: 'inherit', transition: 'all .15s', ...style,
      }}>{children}</button>
  )
}

export function BtnRow({ children }) {
  return (
    <div style={{ display: 'flex', gap: 10, justifyContent: 'space-between', marginTop: 26, alignItems: 'center' }}>
      {children}
    </div>
  )
}

export function SectionTitle({ title, sub }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 19, fontWeight: 700, color: '#0f172a', letterSpacing: '-.4px', marginBottom: 4 }}>{title}</div>
      {sub && <div style={{ fontSize: 13, color: '#6b7280', lineHeight: 1.6 }}>{sub}</div>}
    </div>
  )
}

export function ProgressBar({ step, total, label, t }) {
  const pct = Math.round((step / total) * 100)
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 8 }}>
        <span style={{ fontWeight: 600, color: '#374151', textTransform: 'uppercase', letterSpacing: '.05em' }}>{label}</span>
        <span style={{ color: '#9ca3af' }}>{t.step} {step} {t.of} {total}</span>
      </div>
      <div style={{ height: 4, background: '#f3f4f6', borderRadius: 100, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          background: `linear-gradient(90deg, ${G} 0%, #22c55e 100%)`,
          borderRadius: 100, width: `${pct}%`,
          transition: 'width .5s cubic-bezier(.4,0,.2,1)',
        }} />
      </div>
    </div>
  )
}

export function Metric({ value, label, sub, accent }) {
  return (
    <div style={{
      background: accent ? 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)' : '#f9fafb',
      border: `1px solid ${accent ? '#bbf7d0' : '#f3f4f6'}`,
      borderRadius: 12, padding: '16px 12px', textAlign: 'center',
      boxShadow: accent ? '0 2px 8px rgba(26,107,74,.08)' : 'none',
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: GD, letterSpacing: '-.5px' }}>{value}</div>
      <div style={{ fontSize: 10, color: '#6b7280', marginTop: 4, textTransform: 'uppercase', letterSpacing: '.07em', fontWeight: 600 }}>{label}</div>
      {sub && <div style={{ fontSize: 10, color: '#b0b8c4', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

export function DarkBox({ children, style }) {
  return (
    <div style={{
      background: 'linear-gradient(160deg, #0b1f14 0%, #0f2a1a 100%)',
      borderRadius: 16, padding: 22, marginBottom: 14,
      border: '1px solid rgba(34,197,94,.1)',
      ...style,
    }}>{children}</div>
  )
}
