# fonctionnel
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal

CENTIME = Decimal("0.01")


def arrondir(montant: Decimal) -> Decimal:
    return Decimal(montant).quantize(CENTIME, rounding=ROUND_HALF_UP)


def borner(valeur: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return max(minimum, min(valeur, maximum))


def frais_proportionnels(montant: Decimal, taux: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return arrondir(borner(montant * taux, minimum, maximum))


def frais_virement_courant(montant: Decimal) -> Decimal:
    return frais_proportionnels(montant, Decimal("0.005"), Decimal("50"), Decimal("1000"))


def frais_virement_devise(montant: Decimal) -> Decimal:
    return frais_proportionnels(montant, Decimal("0.01"), Decimal("1"), Decimal("20"))


def convertir(montant: Decimal, source: str, cible: str, taux_vers_dzd: Mapping[str, Decimal]) -> Decimal:
    """Convertit un montant d'une devise à une autre en passant par le dinar.

    `taux_vers_dzd` donne la valeur d'une unité de chaque devise en DZD,
    ex. {"DZD": 1, "EUR": 150, "USD": 135}.
    """
    if source == cible:
        return arrondir(montant)
    en_dzd = Decimal(montant) * Decimal(taux_vers_dzd[source])
    return arrondir(en_dzd / Decimal(taux_vers_dzd[cible]))


def interets_mensuels(solde: Decimal, taux_annuel: Decimal) -> Decimal:
    if solde <= 0:
        return Decimal("0.00")
    return arrondir(Decimal(solde) * Decimal(taux_annuel) / 12)
