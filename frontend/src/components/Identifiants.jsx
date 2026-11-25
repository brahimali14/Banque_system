import { useState } from 'react'
import { ouvrirPdf } from '../api/client.js'
import { useLangue } from '../i18n/Langue.jsx'
import { Alerte } from './Interface.jsx'

export default function Identifiants({ clientId, identifiants }) {
  const { t, erreur: traduireErreur, date } = useLangue()
  const [erreur, setErreur] = useState(null)
  const imprimer = async () => {
    try {
      await ouvrirPdf(`/api/clients/${clientId}/fiche-identifiants.pdf`, {
        methode: 'POST',
        corps: { mot_de_passe_temporaire: identifiants.mot_de_passe_temporaire },
      })
    } catch (e) {
      setErreur(e)
    }
  }
  return (
    <div className="identifiants">
      <Alerte type="attention">{t('Notez ou imprimez ces identifiants maintenant : le mot de passe ne sera plus jamais affiché.')}</Alerte>
      <span>{t("Nom d'utilisateur")} : <code className="code">{identifiants.login}</code></span>
      <span>{t('Mot de passe temporaire')} : <code className="code">{identifiants.mot_de_passe_temporaire}</code></span>
      <small>
        {t('Valable jusqu’au {date} · à changer obligatoirement à la première connexion.', { date: date(identifiants.expiration) })}
      </small>
      {clientId && (
        <div>
          <button className="bouton" onClick={imprimer}>{t('Imprimer la fiche (PDF)')}</button>
        </div>
      )}
      <Alerte type="erreur">{traduireErreur(erreur)}</Alerte>
    </div>
  )
}
