import { useState } from 'react'
import { api } from '../../api/client.js'
import Identifiants from '../../components/Identifiants.jsx'
import { Alerte, Badge, Carte, Chargement, Tableau } from '../../components/Interface.jsx'
import { ROLES } from '../../components/Layout.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'

export default function Utilisateurs() {
  const { t, erreur, date } = useLangue()
  const utilisateurs = useDonnees('/api/admin/utilisateurs')
  const [nouveau, setNouveau] = useState({ login: '', nom_affiche: '', role: 'AGENT' })
  const [identifiants, setIdentifiants] = useState(null)
  const [message, setMessage] = useState(null)
  const [role, setRole] = useState('PERSONNEL')

  const executer = async (action) => {
    setMessage(null)
    try {
      await action()
      utilisateurs.recharger()
    } catch (e) {
      setMessage({ type: 'erreur', texte: erreur(e) })
    }
  }

  const creer = (evenement) => {
    evenement.preventDefault()
    executer(async () => {
      setIdentifiants(await api('/api/admin/utilisateurs', { methode: 'POST', corps: nouveau }))
      setNouveau({ login: '', nom_affiche: '', role: 'AGENT' })
    })
  }

  const lignes = (utilisateurs.donnees ?? []).filter((u) => (role === 'PERSONNEL' ? u.role !== 'CLIENT' : role === 'TOUS' || u.role === role))

  return (
    <>
      <h1>{t('Utilisateurs')}</h1>
      <p className="sous-titre">{t('Comptes du personnel et accès des clients.')}</p>
      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>

      <Carte titre={t('Nouveau membre du personnel')}>
        <form className="filtres" onSubmit={creer}>
          <div className="champ">
            <label htmlFor="login">{t("Nom d'utilisateur")}</label>
            <input id="login" className="code" placeholder="prenom.nom" pattern="[a-zA-Z0-9._\-]+" required minLength={3}
              value={nouveau.login} onChange={(e) => setNouveau((n) => ({ ...n, login: e.target.value }))} />
          </div>
          <div className="champ">
            <label htmlFor="nom_affiche">{t('Nom complet')}</label>
            <input id="nom_affiche" required minLength={2} value={nouveau.nom_affiche}
              onChange={(e) => setNouveau((n) => ({ ...n, nom_affiche: e.target.value }))} />
          </div>
          <div className="champ">
            <label htmlFor="role">{t('Rôle')}</label>
            <select id="role" value={nouveau.role} onChange={(e) => setNouveau((n) => ({ ...n, role: e.target.value }))}>
              {['AGENT', 'SUPERVISEUR', 'ADMIN'].map((r) => <option key={r} value={r}>{t(ROLES[r])}</option>)}
            </select>
          </div>
          <button className="bouton">{t('Créer')}</button>
        </form>
        {identifiants && <Identifiants identifiants={identifiants} />}
      </Carte>

      <Carte>
        <div className="filtres">
          <div className="champ">
            <label htmlFor="filtre-role">{t('Afficher')}</label>
            <select id="filtre-role" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="PERSONNEL">{t('Personnel')}</option>
              <option value="CLIENT">{t('Clients')}</option>
              <option value="TOUS">{t('Tous')}</option>
            </select>
          </div>
        </div>
        {utilisateurs.chargement ? <Chargement /> : (
          <Tableau
            lignes={lignes}
            colonnes={[
              { cle: 'login', titre: t("Nom d'utilisateur"), rendu: (u) => <span className="code">{u.login}</span> },
              { cle: 'nom_affiche', titre: t('Nom complet') },
              { cle: 'role', titre: t('Rôle'), rendu: (u) => t(ROLES[u.role]) },
              { cle: 'statut_acces', titre: t('État'), rendu: (u) => <Badge statut={u.statut_acces} /> },
              { cle: 'derniere_connexion', titre: t('Dernière connexion'), rendu: (u) => date(u.derniere_connexion) },
              { cle: 'actions', titre: '', rendu: (u) => (
                <div className="carte-actions">
                  {u.role !== 'CLIENT' && (
                    <button className="bouton bouton-secondaire bouton-petit" onClick={() => executer(async () => {
                      setIdentifiants(await api(`/api/admin/utilisateurs/${u.id}/reinitialiser`, { methode: 'POST' }))
                    })}>{t('Réinitialiser')}</button>
                  )}
                  <button className={`bouton bouton-petit ${u.statut_acces === 'DESACTIVE' ? 'bouton-secondaire' : 'bouton-rouge'}`}
                    onClick={() => executer(() => api(`/api/admin/utilisateurs/${u.id}/statut`, { methode: 'PATCH', corps: { actif: u.statut_acces === 'DESACTIVE' } }))}>
                    {t(u.statut_acces === 'DESACTIVE' ? 'Activer' : 'Désactiver')}
                  </button>
                </div>
              ) },
            ]}
          />
        )}
      </Carte>
    </>
  )
}
