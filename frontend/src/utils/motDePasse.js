// fonctionnel
export const REGLES = [
  { id: 'longueur', texte: '8 caractères minimum', test: (m) => m.length >= 8 },
  { id: 'majuscule', texte: 'Une majuscule', test: (m) => /[A-Z]/.test(m) },
  { id: 'minuscule', texte: 'Une minuscule', test: (m) => /[a-z]/.test(m) },
  { id: 'chiffre', texte: 'Un chiffre', test: (m) => /\d/.test(m) },
]

export const verifierRegles = (motDePasse) => REGLES.map((regle) => ({ ...regle, ok: regle.test(motDePasse) }))

export const estRobuste = (motDePasse) => REGLES.every((regle) => regle.test(motDePasse))
