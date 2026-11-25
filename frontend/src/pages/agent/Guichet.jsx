import { useRef, useState } from 'react'
import { api, ouvrirPdf } from '../../api/client.js'
import { useSession } from '../../auth/Session.jsx'
import Icone from '../../components/Icone.jsx'
import { Alerte, Badge, Carte } from '../../components/Interface.jsx'
import { useLangue } from '../../i18n/Langue.jsx'
import { etatSaisie, normaliser } from '../../utils/numeros.js'

const ICONES_SAISIE = { valide: 'valide', invalide: 'refus' }

const MESSAGES_SAISIE = {
  vide: 'Exemple : RET-K7M2-9QXB (minuscules, espaces et tirets acceptés).',
  incomplet: 'Saisie en cours…',
  invalide: 'Numéro mal saisi : vérifiez les caractères.',
  valide: 'Numéro valide — appuyez sur Entrée.',
}

function duree(minutes, t) {
  const heures = Math.floor(minutes / 60)
  return heures ? t('{h} h {m} min', { h: heures, m: minutes % 60 }) : t('{m} min', { m: minutes })
}

// evenementiel
export default function Guichet() {
  const { session } = useSession()
  const { t, erreur, montant } = useLangue()
  const champ = useRef(null)
  const [saisie, setSaisie] = useState('')
  const [vue, setVue] = useState(null)
  const [identiteVerifiee, setIdentiteVerifiee] = useState(false)
  const [motif, setMotif] = useState('')
  const [message, setMessage] = useState(null)
  const [resultat, setResultat] = useState(null)
  const [occupe, setOccupe] = useState(false)

  const etat = etatSaisie(saisie)

  const recommencer = () => {
    setSaisie('')
    setVue(null)
    setIdentiteVerifiee(false)
    setMotif('')
    setResultat(null)
    setMessage(null)
    champ.current?.focus()
  }

  const rechercher = async () => {
    if (etat !== 'valide' || occupe) return
    setOccupe(true)
    setMessage(null)
    setResultat(null)
    setVue(null)
    setIdentiteVerifiee(false)
    setMotif('')
    try {
      setVue(await api(`/api/agent/bordereaux/${normaliser(saisie)}`))
    } catch (e) {
      setMessage({ type: 'erreur', texte: erreur(e) })
    } finally {
      setOccupe(false)
    }
  }

  const surTouche = (evenement) => {
    if (evenement.key === 'Enter') {
      evenement.preventDefault()
      rechercher()
    }
  }

  const decider = async (action) => {
    setOccupe(true)
    setMessage(null)
    const numero = vue.demande.numero_bordereau
    try {
      if (action === 'valider') {
        const reponse = await api(`/api/agent/bordereaux/${numero}/valider`, { methode: 'POST' })
        setResultat(reponse)
        setMessage({
          type: reponse.transaction ? 'succes' : 'attention',
          texte: t(reponse.transaction ? 'Opération validée.' : 'Montant supérieur au seuil : la demande est transmise au superviseur.'),
        })
      } else {
        await api(`/api/agent/bordereaux/${numero}/refuser`, { methode: 'POST', corps: { motif } })
        setResultat({ refus: true })
        setMessage({ type: 'info', texte: t('Bordereau {numero} refusé : {motif}', { numero, motif }) })
      }
      setVue(null)
    } catch (e) {
      setMessage({ type: 'erreur', texte: erreur(e) })
    } finally {
      setOccupe(false)
    }
  }

  const d = vue?.demande
  const estDepot = d?.type === 'DEPOT'
  const attenteSuperviseur = d?.statut === 'EN_ATTENTE_SUPERVISEUR'
  const bloqueParSeuil = attenteSuperviseur && session.role !== 'SUPERVISEUR'

  return (
    <>
      <h1>{t('Guichet')}</h1>
      <p className="sous-titre">{t('Saisissez le numéro imprimé sur le bordereau du client.')}</p>

      <Carte className="carte-bordereau">
        <label htmlFor="numero" className="champ"><strong>{t('Numéro du bordereau')}</strong></label>
        <div className="saisie-numero">
          <input
            id="numero"
            ref={champ}
            className={etat === 'valide' ? 'valide' : etat === 'invalide' ? 'invalide' : undefined}
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            onKeyDown={surTouche}
            placeholder="RET-XXXX-XXXX"
            autoComplete="off"
            spellCheck={false}
            autoFocus
            maxLength={20}
          />
          <button className="bouton bouton-grand" onClick={rechercher} disabled={etat !== 'valide' || occupe}>
            {t('Rechercher')}
          </button>
        </div>
        <div className={`etat-saisie ${etat}`} aria-live="polite">
          {ICONES_SAISIE[etat] && <Icone nom={ICONES_SAISIE[etat]} />}
          <span>{t(MESSAGES_SAISIE[etat])}</span>
        </div>
      </Carte>

      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>

      {resultat && (
        <div className="carte-actions espace-bas">
          {resultat.transaction && (
            <button className="bouton bouton-secondaire" onClick={() => ouvrirPdf(`/api/transactions/${resultat.transaction.reference}/recu.pdf`)}>
              {t('Imprimer le reçu')}
            </button>
          )}
          <button className="bouton" onClick={recommencer}>{t('Client suivant')}</button>
        </div>
      )}

      {vue && (
        <Carte titre={`${t(estDepot ? 'Dépôt' : 'Retrait')} — ${d.numero_bordereau}`} actions={<Badge statut={d.statut} />}>
          <div className="controles">
            <span><Icone nom="valide" /> {t('Numéro valide')}</span>
            <span><Icone nom="valide" /> {t('Non expiré (reste {duree})', { duree: duree(vue.minutes_restantes, t) })}</span>
            <span><Icone nom="valide" /> {t('Non traité')}</span>
          </div>
          {vue.depasse_seuil && !attenteSuperviseur && session.role !== 'SUPERVISEUR' && (
            <Alerte type="attention">{t('Montant supérieur au seuil : en acceptant, la demande sera transmise au superviseur.')}</Alerte>
          )}
          {bloqueParSeuil && <Alerte type="attention">{t("Cette opération attend l'approbation d'un superviseur.")}</Alerte>}

          <dl className="detail-operation">
            <dt>{t('Montant')}</dt>
            <dd className="montant-geant">{montant(d.montant, d.devise)}</dd>
            <dt>{t('Client')}</dt>
            <dd>{vue.client_nom}</dd>
            <dt>{t("N° d'identité")}</dt>
            <dd className="code">{vue.client_numero_identite}</dd>
            <dt>{t('Téléphone')}</dt>
            <dd className="code">{vue.client_telephone}</dd>
            <dt>{t('Compte')}</dt>
            <dd><span className="code">{d.numero_compte}</span> — {t(vue.compte_libelle)} ({d.devise})</dd>
            <dt>{t('Solde actuel')}</dt>
            <dd>{montant(vue.solde, d.devise)}</dd>
            <dt>{t('Solde après opération')}</dt>
            <dd>{montant(vue.solde_apres_operation, d.devise)}</dd>
          </dl>

          {!bloqueParSeuil && (
            <>
              <label className="case">
                <input type="checkbox" checked={identiteVerifiee} onChange={(e) => setIdentiteVerifiee(e.target.checked)} />
                {t(estDepot ? "J'ai vérifié la pièce d'identité et compté les espèces" : "J'ai vérifié la pièce d'identité du client")}
              </label>
              <div className="decision">
                <button className="bouton bouton-vert bouton-grand" disabled={!identiteVerifiee || occupe} onClick={() => decider('valider')}>
                  <Icone nom="valide" /> {t('Accepter')}
                </button>
                <div className="refus">
                  <input placeholder={t('Motif du refus (obligatoire)')} value={motif} onChange={(e) => setMotif(e.target.value)} />
                  <button className="bouton bouton-rouge" disabled={motif.trim().length < 3 || occupe} onClick={() => decider('refuser')}>
                    <Icone nom="refus" /> {t('Refuser')}
                  </button>
                </div>
              </div>
            </>
          )}
        </Carte>
      )}
    </>
  )
}
