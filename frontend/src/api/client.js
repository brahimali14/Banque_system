const CLE_SESSION = 'bankservices.session'

export class ErreurApi extends Error {
  constructor(code, message, statut) {
    super(message)
    this.code = code
    this.statut = statut
  }
}

export function lireSession() {
  try {
    return JSON.parse(sessionStorage.getItem(CLE_SESSION))
  } catch {
    return null
  }
}

export function ecrireSession(session) {
  if (session) sessionStorage.setItem(CLE_SESSION, JSON.stringify(session))
  else sessionStorage.removeItem(CLE_SESSION)
}

async function envoyer(chemin, { methode = 'GET', corps } = {}) {
  const session = lireSession()
  const entetes = {}
  if (corps !== undefined) entetes['Content-Type'] = 'application/json'
  if (session?.jeton) entetes.Authorization = `Bearer ${session.jeton}`

  let reponse
  try {
    reponse = await fetch(chemin, {
      method: methode,
      headers: entetes,
      body: corps === undefined ? undefined : JSON.stringify(corps),
    })
  } catch {
    throw new ErreurApi('RESEAU', "Le serveur ne répond pas. Vérifiez que l'API est lancée.", 0)
  }

  if (!reponse.ok) {
    let erreur = { code: 'ERREUR', message: `Erreur ${reponse.status}` }
    try {
      erreur = await reponse.json()
    } catch {

    }
    if (reponse.status === 401 && session && chemin !== '/api/auth/connexion') {
      window.dispatchEvent(new CustomEvent('session-expiree', { detail: erreur.message }))
    }
    if (erreur.code === 'CHANGEMENT_MDP_REQUIS') {
      window.dispatchEvent(new CustomEvent('changement-mdp-requis'))
    }
    throw new ErreurApi(erreur.code, erreur.message, reponse.status)
  }
  return reponse
}

export async function api(chemin, options) {
  const reponse = await envoyer(chemin, options)
  return reponse.status === 204 ? null : reponse.json()
}

export async function ouvrirPdf(chemin, options) {
  const reponse = await envoyer(chemin, options)
  const blob = await reponse.blob()
  const url = URL.createObjectURL(blob)
  const nom = /filename="([^"]+)"/.exec(reponse.headers.get('Content-Disposition') ?? '')?.[1] ?? 'document.pdf'
  const onglet = window.open(url, '_blank')
  if (!onglet) {
    const lien = document.createElement('a')
    lien.href = url
    lien.download = nom
    lien.click()
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
