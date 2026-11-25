import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import ar from '../i18n/ar.js'
import en from '../i18n/en.js'
import { traduire } from '../i18n/Langue.jsx'

const RACINE = join(__dirname, '..')

function fichiersSource(dossier) {
  return readdirSync(dossier).flatMap((nom) => {
    const chemin = join(dossier, nom)
    if (statSync(chemin).isDirectory()) return nom === '__tests__' || nom === 'i18n' ? [] : fichiersSource(chemin)
    return /\.jsx?$/.test(nom) ? [chemin] : []
  })
}

function textesDuCode() {
  const textes = new Set()
  for (const fichier of fichiersSource(RACINE)) {
    const source = readFileSync(fichier, 'utf8')
    for (const m of source.matchAll(/\bt\(\s*(['"])((?:(?!\1).)*)\1/g)) textes.add(m[2])
    for (const m of source.matchAll(/\bt\(\s*[\w.!=' ]+\?\s*(['"])((?:(?!\1).)*)\1\s*:\s*(['"])((?:(?!\3).)*)\3/g)) {
      textes.add(m[2])
      textes.add(m[4])
    }
  }
  return textes
}

const TEXTES_CONSTANTS = [
  'Mes comptes', 'Mon profil', 'Paramètres', 'Utilisateurs', 'Agent', 'Superviseur', 'Administrateur',
  'En attente', 'Chez le superviseur', 'Validée', 'Refusée', 'Annulée', 'Expirée', 'Actif', 'Bloqué', 'Clôturé',
  '1re connexion', 'Verrouillé', 'Expiré', 'Désactivé', 'Virement émis', 'Virement reçu', 'Frais', 'Intérêts',
  '8 caractères minimum', 'Une majuscule', 'Une minuscule', 'Un chiffre', 'Saisissez un montant.',
  'Montant invalide (2 décimales au maximum).', 'Le montant doit être strictement positif.',
  'Votre session a expiré, veuillez vous reconnecter.', 'Mot de passe enregistré.', 'Compte bloqué.',
  'Compte réactivé.', 'Compte clôturé.', 'Seuil de double validation (DA)', 'Au-dessus, un superviseur doit approuver.',
  'Validité des bordereaux (heures)', 'Après ce délai, le bordereau expire.', 'Validité du mot de passe temporaire (jours)',
  'Tentatives de connexion avant verrouillage', 'Expirer les bordereaux dépassés', 'Verser les intérêts mensuels (épargne)',
  'Prélever les frais de tenue de compte', 'Exemple : RET-K7M2-9QXB (minuscules, espaces et tirets acceptés).',
  'Saisie en cours…', 'Numéro mal saisi : vérifiez les caractères.', 'Numéro valide — appuyez sur Entrée.',
  'Langue', 'Prénom',
]

const CODES_ERREUR = Object.keys(en.erreurs)

describe('traductions', () => {
  const textes = [...textesDuCode(), ...TEXTES_CONSTANTS]

  it.each([['anglais', en], ['arabe', ar]])('tous les textes existent en %s', (_, dictionnaire) => {
    const manquants = textes.filter((texte) => !(texte in dictionnaire.textes))
    expect(manquants).toEqual([])
  })

  it('les deux langues ont les mêmes messages d’erreur', () => {
    expect(Object.keys(ar.erreurs).sort()).toEqual([...CODES_ERREUR].sort())
  })

  it('garde les mêmes {paramètres} dans chaque traduction', () => {
    for (const dictionnaire of [en, ar]) {
      for (const [francais, traduction] of Object.entries(dictionnaire.textes)) {
        const attendus = (francais.match(/\{\w+\}/g) ?? []).sort()
        expect([francais, (traduction.match(/\{\w+\}/g) ?? []).sort()]).toEqual([francais, attendus])
      }
    }
  })

  it('remplace les paramètres et revient au français si besoin', () => {
    expect(traduire('ar', 'Bonjour {nom}', { nom: 'Amine' })).toBe('مرحبًا Amine')
    expect(traduire('en', 'Texte inconnu')).toBe('Texte inconnu')
    expect(traduire('fr', 'Bonjour {nom}', { nom: 'Sara' })).toBe('Bonjour Sara')
  })
})
