from datetime import UTC, datetime, timedelta

import jwt

from app import config
from app.errors import ErreurBancaire


def creer_jeton(utilisateur) -> str:
    charge = {
        "sub": str(utilisateur.id),
        "role": str(utilisateur.role),
        "mdp_a_changer": bool(utilisateur.doit_changer_mdp),
        "exp": datetime.now(UTC) + timedelta(minutes=config.JWT_DUREE_MINUTES),
    }
    return jwt.encode(charge, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def lire_jeton(jeton: str) -> dict:
    try:
        return jwt.decode(jeton, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ErreurBancaire("NON_AUTHENTIFIE") from exc
