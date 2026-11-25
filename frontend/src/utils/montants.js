// fonctionnel

const FORMATS = {
  fr: { milliers: ' ', decimale: ',', symboles: { DZD: 'DA', EUR: '€', USD: '$' } },
  en: { milliers: ',', decimale: '.', symboles: { DZD: 'DZD', EUR: '€', USD: '$' } },
  ar: { milliers: ',', decimale: '.', symboles: { DZD: 'د.ج', EUR: '€', USD: '$' } },
}

export function enCentimes(valeur) {
  const texte = String(valeur ?? '').trim().replace(/\s/g, '').replace(',', '.')
  if (!/^-?\d+(\.\d{1,2})?$/.test(texte)) return null
  const negatif = texte.startsWith('-')
  const [entier, decimales = ''] = texte.replace('-', '').split('.')
  const centimes = Number(entier) * 100 + Number(decimales.padEnd(2, '0'))
  return negatif ? -centimes : centimes
}

export function depuisCentimes(centimes) {
  const signe = centimes < 0 ? '-' : ''
  const absolu = Math.abs(centimes)
  return `${signe}${Math.floor(absolu / 100)}.${String(absolu % 100).padStart(2, '0')}`
}

export function formaterMontant(valeur, devise = 'DZD', langue = 'fr') {
  const centimes = enCentimes(typeof valeur === 'number' ? valeur.toFixed(2) : valeur)
  if (centimes === null) return '—'
  const format = FORMATS[langue] ?? FORMATS.fr
  const [entier, decimales] = depuisCentimes(Math.abs(centimes)).split('.')
  const groupes = entier.replace(/\B(?=(\d{3})+(?!\d))/g, format.milliers)
  return `${centimes < 0 ? '-' : ''}${groupes}${format.decimale}${decimales} ${format.symboles[devise] ?? devise}`
}

export function erreurMontant(saisie) {
  const centimes = enCentimes(saisie)
  if (String(saisie ?? '').trim() === '') return 'Saisissez un montant.'
  if (centimes === null) return 'Montant invalide (2 décimales au maximum).'
  if (centimes <= 0) return 'Le montant doit être strictement positif.'
  return null
}

export function borner(valeur, minimum, maximum) {
  return Math.max(minimum, Math.min(valeur, maximum))
}

export function apercuFrais(typeCompte, montantCentimes) {
  if (montantCentimes === null || montantCentimes <= 0) return 0
  if (typeCompte === 'COURANT') return borner(Math.round(montantCentimes * 0.005), 5000, 100000)
  if (typeCompte === 'DEVISE') return borner(Math.round(montantCentimes * 0.01), 100, 2000)
  return 0
}
