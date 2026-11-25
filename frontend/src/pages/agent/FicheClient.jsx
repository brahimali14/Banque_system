import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api/client.js'
import Identifiants from '../../components/Identifiants.jsx'
import { Alerte, Badge, Carte, Chargement, FlecheRetour, Montant, Tableau } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'
import { ChampsClient } from './Clients.jsx'

export default function FicheClient() {
  const { id } = useParams()
  const naviguer = useNavigate()
  const { t, erreur: traduireErreur, jour, date } = useLangue()
  const fiche = useDonnees(`/api/clients/${id}`)
  const [edition, setEdition] = useState(null)
  const [ouverture, setOuverture] = useState({ type_compte: 'COURANT', devise: 'EUR' })
  const [identifiants, setIdentifiants] = useState(null)
  const [message, setMessage] = useState(null)

  if (fiche.chargement && !fiche.donnees) return <Chargement />
  if (!fiche.donnees) return <Alerte type="erreur">{traduireErreur(fiche.erreur)}</Alerte>
  const c = fiche.donnees

  const executer = async (action, succes) => {
    setMessage(null)
    try {
      await action()
      setMessage({ type: 'succes', texte: succes })
      fiche.recharger()
    } catch (e) {
      setMessage({ type: 'erreur', texte: traduireErreur(e) })
    }
  }

  const enregistrer = (evenement) => {
    evenement.preventDefault()
    executer(async () => {
      await api(`/api/clients/${id}`, { methode: 'PUT', corps: edition })
      setEdition(null)
    }, t('Informations enregistrées.'))
  }

  const ouvrirCompte = (evenement) => {
    evenement.preventDefault()
    const corps = ouverture.type_compte === 'DEVISE' ? ouverture : { type_compte: ouverture.type_compte }
    executer(() => api(`/api/clients/${id}/comptes`, { methode: 'POST', corps }), t('Compte ouvert.'))
  }

  const reinitialiser = () => {
    if (!window.confirm(t("Générer un nouveau mot de passe temporaire pour {nom} ?", { nom: c.nom_complet }))) return
    executer(async () => {
      setIdentifiants(await api(`/api/clients/${id}/reinitialiser-acces`, { methode: 'POST' }))
    }, t('Nouvel accès généré.'))
  }

  return (
    <>
      <p><Link to="/agent/clients"><FlecheRetour /></Link></p>
      <div className="entete-page">
        <div>
          <h1>{c.nom_complet}</h1>
          <p className="sous-titre">{t('Client depuis le {date}', { date: jour(c.date_creation) })}</p>
        </div>
      </div>
      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>

      <div className="grille-2">
        <Carte titre={t('Informations')} actions={!edition && (
          <button className="bouton bouton-secondaire bouton-petit" onClick={() => setEdition({ ...c })}>{t('Modifier')}</button>
        )}>
          {edition ? (
            <form className="formulaire" onSubmit={enregistrer}>
              <ChampsClient valeurs={edition} surChangement={(e) => setEdition((v) => ({ ...v, [e.target.name]: e.target.value }))} t={t} />
              <div className="carte-actions">
                <button className="bouton">{t('Enregistrer')}</button>
                <button type="button" className="bouton bouton-secondaire" onClick={() => setEdition(null)}>{t('Annuler')}</button>
              </div>
            </form>
          ) : (
            <dl className="detail-operation">
              <dt>{t("N° d'identité")}</dt><dd className="code">{c.numero_identite}</dd>
              <dt>{t('Téléphone')}</dt><dd className="code">{c.telephone}</dd>
              <dt>{t('E-mail')}</dt><dd>{c.email ?? '—'}</dd>
              <dt>{t('Adresse')}</dt><dd>{c.adresse ?? '—'}</dd>
            </dl>
          )}
        </Carte>

        <Carte titre={t('Accès en ligne')}>
          <dl className="detail-operation">
            <dt>{t("Nom d'utilisateur")}</dt><dd className="code">{c.login ?? '—'}</dd>
            <dt>{t('État')}</dt><dd>{c.statut_acces ? <Badge statut={c.statut_acces} /> : '—'}</dd>
          </dl>
          <button className="bouton bouton-secondaire" onClick={reinitialiser}>{t("Réinitialiser l'accès")}</button>
          {identifiants && <Identifiants clientId={c.id} identifiants={identifiants} />}
        </Carte>
      </div>

      <Carte titre={t('Comptes')}>
        <Tableau
          cle="numero"
          lignes={c.comptes}
          vide={t("Ce client n'a pas encore de compte.")}
          surClicLigne={(compte) => naviguer(`/agent/comptes/${compte.numero}`)}
          colonnes={[
            { cle: 'numero', titre: t('Numéro'), rendu: (x) => <span className="code">{x.numero}</span> },
            { cle: 'libelle', titre: t('Type'), rendu: (x) => t(x.libelle) },
            { cle: 'devise', titre: t('Devise') },
            { cle: 'solde', titre: t('Solde'), droite: true, rendu: (x) => <Montant valeur={x.solde} devise={x.devise} /> },
            { cle: 'solde_disponible', titre: t('Disponible'), droite: true, rendu: (x) => <Montant valeur={x.solde_disponible} devise={x.devise} /> },
            { cle: 'statut', titre: t('Statut'), rendu: (x) => <Badge statut={x.statut} /> },
            { cle: 'date_ouverture', titre: t('Ouvert le'), rendu: (x) => date(x.date_ouverture) },
          ]}
        />
        <form className="filtres espace-haut" onSubmit={ouvrirCompte}>
          <div className="champ">
            <label htmlFor="type_compte">{t('Nouveau compte')}</label>
            <select id="type_compte" value={ouverture.type_compte} onChange={(e) => setOuverture((o) => ({ ...o, type_compte: e.target.value }))}>
              <option value="COURANT">{t('Compte courant')}</option>
              <option value="EPARGNE">{t('Compte épargne')}</option>
              <option value="DEVISE">{t('Compte devise')}</option>
            </select>
          </div>
          {ouverture.type_compte === 'DEVISE' && (
            <div className="champ">
              <label htmlFor="devise">{t('Devise')}</label>
              <select id="devise" value={ouverture.devise} onChange={(e) => setOuverture((o) => ({ ...o, devise: e.target.value }))}>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
          )}
          <button className="bouton">{t('Ouvrir le compte')}</button>
        </form>
      </Carte>
    </>
  )
}
