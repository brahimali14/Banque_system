from datetime import timedelta

import pytest

from app import horloge
from app.security.mots_de_passe import choisir_login, motif_mot_de_passe_faible, normaliser_login
from tests.conftest import entete

CLIENT = {"numero_identite": "109870000000000042", "nom": "Ben Ali", "prenom": "Amine", "telephone": "0550123456"}


def test_login_sans_accents_ni_espaces():
    assert normaliser_login("Amine", "Ben Ali") == "amine.benali"
    assert normaliser_login("Hélène", "Aït-Saïd") == "helene.aitsaid"


def test_login_unique():
    assert choisir_login("amine.benali", set()) == "amine.benali"
    assert choisir_login("amine.benali", {"amine.benali", "amine.benali2"}) == "amine.benali3"


@pytest.mark.parametrize("mot_de_passe", ["court1A", "sansmajuscule1", "SANSMINUSCULE1", "SansChiffre"])
def test_mots_de_passe_faibles(mot_de_passe):
    assert motif_mot_de_passe_faible(mot_de_passe) == "MOT_DE_PASSE_FAIBLE"


def test_mot_de_passe_robuste():
    assert motif_mot_de_passe_faible("Solide2026") is None


def _creer_client(http, agent):
    reponse = http.post("/api/clients", json=CLIENT, headers=entete(http, agent.login))
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def test_creation_client_genere_les_identifiants(http, agent):
    donnees = _creer_client(http, agent)
    identifiants = donnees["identifiants"]
    assert identifiants["login"] == "amine.benali"
    assert len(identifiants["mot_de_passe_temporaire"]) == 10
    assert donnees["client"]["statut_acces"] == "TEMPORAIRE"


def test_homonyme_recoit_un_autre_login(http, agent):
    _creer_client(http, agent)
    autre = {**CLIENT, "numero_identite": "109870000000000043"}
    reponse = http.post("/api/clients", json=autre, headers=entete(http, agent.login))
    assert reponse.json()["identifiants"]["login"] == "amine.benali2"


def test_identite_en_double_refusee(http, agent):
    _creer_client(http, agent)
    reponse = http.post("/api/clients", json=CLIENT, headers=entete(http, agent.login))
    assert reponse.status_code == 409
    assert reponse.json()["code"] == "IDENTITE_DEJA_UTILISEE"


def test_premiere_connexion_oblige_a_changer_le_mot_de_passe(http, agent):
    identifiants = _creer_client(http, agent)["identifiants"]
    connexion = http.post(
        "/api/auth/connexion",
        json={"login": identifiants["login"], "mot_de_passe": identifiants["mot_de_passe_temporaire"]},
    ).json()
    assert connexion["doit_changer_mdp"] is True
    jeton_limite = {"Authorization": f"Bearer {connexion['jeton']}"}


    bloque = http.get("/api/moi/comptes", headers=jeton_limite)
    assert bloque.status_code == 403
    assert bloque.json()["code"] == "CHANGEMENT_MDP_REQUIS"


    url = "/api/auth/changer-mot-de-passe"
    assert http.post(url, json={"nouveau": "faible", "confirmation": "faible"}, headers=jeton_limite).json()["code"] == "MOT_DE_PASSE_FAIBLE"
    assert http.post(url, json={"nouveau": "Solide2026", "confirmation": "Autre2026"}, headers=jeton_limite).json()["code"] == "CONFIRMATION_DIFFERENTE"


    reponse = http.post(url, json={"nouveau": "Solide2026", "confirmation": "Solide2026"}, headers=jeton_limite)
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["doit_changer_mdp"] is False
    jeton_complet = {"Authorization": f"Bearer {reponse.json()['jeton']}"}
    assert http.get("/api/moi/comptes", headers=jeton_complet).status_code == 200


    ancien = http.post(
        "/api/auth/connexion",
        json={"login": identifiants["login"], "mot_de_passe": identifiants["mot_de_passe_temporaire"]},
    )
    assert ancien.status_code == 401
    assert http.post("/api/auth/connexion", json={"login": "amine.benali", "mot_de_passe": "Solide2026"}).status_code == 200


def test_verrouillage_apres_cinq_echecs_puis_reinitialisation(http, agent):
    donnees = _creer_client(http, agent)
    for _ in range(4):
        assert http.post("/api/auth/connexion", json={"login": "amine.benali", "mot_de_passe": "faux"}).status_code == 401
    cinquieme = http.post("/api/auth/connexion", json={"login": "amine.benali", "mot_de_passe": "faux"})
    assert cinquieme.json()["code"] == "ACCES_VERROUILLE"
    bon = donnees["identifiants"]["mot_de_passe_temporaire"]
    assert http.post("/api/auth/connexion", json={"login": "amine.benali", "mot_de_passe": bon}).json()["code"] == "ACCES_VERROUILLE"

    nouveau = http.post(f"/api/clients/{donnees['client']['id']}/reinitialiser-acces", headers=entete(http, agent.login)).json()
    reponse = http.post("/api/auth/connexion", json={"login": "amine.benali", "mot_de_passe": nouveau["mot_de_passe_temporaire"]})
    assert reponse.status_code == 200
    assert reponse.json()["doit_changer_mdp"] is True


def test_mot_de_passe_temporaire_expire(http, agent, monkeypatch):
    identifiants = _creer_client(http, agent)["identifiants"]
    plus_tard = horloge.maintenant() + timedelta(days=8)
    monkeypatch.setattr("app.services.acces.maintenant", lambda: plus_tard)
    reponse = http.post(
        "/api/auth/connexion",
        json={"login": identifiants["login"], "mot_de_passe": identifiants["mot_de_passe_temporaire"]},
    )
    assert reponse.json()["code"] == "MOT_DE_PASSE_TEMPORAIRE_EXPIRE"


def test_fiche_identifiants_pdf(http, agent):
    donnees = _creer_client(http, agent)
    url = f"/api/clients/{donnees['client']['id']}/fiche-identifiants.pdf"
    bon = http.post(url, json={"mot_de_passe_temporaire": donnees["identifiants"]["mot_de_passe_temporaire"]}, headers=entete(http, agent.login))
    assert bon.status_code == 200
    assert bon.content.startswith(b"%PDF")
    faux = http.post(url, json={"mot_de_passe_temporaire": "invente"}, headers=entete(http, agent.login))
    assert faux.status_code == 401


def test_un_client_n_accede_pas_aux_routes_agent(http, client_amine):
    reponse = http.get("/api/clients", headers=entete(http, "amine.benali"))
    assert reponse.status_code == 403
    assert reponse.json()["code"] == "ACCES_INTERDIT"


def test_sans_jeton(http):
    assert http.get("/api/moi/comptes").json()["code"] == "NON_AUTHENTIFIE"
