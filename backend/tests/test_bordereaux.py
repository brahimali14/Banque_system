from datetime import timedelta
from decimal import Decimal

from app import horloge
from tests.conftest import entete


def _compte(client_amine):
    return client_amine.comptes[0].numero


def _demander(http, numero_compte, type_operation, montant):
    return http.post(
        "/api/moi/demandes",
        json={"numero_compte": numero_compte, "type": type_operation, "montant": str(montant)},
        headers=entete(http, "amine.benali"),
    )


def _solde(http, numero_compte):
    return http.get(f"/api/comptes/{numero_compte}", headers=entete(http, "amine.benali")).json()


def test_retrait_complet_avec_montant_bloque(http, client_amine, agent):
    compte = _compte(client_amine)
    demande = _demander(http, compte, "RETRAIT", 12000)
    assert demande.status_code == 201, demande.text
    numero = demande.json()["numero_bordereau"]
    assert numero.startswith("RET-")


    etat = _solde(http, compte)
    assert Decimal(etat["solde"]) == Decimal("50000")
    assert Decimal(etat["solde_disponible"]) == Decimal("38000")

    # Bordereau PDF
    pdf = http.get(f"/api/moi/demandes/{numero}/bordereau.pdf", headers=entete(http, "amine.benali"))
    assert pdf.content.startswith(b"%PDF")


    agent_h = entete(http, agent.login)
    vue = http.get(f"/api/agent/bordereaux/{numero.lower().replace('-', ' ')}", headers=agent_h)
    assert vue.status_code == 200, vue.text
    assert vue.json()["client_nom"] == "Amine BENALI"
    assert Decimal(vue.json()["solde_apres_operation"]) == Decimal("38000")

    valide = http.post(f"/api/agent/bordereaux/{numero}/valider", headers=agent_h)
    assert valide.status_code == 200, valide.text
    assert valide.json()["demande"]["statut"] == "VALIDEE"
    reference = valide.json()["transaction"]["reference"]

    etat = _solde(http, compte)
    assert Decimal(etat["solde"]) == Decimal("38000")
    assert Decimal(etat["montant_bloque"]) == Decimal("0")


    assert http.get(f"/api/transactions/{reference}/recu.pdf", headers=agent_h).content.startswith(b"%PDF")
    deuxieme = http.post(f"/api/agent/bordereaux/{numero}/valider", headers=agent_h)
    assert deuxieme.json()["code"] == "BORDEREAU_DEJA_TRAITE"


def test_depot_puis_refus(http, client_amine, agent):
    numero = _demander(http, _compte(client_amine), "DEPOT", 5000).json()["numero_bordereau"]
    agent_h = entete(http, agent.login)
    refus = http.post(f"/api/agent/bordereaux/{numero}/refuser", json={"motif": "Espèces non conformes"}, headers=agent_h)
    assert refus.json()["statut"] == "REFUSEE"
    assert Decimal(_solde(http, _compte(client_amine))["solde"]) == Decimal("50000")


def test_refus_d_un_retrait_libere_le_montant(http, client_amine, agent):
    compte = _compte(client_amine)
    numero = _demander(http, compte, "RETRAIT", 10000).json()["numero_bordereau"]
    http.post(f"/api/agent/bordereaux/{numero}/refuser", json={"motif": "Pièce d'identité absente"}, headers=entete(http, agent.login))
    assert Decimal(_solde(http, compte)["solde_disponible"]) == Decimal("50000")


def test_annulation_par_le_client(http, client_amine):
    compte = _compte(client_amine)
    numero = _demander(http, compte, "RETRAIT", 10000).json()["numero_bordereau"]
    reponse = http.delete(f"/api/moi/demandes/{numero}", headers=entete(http, "amine.benali"))
    assert reponse.json()["statut"] == "ANNULEE"
    assert Decimal(_solde(http, compte)["solde_disponible"]) == Decimal("50000")


def test_retrait_refuse_si_solde_insuffisant(http, client_amine):
    reponse = _demander(http, _compte(client_amine), "RETRAIT", 50000.01)  # solde : 50 000, pas de découvert
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "SOLDE_INSUFFISANT"


