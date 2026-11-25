import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { ACCUEIL_PAR_ROLE, useSession } from '../auth/Session.jsx'
import { Alerte } from '../components/Interface.jsx'
import { SelecteurLangue, useLangue } from '../i18n/Langue.jsx'

export default function Connexion() {
  const { session, connecter, avis } = useSession()
  const { t, erreur: traduireErreur } = useLangue()
  const naviguer = useNavigate()
  const [login, setLogin] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [erreur, setErreur] = useState(null)
  const [envoi, setEnvoi] = useState(false)

  if (session && !envoi) {
    return <Navigate to={session.doit_changer_mdp ? '/changer-mot-de-passe' : ACCUEIL_PAR_ROLE[session.role]} replace />
  }

  const surSoumission = async (evenement) => {
    evenement.preventDefault()
    setErreur(null)
    setEnvoi(true)
    try {
      const nouvelle = await connecter(login, motDePasse)
      naviguer(nouvelle.doit_changer_mdp ? '/changer-mot-de-passe' : ACCUEIL_PAR_ROLE[nouvelle.role], { replace: true })
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
        <p className="sous-titre">{t('Connectez-vous à votre espace.')}</p>
        <Alerte type="attention">{avis && t(avis)}</Alerte>
        <Alerte type="erreur">{traduireErreur(erreur)}</Alerte>
        <form className="formulaire" onSubmit={surSoumission}>
          <div className="champ">
            <label htmlFor="login">{t("Nom d'utilisateur")}</label>
            <input id="login" dir="ltr" value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" autoFocus required />
          </div>
          <div className="champ">
            <label htmlFor="mdp">{t('Mot de passe')}</label>
            <input id="mdp" dir="ltr" type="password" value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)}
              autoComplete="current-password" required />
          </div>
          <button className="bouton bouton-grand" disabled={envoi}>
            {envoi ? t('Connexion…') : t('Se connecter')}
          </button>
        </form>
        <p className="note-bas">
          {t("Nouveau client ? Votre agence vous remet un nom d'utilisateur et un mot de passe temporaire.")}
        </p>
      </div>
    </div>
  )
}
