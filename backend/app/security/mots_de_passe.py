import re
import secrets
import string
import unicodedata

import bcrypt

SYMBOLES = "#@!%*?"


def hacher(mot_de_passe: str) -> str:
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verifier(mot_de_passe: str, hache: str) -> bool:
    try:
        return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hache.encode("ascii"))
    except ValueError:
        return False


def generer_mot_de_passe_temporaire(longueur: int = 10) -> str:
    obligatoires = [
        secrets.choice(string.ascii_uppercase.replace("O", "").replace("I", "")),
        secrets.choice(string.ascii_lowercase.replace("l", "")),
        secrets.choice("23456789"),
        secrets.choice(SYMBOLES),
    ]
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789" + SYMBOLES
    reste = [secrets.choice(alphabet) for _ in range(longueur - len(obligatoires))]
    caracteres = obligatoires + reste
    secrets.SystemRandom().shuffle(caracteres)
    return "".join(caracteres)


def motif_mot_de_passe_faible(mot_de_passe: str) -> str | None:
    if (
        len(mot_de_passe) < 8
        or not re.search(r"[A-Z]", mot_de_passe)
        or not re.search(r"[a-z]", mot_de_passe)
        or not re.search(r"\d", mot_de_passe)
    ):
        return "MOT_DE_PASSE_FAIBLE"
    return None


def normaliser_login(prenom: str, nom: str) -> str:

    def nettoyer(texte: str) -> str:
        sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
        return "".join(car for car in sans_accents.lower() if car.isalnum())

    return f"{nettoyer(prenom)}.{nettoyer(nom)}".strip(".") or "client"


def choisir_login(base: str, existants: set[str]) -> str:
    if base not in existants:
        return base
    suffixe = 2
    while f"{base}{suffixe}" in existants:
        suffixe += 1
    return f"{base}{suffixe}"
