import os
from decimal import Decimal
from pathlib import Path

DOSSIER_BACKEND = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("BANK_SECRET_KEY", "dev-secret-a-changer-en-production")
DATABASE_URL = os.environ.get("BANK_DATABASE_URL", f"sqlite:///{(DOSSIER_BACKEND / 'bankservices.db').as_posix()}")
JWT_ALGORITHM = "HS256"
JWT_DUREE_MINUTES = 120

NOM_BANQUE = "BankServices"

DECOUVERT_COURANT = Decimal("20000.00")
PLAFOND_RETRAIT_JOUR_COURANT = Decimal("200000.00")
SOLDE_MINIMUM_EPARGNE = Decimal("1000.00")
RETRAITS_MAX_MOIS_EPARGNE = 2
TAUX_INTERET_EPARGNE = Decimal("0.025")
PLAFOND_RETRAIT_JOUR_DEVISE = Decimal("1000.00")
FRAIS_TENUE_COMPTE_COURANT = Decimal("150.00")

PARAMETRES_PAR_DEFAUT = {
    "seuil_superviseur_dzd": "500000.00",
    "validite_bordereau_heures": "24",
    "validite_mdp_temporaire_jours": "7",
    "tentatives_max_connexion": "5",
}

TAUX_CHANGE_PAR_DEFAUT = {"DZD": Decimal("1.00"), "EUR": Decimal("150.00"), "USD": Decimal("135.00")}
