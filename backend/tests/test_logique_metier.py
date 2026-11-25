"""Règles métier corrigées : pas d'argent sans solde, comptes clôturés, paramètres et tâches mensuelles."""
from datetime import timedelta
from decimal import Decimal

import pytest

from app import horloge
from app.domain.enums import TypeOperation
from app.errors import ErreurBancaire
from tests.conftest import MDP_TEST, entete

D = Decimal


@pytest.fixture
def client_sans_argent(banque, agent):
    """Nouveau client, compte courant ouvert, aucun dépôt (solde 0 DA)."""
    client, utilisateur, _ = banque.ajouterClient(
        {"numero_identite": "109870000000000077", "nom": "Brahim", "prenom": "Ali", "telephone": "0550999999"},
        agent,
    )
    utilisateur.definirMotDePasseDefinitif(MDP_TEST)
    banque.ouvrirCompte(client, "COURANT", None, agent)
    banque.db.commit()
    return client


def _code(erreur) -> str:
    return erreur.value.code


# --- Un retrait exige de l'argent disponible ----------------------------------------------

def test_client_sans_argent_ne_peut_pas_demander_un_retrait(http, client_sans_argent):
    compte = client_sans_argent.comptes[0].numero
    reponse = http.post(
        "/api/moi/demandes",
        json={"numero_compte": compte, "type": "RETRAIT", "montant": "12000"},
        headers=entete(http, client_sans_argent.utilisateur.login),
    )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "SOLDE_INSUFFISANT"


def test_agent_ne_peut_pas_faire_retirer_un_compte_vide(banque, client_sans_argent, agent):
    compte = client_sans_argent.comptes[0]
    with pytest.raises(ErreurBancaire) as erreur:
        banque.operationGuichet(compte, TypeOperation.RETRAIT, D("1000"), agent)
    assert _code(erreur) == "SOLDE_INSUFFISANT"
    assert compte.solde == D("0.00")


def test_virement_depuis_un_compte_vide_refuse(banque, client_sans_argent, client_amine):
    source = client_sans_argent.comptes[0]
    with pytest.raises(ErreurBancaire) as erreur:
        banque.virement(source, client_amine.comptes[0], D("500"), client_sans_argent.utilisateur)
    assert _code(erreur) == "SOLDE_INSUFFISANT"


def test_le_superviseur_peut_accorder_un_decouvert(banque, client_sans_argent, agent, chef):
    compte = client_sans_argent.comptes[0]
    banque.modifierDecouvert(compte, D("5000"), chef)
    banque.operationGuichet(compte, TypeOperation.RETRAIT, D("5000"), agent)
    assert compte.solde == D("-5000.00")
    with pytest.raises(ErreurBancaire):
        banque.operationGuichet(compte, TypeOperation.RETRAIT, D("0.01"), agent)


# --- Bordereaux périmés : l'argent réservé redevient disponible -----------------------------

def test_bordereau_perime_libere_l_argent(http, banque, client_amine, monkeypatch):
    compte = client_amine.comptes[0]
    login = client_amine.utilisateur.login
    reponse = http.post(
        "/api/moi/demandes",
        json={"numero_compte": compte.numero, "type": "RETRAIT", "montant": "40000"},
        headers=entete(http, login),
    )
    assert reponse.status_code == 201

    plus_tard = horloge.maintenant() + timedelta(hours=25)
    monkeypatch.setattr("app.services.banque.maintenant", lambda: plus_tard)
    comptes = http.get("/api/moi/comptes", headers=entete(http, login)).json()
    assert D(comptes[0]["solde_disponible"]) == D("50000")
    # et une nouvelle demande peut utiliser cet argent
    nouvelle = http.post(
        "/api/moi/demandes",
        json={"numero_compte": compte.numero, "type": "RETRAIT", "montant": "40000"},
        headers=entete(http, login),
    )
    assert nouvelle.status_code == 201, nouvelle.text


# --- Comptes clôturés et statuts ------------------------------------------------------------

