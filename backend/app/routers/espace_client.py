from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Utilisateur
from app.errors import ErreurBancaire
from app.pdf import documents
from app.routers.convertir import client_sortie, compte_sortie, demande_sortie, reponse_pdf, verifier_acces_compte
from app.schemas import (
    ClientSortie,
    CompteSortie,
    CoordonneesEntree,
    DemandeEntree,
    DemandeSortie,
    VirementEntree,
    VirementSortie,
)
from app.security.dependances import client_connecte
from app.services.banque import Banque

routeur = APIRouter(prefix="/api/moi", tags=["Espace client"])


@routeur.get("/profil", response_model=ClientSortie)
def profil(utilisateur: Utilisateur = Depends(client_connecte)):
    return client_sortie(utilisateur.client)


@routeur.put("/profil", response_model=ClientSortie)
def modifier_coordonnees(
    entree: CoordonneesEntree, utilisateur: Utilisateur = Depends(client_connecte), db: Session = Depends(get_db)
):
    client = Banque(db).modifierClient(utilisateur.client, entree.model_dump(), utilisateur)
    return client_sortie(client)


@routeur.get("/comptes", response_model=list[CompteSortie])
def mes_comptes(utilisateur: Utilisateur = Depends(client_connecte), db: Session = Depends(get_db)):
    Banque(db).expirerDemandes()  # l'argent des bordereaux périmés redevient disponible
    return [compte_sortie(c) for c in utilisateur.client.comptes]


@routeur.post("/demandes", response_model=DemandeSortie, status_code=201)
def creer_demande(entree: DemandeEntree, utilisateur: Utilisateur = Depends(client_connecte), db: Session = Depends(get_db)):
    """Crée une demande de dépôt ou de retrait ; le bordereau PDF est ensuite téléchargeable."""
    banque = Banque(db)
    compte = banque.trouverCompte(entree.numero_compte)
    verifier_acces_compte(utilisateur, compte)
    return demande_sortie(banque.creerDemande(compte, entree.type, entree.montant, utilisateur))


@routeur.get("/demandes", response_model=list[DemandeSortie])
def mes_demandes(utilisateur: Utilisateur = Depends(client_connecte), db: Session = Depends(get_db)):
    banque = Banque(db)
    banque.expirerDemandes()
    demandes = [d for compte in utilisateur.client.comptes for d in compte.demandes]
    return [demande_sortie(d) for d in sorted(demandes, key=lambda d: d.date_creation, reverse=True)]


def _ma_demande(numero: str, utilisateur: Utilisateur, banque: Banque):
    demande = banque.trouverDemande(numero.strip().upper())
    if demande.compte.client_id != utilisateur.client_id:
        raise ErreurBancaire("BORDEREAU_INTROUVABLE")
    return demande


@routeur.get("/demandes/{numero}/bordereau.pdf")
def telecharger_bordereau(numero: str, utilisateur: Utilisateur = Depends(client_connecte), db: Session = Depends(get_db)):
    demande = _ma_demande(numero, utilisateur, Banque(db))
    contenu = documents.bordereau(demande, demande.compte, utilisateur.client)
    return reponse_pdf(contenu, f"bordereau-{demande.numero_bordereau}.pdf")


@routeur.delete("/demandes/{numero}", response_model=DemandeSortie)
def annuler_demande(numero: str, utilisateur: Utilisateur = Depends(client_connecte), db: Session = Depends(get_db)):
    banque = Banque(db)
    return demande_sortie(banque.annulerDemande(_ma_demande(numero, utilisateur, banque), utilisateur))


@routeur.post("/virements", response_model=VirementSortie, status_code=201)
def virement(entree: VirementEntree, utilisateur: Utilisateur = Depends(client_connecte), db: Session = Depends(get_db)):
    banque = Banque(db)
    source = banque.trouverCompte(entree.compte_source)
    verifier_acces_compte(utilisateur, source)
    destination = banque.trouverCompte(entree.compte_destination)
    resultat = banque.virement(source, destination, entree.montant, utilisateur)
    return VirementSortie(**resultat, message="Virement effectué.")
