# procedural
from decimal import Decimal, InvalidOperation

from app.domain.comptes import CompteBancaire, ContexteRetrait
from app.domain.enums import TypeOperation
from app.domain.operations import Transaction
from app.errors import ErreurBancaire
from app.rules.imperative import calculer_nouveau_solde

CENTIME = Decimal("0.01")


def verifierMontant(montant) -> Decimal:
    try:
        valeur = Decimal(str(montant))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ErreurBancaire("MONTANT_INVALIDE") from exc
    if not valeur.is_finite() or valeur <= 0:
        raise ErreurBancaire("MONTANT_INVALIDE")
    if valeur != valeur.quantize(CENTIME):
        raise ErreurBancaire("PRECISION_INVALIDE")
    return valeur.quantize(CENTIME)


def calculerSolde(transactions, solde_initial: Decimal = Decimal("0.00")) -> Decimal:
    solde = solde_initial
    for transaction in transactions:
        solde = calculer_nouveau_solde(solde, transaction.montant, transaction.type)
    return solde


def effectuerDepot(
    compte: CompteBancaire,
    montant,
    libelle: str = "Dépôt d'espèces",
    agent_id: int | None = None,
) -> Transaction:
    valeur = verifierMontant(montant)
    return compte.crediter(valeur, TypeOperation.DEPOT, libelle, agent_id)


def effectuerRetrait(
    compte: CompteBancaire,
    montant,
    contexte: ContexteRetrait | None = None,
    libelle: str = "Retrait d'espèces",
    agent_id: int | None = None,
) -> Transaction:
    valeur = verifierMontant(montant)
    compte.verifierActif()
    compte.verifierRetrait(valeur, contexte)
    return compte.debiter(valeur, TypeOperation.RETRAIT, libelle, agent_id)


def calculerTotalOperations(transactions, type_operation: TypeOperation | None = None) -> Decimal:
    total = Decimal("0.00")
    for transaction in transactions:
        if type_operation is None or transaction.type == type_operation:
            total = total + transaction.montant
    return total
