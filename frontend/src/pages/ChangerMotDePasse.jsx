import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import { ACCUEIL_PAR_ROLE, useSession } from '../auth/Session.jsx'
import Icone from '../components/Icone.jsx'
import { Alerte, FlecheRetour } from '../components/Interface.jsx'
import { SelecteurLangue, useLangue } from '../i18n/Langue.jsx'
import { estRobuste, verifierRegles } from '../utils/motDePasse.js'

export default function ChangerMotDePasse() {
  const { session, memoriser, deconnecter } = useSession()
  const { t, erreur: traduireErreur } = useLangue()
  const naviguer = useNavigate()
  const [ancien, setAncien] = useState('')
  const [nouveau, setNouveau] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [erreur, setErreur] = useState(null)
  const [envoi, setEnvoi] = useState(false)

  if (!session) return <Navigate to="/connexion" replace />
  const premiereConnexion = session.doit_changer_mdp
  const regles = verifierRegles(nouveau) // recalculé à chaque frappe (événement onChange)
  const identiques = confirmation.length > 0 && nouveau === confirmation
  const pret = estRobuste(nouveau) && identiques && (premiereConnexion || ancien)

  const surSoumission = async (evenement) => {
    evenement.preventDefault()
    setErreur(null)
    setEnvoi(true)
    try {
      const nouvelle = await api('/api/auth/changer-mot-de-passe', {
        methode: 'POST',
        corps: { ancien: premiereConnexion ? null : ancien, nouveau, confirmation },
      })
      memoriser(nouvelle)
      naviguer(ACCUEIL_PAR_ROLE[nouvelle.role], { replace: true, state: { message: 'Mot de passe enregistré.' } })
    } catch (e) {
      setErreur(e)
      setEnvoi(false)
    }
  }

  return (
    <div className="ecran-connexion">
      <div className="boite-connexion">
        <div className="entete-connexion">
          <div className="logo">
            <img src="/favicon.svg" alt="" width="32" height="32" /> BankServices
          </div>
          <SelecteurLangue clair />
        </div>
        <h1>{t(premiereConnexion ? 'Choisissez votre mot de passe' : 'Changer mon mot de passe')}</h1>
        {premiereConnexion ? (
          <Alerte type="info">
            {t("Bienvenue {nom}. Pour votre sécurité, remplacez le mot de passe temporaire remis par l'agence avant d'accéder à vos comptes.", { nom: session.nom_affiche })}
          </Alerte>
        ) : (
          <p className="sous-titre">{t('Connecté en tant que {login}.', { login: session.login })}</p>
        )}
        <Alerte type="erreur">{traduireErreur(erreur)}</Alerte>
        <form className="formulaire" onSubmit={surSoumission}>
          {!premiereConnexion && (
            <div className="champ">
              <label htmlFor="ancien">{t('Mot de passe actuel')}</label>
              <input id="ancien" dir="ltr" type="password" value={ancien} onChange={(e) => setAncien(e.target.value)} required />
            </div>
          )}
          <div className="champ">
            <label htmlFor="nouveau">{t('Nouveau mot de passe')}</label>
            <input id="nouveau" dir="ltr" type="password" value={nouveau} onChange={(e) => setNouveau(e.target.value)}
              autoComplete="new-password" autoFocus />
            <ul className="regles" aria-label={t('Règles du mot de passe')}>
              {regles.map((r) => (
                <li key={r.id} className={r.ok ? 'ok' : undefined}>
                  <Icone nom={r.ok ? 'valide' : 'attente'} /> {t(r.texte)}
                </li>
              ))}
            </ul>
          </div>
          <div className="champ">
            <label htmlFor="confirmation">{t('Confirmer le mot de passe')}</label>
            <input id="confirmation" dir="ltr" type="password" value={confirmation} onChange={(e) => setConfirmation(e.target.value)}
              autoComplete="new-password" />
            {confirmation && !identiques && <small className="erreur-champ">{t('Les deux saisies sont différentes.')}</small>}
          </div>
          <button className="bouton bouton-grand" disabled={!pret || envoi}>{t('Enregistrer')}</button>
        </form>
        <p className="note-bas">
          {premiereConnexion ? (
            <button type="button" className="bouton bouton-secondaire bouton-petit" onClick={() => deconnecter()}>
              {t('Se déconnecter')}
            </button>
          ) : (
            <Link to={ACCUEIL_PAR_ROLE[session.role]}><FlecheRetour /></Link>
          )}
        </p>
      </div>
    </div>
  )
}
