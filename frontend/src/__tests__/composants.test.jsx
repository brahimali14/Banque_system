import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FournisseurSession } from '../auth/Session.jsx'
import { Badge, Tableau } from '../components/Interface.jsx'
import { FournisseurLangue, SelecteurLangue } from '../i18n/Langue.jsx'
import Guichet from '../pages/agent/Guichet.jsx'

function rendre(element, langue = 'fr') {
  sessionStorage.setItem(
    'bankservices.session',
    JSON.stringify({ jeton: 'x', role: 'AGENT', login: 'agent', nom_affiche: 'Agent', doit_changer_mdp: false }),
  )
  return render(
    <MemoryRouter>
      <FournisseurLangue langue={langue}>
        <FournisseurSession>{element}</FournisseurSession>
      </FournisseurLangue>
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.restoreAllMocks()
  sessionStorage.clear()
  localStorage.clear()
})

describe('Tableau (déclaratif)', () => {
  it('construit les lignes à partir de la description des colonnes', () => {
    rendre(
      <Tableau
        lignes={[{ id: 1, nom: 'Amine' }, { id: 2, nom: 'Sara' }]}
        colonnes={[{ cle: 'nom', titre: 'Nom' }, { cle: 'id', titre: 'N°', rendu: (l) => `#${l.id}` }]}
      />,
    )
    expect(screen.getAllByRole('row')).toHaveLength(3)
    expect(screen.getByText('#2')).toBeInTheDocument()
  })

  it('affiche le message vide traduit', () => {
    rendre(<Tableau lignes={[]} colonnes={[]} />, 'en')
    expect(screen.getByText('No data.')).toBeInTheDocument()
  })
})

describe('langues', () => {
  it('traduit les statuts', () => {
    rendre(<Badge statut="EN_ATTENTE" />, 'ar')
    expect(screen.getByText('قيد الانتظار')).toBeInTheDocument()
  })

  it("passe la page de droite à gauche en arabe", async () => {
    rendre(<SelecteurLangue />)
    await userEvent.selectOptions(screen.getByRole('combobox'), 'ar')
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('ar')
    await userEvent.selectOptions(screen.getByRole('combobox'), 'en')
    expect(document.documentElement.dir).toBe('ltr')
  })
})

describe('Guichet (événementiel)', () => {
  it('vérifie le numéro à chaque frappe et ne cherche que s’il est valide', async () => {
    const appel = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ code: 'BORDEREAU_INTROUVABLE', message: 'Aucun bordereau ne correspond à ce numéro.' }), { status: 404 }),
    )
    rendre(<Guichet />)
    const champ = screen.getByLabelText('Numéro du bordereau')
    const bouton = screen.getByRole('button', { name: 'Rechercher' })

    await userEvent.type(champ, 'RET-K7M2-9QXA')
    expect(screen.getByText('Numéro mal saisi : vérifiez les caractères.')).toBeInTheDocument()
    expect(bouton).toBeDisabled()

    await userEvent.clear(champ)
    await userEvent.type(champ, 'ret k7m2 9qxb{Enter}')
    expect(appel).toHaveBeenCalledWith('/api/agent/bordereaux/RET-K7M2-9QXB', expect.anything())
    expect(await screen.findByText('Aucun bordereau ne correspond à ce numéro.')).toBeInTheDocument()
  })

  it('affiche le détail et exige la vérification de l’identité avant d’accepter', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          demande: {
            numero_bordereau: 'RET-K7M2-9QXB', type: 'RETRAIT', montant: '12000.00', devise: 'DZD', statut: 'EN_ATTENTE',
            numero_compte: 'BS-CC-000001', date_creation: '2026-11-11T10:00:00', date_expiration: '2026-11-12T10:00:00',
            motif_refus: null, reference_transaction: null,
          },
          client_nom: 'Amine BENALI', client_numero_identite: '109870000000000001', client_telephone: '0550 12 34 56',
          compte_libelle: 'Compte courant', solde: '50000.00', solde_disponible: '38000.00',
          solde_apres_operation: '38000.00', depasse_seuil: false, minutes_restantes: 1260,
        }),
        { status: 200 },
      ),
    )
    rendre(<Guichet />, 'en')
    await userEvent.type(screen.getByLabelText('Slip number'), 'RET-K7M2-9QXB{Enter}')
    expect(await screen.findByText('Amine BENALI')).toBeInTheDocument()
    expect(screen.getByText('12,000.00 DZD')).toBeInTheDocument()
    expect(screen.getByText(/Not expired \(21 h 0 min left\)/)).toBeInTheDocument()

    const accepter = screen.getByRole('button', { name: /Accept/ })
    expect(accepter).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox'))
    expect(accepter).toBeEnabled()
  })
})
