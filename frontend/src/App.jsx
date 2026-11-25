import { Navigate, Route, Routes } from 'react-router-dom'
import { ACCUEIL_PAR_ROLE, useSession } from './auth/Session.jsx'
import Layout from './components/Layout.jsx'
import ChangerMotDePasse from './pages/ChangerMotDePasse.jsx'
import Connexion from './pages/Connexion.jsx'
import DetailCompte from './pages/DetailCompte.jsx'
import Audit from './pages/admin/Audit.jsx'
import Parametres from './pages/admin/Parametres.jsx'
import Utilisateurs from './pages/admin/Utilisateurs.jsx'
import Clients from './pages/agent/Clients.jsx'
import FicheClient from './pages/agent/FicheClient.jsx'
import Guichet from './pages/agent/Guichet.jsx'
import OperationDirecte from './pages/agent/OperationDirecte.jsx'
import MesComptes from './pages/client/MesComptes.jsx'
import MesDemandes from './pages/client/MesDemandes.jsx'
import NouvelleDemande from './pages/client/NouvelleDemande.jsx'
import Profil from './pages/client/Profil.jsx'
import Virement from './pages/client/Virement.jsx'
import Approbations from './pages/superviseur/Approbations.jsx'
import TableauDeBord from './pages/superviseur/TableauDeBord.jsx'

const GUICHET = ['AGENT', 'SUPERVISEUR']
const PERSONNEL = ['AGENT', 'SUPERVISEUR', 'ADMIN']

function Protege({ roles, children }) {
  const { session } = useSession()
  if (!session) return <Navigate to="/connexion" replace />
  if (session.doit_changer_mdp) return <Navigate to="/changer-mot-de-passe" replace />
  if (roles && !roles.includes(session.role)) return <Navigate to={ACCUEIL_PAR_ROLE[session.role]} replace />
  return children
}

function Accueil() {
  const { session } = useSession()
  if (!session) return <Navigate to="/connexion" replace />
  if (session.doit_changer_mdp) return <Navigate to="/changer-mot-de-passe" replace />
  return <Navigate to={ACCUEIL_PAR_ROLE[session.role]} replace />
}

const page = (roles, element) => <Protege roles={roles}>{element}</Protege>

export default function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<Connexion />} />
      <Route path="/changer-mot-de-passe" element={<ChangerMotDePasse />} />
      <Route element={<Protege><Layout /></Protege>}>
        <Route path="/client" element={page(['CLIENT'], <MesComptes />)} />
        <Route path="/client/comptes/:numero" element={page(['CLIENT'], <DetailCompte />)} />
        <Route path="/client/demande" element={page(['CLIENT'], <NouvelleDemande />)} />
        <Route path="/client/demandes" element={page(['CLIENT'], <MesDemandes />)} />
        <Route path="/client/virement" element={page(['CLIENT'], <Virement />)} />
        <Route path="/client/profil" element={page(['CLIENT'], <Profil />)} />

        <Route path="/agent/guichet" element={page(GUICHET, <Guichet />)} />
        <Route path="/agent/operation" element={page(GUICHET, <OperationDirecte />)} />
        <Route path="/agent/clients" element={page(PERSONNEL, <Clients />)} />
        <Route path="/agent/clients/:id" element={page(PERSONNEL, <FicheClient />)} />
        <Route path="/agent/comptes/:numero" element={page(PERSONNEL, <DetailCompte />)} />

        <Route path="/superviseur" element={page(['SUPERVISEUR'], <TableauDeBord />)} />
        <Route path="/superviseur/approbations" element={page(['SUPERVISEUR'], <Approbations />)} />

        <Route path="/admin" element={page(['ADMIN'], <Parametres />)} />
        <Route path="/admin/utilisateurs" element={page(['ADMIN'], <Utilisateurs />)} />
        <Route path="/admin/audit" element={page(['ADMIN'], <Audit />)} />
      </Route>
      <Route path="*" element={<Accueil />} />
    </Routes>
  )
}
