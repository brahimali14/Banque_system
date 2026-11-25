// fonctionnel
export const ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
const POIDS = [1, 3, 5, 7, 9, 11, 13]
const PREFIXES = ['DEP', 'RET', 'TRX']

export function cleControle(corps) {
  const total = [...corps].reduce((acc, car, i) => acc + POIDS[i] * ALPHABET.indexOf(car), 0)
  return ALPHABET[total % ALPHABET.length]
}

export function normaliser(saisie) {
  const brut = [...String(saisie).toUpperCase()].filter((c) => /[A-Z0-9]/.test(c)).join('')
  const prefixe = brut.slice(0, 3)
  const reste = brut.slice(3)
  if (!PREFIXES.includes(prefixe) || reste.length !== POIDS.length + 1) return null
  return `${prefixe}-${reste.slice(0, 4)}-${reste.slice(4)}`
}

export function etatSaisie(saisie) {
  const brut = [...String(saisie).toUpperCase()].filter((c) => /[A-Z0-9]/.test(c)).join('')
  if (brut.length === 0) return 'vide'
  if (brut.length < 11) return 'incomplet'
  const numero = normaliser(saisie)
  if (!numero) return 'invalide'
  const caracteres = numero.slice(4).replace('-', '')
  if ([...caracteres].some((c) => !ALPHABET.includes(c))) return 'invalide'
  return cleControle(caracteres.slice(0, -1)) === caracteres.at(-1) ? 'valide' : 'invalide'
}
