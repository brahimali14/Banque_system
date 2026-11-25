# poo
from decimal import Decimal

import pytest

from app.domain import CompteBancaire, CompteCourant, CompteDevise, CompteEpargne, ContexteRetrait
from app.domain.enums import StatutCompte, TypeOperation
from app.errors import ErreurBancaire

D = Decimal


def test_heritage():
    for classe in (CompteCourant, CompteEpargne, CompteDevise):
        assert issubclass(classe, CompteBancaire)


def test_compte_bancaire_est_abstrait():
    with pytest.raises(Exception):
        CompteBancaire(numero="X", client_id=1)


def test_valeurs_par_defaut_selon_le_type(courant, epargne, devise_eur):
    assert courant.decouvert_autorise == D("20000.00")
    assert epargne.taux_interet == D("0.025")
    assert devise_eur.devise == "EUR"


def test_devise_interdite():
    with pytest.raises(ErreurBancaire) as erreur:
        CompteDevise(numero="X", client_id=1, devise="DZD")
    assert erreur.value.code == "DEVISE_INVALIDE"


def test_polymorphisme_meme_retrait_trois_resultats(courant, epargne, devise_eur):
    """60 000 sur un solde de 50 000 : seul le compte courant (découvert) accepte."""
    courant.solde = epargne.solde = devise_eur.solde = D("50000")
    devise_eur.plafond_retrait_jour = D("100000")
    resultats = {type(c).__name__: c.peutRetirer(D("60000")) for c in (courant, epargne, devise_eur)}
    assert resultats == {"CompteCourant": True, "CompteEpargne": False, "CompteDevise": False}


def test_courant_refuse_au_dela_du_decouvert(courant):
    assert courant.motifRefusRetrait(D("70000.01"), ContexteRetrait()) == "SOLDE_INSUFFISANT"


def test_courant_plafond_journalier(courant):
    courant.solde = D("500000")
    contexte = ContexteRetrait(retire_aujourdhui=D("190000"))
    assert courant.motifRefusRetrait(D("20000"), contexte) == "PLAFOND_DEPASSE"
    assert courant.motifRefusRetrait(D("10000"), contexte) is None

    assert courant.motifRefusRetrait(D("300000"), ContexteRetrait(retrait_especes=False)) is None


def test_epargne_solde_minimum(epargne):
    assert epargne.motifRefusRetrait(D("9000"), ContexteRetrait()) is None
    assert epargne.motifRefusRetrait(D("9000.01"), ContexteRetrait()) == "SOLDE_MINIMUM_EPARGNE"


def test_epargne_deux_retraits_par_mois(epargne):
    assert epargne.motifRefusRetrait(D("100"), ContexteRetrait(retraits_ce_mois=2)) == "LIMITE_RETRAITS_EPARGNE"


def test_epargne_virement_seulement_vers_le_meme_client(epargne, courant):
    autre = CompteCourant(numero="BS-CC-000099", client_id=2)
    assert epargne.motifRefusVirementVers(courant) is None
    assert epargne.motifRefusVirementVers(autre) == "VIREMENT_EPARGNE_INTERDIT"


def test_frais_polymorphes(courant, epargne, devise_eur):
    assert courant.calculerFrais(TypeOperation.VIREMENT_EMIS, D("100000")) == D("500.00")
    assert epargne.calculerFrais(TypeOperation.VIREMENT_EMIS, D("100000")) == D("0.00")
    assert devise_eur.calculerFrais(TypeOperation.VIREMENT_EMIS, D("100")) == D("1.00")


def test_interets_epargne(epargne):
    assert epargne.calculerInteretsMensuels() == D("20.83")  # 10 000 × 2,5 % / 12


def test_bloquer_et_liberer(courant):
    courant.bloquer(D("12000"))
    assert courant.solde == D("50000")
    assert courant.soldeDisponible() == D("38000")
    courant.liberer(D("12000"))
    assert courant.soldeDisponible() == D("50000")


def test_compte_bloque_refuse_les_operations(courant):
    courant.statut = StatutCompte.BLOQUE
    with pytest.raises(ErreurBancaire) as erreur:
        courant.crediter(D("10"), TypeOperation.DEPOT, "test")
    assert erreur.value.code == "COMPTE_BLOQUE"
