import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { formaterMontant } from '../utils/montants.js'
import ar from './ar.js'
import en from './en.js'

export const LANGUES = {
  fr: { nom: 'Français', direction: 'ltr', locale: 'fr-FR' },
  en: { nom: 'English', direction: 'ltr', locale: 'en-GB' },
  ar: { nom: 'العربية', direction: 'rtl', locale: 'ar-DZ' },
}
const DICTIONNAIRES = { fr: { textes: {}, erreurs: {} }, en, ar }
const CLE = 'bankservices.langue'

export function traduire(langue, texte, parametres = {}) {
  const modele = DICTIONNAIRES[langue]?.textes[texte] ?? texte
  return modele.replace(/\{(\w+)\}/g, (_, nom) => String(parametres[nom] ?? `{${nom}}`))
}

const ContexteLangue = createContext(null)

function langueInitiale() {
  const enregistree = typeof localStorage !== 'undefined' ? localStorage.getItem(CLE) : null
  return LANGUES[enregistree] ? enregistree : 'fr'
}

export function FournisseurLangue({ children, langue: imposee }) {
  const [langue, setLangue] = useState(imposee ?? langueInitiale)

  useEffect(() => {
    localStorage.setItem(CLE, langue)
    document.documentElement.lang = langue
    document.documentElement.dir = LANGUES[langue].direction
  }, [langue])

  const t = useCallback((texte, parametres) => traduire(langue, texte, parametres), [langue])

  const valeur = useMemo(() => {
    const locale = LANGUES[langue].locale
    return {
      langue,
      setLangue,
      t,
            erreur: (e) => (e ? DICTIONNAIRES[langue].erreurs[e.code] ?? e.message : null),
      montant: (valeur, devise) => formaterMontant(valeur, devise, langue),
      date: (valeur) =>
        valeur ? new Date(valeur).toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' }) : '—',
      jour: (valeur) => (valeur ? new Date(valeur).toLocaleDateString(locale) : '—'),
    }
  }, [langue, t])

  return <ContexteLangue.Provider value={valeur}>{children}</ContexteLangue.Provider>
}

export function useLangue() {
  return useContext(ContexteLangue)
}

export function SelecteurLangue({ clair = false }) {
  const { langue, setLangue, t } = useLangue()
  return (
    <select
      className={`selecteur-langue ${clair ? 'clair' : ''}`}
      value={langue}
      onChange={(e) => setLangue(e.target.value)}
      aria-label={t('Langue')}
    >
      {Object.entries(LANGUES).map(([code, { nom }]) => (
        <option key={code} value={code}>{nom}</option>
      ))}
    </select>
  )
}
