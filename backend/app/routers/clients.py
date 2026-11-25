from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Utilisateur
from app.domain.enums import StatutAcces
from app.errors import ErreurBancaire
from app.pdf import documents
from app.routers.convertir import (
    client_resume,
    client_sortie,
    compte_sortie,
    identifiants_sortie,
    reponse_pdf,
)
from app.schemas import (
    ClientCreeSortie,
    ClientEntree,
    ClientModification,
    ClientResume,
    ClientSortie,
    CompteSortie,
    FicheIdentifiantsEntree,
    IdentifiantsSortie,
    OuvertureCompteEntree,
)
from app.security.dependances import personnel
from app.services.banque import Banque

routeur = APIRouter(prefix="/api/clients", tags=["Clients"])


@routeur.get("", response_model=list[ClientResume])
def lister_clients(q: str | None = None, agent: Utilisateur = Depends(personnel), db: Session = Depends(get_db)):
    """Liste des clients ; `q` recherche dans le nom, le prénom, le téléphone, l'identité ou un n° de compte."""
    return [client_resume(c) for c in Banque(db).rechercherClients(q)]


@routeur.post("", response_model=ClientCreeSortie, status_code=201)
def ajouter_client(entree: ClientEntree, agent: Utilisateur = Depends(personnel), db: Session = Depends(get_db)):
    """Crée le client et génère son nom d'utilisateur + mot de passe temporaire (affiché une seule fois)."""
    client, utilisateur, mot_de_passe = Banque(db).ajouterClient(entree.model_dump(), agent)
    return ClientCreeSortie(client=client_sortie(client), identifiants=identifiants_sortie(utilisateur, mot_de_passe))


@routeur.get("/{client_id}", response_model=ClientSortie)
def consulter_client(client_id: int, agent: Utilisateur = Depends(personnel), db: Session = Depends(get_db)):
    return client_sortie(Banque(db).trouverClient(client_id))


@routeur.put("/{client_id}", response_model=ClientSortie)
def modifier_client(
    client_id: int, entree: ClientModification, agent: Utilisateur = Depends(personnel), db: Session = Depends(get_db)
):
    banque = Banque(db)
    client = banque.modifierClient(banque.trouverClient(client_id), entree.model_dump(), agent)
    return client_sortie(client)


@routeur.post("/{client_id}/comptes", response_model=CompteSortie, status_code=201)
def ouvrir_compte(
    client_id: int, entree: OuvertureCompteEntree, agent: Utilisateur = Depends(personnel), db: Session = Depends(get_db)
):
    banque = Banque(db)
    compte = banque.ouvrirCompte(banque.trouverClient(client_id), entree.type_compte, entree.devise, agent)
    return compte_sortie(compte)


@routeur.post("/{client_id}/reinitialiser-acces", response_model=IdentifiantsSortie)
def reinitialiser_acces(client_id: int, agent: Utilisateur = Depends(personnel), db: Session = Depends(get_db)):
    """Nouveau mot de passe temporaire (client verrouillé, mot de passe oublié ou expiré)."""
    banque = Banque(db)
    utilisateur, mot_de_passe = banque.reinitialiserAcces(banque.trouverClient(client_id), agent)
    return identifiants_sortie(utilisateur, mot_de_passe)


@routeur.post("/{client_id}/fiche-identifiants.pdf")
def fiche_identifiants(
    client_id: int,
    entree: FicheIdentifiantsEntree,
    agent: Utilisateur = Depends(personnel),
    db: Session = Depends(get_db),
):
    """PDF à imprimer et remettre au client.

    Le mot de passe n'est stocké que haché : l'agent renvoie celui qu'il vient de recevoir,
    et on vérifie qu'il correspond bien au mot de passe temporaire en cours.
    """
    client = Banque(db).trouverClient(client_id)
    utilisateur = client.utilisateur
    if (
        utilisateur is None
        or utilisateur.statut_acces != StatutAcces.TEMPORAIRE
        or not utilisateur.verifierMotDePasse(entree.mot_de_passe_temporaire)
    ):
        raise ErreurBancaire("IDENTIFIANTS_INCORRECTS", "Ce mot de passe temporaire n'est plus valable.")
    contenu = documents.fiche_identifiants(
        client, utilisateur.login, entree.mot_de_passe_temporaire, utilisateur.expiration_mdp_temporaire
    )
    return reponse_pdf(contenu, f"identifiants-{utilisateur.login}.pdf")
