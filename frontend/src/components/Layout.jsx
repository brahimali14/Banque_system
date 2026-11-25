import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useSession } from '../auth/Session.jsx'
import { SelecteurLangue, useLangue } from '../i18n/Langue.jsx'

const MENUS = {
  CLIENT: [
    ['/client', 'Mes comptes', true],
    ['/client/demande', 'Dépôt / retrait'],
    ['/client/demandes', 'Mes bordereaux'],
    ['/client/virement', 'Virement'],
    ['/client/profil', 'Mon profil'],
  ],
  AGENT: [
    ['/agent/guichet', 'Guichet'],
    ['/agent/clients', 'Clients'],
    ['/agent/operation', 'Opération directe'],
  ],
  SUPERVISEUR: [
    ['/superviseur', 'Tableau de bord', true],
    ['/superviseur/approbations', 'À approuver'],
    ['/agent/guichet', 'Guichet'],
    ['/agent/clients', 'Clients'],
    ['/agent/operation', 'Opération directe'],
  ],
  ADMIN: [
    ['/admin', 'Paramètres', true],
    ['/admin/utilisateurs', 'Utilisateurs'],
    ['/admin/audit', "Journal d'audit"],
    ['/agent/clients', 'Clients'],
  ],
}

export const ROLES = { CLIENT: 'Client', AGENT: 'Agent', SUPERVISEUR: 'Superviseur', ADMIN: 'Administrateur' }

export default function Layout() {
  const { session, deconnecter } = useSession()
  const { t } = useLangue()
  const naviguer = useNavigate()

  const quitter = () => {
    deconnecter()
    naviguer('/connexion')
  }

  return (
    <div className="application">
      <header className="barre">
        <div className="barre-interieur">
          <span className="logo">
            <img src="/favicon.svg" alt="" width="28" height="28" /> BankServices
          </span>
          <nav className="menu">
            {MENUS[session.role].map(([chemin, libelle, exact]) => (
              <NavLink key={chemin} to={chemin} end={exact}>
                {t(libelle)}
              </NavLink>
            ))}
          </nav>
          <div className="utilisateur">
            <SelecteurLangue />
            <span>
              {session.nom_affiche}
              <small>{t(ROLES[session.role])}</small>
            </span>
            <button type="button" className="bouton bouton-discret" onClick={quitter}>
              {t('Déconnexion')}
            </button>
          </div>
        </div>
      </header>
      <main className="contenu">
        <Outlet />
      </main>
      <footer className="pied">{t('Simulateur pédagogique — données fictives')}</footer>
    </div>
  )
}
