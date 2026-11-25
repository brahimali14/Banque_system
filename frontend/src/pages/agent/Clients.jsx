import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import Identifiants from '../../components/Identifiants.jsx'
import { Alerte, Carte, Chargement, Tableau } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'

const VIDE = { prenom: '', nom: '', numero_identite: '', telephone: '', email: '', adresse: '' }

export function ChampsClient({ valeurs, surChangement, t }) {
  const champ = (nom, libelle, options = {}) => (
    <div className="champ">
      <label htmlFor={nom}>{t(libelle)}</label>
      <input id={nom} name={nom} value={valeurs[nom] ?? ''} onChange={surChangement} {...options} />
    </div>
  )
  return (
    <>
      {champ('prenom', 'Prénom', { required: true })}
      {champ('nom', 'Nom', { required: true })}
      {champ('numero_identite', "N° d'identité", { required: true, minLength: 6 })}
      {champ('telephone', 'Téléphone', { required: true, minLength: 6 })}
      {champ('email', 'E-mail', { type: 'email' })}
      {champ('adresse', 'Adresse')}
    </>
  )
}

export default function Clients() {
  const { t, erreur: traduireErreur, jour } = useLangue()
  const naviguer = useNavigate()
  const [recherche, setRecherche] = useState('')
  const [requete, setRequete] = useState('')
  const [formulaire, setFormulaire] = useState(null)
  const [cree, setCree] = useState(null)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    const minuteur = setTimeout(() => setRequete(recherche.trim()), 300)
    return () => clearTimeout(minuteur)
  }, [recherche])
  const clients = useDonnees(`/api/clients${requete ? `?q=${encodeURIComponent(requete)}` : ''}`)

  const changer = (e) => setFormulaire((f) => ({ ...f, [e.target.name]: e.target.value }))
  const ajouter = async (evenement) => {
    evenement.preventDefault()
    setErreur(null)
    try {
      const reponse = await api('/api/clients', { methode: 'POST', corps: formulaire })
      setCree(reponse)
      setFormulaire(null)
      clients.recharger()
    } catch (e) {
      setErreur(e)
    }
  }

  return (
    <>
      <div className="entete-page">
        <div>
          <h1>{t('Clients')}</h1>
          <p className="sous-titre">{t('Rechercher, consulter et ajouter des clients.')}</p>
        </div>
        {!formulaire && (
          <button className="bouton" onClick={() => { setFormulaire(VIDE); setCree(null) }}>
            {t('Nouveau client')}
          </button>
        )}
      </div>

      {cree && (
        <Carte titre={t('Client {nom} créé', { nom: cree.client.nom_complet })}
          actions={<Link className="bouton bouton-secondaire" to={`/agent/clients/${cree.client.id}`}>{t('Ouvrir un compte')}</Link>}>
          <Identifiants clientId={cree.client.id} identifiants={cree.identifiants} />
        </Carte>
      )}

      {formulaire && (
        <Carte titre={t('Nouveau client')}>
          <Alerte type="erreur">{traduireErreur(erreur)}</Alerte>
          <p className="sous-titre">{t("Le système génère automatiquement le nom d'utilisateur et un mot de passe temporaire.")}</p>
          <form className="formulaire large" onSubmit={ajouter}>
            <ChampsClient valeurs={formulaire} surChangement={changer} t={t} />
            <div className="carte-actions aligne-bas">
              <button className="bouton">{t('Créer le client')}</button>
              <button type="button" className="bouton bouton-secondaire" onClick={() => setFormulaire(null)}>{t('Annuler')}</button>
            </div>
          </form>
        </Carte>
      )}

      <Carte>
        <div className="filtres">
          <div className="champ champ-large">
            <label htmlFor="recherche">{t('Rechercher')}</label>
            <input id="recherche" placeholder={t('Nom, prénom, téléphone, identité ou n° de compte')}
              value={recherche} onChange={(e) => setRecherche(e.target.value)} />
          </div>
        </div>
        {clients.chargement && !clients.donnees ? <Chargement /> : (
          <Tableau
            lignes={clients.donnees}
            vide={t('Aucun client trouvé.')}
            surClicLigne={(c) => naviguer(`/agent/clients/${c.id}`)}
            colonnes={[
              { cle: 'nom_complet', titre: t('Client'), rendu: (c) => <strong>{c.nom_complet}</strong> },
              { cle: 'numero_identite', titre: t("N° d'identité"), rendu: (c) => <span className="code">{c.numero_identite}</span> },
              { cle: 'telephone', titre: t('Téléphone'), rendu: (c) => <span className="code">{c.telephone}</span> },
              { cle: 'nombre_comptes', titre: t('Comptes'), droite: true },
              { cle: 'date_creation', titre: t('Client depuis'), rendu: (c) => jour(c.date_creation) },
            ]}
          />
        )}
      </Carte>
    </>
  )
}
