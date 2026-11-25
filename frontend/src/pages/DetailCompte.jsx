import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, ouvrirPdf } from '../api/client.js'
import { useSession } from '../auth/Session.jsx'
import { Alerte, Badge, Carte, Chargement, FlecheRetour, Indicateur, Montant, Tableau } from '../components/Interface.jsx'
import { useDonnees } from '../hooks/useDonnees.js'
import { LANGUES, useLangue } from '../i18n/Langue.jsx'
import { depuisCentimes } from '../utils/montants.js'
import { LIBELLES_TYPES, filtrerParPeriode, filtrerParType, parMois, rechercher, resume, versLignes } from '../utils/stats.js'

const FILTRES_VIDES = { type: '', debut: '', fin: '', texte: '' }

export default function DetailCompte() {
  const { numero } = useParams()
  const { session } = useSession()
  const { t, langue, erreur, montant, jour } = useLangue()
  const compte = useDonnees(`/api/comptes/${numero}`)
  const historique = useDonnees(`/api/comptes/${numero}/transactions`)
  const statsServeur = useDonnees(`/api/comptes/${numero}/statistiques`)
  const [filtres, setFiltres] = useState(FILTRES_VIDES)
  const [message, setMessage] = useState(null)

  const operations = useMemo(() => {
    const toutes = historique.donnees ?? []
    return rechercher(filtrerParType(filtrerParPeriode(toutes, filtres.debut, filtres.fin), filtres.type), filtres.texte)
  }, [historique.donnees, filtres])
  const lignes = useMemo(() => versLignes(operations, langue, LANGUES[langue].locale), [operations, langue])
  const totaux = useMemo(() => resume(operations), [operations])
  const graphique = useMemo(() => parMois(operations), [operations])

  const changerFiltre = (evenement) => setFiltres((f) => ({ ...f, [evenement.target.name]: evenement.target.value }))

  if (compte.chargement) return <Chargement />
  if (!compte.donnees) return <Alerte type="erreur">{erreur(compte.erreur)}</Alerte>
  const c = compte.donnees
  const devise = c.devise
  const retour = session.role === 'CLIENT' ? '/client' : `/agent/clients/${c.client_id}`
  const parametres = new URLSearchParams()
  if (filtres.debut) parametres.set('debut', filtres.debut)
  if (filtres.fin) parametres.set('fin', filtres.fin)
  const enMontant = (centimes) => montant(depuisCentimes(centimes), devise)

  const executer = async (action, succes) => {
    setMessage(null)
    try {
      await action()
      setMessage({ type: 'succes', texte: succes })
      await compte.recharger()
    } catch (e) {
      setMessage({ type: 'erreur', texte: erreur(e) })
    }
  }
  const changerStatut = (statut, succes) =>
    executer(() => api(`/api/comptes/${numero}/statut`, { methode: 'PATCH', corps: { statut } }), t(succes))
  const modifierDecouvert = () => {
    const valeur = window.prompt(t('Nouveau découvert autorisé (DA) :'), c.decouvert_autorise)
    if (valeur === null) return
    executer(() => api(`/api/comptes/${numero}/decouvert`, { methode: 'PATCH', corps: { decouvert_autorise: valeur } }), t('Découvert modifié.'))
  }

  return (
    <>
      <p><Link to={retour}><FlecheRetour /></Link></p>
      <div className="entete-page">
        <div>
          <h1>{t(c.libelle)} <Badge statut={c.statut} /></h1>
          <p className="sous-titre">
            <span className="code">{c.numero}</span> · {c.titulaire} · {t('ouvert le {date}', { date: jour(c.date_ouverture) })}
          </p>
        </div>
        <div className="carte-actions">
          {session.role === 'CLIENT' && c.statut === 'ACTIF' && (
            <Link className="bouton" to={`/client/demande?compte=${c.numero}`}>{t('Dépôt / retrait')}</Link>
          )}
          <button className="bouton bouton-secondaire" onClick={() => ouvrirPdf(`/api/comptes/${numero}/releve.pdf?${parametres}`)}>
            {t('Relevé PDF')}
          </button>
        </div>
      </div>
      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>

      <div className="indicateurs">
        <Indicateur titre={t('Solde')} valeur={montant(c.solde, devise)} />
        <Indicateur titre={t('Disponible')} valeur={montant(c.solde_disponible, devise)}
          detail={Number(c.montant_bloque) > 0 ? t('{montant} réservés', { montant: montant(c.montant_bloque, devise) }) : null} />
        {(Number(c.decouvert_autorise) > 0 || (c.decouvert_autorise !== null && session.role === 'SUPERVISEUR')) && <Indicateur titre={t('Découvert autorisé')} valeur={montant(c.decouvert_autorise, devise)} />}
        {c.taux_interet && <Indicateur titre={t("Taux d'intérêt")} valeur={t('{taux} % / an', { taux: (Number(c.taux_interet) * 100).toFixed(2) })} />}
        {c.plafond_retrait_jour && <Indicateur titre={t('Plafond de retrait')} valeur={montant(c.plafond_retrait_jour, devise)} detail={t('par jour')} />}
      </div>

      {session.role === 'SUPERVISEUR' && (
        <Carte titre={t('Actions du superviseur')}>
          <div className="carte-actions">
            {c.statut === 'ACTIF' && <button className="bouton bouton-rouge" onClick={() => changerStatut('BLOQUE', 'Compte bloqué.')}>{t('Bloquer le compte')}</button>}
            {c.statut === 'BLOQUE' && <button className="bouton bouton-secondaire" onClick={() => changerStatut('ACTIF', 'Compte réactivé.')}>{t('Réactiver')}</button>}
            {c.statut !== 'CLOTURE' && <button className="bouton bouton-rouge" onClick={() => changerStatut('CLOTURE', 'Compte clôturé.')}>{t('Clôturer')}</button>}
            {c.type_compte === 'COURANT' && <button className="bouton bouton-secondaire" onClick={modifierDecouvert}>{t('Modifier le découvert')}</button>}
          </div>
        </Carte>
      )}

      <Carte titre={t('Historique des opérations')}>
        <div className="filtres">
          <div className="champ">
            <label htmlFor="type">{t('Type')}</label>
            <select id="type" name="type" value={filtres.type} onChange={changerFiltre}>
              <option value="">{t('Tous')}</option>
              {Object.entries(LIBELLES_TYPES).map(([valeur, libelle]) => <option key={valeur} value={valeur}>{t(libelle)}</option>)}
            </select>
          </div>
          <div className="champ">
            <label htmlFor="debut">{t('Du')}</label>
            <input id="debut" type="date" name="debut" value={filtres.debut} onChange={changerFiltre} />
          </div>
          <div className="champ">
            <label htmlFor="fin">{t('Au')}</label>
            <input id="fin" type="date" name="fin" value={filtres.fin} onChange={changerFiltre} />
          </div>
          <div className="champ champ-large">
            <label htmlFor="texte">{t('Rechercher')}</label>
            <input id="texte" name="texte" placeholder={t('Référence, libellé, compte…')} value={filtres.texte} onChange={changerFiltre} />
          </div>
          <button className="bouton bouton-secondaire" onClick={() => setFiltres(FILTRES_VIDES)}>{t('Effacer')}</button>
        </div>

        <div className="indicateurs">
          <Indicateur titre={t('Opérations')} valeur={totaux.nombre} />
          <Indicateur titre={t('Total des dépôts')} valeur={enMontant(totaux.depots)} ton="credit" />
          <Indicateur titre={t('Total des retraits')} valeur={enMontant(totaux.retraits)} ton="debit" />
          <Indicateur titre={t('Variation nette')} valeur={enMontant(totaux.variation)}
            ton={totaux.variation >= 0 ? 'credit' : 'debit'} detail={t('crédits − débits')} />
        </div>

        {historique.chargement ? <Chargement /> : (
          <Tableau
            cle="reference"
            lignes={lignes}
            vide={t('Aucune opération pour ces filtres.')}
            colonnes={[
              { cle: 'dateAffichee', titre: t('Date') },
              { cle: 'typeLibelle', titre: t('Type'), rendu: (l) => t(l.typeLibelle) },
              { cle: 'libelle', titre: t('Libellé') },
              { cle: 'montantAffiche', titre: t('Montant'), droite: true, rendu: (l) => <span className={`montant ${l.sens}`}>{l.montantAffiche}</span> },
              { cle: 'solde_apres', titre: t('Solde après'), droite: true, rendu: (l) => <Montant valeur={l.solde_apres} devise={devise} /> },
              { cle: 'reference', titre: t('Reçu'), rendu: (l) => (
                <button className="bouton bouton-secondaire bouton-petit" title={l.reference} onClick={() => ouvrirPdf(`/api/transactions/${l.reference}/recu.pdf`)}>PDF</button>
              ) },
            ]}
          />
        )}
      </Carte>

      <div className="grille-2">
        <Carte titre={t('Crédits et débits par mois')}>
          {graphique.length ? (
            <div className="graphique" dir="ltr">
              <ResponsiveContainer>
                <BarChart data={graphique}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--trait)" />
                  <XAxis dataKey="mois" />
                  <YAxis width={80} tickFormatter={(v) => v.toLocaleString(LANGUES[langue].locale)} />
                  <Tooltip formatter={(v) => montant(v, devise)} />
                  <Legend />
                  <Bar dataKey="credits" name={t('Crédits')} fill="var(--credit)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="debits" name={t('Débits')} fill="var(--debit)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="vide">{t('Pas encore de données.')}</p>}
        </Carte>
        <Carte titre={t('Totaux calculés par le serveur (SQL)')}>
          <p className="sous-titre serre">
            <code className="code">SELECT type, COUNT(*), SUM(montant) … GROUP BY type</code> — {t('12 derniers mois')}
          </p>
          <Tableau
            cle="type"
            lignes={statsServeur.donnees?.par_type_sql ?? []}
            colonnes={[
              { cle: 'type', titre: t('Type'), rendu: (l) => t(LIBELLES_TYPES[l.type] ?? l.type) },
              { cle: 'nombre', titre: t('Nombre'), droite: true },
              { cle: 'total', titre: t('Total'), droite: true, rendu: (l) => <Montant valeur={l.total} devise={devise} /> },
            ]}
          />
        </Carte>
      </div>
    </>
  )
}
