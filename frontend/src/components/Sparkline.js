import React from 'react'

/**
 * Mini grafico SVG inline (senza dipendenze) per l'andamento dei prezzi.
 * values: lista di prezzi in ordine cronologico.
 */
export default function Sparkline({ values = [], width = 120, height = 36, stroke = '#7e3af2' }) {
  if (!values || values.length < 2) return null

  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const step = width / (values.length - 1)
  const points = values
    .map((v, i) => {
      const x = (i * step).toFixed(1)
      const y = (height - 4 - ((v - min) / range) * (height - 8)).toFixed(1)
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="inline-block"
      role="img"
      aria-label={`Andamento prezzo: minimo ${min.toFixed(2)} euro, massimo ${max.toFixed(2)} euro`}
    >
      <polyline
        points={points}
        fill="none"
        stroke={stroke}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}
