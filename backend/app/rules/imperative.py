# imperatif
from datetime import date
from decimal import Decimal

from app.domain.enums import TypeOperation


def calculer_nouveau_solde(solde: Decimal, montant: Decimal, type_operation: TypeOperation) -> Decimal:
    nouveau_solde = solde
    if type_operation in (TypeOperation.DEPOT, TypeOperation.VIREMENT_RECU, TypeOperation.INTERETS):
        nouveau_solde = nouveau_solde + montant
    elif type_operation in (TypeOperation.RETRAIT, TypeOperation.VIREMENT_EMIS, TypeOperation.FRAIS):
        nouveau_solde = nouveau_solde - montant
    else:
        raise ValueError(f"Type d'opération inconnu : {type_operation}")
    return nouveau_solde


def simuler_retrait(solde: Decimal, montant: Decimal, decouvert_autorise: Decimal = Decimal("0")) -> dict:
    accepte = False
    nouveau_solde = solde
    message = ""

    if montant <= 0:
        message = "Refusé : le montant doit être strictement positif."
    elif montant > solde + decouvert_autorise:
        message = f"Refusé : solde insuffisant ({solde} DA disponibles)."
    else:
        accepte = True
        nouveau_solde = solde - montant
        message = f"Retrait de {montant} DA accepté. Nouveau solde : {nouveau_solde} DA."

    return {"accepte": accepte, "nouveau_solde": nouveau_solde, "message": message}


def totaux_par_boucle(transactions) -> dict:
    total_depots = Decimal("0.00")
    total_retraits = Decimal("0.00")
    total_frais = Decimal("0.00")
    nombre = 0

    for transaction in transactions:
        nombre = nombre + 1
        if transaction.type == TypeOperation.DEPOT:
            total_depots = total_depots + transaction.montant
        elif transaction.type == TypeOperation.RETRAIT:
            total_retraits = total_retraits + transaction.montant
        elif transaction.type == TypeOperation.FRAIS:
            total_frais = total_frais + transaction.montant

    return {
        "nombre": nombre,
        "total_depots": total_depots,
        "total_retraits": total_retraits,
        "total_frais": total_frais,
    }


def total_retire_le(transactions, jour: date) -> Decimal:
    total = Decimal("0.00")
    for transaction in transactions:
        if transaction.type == TypeOperation.RETRAIT and transaction.date.date() == jour:
            total = total + transaction.montant
    return total


def nombre_retraits_du_mois(transactions, annee: int, mois: int) -> int:
    compteur = 0
    for transaction in transactions:
        if (
            transaction.type == TypeOperation.RETRAIT
            and transaction.date.year == annee
            and transaction.date.month == mois
        ):
            compteur = compteur + 1
    return compteur
