from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Utilisateur
from app.domain.enums import Role, StatutAcces
from app.errors import ErreurBancaire
from app.security.jetons import lire_jeton

_bearer = HTTPBearer(auto_error=False)


def _utilisateur_du_jeton(
    identifiants: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> tuple[Utilisateur, dict]:
    if identifiants is None:
        raise ErreurBancaire("NON_AUTHENTIFIE")
    charge = lire_jeton(identifiants.credentials)
    utilisateur = db.get(Utilisateur, int(charge["sub"]))
    if utilisateur is None:
        raise ErreurBancaire("NON_AUTHENTIFIE")
    if utilisateur.statut_acces in (StatutAcces.VERROUILLE, StatutAcces.DESACTIVE):
        raise ErreurBancaire("ACCES_VERROUILLE" if utilisateur.statut_acces == StatutAcces.VERROUILLE else "ACCES_DESACTIVE")
    return utilisateur, charge


def utilisateur_meme_temporaire(contexte=Depends(_utilisateur_du_jeton)) -> Utilisateur:
    return contexte[0]


def utilisateur_connecte(contexte=Depends(_utilisateur_du_jeton)) -> Utilisateur:
    utilisateur, charge = contexte
    if utilisateur.doit_changer_mdp or charge.get("mdp_a_changer"):
        raise ErreurBancaire("CHANGEMENT_MDP_REQUIS")
    return utilisateur


def exiger_roles(*roles: Role):
    def dependance(utilisateur: Utilisateur = Depends(utilisateur_connecte)) -> Utilisateur:
        if utilisateur.role not in roles:
            raise ErreurBancaire("ACCES_INTERDIT")
        return utilisateur

    return dependance


client_connecte = exiger_roles(Role.CLIENT)
personnel = exiger_roles(Role.AGENT, Role.SUPERVISEUR, Role.ADMIN)
guichet = exiger_roles(Role.AGENT, Role.SUPERVISEUR)
superviseur = exiger_roles(Role.SUPERVISEUR)
administrateur = exiger_roles(Role.ADMIN)
