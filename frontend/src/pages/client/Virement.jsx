import { useState } from 'react'
import { api } from '../../api/client.js'
import { Alerte, Carte, Chargement, Montant } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'
import { apercuFrais, depuisCentimes, enCentimes, erreurMontant } from '../../utils/montants.js'

export default function Virement() {
  const { t, erreur: traduireErreur, montant: formater } = useLangue()
  const comptes = useDonnees('/api/moi/comptes')
  const [source, setSource] = useState('')
  const [destination, setDestination] = useState('')
  const [montant, setMontant] = useState('')
  const [etape, setEtape] = useState('saisie') // saisie → confirmation → resultat
  const [erreur, setErreur] = useState(null)
  const [resultat, setResultat] = useState(null)

  if (comptes.chargement) return <Chargement />
  const actifs = (comptes.donnees ?? []).filter((c) => c.statut === 'ACTIF')
  const compteSource = actifs.find((c) => c.numero === source) ?? actifs[0]
  const autres = actifs.filter((c) => c.numero !== compteSource?.numero)
  const erreurSaisie = erreurMontant(montant)
  const frais = apercuFrais(compteSource?.type_compte, enCentimes(montant))
  const destinationNormalisee = destination.trim().toUpperCase()

  const verifier = (evenement) => {
    evenement.preventDefault()
    setErreur(null)
    if (!destinationNormalisee) return setErreur(t('Indiquez le compte destinataire.'))
    if (destinationNormalisee === compteSource.numero) return setErreur(t('Un virement doit concerner deux comptes distincts.'))
    if (erreurSaisie) return setErreur(t(erreurSaisie))
    setEtape('confirmation')
  }

  const confirmer = async () => {
    setErreur(null)
    try {
      setResultat(
        await api('/api/moi/virements', {
          methode: 'POST',
          corps: { compte_source: compteSource.numero, compte_destination: destinationNormalisee, montant },
        }),
      )
      setEtape('resultat')
      comptes.recharger()
    } catch (e) {
      setErreur(traduireErreur(e))
      setEtape('saisie')
    }
  }

  return (
    <>
      <h1>{t('Virement')}</h1>
      <p className="sous-titre">{t('Le débit et le crédit sont enregistrés ensemble, ou pas du tout.')}</p>
      <Alerte type="erreur">{erreur}</Alerte>

      {etape === 'resultat' && resultat && (
        <Carte titre={t('Virement effectué')}>
          <Alerte type="succes">
            {t('{debit} débités, {credit} crédités.', {
              debit: formater(resultat.montant_debite, resultat.devise_source),
              credit: formater(resultat.montant_credite, resultat.devise_destination),
            })}
            {Number(resultat.frais) > 0 && ' ' + t('Frais : {frais}', { frais: formater(resultat.frais, resultat.devise_source) })}
          </Alerte>
          <p>
            {t('Référence')} : <span className="code">{resultat.reference}</span> · {t('Nouveau solde')} :{' '}
            <Montant valeur={resultat.nouveau_solde_source} devise={resultat.devise_source} />
          </p>
          <button className="bouton" onClick={() => { setEtape('saisie'); setMontant(''); setDestination('') }}>{t('Nouveau virement')}</button>
        </Carte>
      )}

      {etape === 'confirmation' && (
        <Carte titre={t('Confirmer le virement')}>
          <dl className="detail-operation">
            <dt>{t('Depuis')}</dt><dd>{t(compteSource.libelle)} — <span className="code">{compteSource.numero}</span></dd>
            <dt>{t('Vers')}</dt><dd className="code">{destinationNormalisee}</dd>
            <dt>{t('Montant')}</dt><dd className="montant-geant">{formater(montant, compteSource.devise)}</dd>
            <dt>{t('Frais estimés')}</dt><dd>{formater(depuisCentimes(frais), compteSource.devise)}</dd>
            <dt>{t('Total débité')}</dt><dd>{formater(depuisCentimes(enCentimes(montant) + frais), compteSource.devise)}</dd>
          </dl>
          <p className="sous-titre">{t('Si le compte destinataire est dans une autre devise, le montant sera converti au taux du jour.')}</p>
          <div className="carte-actions">
            <button className="bouton bouton-vert bouton-grand" onClick={confirmer}>{t('Confirmer')}</button>
            <button className="bouton bouton-secondaire bouton-grand" onClick={() => setEtape('saisie')}>{t('Modifier')}</button>
          </div>
        </Carte>
      )}

      {etape === 'saisie' && (
        <Carte>
          {actifs.length === 0 ? <p className="vide">{t('Aucun compte actif.')}</p> : (
            <form className="formulaire" onSubmit={verifier}>
              <div className="champ">
                <label htmlFor="source">{t('Compte à débiter')}</label>
                <select id="source" value={compteSource.numero} onChange={(e) => setSource(e.target.value)}>
                  {actifs.map((c) => <option key={c.numero} value={c.numero}>{t(c.libelle)} — {c.numero} ({c.devise})</option>)}
                </select>
                <small>
                  {t('Disponible')} : <Montant valeur={compteSource.solde_disponible} devise={compteSource.devise} />
                  {compteSource.type_compte === 'EPARGNE' && ' · ' + t('uniquement vers vos propres comptes')}
                </small>
              </div>
              <div className="champ">
                <label htmlFor="destination">{t('Compte destinataire')}</label>
                <input id="destination" dir="ltr" list="mes-comptes" placeholder="BS-CC-000012" value={destination} onChange={(e) => setDestination(e.target.value)} />
                <datalist id="mes-comptes">
                  {autres.map((c) => <option key={c.numero} value={c.numero}>{t(c.libelle)} ({c.devise})</option>)}
                </datalist>
              </div>
              <div className="champ">
                <label htmlFor="montant">{t('Montant')} ({compteSource.devise})</label>
                <input id="montant" dir="ltr" inputMode="decimal" value={montant} onChange={(e) => setMontant(e.target.value)} />
                {!erreurSaisie && <small>{t('Frais estimés')} : {formater(depuisCentimes(frais), compteSource.devise)}</small>}
              </div>
              <button className="bouton bouton-grand">{t('Continuer')}</button>
            </form>
          )}
        </Carte>
      )}
    </>
  )
}
