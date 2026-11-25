import { useState } from 'react'
import { api } from '../../api/client.js'
import { Alerte, Carte, Chargement, Montant, Tableau } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'

export default function Approbations() {
  const { t, erreur, date } = useLangue()
  const demandes = useDonnees('/api/superviseur/demandes')
  const [message, setMessage] = useState(null)

  const decider = async (demande, approuver) => {
    const numero = demande.numero_bordereau
    let corps
    if (!approuver) {
      const motif = window.prompt(t('Motif du rejet :'))
      if (!motif || motif.trim().length < 3) return
      corps = { motif }
    }
    try {
      await api(`/api/agent/bordereaux/${numero}/${approuver ? 'valider' : 'refuser'}`, { methode: 'POST', corps })
      setMessage({ type: 'succes', texte: t(approuver ? 'Opération {numero} approuvée.' : 'Opération {numero} rejetée.', { numero }) })
      demandes.recharger()
    } catch (e) {
      setMessage({ type: 'erreur', texte: erreur(e) })
    }
  }

  return (
    <>
      <h1>{t('À approuver')}</h1>
      <p className="sous-titre">{t('Opérations supérieures au seuil, transmises par les agents.')}</p>
      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>
      <Carte>
        {demandes.chargement ? <Chargement /> : (
          <Tableau
            cle="numero_bordereau"
            lignes={demandes.donnees}
            vide={t('Aucune opération en attente.')}
            colonnes={[
              { cle: 'numero_bordereau', titre: t('Numéro'), rendu: (d) => <span className="code numero-bordereau">{d.numero_bordereau}</span> },
              { cle: 'type', titre: t('Opération'), rendu: (d) => t(d.type === 'DEPOT' ? 'Dépôt' : 'Retrait') },
              { cle: 'numero_compte', titre: t('Compte'), rendu: (d) => <span className="code">{d.numero_compte}</span> },
              { cle: 'montant', titre: t('Montant'), droite: true, rendu: (d) => <strong><Montant valeur={d.montant} devise={d.devise} /></strong> },
              { cle: 'date_creation', titre: t('Créé le'), rendu: (d) => date(d.date_creation) },
              { cle: 'actions', titre: '', rendu: (d) => (
                <div className="carte-actions">
                  <button className="bouton bouton-vert bouton-petit" onClick={() => decider(d, true)}>{t('Approuver')}</button>
                  <button className="bouton bouton-rouge bouton-petit" onClick={() => decider(d, false)}>{t('Rejeter')}</button>
                </div>
              ) },
            ]}
          />
        )}
      </Carte>
    </>
  )
}
