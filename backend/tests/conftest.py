from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import creer_moteur, get_db
from app.domain import CompteCourant, CompteDevise, CompteEpargne
from app.domain.enums import Role
from app.main import creer_application, initialiser_base
from app.services.banque import Banque

MDP_TEST = "Test@2026"


@pytest.fixture
def moteur():
    moteur_test = creer_moteur("sqlite://", poolclass=StaticPool)
    initialiser_base(moteur_test)
    yield moteur_test
    moteur_test.dispose()


@pytest.fixture
def db(moteur):
    session = sessionmaker(bind=moteur, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture
def banque(db) -> Banque:
    return Banque(db)


def creer_personnel(banque: Banque, login: str, role: Role):
    utilisateur, _ = banque.acces.creerPersonnel(login, login.title(), role)
    utilisateur.definirMotDePasseDefinitif(MDP_TEST)
    banque.db.commit()
    return utilisateur


@pytest.fixture
def agent(banque):
    return creer_personnel(banque, "agent.test", Role.AGENT)


@pytest.fixture
def chef(banque):
    return creer_personnel(banque, "chef.test", Role.SUPERVISEUR)


@pytest.fixture
def admin(banque):
    return creer_personnel(banque, "admin.test", Role.ADMIN)


@pytest.fixture
def client_amine(banque, agent):
    """Client avec un compte courant crédité de 50 000 DA (exemple du sujet)."""
    client, utilisateur, _ = banque.ajouterClient(
        {"numero_identite": "109870000000000001", "nom": "Benali", "prenom": "Amine", "telephone": "0550123456"},
        agent,
    )
    utilisateur.definirMotDePasseDefinitif(MDP_TEST)
    compte = banque.ouvrirCompte(client, "COURANT", None, agent)
    banque.operationGuichet(compte, "DEPOT", Decimal("50000"), agent)
    return client


@pytest.fixture
def http(moteur):
    application = creer_application(moteur)
    fabrique = sessionmaker(bind=moteur, autoflush=False, expire_on_commit=False)

    def db_de_test():
        session = fabrique()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = db_de_test
    with TestClient(application) as client_http:
        yield client_http


def entete(http: TestClient, login: str, mot_de_passe: str = MDP_TEST) -> dict:
    reponse = http.post("/api/auth/connexion", json={"login": login, "mot_de_passe": mot_de_passe})
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['jeton']}"}



@pytest.fixture
def courant():
    compte = CompteCourant(numero="BS-CC-000001", client_id=1)
    compte.solde = Decimal("50000.00")
    return compte


@pytest.fixture
def epargne():
    compte = CompteEpargne(numero="BS-CE-000002", client_id=1)
    compte.solde = Decimal("10000.00")
    return compte


@pytest.fixture
def devise_eur():
    compte = CompteDevise(numero="BS-CD-000003", client_id=1, devise="EUR")
    compte.solde = Decimal("500.00")
    return compte

