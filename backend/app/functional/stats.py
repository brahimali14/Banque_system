# fonctionnel
from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import Decimal
from functools import reduce

from app.domain.enums import CREDITS, DEBITS, TypeOperation

ZERO = Decimal("0.00")


def filtrer_par_type(operations: Iterable, *types: TypeOperation) -> tuple:
    return tuple(filter(lambda op: op.type in types, operations))


def filtrer_par_periode(operations: Iterable, debut: datetime | None, fin: datetime | None) -> tuple:
    return tuple(
        filter(
            lambda op: (debut is None or op.date >= debut) and (fin is None or op.date <= fin),
            operations,
        )
    )


def total(operations: Iterable) -> Decimal:
    return reduce(lambda acc, op: acc + op.montant, operations, ZERO)


def totaux_par_type(operations: Iterable) -> dict[str, Decimal]:
    return reduce(
        lambda acc, op: {**acc, str(op.type): acc.get(str(op.type), ZERO) + op.montant},
        operations,
        {},
    )


def montant_signe(op) -> Decimal:
    return op.montant if op.type in CREDITS else -op.montant


def formater_montant(montant: Decimal, devise: str = "DZD") -> str:
    symbole = {"DZD": "DA", "EUR": "€", "USD": "$"}.get(devise, devise)
    entier, decimales = f"{abs(montant):.2f}".split(".")
    groupes = []
    while entier:
        groupes.insert(0, entier[-3:])
        entier = entier[:-3]
    signe = "-" if montant < 0 else ""
    return f"{signe}{' '.join(groupes)},{decimales} {symbole}"


def vers_affichage(operations: Iterable, devise: str = "DZD") -> list[dict]:
    return list(
        map(
            lambda op: {
                "reference": op.reference,
                "date": op.date.strftime("%d/%m/%Y %H:%M"),
                "type": str(op.type),
                "sens": "credit" if op.type in CREDITS else "debit",
                "montant_affiche": formater_montant(montant_signe(op), devise),
            },
            operations,
        )
    )


def resume(operations: Sequence) -> dict:
    depots = total(filtrer_par_type(operations, TypeOperation.DEPOT))
    retraits = total(filtrer_par_type(operations, TypeOperation.RETRAIT))
    credits = total(filter(lambda op: op.type in CREDITS, operations))
    debits = total(filter(lambda op: op.type in DEBITS, operations))
    return {
        "nombre_operations": len(operations),
        "total_depots": depots,
        "total_retraits": retraits,
        "total_credits": credits,
        "total_debits": debits,
        "variation_nette": credits - debits,
        "par_type": totaux_par_type(operations),
    }
