import random
import sys
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, moteur
from app.domain import ContexteRetrait, Utilisateur
from app.domain.enums import Role, TypeOperation
from app.horloge import maintenant
from app.main import initialiser_base
from app.services.banque import Banque
from app.services.procedures import effectuerDepot, effectuerRetrait

MDP_DEMO = "12345678"
MDP_CLIENT = MDP_DEMO
MDP_PREMIERE_CONNEXION = MDP_DEMO

PERSONNEL = [
    ("admin", "Administrateur", Role.ADMIN, MDP_DEMO),
    ("s.haddad", "Samir HADDAD", Role.SUPERVISEUR, MDP_DEMO),
    ("a.mansouri", "Asma MANSOURI", Role.AGENT, MDP_DEMO),
    ("k.belkacem", "Khaled BELKACEM", Role.AGENT, MDP_DEMO),
]

CLIENTS = [
    ("Amine", "Benali", "109870000000000001", "0550 12 34 56", "Alger", [("COURANT", None), ("EPARGNE", None), ("DEVISE", "EUR")]),
    ("Sara", "Boudiaf", "109870000000000002", "0661 23 45 67", "Oran", [("COURANT", None), ("EPARGNE", None)]),
    ("Yacine", "Cherif", "109870000000000003", "0770 34 56 78", "Constantine", [("COURANT", None), ("DEVISE", "USD")]),
    ("Lina", "Hamidi", "109870000000000004", "0552 45 67 89", "Blida", [("COURANT", None)]),
    ("Karim", "Ziani", "109870000000000005", "0663 56 78 90", "Sétif", [("COURANT", None), ("EPARGNE", None), ("DEVISE", "EUR"), ("DEVISE", "USD")]),
    ("Nour", "Meziane", "109870000000000006", "0771 67 89 01", "Tlemcen", [("COURANT", None), ("EPARGNE", None)]),
    ("Rania", "Saadi", "109870000000000007", "0553 78 90 12", "Béjaïa", [("COURANT", None)]),
    ("Yasmine", "Kaci", "109870000000000008", "0664 89 01 23", "Tizi Ouzou", [("COURANT", None)]),
]


def _montant(alea: random.Random, minimum: int, maximum: int, compte) -> Decimal:
    valeur = Decimal(alea.randrange(minimum, maximum))
    return valeur if compte.devise != "DZD" else valeur * 100


def _historique(compte, agent_id: int, alea: random.Random) -> None:
    sans_plafond = ContexteRetrait(retrait_especes=False)
    initial = effectuerDepot(compte, _montant(alea, 800, 3000, compte) / 10 * (10 if compte.devise == "DZD" else 1), "Versement initial", agent_id)
    initial.date = maintenant() - timedelta(days=125)
    for jour in sorted(alea.sample(range(3, 120), 10), reverse=True):
        if alea.random() < 0.6:
            transaction = effectuerDepot(compte, _montant(alea, 20, 400, compte), "Dépôt au guichet", agent_id)
        else:
            montant = _montant(alea, 10, 150, compte)
            if not compte.peutRetirer(montant, sans_plafond):
                continue
            transaction = effectuerRetrait(compte, montant, sans_plafond, "Retrait au guichet", agent_id)
        transaction.date = maintenant() - timedelta(days=jour, hours=alea.randrange(0, 8))


def remplir(db: Session) -> None:
    banque = Banque(db)
    alea = random.Random(2026)

    personnel = {}
    for login, nom, role, mot_de_passe in PERSONNEL:
        utilisateur, _ = banque.acces.creerPersonnel(login, nom, role)
        utilisateur.definirMotDePasseDefinitif(mot_de_passe)
        personnel[login] = utilisateur
    db.commit()
    agent = personnel["a.mansouri"]

    comptes_par_client = {}
    for prenom, nom, identite, telephone, ville, comptes in CLIENTS:
        client, utilisateur, _ = banque.ajouterClient(
            {
                "numero_identite": identite,
                "nom": nom,
                "prenom": prenom,
                "telephone": telephone,
                "email": f"{prenom.lower()}.{nom.lower()}@exemple.dz",
                "adresse": f"{alea.randrange(1, 120)} rue des Oliviers, {ville}",
            },
            agent,
        )
        if prenom == "Yasmine":
            utilisateur.definirMotDePasseTemporaire(MDP_PREMIERE_CONNEXION, maintenant() + timedelta(days=7))
        else:
            utilisateur.definirMotDePasseDefinitif(MDP_CLIENT)
        ouverts = [banque.ouvrirCompte(client, type_compte, devise, agent) for type_compte, devise in comptes]
        for compte in ouverts:
            compte.date_ouverture = maintenant() - timedelta(days=130)
            _historique(compte, agent.id, alea)
        comptes_par_client[prenom] = ouverts
        db.commit()

    amine = db.scalar(select(Utilisateur).where(Utilisateur.login == "amine.benali"))
    karim = db.scalar(select(Utilisateur).where(Utilisateur.login == "karim.ziani"))
    exemples = [
        banque.creerDemande(comptes_par_client["Amine"][0], TypeOperation.RETRAIT, Decimal("12000"), amine),
        banque.creerDemande(comptes_par_client["Amine"][0], TypeOperation.DEPOT, Decimal("35000"), amine),
        banque.creerDemande(comptes_par_client["Karim"][0], TypeOperation.DEPOT, Decimal("750000"), karim),
    ]
    print("Bordereaux en attente (à saisir au guichet) :")
    for demande in exemples:
        print(f"  {demande.numero_bordereau}  {demande.type:<7} {demande.montant:>12} DA  compte {demande.compte.numero}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--reset" in sys.argv:
        Base.metadata.drop_all(moteur)
    initialiser_base(moteur)
    with Session(moteur) as db:
        if db.scalar(select(Utilisateur.id).limit(1)) is not None:
            print("La base contient déjà des données. Utilisez --reset pour tout recommencer.")
            return
        remplir(db)
    print("Données fictives créées. Voir les identifiants de démonstration en haut de app/seed.py.")


if __name__ == "__main__":
    main()