def test_compte_cloture_ne_peut_pas_etre_rouvert(banque, client_sans_argent, chef):
    compte = client_sans_argent.comptes[0]
    banque.changerStatutCompte(compte, "CLOTURE", chef)
    for statut in ("ACTIF", "BLOQUE"):
        with pytest.raises(ErreurBancaire) as erreur:
            banque.changerStatutCompte(compte, statut, chef)
        assert _code(erreur) == "COMPTE_CLOTURE"
    with pytest.raises(ErreurBancaire) as erreur:
        banque.modifierDecouvert(compte, D("1000"), chef)
    assert _code(erreur) == "COMPTE_CLOTURE"


def test_statut_inconnu_donne_une_erreur_lisible(http, client_amine, chef):
    reponse = http.patch(
        f"/api/comptes/{client_amine.comptes[0].numero}/statut",
        json={"statut": "SUSPENDU"},
        headers=entete(http, chef.login),
    )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "STATUT_INVALIDE"


# --- Paramètres de l'administrateur -----------------------------------------------------------

@pytest.mark.parametrize(
    "cle, valeur",
    [
        ("seuil_superviseur_dzd", "abc"),
        ("seuil_superviseur_dzd", "-5"),
        ("seuil_superviseur_dzd", "0"),
        ("validite_bordereau_heures", "1.5"),
        ("validite_bordereau_heures", "0"),
        ("tentatives_max_connexion", "1"),
        ("validite_mdp_temporaire_jours", "NaN"),
    ],
)
def test_parametre_invalide_refuse(http, admin, cle, valeur):
    reponse = http.put(f"/api/admin/parametres/{cle}", json={"valeur": valeur}, headers=entete(http, admin.login))
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "PARAMETRE_INVALIDE"


def test_parametre_valide_normalise(banque, admin):
    banque.modifierParametre("validite_bordereau_heures", " 48 ", admin)
    assert banque.parametre("validite_bordereau_heures") == "48"


# --- Tâches mensuelles ------------------------------------------------------------------------

def test_interets_verses_une_seule_fois_par_mois(banque, admin, client_amine, agent):
    epargne = banque.ouvrirCompte(client_amine, "EPARGNE", None, agent)
    banque.operationGuichet(epargne, TypeOperation.DEPOT, D("120000"), agent)
    assert banque.verserInterets(admin) == 1
    solde = epargne.solde
    with pytest.raises(ErreurBancaire) as erreur:
        banque.verserInterets(admin)
    assert _code(erreur) == "TACHE_DEJA_EXECUTEE"
    assert epargne.solde == solde


def test_frais_de_tenue_sans_solde_negatif(banque, admin, client_amine, client_sans_argent):
    vide = client_sans_argent.comptes[0]
    assert banque.preleverFraisTenue(admin) == 1  # seul le compte d'Amine (50 000 DA) est prélevé
    assert vide.solde == D("0.00")
    assert client_amine.comptes[0].solde == D("49850.00")
    with pytest.raises(ErreurBancaire) as erreur:
        banque.preleverFraisTenue(admin)
    assert _code(erreur) == "TACHE_DEJA_EXECUTEE"


# --- Virements --------------------------------------------------------------------------------

def test_virement_trop_petit_apres_conversion(banque, client_amine, agent):
    eur = banque.ouvrirCompte(client_amine, "DEVISE", "EUR", agent)
    with pytest.raises(ErreurBancaire) as erreur:
        banque.virement(client_amine.comptes[0], eur, D("0.50"), client_amine.utilisateur)
    assert _code(erreur) == "MONTANT_TROP_PETIT"


def test_virement_par_agent_au_dessus_du_seuil(banque, client_amine, client_sans_argent, agent, chef):
    source = client_amine.comptes[0]
    banque.operationGuichet(source, TypeOperation.DEPOT, D("400000"), agent)
    banque.operationGuichet(source, TypeOperation.DEPOT, D("400000"), agent)
    destination = client_sans_argent.comptes[0]
    with pytest.raises(ErreurBancaire) as erreur:
        banque.virement(source, destination, D("600000"), agent)
    assert _code(erreur) == "APPROBATION_SUPERVISEUR"
    banque.virement(source, destination, D("600000"), chef)
    assert destination.solde == D("600000.00")