def test_double_demande_avec_le_meme_argent_impossible(http, client_amine):
    compte = _compte(client_amine)
    assert _demander(http, compte, "RETRAIT", 30000).status_code == 201
    assert _demander(http, compte, "RETRAIT", 30000).json()["code"] == "SOLDE_INSUFFISANT"


def test_depot_montant_negatif(http, client_amine):
    reponse = _demander(http, _compte(client_amine), "DEPOT", -50)
    assert reponse.json() == {"code": "MONTANT_INVALIDE", "message": "Le montant doit être strictement positif."}


def test_numero_mal_saisi_et_introuvable(http, agent):
    agent_h = entete(http, agent.login)
    assert http.get("/api/agent/bordereaux/RET-ABCD-1234", headers=agent_h).json()["code"] == "NUMERO_INVALIDE"
    from app.functional.numeros import composer_numero

    inconnu = composer_numero("RET", "ZZZZZZZ")
    assert http.get(f"/api/agent/bordereaux/{inconnu}", headers=agent_h).json()["code"] == "BORDEREAU_INTROUVABLE"


def test_bordereau_expire_libere_le_montant(http, client_amine, agent, monkeypatch):
    compte = _compte(client_amine)
    numero = _demander(http, compte, "RETRAIT", 10000).json()["numero_bordereau"]
    plus_tard = horloge.maintenant() + timedelta(hours=25)
    monkeypatch.setattr("app.services.banque.maintenant", lambda: plus_tard)
    reponse = http.get(f"/api/agent/bordereaux/{numero}", headers=entete(http, agent.login))
    assert reponse.status_code == 410
    assert reponse.json()["code"] == "BORDEREAU_EXPIRE"
    assert Decimal(_solde(http, compte)["solde_disponible"]) == Decimal("50000")


def test_gros_montant_transmis_au_superviseur(http, client_amine, agent, chef):
    numero = _demander(http, _compte(client_amine), "DEPOT", 750000).json()["numero_bordereau"]
    agent_h, chef_h = entete(http, agent.login), entete(http, chef.login)

    transmis = http.post(f"/api/agent/bordereaux/{numero}/valider", headers=agent_h).json()
    assert transmis["demande"]["statut"] == "EN_ATTENTE_SUPERVISEUR"
    assert transmis["transaction"] is None
    assert http.post(f"/api/agent/bordereaux/{numero}/valider", headers=agent_h).json()["code"] == "APPROBATION_SUPERVISEUR"

    a_approuver = http.get("/api/superviseur/demandes", headers=chef_h).json()
    assert [d["numero_bordereau"] for d in a_approuver] == [numero]
    approuve = http.post(f"/api/agent/bordereaux/{numero}/valider", headers=chef_h).json()
    assert approuve["demande"]["statut"] == "VALIDEE"
    assert Decimal(_solde(http, _compte(client_amine))["solde"]) == Decimal("800000")


def test_un_client_ne_voit_pas_le_bordereau_d_un_autre(http, client_amine, banque, agent):
    numero = _demander(http, _compte(client_amine), "DEPOT", 100).json()["numero_bordereau"]
    _, autre, _ = banque.ajouterClient(
        {"numero_identite": "109870000000000077", "nom": "Saadi", "prenom": "Rania", "telephone": "0553789012"}, agent
    )
    autre.definirMotDePasseDefinitif("Test@2026")
    banque.db.commit()
    reponse = http.get(f"/api/moi/demandes/{numero}/bordereau.pdf", headers=entete(http, "rania.saadi"))
    assert reponse.status_code == 404


def test_epargne_limitee_a_deux_retraits_par_mois(http, client_amine, banque, agent):
    epargne = banque.ouvrirCompte(client_amine, "EPARGNE", None, agent)
    banque.operationGuichet(epargne, "DEPOT", Decimal("20000"), agent)
    assert _demander(http, epargne.numero, "RETRAIT", 1000).status_code == 201
    assert _demander(http, epargne.numero, "RETRAIT", 1000).status_code == 201
    assert _demander(http, epargne.numero, "RETRAIT", 1000).json()["code"] == "LIMITE_RETRAITS_EPARGNE"
