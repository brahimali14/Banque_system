# imperatif et procedural
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace as Op

import pytest

from app.domain.enums import TypeOperation as T
from app.errors import ErreurBancaire
from app.rules.imperative import (
    calculer_nouveau_solde,
    nombre_retraits_du_mois,
    simuler_retrait,
    total_retire_le,
    totaux_par_boucle,
)
from app.services.procedures import (
    calculerSolde,
    calculerTotalOperations,
    effectuerDepot,
    effectuerRetrait,
    verifierMontant,
)

D = Decimal
OPERATIONS = [
    Op(type=T.DEPOT, montant=D("50000"), date=datetime(2026, 11, 2, 9)),
    Op(type=T.RETRAIT, montant=D("12000"), date=datetime(2026, 11, 10, 10)),
    Op(type=T.RETRAIT, montant=D("3000"), date=datetime(2026, 11, 10, 15)),
    Op(type=T.FRAIS, montant=D("150"), date=datetime(2026, 10, 31, 23)),
]


def test_exemple_du_sujet_50000_moins_12000():
    resultat = simuler_retrait(D("50000"), D("12000"))
    assert resultat["accepte"] is True
    assert resultat["nouveau_solde"] == D("38000")
    assert "38000" in resultat["message"]


@pytest.mark.parametrize("montant", [D("0"), D("-5")])
def test_simuler_retrait_refuse_montant_non_positif(montant):
    assert simuler_retrait(D("50000"), montant)["accepte"] is False


def test_simuler_retrait_refuse_si_solde_insuffisant():
    resultat = simuler_retrait(D("10000"), D("12000"))
    assert resultat["accepte"] is False
    assert resultat["nouveau_solde"] == D("10000")


def test_simuler_retrait_utilise_le_decouvert():
    assert simuler_retrait(D("10000"), D("12000"), decouvert_autorise=D("5000"))["accepte"] is True


def test_calculer_nouveau_solde():
    assert calculer_nouveau_solde(D("100"), D("30"), T.DEPOT) == D("130")
    assert calculer_nouveau_solde(D("100"), D("30"), T.RETRAIT) == D("70")


def test_totaux_par_boucle():
    totaux = totaux_par_boucle(OPERATIONS)
    assert totaux == {"nombre": 4, "total_depots": D("50000"), "total_retraits": D("15000"), "total_frais": D("150")}


def test_retraits_du_jour_et_du_mois():
    assert total_retire_le(OPERATIONS, datetime(2026, 11, 10).date()) == D("15000")
    assert nombre_retraits_du_mois(OPERATIONS, 2026, 11) == 2
    assert nombre_retraits_du_mois(OPERATIONS, 2026, 10) == 0


@pytest.mark.parametrize("saisie, attendu", [("100", D("100.00")), (D("12.5"), D("12.50")), (7, D("7.00"))])
def test_verifier_montant_valide(saisie, attendu):
    assert verifierMontant(saisie) == attendu


@pytest.mark.parametrize("saisie", ["0", "-1", "abc", None, "NaN", "Infinity"])
def test_verifier_montant_invalide(saisie):
    with pytest.raises(ErreurBancaire) as erreur:
        verifierMontant(saisie)
    assert erreur.value.code == "MONTANT_INVALIDE"


def test_verifier_montant_refuse_plus_de_deux_decimales():
    with pytest.raises(ErreurBancaire) as erreur:
        verifierMontant("10.005")
    assert erreur.value.code == "PRECISION_INVALIDE"


def test_calculer_solde_rejoue_l_historique():
    assert calculerSolde(OPERATIONS) == D("34850")
    assert calculerSolde([], D("100")) == D("100")


def test_calculer_total_operations():
    assert calculerTotalOperations(OPERATIONS) == D("65150")
    assert calculerTotalOperations(OPERATIONS, T.RETRAIT) == D("15000")


def test_effectuer_depot(courant):
    transaction = effectuerDepot(courant, "1500.50")
    assert courant.solde == D("51500.50")
    assert transaction.type == T.DEPOT
    assert transaction.solde_apres == D("51500.50")
    assert transaction.reference.startswith("TRX-")
    assert courant.transactions == [transaction]  # historique (contrainte 7)


def test_effectuer_depot_refuse_montant_nul(courant):
    with pytest.raises(ErreurBancaire):
        effectuerDepot(courant, 0)
    assert courant.solde == D("50000.00")
    assert courant.transactions == []


def test_effectuer_retrait(courant):
    effectuerRetrait(courant, D("12000"))
    assert courant.solde == D("38000.00")


def test_effectuer_retrait_refuse(courant):
    with pytest.raises(ErreurBancaire) as erreur:
        effectuerRetrait(courant, D("80000"))
    assert erreur.value.code == "SOLDE_INSUFFISANT"
    assert courant.solde == D("50000.00")
