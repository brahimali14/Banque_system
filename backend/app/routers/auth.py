from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Utilisateur
from app.schemas import ChangementMdpEntree, ConnexionEntree, ConnexionSortie, UtilisateurSortie
from app.security.dependances import utilisateur_meme_temporaire
from app.security.jetons import creer_jeton
from app.services.acces import ServiceAcces
from app.routers.convertir import utilisateur_sortie

routeur = APIRouter(prefix="/api/auth", tags=["Authentification"])


def _session(utilisateur: Utilisateur) -> ConnexionSortie:
    return ConnexionSortie(
        jeton=creer_jeton(utilisateur),
        login=utilisateur.login,
        role=utilisateur.role,
        nom_affiche=utilisateur.nom_affiche,
        doit_changer_mdp=utilisateur.doit_changer_mdp,
    )


@routeur.post("/connexion", response_model=ConnexionSortie)
def connexion(entree: ConnexionEntree, db: Session = Depends(get_db)):
    utilisateur = ServiceAcces(db).connecter(entree.login, entree.mot_de_passe)
    return _session(utilisateur)


@routeur.post("/changer-mot-de-passe", response_model=ConnexionSortie)
def changer_mot_de_passe(
    entree: ChangementMdpEntree,
    utilisateur: Utilisateur = Depends(utilisateur_meme_temporaire),
    db: Session = Depends(get_db),
):
    ServiceAcces(db).changerMotDePasse(utilisateur, entree.ancien, entree.nouveau, entree.confirmation)
    return _session(utilisateur)


@routeur.get("/moi", response_model=UtilisateurSortie)
def moi(utilisateur: Utilisateur = Depends(utilisateur_meme_temporaire)):
    return utilisateur_sortie(utilisateur)
