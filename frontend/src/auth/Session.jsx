import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, ecrireSession, lireSession } from '../api/client.js'

const ContexteSession = createContext(null)

export const ACCUEIL_PAR_ROLE = {
  CLIENT: '/client',
  AGENT: '/agent/guichet',
  SUPERVISEUR: '/superviseur',
  ADMIN: '/admin',
}

export function FournisseurSession({ children }) {
  const [session, setSession] = useState(lireSession)
  const [avis, setAvis] = useState(null)

  const memoriser = useCallback((nouvelle) => {
    ecrireSession(nouvelle)
    setSession(nouvelle)
  }, [])

  const connecter = useCallback(
    async (login, motDePasse) => {
      const reponse = await api('/api/auth/connexion', { methode: 'POST', corps: { login, mot_de_passe: motDePasse } })
      setAvis(null)
      memoriser(reponse)
      return reponse
    },
    [memoriser],
  )

  const deconnecter = useCallback(
    (message = null) => {
      setAvis(message)
      memoriser(null)
    },
    [memoriser],
  )

  // evenementiel
  useEffect(() => {
    const surExpiration = () => deconnecter('Votre session a expiré, veuillez vous reconnecter.')
    const surChangementRequis = () => setSession((s) => (s ? { ...s, doit_changer_mdp: true } : s))
    window.addEventListener('session-expiree', surExpiration)
    window.addEventListener('changement-mdp-requis', surChangementRequis)
    return () => {
      window.removeEventListener('session-expiree', surExpiration)
      window.removeEventListener('changement-mdp-requis', surChangementRequis)
    }
  }, [deconnecter])

  const valeur = useMemo(
    () => ({ session, connecter, deconnecter, memoriser, avis }),
    [session, connecter, deconnecter, memoriser, avis],
  )
  return <ContexteSession.Provider value={valeur}>{children}</ContexteSession.Provider>
}

export function useSession() {
  return useContext(ContexteSession)
}
