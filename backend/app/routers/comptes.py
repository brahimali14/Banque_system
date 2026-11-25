from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Utilisateur
from app.domain.enums import TypeOperation
from app.functional import stats
from app.horloge import maintenant
from app.pdf import documents
from app.routers.convertir import (
    compte_sortie,
    decimaux_en_texte,
    reponse_pdf,
    transaction_sortie,
    verifier_acces_compte,
)
from app.schemas import (
    CompteSortie,
    DecouvertEntree,
    StatutCompteEntree,
    TransactionSortie,
    VirementEntree,
    VirementSortie,
)
from app.security.dependances import personnel, superviseur, utilisateur_connecte
from app.services import statistiques
from app.services.banque import Banque

routeur = APIRouter(prefix="/api", tags=["Comptes et opérations"])


def _periode(debut: datetime | None, fin: datetime | None) -> tuple[datetime, datetime]:
    fin = fin or maintenant()
    if fin.time() == time(0, 0):
        fin = datetime.combine(fin.date(), time(23, 59, 59))
    return debut or fin - timedelta(days=365), fin


@routeur.get("/comptes/{numero}", response_model=CompteSortie)
def consulter_compte(numero: str, utilisateur: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    banque = Banque(db)
    banque.expirerDemandes()
    compte = banque.trouverCompte(numero)
    verifier_acces_compte(utilisateur, compte)
    return compte_sortie(compte)


@routeur.get("/comptes/{numero}/transactions", response_model=list[TransactionSortie])
def historique(
    numero: str,
    type: TypeOperation | None = None,
    debut: datetime | None = None,
    fin: datetime | None = None,
    utilisateur: Utilisateur = Depends(utilisateur_connecte),
    db: Session = Depends(get_db),
):
    """Historique d'un compte, filtrable par type et par période (filter() du paradigme fonctionnel)."""
    compte = Banque(db).trouverCompte(numero)
    verifier_acces_compte(utilisateur, compte)
    operations = stats.filtrer_par_periode(compte.transactions, debut, fin and _periode(None, fin)[1])
    if type:
        operations = stats.filtrer_par_type(operations, type)
    return [transaction_sortie(t) for t in reversed(operations)]


@routeur.get("/comptes/{numero}/statistiques")
def statistiques_compte(
    numero: str,
    debut: datetime | None = None,
    fin: datetime | None = None,
    utilisateur: Utilisateur = Depends(utilisateur_connecte),
    db: Session = Depends(get_db),
):
    """Deux façons d'obtenir des totaux : fonctions pures (map/filter/reduce) et SQL déclaratif."""
    compte = Banque(db).trouverCompte(numero)
    verifier_acces_compte(utilisateur, compte)
    debut, fin = _periode(debut, fin)
    operations = stats.filtrer_par_periode(compte.transactions, debut, fin)
    return decimaux_en_texte(
        {
            "compte": compte.numero,
            "devise": compte.devise,
            "periode": {"debut": debut, "fin": fin},
            "resume": stats.resume(operations),
            "par_type_sql": statistiques.totaux_par_type(db, compte.id, debut, fin),
            "evolution_mensuelle_sql": statistiques.evolution_mensuelle(db, compte.id),
        }
    )


@routeur.get("/comptes/{numero}/releve.pdf")
def releve(
    numero: str,
    debut: datetime | None = None,
    fin: datetime | None = None,
    utilisateur: Utilisateur = Depends(utilisateur_connecte),
    db: Session = Depends(get_db),
):
    compte = Banque(db).trouverCompte(numero)
    verifier_acces_compte(utilisateur, compte)
    debut, fin = _periode(debut, fin)
    operations = stats.filtrer_par_periode(compte.transactions, debut, fin)
    return reponse_pdf(documents.releve(compte, compte.client, operations, debut, fin), f"releve-{compte.numero}.pdf")


@routeur.patch("/comptes/{numero}/statut", response_model=CompteSortie)
def changer_statut(
    numero: str, entree: StatutCompteEntree, chef: Utilisateur = Depends(superviseur), db: Session = Depends(get_db)
):
    """ACTIF, BLOQUE ou CLOTURE (clôture seulement si solde nul et aucune demande en cours)."""
    banque = Banque(db)
    return compte_sortie(banque.changerStatutCompte(banque.trouverCompte(numero), entree.statut, chef))


@routeur.patch("/comptes/{numero}/decouvert", response_model=CompteSortie)
def modifier_decouvert(
    numero: str, entree: DecouvertEntree, chef: Utilisateur = Depends(superviseur), db: Session = Depends(get_db)
):
    banque = Banque(db)
    return compte_sortie(banque.modifierDecouvert(banque.trouverCompte(numero), entree.decouvert_autorise, chef))


@routeur.get("/transactions/{reference}", response_model=TransactionSortie)
def verifier_transaction(reference: str, utilisateur: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    """Vérifier l'authenticité d'un reçu grâce à son numéro."""
    transaction = Banque(db).trouverTransaction(reference)
    verifier_acces_compte(utilisateur, transaction.compte)
    return transaction_sortie(transaction)


@routeur.get("/transactions/{reference}/recu.pdf")
def recu(reference: str, utilisateur: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    transaction = Banque(db).trouverTransaction(reference)
    verifier_acces_compte(utilisateur, transaction.compte)
    agent = db.get(Utilisateur, transaction.agent_id) if transaction.agent_id else None
    contenu = documents.recu(transaction, transaction.compte, transaction.compte.client, agent.nom_affiche if agent else None)
    return reponse_pdf(contenu, f"recu-{transaction.reference}.pdf")


@routeur.post("/virements", response_model=VirementSortie, status_code=201)
def virement_par_agent(entree: VirementEntree, agent: Utilisateur = Depends(personnel), db: Session = Depends(get_db)):
    """Virement saisi par un agent pour le compte d'un client."""
    banque = Banque(db)
    resultat = banque.virement(
        banque.trouverCompte(entree.compte_source), banque.trouverCompte(entree.compte_destination), entree.montant, agent
    )
    return VirementSortie(**resultat, message="Virement effectué.")
