import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'

export function useDonnees(chemin) {
  const [etat, setEtat] = useState({ donnees: null, erreur: null, chargement: Boolean(chemin) })

  const recharger = useCallback(async () => {
    if (!chemin) return
    setEtat((e) => ({ ...e, chargement: true }))
    try {
      const donnees = await api(chemin)
      setEtat({ donnees, erreur: null, chargement: false })
    } catch (erreur) {
      setEtat({ donnees: null, erreur, chargement: false })
    }
  }, [chemin])

  useEffect(() => {
    recharger()
  }, [recharger])

  return { ...etat, recharger }
}
