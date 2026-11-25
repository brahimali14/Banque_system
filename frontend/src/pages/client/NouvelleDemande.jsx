import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, ouvrirPdf } from '../../api/client.js'
import { Alerte, Bordereau, Carte, Chargement, Montant } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'
import { erreurMontant } from '../../utils/montants.js'

export default function NouvelleDemande() {
  const { t, erreur: traduireErreur, montant: formater, date } = useLangue()
  const [parametres] = useSearchParams()
  const comptes = useDonnees('/api/moi/comptes')
  const [type, setType] = useState('RETRAIT')
  const [numeroCompte, setNumeroCompte] = useState(parametres.get('compte') ?? '')
  const [montant, setMontant] = useState('')
  const [touche, setTouche] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [demande, setDemande] = useState(null)
  const [envoi, setEnvoi] = useState(false)

  if (comptes.chargement) return <Chargement />
  const actifs = (comptes.donnees ?? []).filter((c) => c.statut === 'ACTIF')
  const compte = actifs.find((c) => c.numero === numeroCompte) ?? actifs[0]
  const erreurSaisie = erreurMontant(montant)

  const surSoumission = async (evenement) => {
    evenement.preventDefault()
    setTouche(true)
    if (erreurSaisie) return
    setErreur(null)
    setEnvoi(true)
    try {
      setDemande(await api('/api/moi/demandes', { methode: 'POST', corps: { numero_compte: compte.numero, type, montant } }))
    } catch (e) {
      setErreur(e)
    } finally {
      setEnvoi(false)
    }
  }

  if (demande) {
    const somme = formater(demande.montant, demande.devise)
    return (
      <Carte titre={t('Votre bordereau est prêt')}>
        <Alerte type="succes">
          {t(demande.type === 'DEPOT' ? 'Demande de dépôt de {montant} enregistrée.' : 'Demande de retrait de {montant} enregistrée.', { montant: somme })}
          {demande.type === 'RETRAIT' && ' ' + t('Ce montant est réservé sur votre compte jusqu’au passage au guichet.')}
        </Alerte>
        <Bordereau legende={t("Numéro du bordereau, à communiquer à l'agent")} numero={demande.numero_bordereau}>
          {t('Valable jusqu’au {date}', { date: date(demande.date_expiration) })}
        </Bordereau>
        <div className="carte-actions">
          <button className="bouton bouton-grand" onClick={() => ouvrirPdf(`/api/moi/demandes/${demande.numero_bordereau}/bordereau.pdf`)}>
            {t('Télécharger le bordereau (PDF)')}
          </button>
          <Link className="bouton bouton-secondaire bouton-grand" to="/client/demandes">{t('Mes bordereaux')}</Link>
          <button className="bouton bouton-secondaire bouton-grand" onClick={() => { setDemande(null); setMontant(''); setTouche(false) }}>
            {t('Nouvelle demande')}
          </button>
        </div>
      </Carte>
    )
  }

  return (
    <>
      <h1>{t('Dépôt ou retrait')}</h1>
      <p className="sous-titre">
        {t("Faites votre demande en ligne, puis présentez le bordereau au guichet avec votre pièce d'identité (valable 24 h).")}
      </p>
      <Carte>
        <Alerte type="erreur">{traduireErreur(erreur ?? comptes.erreur)}</Alerte>
        {actifs.length === 0 ? <p className="vide">{t('Aucun compte actif.')}</p> : (
          <form className="formulaire" onSubmit={surSoumission}>
            <div className="choix" role="radiogroup" aria-label={t("Type d'opération")}>
              <label><input type="radio" name="type" value="DEPOT" checked={type === 'DEPOT'} onChange={(e) => setType(e.target.value)} /> {t('Dépôt')}</label>
              <label><input type="radio" name="type" value="RETRAIT" checked={type === 'RETRAIT'} onChange={(e) => setType(e.target.value)} /> {t('Retrait')}</label>
            </div>
            <div className="champ">
              <label htmlFor="compte">{t('Compte')}</label>
              <select id="compte" value={compte.numero} onChange={(e) => setNumeroCompte(e.target.value)}>
                {actifs.map((c) => (
                  <option key={c.numero} value={c.numero}>{t(c.libelle)} — {c.numero} ({c.devise})</option>
                ))}
              </select>
              <small>{t('Disponible')} : <Montant valeur={compte.solde_disponible} devise={compte.devise} /></small>
            </div>
            <div className="champ">
              <label htmlFor="montant">{t('Montant')} ({compte.devise})</label>
              <input id="montant" dir="ltr" inputMode="decimal" placeholder="12000" value={montant}
                onChange={(e) => setMontant(e.target.value)} onBlur={() => setTouche(true)} />
              {touche && erreurSaisie && <small className="erreur-champ">{t(erreurSaisie)}</small>}
            </div>
            <button className="bouton bouton-grand" disabled={envoi}>
              {envoi ? t('Création…') : t('Générer le bordereau')}
            </button>
          </form>
        )}
      </Carte>
    </>
  )
}
