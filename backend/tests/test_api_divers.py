from decimal import Decimal

from tests.conftest import entete


def test_recherche_client(http, client_amine, agent):
    agent_h = entete(http, agent.login)
    assert len(http.get("/api/clients?q=benal", headers=agent_h).json()) == 1
    assert len(http.get(f"/api/clients?q={client_amine.comptes[0].numero}", headers=agent_h).json()) == 1
    assert http.get("/api/clients?q=inconnu", headers=agent_h).json() == []


def test_modifier_client_et_coordonnees(http, client_amine, agent):
    agent_h = entete(http, agent.login)
    reponse = http.put(f"/api/clients/{client_amine.id}", json={"adresse": "12 rue Didouche, Alger"}, headers=agent_h)
    assert reponse.json()["adresse"] == "12 rue Didouche, Alger"
    client_h = entete(http, "amine.benali")

    reponse = http.put("/api/moi/profil", json={"telephone": "0770000000"}, headers=client_h)
    assert reponse.json()["telephone"] == "0770000000"


def test_ouvrir_plusieurs_comptes(http, client_amine, agent):
    agent_h = entete(http, agent.login)
    url = f"/api/clients/{client_amine.id}/comptes"
    epargne = http.post(url, json={"type_compte": "EPARGNE"}, headers=agent_h)
    assert epargne.json()["numero"].startswith("BS-CE-")
    assert http.post(url, json={"type_compte": "EPARGNE"}, headers=agent_h).json()["code"] == "EPARGNE_DEJA_EXISTANT"
    usd = http.post(url, json={"type_compte": "DEVISE", "devise": "USD"}, headers=agent_h)
    assert usd.json()["devise"] == "USD"
    assert http.post(url, json={"type_compte": "DEVISE", "devise": "DZD"}, headers=agent_h).json()["code"] == "DEVISE_INVALIDE"
    comptes = http.get("/api/moi/comptes", headers=entete(http, "amine.benali")).json()
    assert len({c["numero"] for c in comptes}) == 3


def test_historique_filtre_et_statistiques(http, client_amine, banque, agent):
    compte = client_amine.comptes[0]
    banque.operationGuichet(compte, "RETRAIT", Decimal("2000"), agent)
    client_h = entete(http, "amine.benali")
    tout = http.get(f"/api/comptes/{compte.numero}/transactions", headers=client_h).json()
    assert [t["type"] for t in tout] == ["RETRAIT", "DEPOT"]
    retraits = http.get(f"/api/comptes/{compte.numero}/transactions?type=RETRAIT", headers=client_h).json()
    assert len(retraits) == 1

    statistiques = http.get(f"/api/comptes/{compte.numero}/statistiques", headers=client_h).json()
    assert Decimal(str(statistiques["resume"]["total_depots"])) == Decimal("50000")
    par_type = {ligne["type"]: Decimal(str(ligne["total"])) for ligne in statistiques["par_type_sql"]}
    assert par_type == {"DEPOT": Decimal("50000"), "RETRAIT": Decimal("2000")}
    assert len(statistiques["evolution_mensuelle_sql"]) == 1

    releve = http.get(f"/api/comptes/{compte.numero}/releve.pdf", headers=client_h)
    assert releve.content.startswith(b"%PDF")


def test_client_ne_voit_pas_le_compte_d_un_autre(http, client_amine, banque, agent):
    autre, utilisateur, _ = banque.ajouterClient(
        {"numero_identite": "109870000000000055", "nom": "Kaci", "prenom": "Yasmine", "telephone": "0664890123"}, agent
    )
    utilisateur.definirMotDePasseDefinitif("Test@2026")
    banque.db.commit()
    reponse = http.get(f"/api/comptes/{client_amine.comptes[0].numero}", headers=entete(http, "yasmine.kaci"))
    assert reponse.status_code == 403


def test_operation_guichet_au_dessus_du_seuil(http, client_amine, agent):
    reponse = http.post(
        "/api/agent/operations",
        json={"numero_compte": client_amine.comptes[0].numero, "type": "DEPOT", "montant": "600000"},
        headers=entete(http, agent.login),
    )
    assert reponse.json()["code"] == "APPROBATION_SUPERVISEUR"


def test_superviseur_bloque_puis_cloture(http, client_amine, banque, agent, chef):
    chef_h = entete(http, chef.login)
    compte = client_amine.comptes[0]
    url = f"/api/comptes/{compte.numero}/statut"
    assert http.patch(url, json={"statut": "BLOQUE"}, headers=chef_h).json()["statut"] == "BLOQUE"
    assert http.patch(url, json={"statut": "CLOTURE"}, headers=chef_h).json()["code"] == "COMPTE_NON_VIDE"
    assert http.patch(url, json={"statut": "BLOQUE"}, headers=entete(http, agent.login)).status_code == 403
    tableau = http.get("/api/superviseur/tableau-de-bord", headers=chef_h).json()
    assert tableau["clients"] == 1


def test_administration(http, admin):
    admin_h = entete(http, admin.login)
    cree = http.post("/api/admin/utilisateurs", json={"login": "Nouvel.Agent", "nom_affiche": "Nouvel Agent", "role": "AGENT"}, headers=admin_h)
    assert cree.status_code == 201
    assert cree.json()["login"] == "nouvel.agent"
    connexion = http.post("/api/auth/connexion", json={"login": "nouvel.agent", "mot_de_passe": cree.json()["mot_de_passe_temporaire"]})
    assert connexion.json()["doit_changer_mdp"] is True

    assert http.put("/api/admin/parametres/seuil_superviseur_dzd", json={"valeur": "100000"}, headers=admin_h).json()["seuil_superviseur_dzd"] == "100000.00"
    assert http.put("/api/admin/taux-change/EUR", json={"taux_vers_dzd": "152.5"}, headers=admin_h).json()["EUR"] == "152.5"
    assert http.post("/api/admin/taches/verser-interets", headers=admin_h).status_code == 200
    actions = [ligne["action"] for ligne in http.get("/api/admin/audit", headers=admin_h).json()]
    assert "MODIFICATION_TAUX" in actions and "CREATION_UTILISATEUR" in actions


def test_donnees_invalides_message_lisible(http, agent):
    reponse = http.post("/api/clients", json={"nom": "X"}, headers=entete(http, agent.login))
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "DONNEES_INVALIDES"
    assert "numero_identite" in reponse.json()["champs"]
