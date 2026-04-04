export function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return n.toString()
}

export function formatDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function parseDuration(iso: string | null): string {
  if (!iso) return '-'
  const m = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/)
  if (!m) return iso
  const h = parseInt(m[1] || '0')
  const min = parseInt(m[2] || '0')
  const s = parseInt(m[3] || '0')
  if (h > 0) return h + ':' + String(min).padStart(2, '0') + ':' + String(s).padStart(2, '0')
  return min + ':' + String(s).padStart(2, '0')
}
