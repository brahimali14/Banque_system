from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Utilisateur
from app.domain.enums import StatutDemande, TypeOperation
from app.horloge import maintenant
from app.routers.convertir import decimaux_en_texte, demande_sortie, transaction_sortie
from app.schemas import (
    BordereauAgentSortie,
    DemandeSortie,
    OperationGuichetEntree,
    RefusEntree,
    ResultatValidation,
    TransactionSortie,
)
from app.security.dependances import guichet, superviseur
from app.services import statistiques
from app.services.banque import Banque

routeur_agent = APIRouter(prefix="/api/agent", tags=["Guichet (agent)"])
routeur_superviseur = APIRouter(prefix="/api/superviseur", tags=["Superviseur"])


def _vue_agent(banque: Banque, demande) -> BordereauAgentSortie:
    compte = demande.compte
    if demande.type == TypeOperation.DEPOT:
        solde_apres = compte.solde + demande.montant
    else:
        solde_apres = compte.solde - demande.montant
    restant = demande.date_expiration - maintenant()
    return BordereauAgentSortie(
        demande=demande_sortie(demande),
        client_nom=compte.client.nom_complet,
        client_numero_identite=compte.client.numero_identite,
        client_telephone=compte.client.telephone,
        compte_libelle=compte.LIBELLE,
        solde=compte.solde,
        solde_disponible=compte.soldeDisponible(),
        solde_apres_operation=solde_apres,
        depasse_seuil=banque.enDinars(demande.montant, compte.devise) > banque.seuilSuperviseur(),
        minutes_restantes=max(0, int(restant.total_seconds() // 60)),
    )


@routeur_agent.get("/bordereaux/{numero}", response_model=BordereauAgentSortie)
def rechercher_bordereau(numero: str, agent: Utilisateur = Depends(guichet), db: Session = Depends(get_db)):
    """L'agent tape le numéro (ex. RET-K7M2-9QXB ; minuscules et espaces acceptés)."""
    banque = Banque(db)
    return _vue_agent(banque, banque.rechercherBordereau(numero, agent))


@routeur_agent.post("/bordereaux/{numero}/valider", response_model=ResultatValidation)
def valider_bordereau(numero: str, agent: Utilisateur = Depends(guichet), db: Session = Depends(get_db)):
    demande = Banque(db).validerDemande(numero, agent)
    if demande.statut == StatutDemande.EN_ATTENTE_SUPERVISEUR:
        return ResultatValidation(
            demande=demande_sortie(demande),
            transaction=None,
            message="Montant supérieur au seuil : la demande est transmise au superviseur.",
        )
    return ResultatValidation(
        demande=demande_sortie(demande),
        transaction=transaction_sortie(demande.transaction),
        message="Opération validée.",
    )


@routeur_agent.post("/bordereaux/{numero}/refuser", response_model=DemandeSortie)
def refuser_bordereau(numero: str, entree: RefusEntree, agent: Utilisateur = Depends(guichet), db: Session = Depends(get_db)):
    return demande_sortie(Banque(db).refuserDemande(numero, agent, entree.motif))


@routeur_agent.post("/operations", response_model=TransactionSortie, status_code=201)
def operation_guichet(entree: OperationGuichetEntree, agent: Utilisateur = Depends(guichet), db: Session = Depends(get_db)):
    """Dépôt ou retrait direct pour un client venu sans bordereau."""
    banque = Banque(db)
    compte = banque.trouverCompte(entree.numero_compte)
    return transaction_sortie(banque.operationGuichet(compte, entree.type, entree.montant, agent))


@routeur_superviseur.get("/demandes", response_model=list[DemandeSortie])
def demandes_a_approuver(chef: Utilisateur = Depends(superviseur), db: Session = Depends(get_db)):
    return [demande_sortie(d) for d in Banque(db).demandesASuperviser()]


@routeur_superviseur.get("/tableau-de-bord")
def tableau_de_bord(chef: Utilisateur = Depends(superviseur), db: Session = Depends(get_db)):
    return decimaux_en_texte(statistiques.tableau_de_bord_agence(db, maintenant()))
