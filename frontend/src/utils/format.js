export function formatBalance(val) {
  if (val == null || val === '') return '0'
  const str = String(val)
  if (/\.0+$/.test(str)) {
    return str.replace(/\.0+$/, '')
  }
  return str
}
