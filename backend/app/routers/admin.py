from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import JournalAudit, Utilisateur
from app.domain.enums import Role, StatutAcces
from app.errors import ErreurBancaire
from app.routers.convertir import identifiants_sortie, utilisateur_sortie
from app.schemas import (
    IdentifiantsSortie,
    JournalSortie,
    ParametreEntree,
    PersonnelEntree,
    StatutAccesEntree,
    TauxEntree,
    UtilisateurSortie,
)
from app.security.dependances import administrateur
from app.services.banque import Banque

routeur = APIRouter(prefix="/api/admin", tags=["Administration"])


@routeur.get("/parametres")
def lire_parametres(admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    return Banque(db).parametres()


@routeur.put("/parametres/{cle}")
def modifier_parametre(cle: str, entree: ParametreEntree, admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    banque = Banque(db)
    banque.modifierParametre(cle, entree.valeur, admin)
    return banque.parametres()


@routeur.get("/taux-change")
def lire_taux(admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    return {devise: str(taux) for devise, taux in Banque(db).tauxDeChange().items()}


@routeur.put("/taux-change/{devise}")
def modifier_taux(devise: str, entree: TauxEntree, admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    banque = Banque(db)
    banque.mettreAJourTaux(devise.upper(), entree.taux_vers_dzd, admin)
    return {d: str(t) for d, t in banque.tauxDeChange().items()}


@routeur.get("/utilisateurs", response_model=list[UtilisateurSortie])
def lister_utilisateurs(admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    return [utilisateur_sortie(u) for u in db.scalars(select(Utilisateur).order_by(Utilisateur.role, Utilisateur.login))]


@routeur.post("/utilisateurs", response_model=IdentifiantsSortie, status_code=201)
def creer_personnel(entree: PersonnelEntree, admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    """Crée un agent, un superviseur ou un administrateur avec un mot de passe temporaire."""
    if entree.role == Role.CLIENT:
        raise ErreurBancaire("ACCES_INTERDIT", "Les accès clients sont créés depuis la fiche client.")
    banque = Banque(db)
    with banque.atomique():
        utilisateur, mot_de_passe = banque.acces.creerPersonnel(entree.login, entree.nom_affiche, entree.role)
        banque.journaliser(admin, "CREATION_UTILISATEUR", utilisateur.login, entree.role)
    return identifiants_sortie(utilisateur, mot_de_passe)


def _utilisateur(db: Session, utilisateur_id: int) -> Utilisateur:
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise ErreurBancaire("IDENTIFIANTS_INCORRECTS", "Utilisateur introuvable.")
    return utilisateur


@routeur.post("/utilisateurs/{utilisateur_id}/reinitialiser", response_model=IdentifiantsSortie)
def reinitialiser(utilisateur_id: int, admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    banque = Banque(db)
    utilisateur = _utilisateur(db, utilisateur_id)
    with banque.atomique():
        mot_de_passe = banque.acces.reinitialiser(utilisateur)
        banque.journaliser(admin, "REINITIALISATION_ACCES", utilisateur.login)
    return identifiants_sortie(utilisateur, mot_de_passe)


@routeur.patch("/utilisateurs/{utilisateur_id}/statut", response_model=UtilisateurSortie)
def activer_desactiver(
    utilisateur_id: int, entree: StatutAccesEntree, admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)
):
    banque = Banque(db)
    utilisateur = _utilisateur(db, utilisateur_id)
    if utilisateur.id == admin.id:
        raise ErreurBancaire("ACCES_INTERDIT", "Vous ne pouvez pas désactiver votre propre compte.")
    with banque.atomique():
        if entree.actif:
            utilisateur.statut_acces = StatutAcces.TEMPORAIRE if utilisateur.doit_changer_mdp else StatutAcces.ACTIF
        else:
            utilisateur.statut_acces = StatutAcces.DESACTIVE
        banque.journaliser(admin, "ACTIVATION" if entree.actif else "DESACTIVATION", utilisateur.login)
    return utilisateur_sortie(utilisateur)


@routeur.get("/audit", response_model=list[JournalSortie])
def journal_audit(limite: int = 200, admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    lignes = db.execute(
        select(JournalAudit, Utilisateur.login)
        .outerjoin(Utilisateur, Utilisateur.id == JournalAudit.utilisateur_id)
        .order_by(JournalAudit.id.desc())
        .limit(min(limite, 1000))
    ).all()
    return [
        JournalSortie(id=j.id, date=j.date, utilisateur=login, action=j.action, cible=j.cible, details=j.details)
        for j, login in lignes
    ]


TACHES = {
    "expirer-bordereaux": lambda banque, admin: banque.expirerDemandes(),
    "verser-interets": lambda banque, admin: banque.verserInterets(admin),
    "frais-tenue-compte": lambda banque, admin: banque.preleverFraisTenue(admin),
}


@routeur.post("/taches/{nom}")
def lancer_tache(nom: str, admin: Utilisateur = Depends(administrateur), db: Session = Depends(get_db)):
    """Lance à la main une tâche « Système » (utile pour la démonstration)."""
    tache = TACHES.get(nom)
    if tache is None:
        raise ErreurBancaire("PARAMETRE_INCONNU", f"Tâches disponibles : {', '.join(TACHES)}.")
    return {"tache": nom, "elements_traites": tache(Banque(db), admin)}
