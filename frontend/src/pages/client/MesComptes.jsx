import { Link, useLocation } from 'react-router-dom'
import { useSession } from '../../auth/Session.jsx'
import { Alerte, Badge, Carte, Chargement, Montant, Tableau } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'

export default function MesComptes() {
  const { session } = useSession()
  const { t, erreur, date } = useLangue()
  const { state } = useLocation()
  const comptes = useDonnees('/api/moi/comptes')
  const demandes = useDonnees('/api/moi/demandes')
  const enCours = (demandes.donnees ?? []).filter((d) => ['EN_ATTENTE', 'EN_ATTENTE_SUPERVISEUR'].includes(d.statut))

  return (
    <>
      <div className="entete-page">
        <div>
          <h1>{t('Bonjour {nom}', { nom: session.nom_affiche })}</h1>
          <p className="sous-titre">{t('Vos comptes et vos opérations en cours.')}</p>
        </div>
        <div className="carte-actions">
          <Link className="bouton" to="/client/demande">{t('Dépôt / retrait')}</Link>
          <Link className="bouton bouton-secondaire" to="/client/virement">{t('Virement')}</Link>
        </div>
      </div>
      <Alerte type="succes">{state?.message && t(state.message)}</Alerte>
      <Alerte type="erreur">{erreur(comptes.erreur)}</Alerte>
      {comptes.chargement && <Chargement />}

      <div className="grille">
        {(comptes.donnees ?? []).map((compte) => (
          <Link key={compte.numero} to={`/client/comptes/${compte.numero}`} className="compte">
            <div className="compte-type">
              <span>{t(compte.libelle)}</span>
              {compte.statut !== 'ACTIF' && <Badge statut={compte.statut} />}
            </div>
            <div className="compte-numero code">{compte.numero}</div>
            <div className="compte-solde">
              <Montant valeur={compte.solde} devise={compte.devise} />
            </div>
            <div className="compte-dispo">
              {t('Disponible')} : <Montant valeur={compte.solde_disponible} devise={compte.devise} />
            </div>
          </Link>
        ))}
      </div>

      <Carte titre={t('Bordereaux en attente')} actions={<Link to="/client/demandes">{t('Tout voir')}</Link>}>
        <Tableau
          cle="numero_bordereau"
          lignes={enCours}
          vide={t('Aucun bordereau en attente.')}
          colonnes={[
            { cle: 'numero_bordereau', titre: t('Numéro'), rendu: (d) => <span className="code numero-bordereau">{d.numero_bordereau}</span> },
            { cle: 'type', titre: t('Opération'), rendu: (d) => t(d.type === 'DEPOT' ? 'Dépôt' : 'Retrait') },
            { cle: 'montant', titre: t('Montant'), droite: true, rendu: (d) => <Montant valeur={d.montant} devise={d.devise} /> },
            { cle: 'date_expiration', titre: t('Valable jusqu’au'), rendu: (d) => date(d.date_expiration) },
            { cle: 'statut', titre: t('Statut'), rendu: (d) => <Badge statut={d.statut} /> },
          ]}
        />
      </Carte>
    </>
  )
}
