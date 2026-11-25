# fonctionnel
import copy
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace as Op

import pytest

from app.domain.enums import TypeOperation as T
from app.functional import stats
from app.functional.calculs import convertir, frais_virement_courant, interets_mensuels
from app.functional.lettres import montant_en_lettres
from app.functional.numeros import ALPHABET, composer_numero, est_numero_valide, normaliser

D = Decimal
OPERATIONS = (
    Op(reference="TRX-1", type=T.DEPOT, montant=D("1000"), date=datetime(2026, 9, 1)),
    Op(reference="TRX-2", type=T.RETRAIT, montant=D("200"), date=datetime(2026, 10, 1)),
    Op(reference="TRX-3", type=T.DEPOT, montant=D("300"), date=datetime(2026, 11, 1)),
    Op(reference="TRX-4", type=T.FRAIS, montant=D("50"), date=datetime(2026, 11, 2)),
)
TAUX = {"DZD": D("1"), "EUR": D("150"), "USD": D("135")}


@pytest.mark.parametrize(
    "montant, frais", [(D("1000"), D("50.00")), (D("40000"), D("200.00")), (D("1000000"), D("1000.00"))]
)
def test_frais_virement_courant_bornes(montant, frais):
    assert frais_virement_courant(montant) == frais


def test_conversion_devises():
    assert convertir(D("300"), "EUR", "DZD", TAUX) == D("45000.00")
    assert convertir(D("13500"), "DZD", "USD", TAUX) == D("100.00")
    assert convertir(D("100"), "EUR", "USD", TAUX) == D("111.11")


def test_interets_nuls_si_solde_negatif():
    assert interets_mensuels(D("-50"), D("0.025")) == D("0.00")


def test_filter_map_reduce():
    depots = stats.filtrer_par_type(OPERATIONS, T.DEPOT)
    assert [op.reference for op in depots] == ["TRX-1", "TRX-3"]
    assert stats.total(depots) == D("1300")
    assert stats.totaux_par_type(OPERATIONS) == {"DEPOT": D("1300"), "RETRAIT": D("200"), "FRAIS": D("50")}
    lignes = stats.vers_affichage(OPERATIONS[:2])
    assert lignes[0]["montant_affiche"] == "1 000,00 DA"
    assert lignes[1]["montant_affiche"] == "-200,00 DA"
    assert lignes[1]["sens"] == "debit"


def test_filtrer_par_periode():
    novembre = stats.filtrer_par_periode(OPERATIONS, datetime(2026, 11, 1), None)
    assert [op.reference for op in novembre] == ["TRX-3", "TRX-4"]


def test_resume():
    resume = stats.resume(OPERATIONS)
    assert resume["total_depots"] == D("1300")
    assert resume["total_retraits"] == D("200")
    assert resume["variation_nette"] == D("1050")


def test_les_fonctions_ne_modifient_pas_leurs_entrees():
    avant = copy.deepcopy(OPERATIONS)
    stats.resume(OPERATIONS)
    stats.vers_affichage(OPERATIONS)
    stats.totaux_par_type(OPERATIONS)
    assert OPERATIONS == avant


def test_numero_compose_et_valide():
    numero = composer_numero("RET", "K7M29QX")
    assert numero[:13] == numero and len(numero) == 13
    assert numero.startswith("RET-K7M2-9QX")
    assert est_numero_valide(numero)


def test_saisie_tolerante():
    numero = composer_numero("DEP", "H4TW82N")
    saisie = numero.lower().replace("-", " ")
    assert normaliser(saisie) == numero
    assert est_numero_valide(saisie)


def test_toute_faute_de_frappe_sur_un_caractere_est_detectee():
    numero = composer_numero("RET", "K7M29QX")
    caracteres = numero.replace("-", "")[3:]
    for position in range(len(caracteres)):
        for remplacant in ALPHABET:
            if remplacant == caracteres[position]:
                continue
            faux = caracteres[:position] + remplacant + caracteres[position + 1 :]
            assert not est_numero_valide("RET" + faux), faux


@pytest.mark.parametrize("saisie", ["", "RET-1234", "ABC-K7M2-9QXB", "RET-K7M2-9QX0"])
def test_numeros_mal_formes(saisie):
    assert not est_numero_valide(saisie)


@pytest.mark.parametrize(
    "montant, devise, texte",
    [
        (D("12000"), "DZD", "douze mille dinars algériens"),
        (D("1"), "DZD", "un dinar algérien"),
        (D("71"), "EUR", "soixante et onze euros"),
        (D("80"), "EUR", "quatre-vingts euros"),
        (D("200000"), "DZD", "deux cent mille dinars algériens"),
        (D("1000000"), "EUR", "un million d'euros"),
        (D("2500.50"), "USD", "deux mille cinq cents dollars américains et cinquante cents"),
        (D("99"), "DZD", "quatre-vingt-dix-neuf dinars algériens"),
    ],
)
def test_montant_en_lettres(montant, devise, texte):
    assert montant_en_lettres(montant, devise) == texte
