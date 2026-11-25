from decimal import Decimal

import pytest

from app.domain import CompteBancaire
from app.errors import ErreurBancaire

D = Decimal


@pytest.fixture
def comptes(banque, client_amine, agent):
    courant = client_amine.comptes[0]
    eur = banque.ouvrirCompte(client_amine, "DEVISE", "EUR", agent)
    banque.operationGuichet(eur, "DEPOT", D("500"), agent)
    return courant, eur


def test_virement_avec_frais_et_conversion(banque, comptes, client_amine):
    courant, eur = comptes
    resultat = banque.virement(eur, courant, D("300"), client_amine.utilisateur)
    assert resultat["frais"] == D("3.00")  # 1 %
    assert resultat["montant_credite"] == D("45000.00")  # 300 € × 150
    assert eur.solde == D("197.00")
    assert courant.solde == D("95000.00")
    types = [t.type for t in eur.transactions[-2:]]
    assert types == ["VIREMENT_EMIS", "FRAIS"]
    assert courant.transactions[-1].type == "VIREMENT_RECU"


def test_virement_vers_le_meme_compte_refuse(banque, comptes, client_amine):
    courant, _ = comptes
    with pytest.raises(ErreurBancaire) as erreur:
        banque.virement(courant, courant, D("10"), client_amine.utilisateur)
    assert erreur.value.code == "COMPTES_IDENTIQUES"


def test_virement_atomique_rollback_si_le_credit_echoue(banque, comptes, client_amine, monkeypatch):
    """Si le crédit plante, le débit déjà fait est annulé : ni débit ni crédit."""
    courant, eur = comptes
    solde_eur, solde_courant = eur.solde, courant.solde
    nb_transactions = len(eur.transactions) + len(courant.transactions)

    def credit_en_panne(*args, **kwargs):
        raise RuntimeError("panne pendant le crédit")

    monkeypatch.setattr(CompteBancaire, "crediter", credit_en_panne)
    with pytest.raises(RuntimeError):
        banque.virement(eur, courant, D("100"), client_amine.utilisateur)
    monkeypatch.undo()

    banque.db.expire_all()
    assert eur.solde == solde_eur
    assert courant.solde == solde_courant
    assert len(eur.transactions) + len(courant.transactions) == nb_transactions


def test_virement_epargne_vers_un_autre_client_interdit(banque, client_amine, agent):
    epargne = banque.ouvrirCompte(client_amine, "EPARGNE", None, agent)
    banque.operationGuichet(epargne, "DEPOT", D("20000"), agent)
    autre, _, _ = banque.ajouterClient(
        {"numero_identite": "109870000000000099", "nom": "Hamidi", "prenom": "Lina", "telephone": "0552456789"}, agent
    )
    compte_autre = banque.ouvrirCompte(autre, "COURANT", None, agent)
    with pytest.raises(ErreurBancaire) as erreur:
        banque.virement(epargne, compte_autre, D("100"), client_amine.utilisateur)
    assert erreur.value.code == "VIREMENT_EPARGNE_INTERDIT"

    resultat = banque.virement(epargne, client_amine.comptes[0], D("100"), client_amine.utilisateur)
    assert resultat["frais"] == D("0.00")


def test_virement_par_l_api(http, comptes):
    from tests.conftest import entete

    courant, eur = comptes
    reponse = http.post(
        "/api/moi/virements",
        json={"compte_source": courant.numero, "compte_destination": eur.numero, "montant": "15000"},
        headers=entete(http, "amine.benali"),
    )
    assert reponse.status_code == 201, reponse.text
    assert D(reponse.json()["montant_credite"]) == D("100.00")
    assert D(reponse.json()["frais"]) == D("75.00")
