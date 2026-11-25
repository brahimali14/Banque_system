import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ouvrirPdf } from '../../api/client.js'
import { Alerte, Badge, Carte, Chargement, Montant, Tableau } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'

const STATUTS = [
  ['EN_ATTENTE', 'En attente'],
  ['EN_ATTENTE_SUPERVISEUR', 'Chez le superviseur'],
  ['VALIDEE', 'Validée'],
  ['REFUSEE', 'Refusée'],
  ['ANNULEE', 'Annulée'],
  ['EXPIREE', 'Expirée'],
]

export default function MesDemandes() {
  const { t, erreur, date } = useLangue()
  const demandes = useDonnees('/api/moi/demandes')
  const [statut, setStatut] = useState('')
  const [message, setMessage] = useState(null)

  const annuler = async (numero) => {
    if (!window.confirm(t('Annuler le bordereau {numero} ?', { numero }))) return
    try {
      await api(`/api/moi/demandes/${numero}`, { methode: 'DELETE' })
      setMessage({ type: 'succes', texte: t('Bordereau {numero} annulé.', { numero }) })
      demandes.recharger()
    } catch (e) {
      setMessage({ type: 'erreur', texte: erreur(e) })
    }
  }

  const lignes = (demandes.donnees ?? []).filter((d) => !statut || d.statut === statut)

  return (
    <>
      <div className="entete-page">
        <div>
          <h1>{t('Mes bordereaux')}</h1>
          <p className="sous-titre">{t('Suivez vos demandes de dépôt et de retrait.')}</p>
        </div>
        <Link className="bouton" to="/client/demande">{t('Nouvelle demande')}</Link>
      </div>
      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>
      <Carte>
        <div className="filtres">
          <div className="champ">
            <label htmlFor="statut">{t('Statut')}</label>
            <select id="statut" value={statut} onChange={(e) => setStatut(e.target.value)}>
              <option value="">{t('Tous')}</option>
              {STATUTS.map(([valeur, libelle]) => <option key={valeur} value={valeur}>{t(libelle)}</option>)}
            </select>
          </div>
        </div>
        {demandes.chargement ? <Chargement /> : (
          <Tableau
            cle="numero_bordereau"
            lignes={lignes}
            vide={t('Aucun bordereau.')}
            colonnes={[
              { cle: 'numero_bordereau', titre: t('Numéro'), rendu: (d) => <span className="code numero-bordereau">{d.numero_bordereau}</span> },
              { cle: 'type', titre: t('Opération'), rendu: (d) => t(d.type === 'DEPOT' ? 'Dépôt' : 'Retrait') },
              { cle: 'numero_compte', titre: t('Compte'), rendu: (d) => <span className="code">{d.numero_compte}</span> },
              { cle: 'montant', titre: t('Montant'), droite: true, rendu: (d) => <Montant valeur={d.montant} devise={d.devise} /> },
              { cle: 'date_creation', titre: t('Créé le'), rendu: (d) => date(d.date_creation) },
              { cle: 'statut', titre: t('Statut'), rendu: (d) => (
                <>
                  <Badge statut={d.statut} />
                  {d.motif_refus && <div><small>{d.motif_refus}</small></div>}
                </>
              ) },
              { cle: 'actions', titre: '', rendu: (d) => (
                <div className="carte-actions">
                  {['EN_ATTENTE', 'EN_ATTENTE_SUPERVISEUR'].includes(d.statut) && (
                    <button className="bouton bouton-secondaire bouton-petit" onClick={() => ouvrirPdf(`/api/moi/demandes/${d.numero_bordereau}/bordereau.pdf`)}>{t('Bordereau')}</button>
                  )}
                  {d.statut === 'EN_ATTENTE' && (
                    <button className="bouton bouton-rouge bouton-petit" onClick={() => annuler(d.numero_bordereau)}>{t('Annuler')}</button>
                  )}
                  {d.reference_transaction && (
                    <button className="bouton bouton-secondaire bouton-petit" onClick={() => ouvrirPdf(`/api/transactions/${d.reference_transaction}/recu.pdf`)}>{t('Reçu')}</button>
                  )}
                </div>
              ) },
            ]}
          />
        )}
      </Carte>
    </>
  )
}
