import { Link } from 'react-router-dom'
import { Alerte, Carte, Chargement, Indicateur, Montant, Tableau } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'
import { LIBELLES_TYPES } from '../../utils/stats.js'

export default function TableauDeBord() {
  const { t, erreur, jour } = useLangue()
  const tableau = useDonnees('/api/superviseur/tableau-de-bord')

  if (tableau.chargement) return <Chargement />
  if (!tableau.donnees) return <Alerte type="erreur">{erreur(tableau.erreur)}</Alerte>
  const d = tableau.donnees
  const statuts = d.demandes_par_statut

  return (
    <>
      <div className="entete-page">
        <div>
          <h1>{t('Tableau de bord')}</h1>
          <p className="sous-titre">{t("Activité de l'agence le {date}", { date: jour(d.jour) })}</p>
        </div>
        <button className="bouton bouton-secondaire" onClick={tableau.recharger}>{t('Actualiser')}</button>
      </div>
      <div className="indicateurs">
        <Indicateur titre={t('Clients')} valeur={d.clients} />
        <Indicateur titre={t('Comptes actifs')} valeur={d.comptes_actifs} />
        <Indicateur titre={t('Bordereaux en attente')} valeur={statuts.EN_ATTENTE ?? 0} />
        <Indicateur titre={t('À approuver')} valeur={statuts.EN_ATTENTE_SUPERVISEUR ?? 0}
          ton={statuts.EN_ATTENTE_SUPERVISEUR ? 'debit' : undefined}
          detail={<Link to="/superviseur/approbations">{t('Voir')}</Link>} />
      </div>
      <Carte titre={t('Opérations du jour')}>
        <Tableau
          cle="cle"
          lignes={d.activite_du_jour.map((l) => ({ ...l, cle: `${l.type}-${l.devise}` }))}
          vide={t("Aucune opération aujourd'hui.")}
          colonnes={[
            { cle: 'type', titre: t('Type'), rendu: (l) => t(LIBELLES_TYPES[l.type] ?? l.type) },
            { cle: 'devise', titre: t('Devise') },
            { cle: 'nombre', titre: t('Nombre'), droite: true },
            { cle: 'total', titre: t('Total'), droite: true, rendu: (l) => <Montant valeur={l.total} devise={l.devise} /> },
          ]}
        />
      </Carte>
    </>
  )
}
