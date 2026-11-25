// declaratif
import { useLangue } from '../i18n/Langue.jsx'
import Icone from './Icone.jsx'

export function Alerte({ type = 'info', children, onFermer }) {
  const { t } = useLangue()
  if (!children) return null
  return (
    <div className={`alerte alerte-${type}`} role={type === 'erreur' ? 'alert' : 'status'}>
      <span>{children}</span>
      {onFermer && (
        <button type="button" className="alerte-fermer" onClick={onFermer} aria-label={t('Fermer')}>
          <Icone nom="fermer" />
        </button>
      )}
    </div>
  )
}

export function Chargement() {
  const { t } = useLangue()
  return <p className="chargement">{t('Chargement…')}</p>
}

export function Montant({ valeur, devise = 'DZD', sens }) {
  const { montant } = useLangue()
  return <span className={`montant ${sens ?? ''}`}>{montant(valeur, devise)}</span>
}

const STATUTS = {
  EN_ATTENTE: ['En attente', 'attente'],
  EN_ATTENTE_SUPERVISEUR: ['Chez le superviseur', 'superviseur'],
  VALIDEE: ['Validée', 'succes'],
  REFUSEE: ['Refusée', 'erreur'],
  ANNULEE: ['Annulée', 'neutre'],
  EXPIREE: ['Expirée', 'neutre'],
  ACTIF: ['Actif', 'succes'],
  BLOQUE: ['Bloqué', 'erreur'],
  CLOTURE: ['Clôturé', 'neutre'],
  TEMPORAIRE: ['1re connexion', 'attente'],
  VERROUILLE: ['Verrouillé', 'erreur'],
  EXPIRE: ['Expiré', 'neutre'],
  DESACTIVE: ['Désactivé', 'neutre'],
}

export function Badge({ statut }) {
  const { t } = useLangue()
  const [libelle, couleur] = STATUTS[statut] ?? [statut, 'neutre']
  return <span className={`badge badge-${couleur}`}>{t(libelle)}</span>
}

export function Tableau({ colonnes, lignes, cle = 'id', vide, surClicLigne }) {
  const { t } = useLangue()
  if (!lignes?.length) return <p className="vide">{vide ?? t('Aucune donnée.')}</p>
  return (
    <div className="tableau-conteneur">
      <table className="tableau">
        <thead>
          <tr>
            {colonnes.map((col) => (
              <th key={col.cle} className={col.droite ? 'droite' : undefined}>
                {col.titre}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lignes.map((ligne) => (
            <tr
              key={ligne[cle]}
              className={surClicLigne ? 'cliquable' : undefined}
              onClick={surClicLigne ? () => surClicLigne(ligne) : undefined}
            >
              {colonnes.map((col) => (
                <td key={col.cle} className={col.droite ? 'droite' : undefined}>
                  {col.rendu ? col.rendu(ligne) : ligne[col.cle]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Carte({ titre, actions, children, className = '' }) {
  return (
    <section className={`carte ${className}`}>
      {(titre || actions) && (
        <header className="carte-entete">
          {titre && <h2>{titre}</h2>}
          {actions && <div className="carte-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  )
}

export function Indicateur({ titre, valeur, detail, ton }) {
  return (
    <div className={`indicateur ${ton ?? ''}`}>
      <span className="indicateur-titre">{titre}</span>
      <strong className="indicateur-valeur">{valeur}</strong>
      {detail && <span className="indicateur-detail">{detail}</span>}
    </div>
  )
}

export function FlecheRetour() {
  const { t } = useLangue()
  return <span className="lien-icone"><Icone nom="retour" /> {t('Retour')}</span>
}

export function Bordereau({ legende, numero, children }) {
  return (
    <div className="bordereau">
      {legende && <span className="bordereau-legende">{legende}</span>}
      <code className="bordereau-numero">{numero}</code>
      {children && <div className="bordereau-pied">{children}</div>}
    </div>
  )
}
