from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.domain import JournalAudit, Utilisateur
from app.domain.enums import Role, StatutAcces
from app.errors import ErreurBancaire
from app.horloge import maintenant
from app.security.mots_de_passe import (
    choisir_login,
    generer_mot_de_passe_temporaire,
    motif_mot_de_passe_faible,
    normaliser_login,
)


def _parametre_int(db: Session, cle: str) -> int:
    from app.domain import Parametre

    parametre = db.get(Parametre, cle)
    return int(parametre.valeur if parametre else config.PARAMETRES_PAR_DEFAUT[cle])


class ServiceAcces:
    def __init__(self, db: Session):
        self.db = db

    def _logins_existants(self, base: str) -> set[str]:
        return set(self.db.scalars(select(Utilisateur.login).where(Utilisateur.login.like(f"{base}%"))))

    def _expiration_temporaire(self):
        return maintenant() + timedelta(days=_parametre_int(self.db, "validite_mdp_temporaire_jours"))

    def creerAccesClient(self, client) -> tuple[Utilisateur, str]:
        base = normaliser_login(client.prenom, client.nom)
        login = choisir_login(base, self._logins_existants(base))
        mot_de_passe = generer_mot_de_passe_temporaire()
        expiration = self._expiration_temporaire()
        utilisateur = Utilisateur(login=login, role=Role.CLIENT, nom_affiche=client.nom_complet)
        utilisateur.definirMotDePasseTemporaire(mot_de_passe, expiration)
        self.db.add(utilisateur)
        utilisateur.client = client
        return utilisateur, mot_de_passe

    def creerPersonnel(self, login: str, nom_affiche: str, role: Role) -> tuple[Utilisateur, str]:
        login = login.strip().lower()
        if self.db.scalar(select(Utilisateur.id).where(Utilisateur.login == login)):
            raise ErreurBancaire("LOGIN_DEJA_UTILISE")
        mot_de_passe = generer_mot_de_passe_temporaire()
        utilisateur = Utilisateur(login=login, role=role, nom_affiche=nom_affiche)
        utilisateur.definirMotDePasseTemporaire(mot_de_passe, self._expiration_temporaire())
        self.db.add(utilisateur)
        return utilisateur, mot_de_passe

    def reinitialiser(self, utilisateur: Utilisateur) -> str:
        mot_de_passe = generer_mot_de_passe_temporaire()
        utilisateur.definirMotDePasseTemporaire(mot_de_passe, self._expiration_temporaire())
        return mot_de_passe

    def connecter(self, login: str, mot_de_passe: str) -> Utilisateur:
        utilisateur = self.db.scalar(select(Utilisateur).where(Utilisateur.login == login.strip().lower()))
        if utilisateur is None:
            raise ErreurBancaire("IDENTIFIANTS_INCORRECTS")
        if utilisateur.statut_acces == StatutAcces.DESACTIVE:
            raise ErreurBancaire("ACCES_DESACTIVE")
        if utilisateur.statut_acces == StatutAcces.VERROUILLE:
            raise ErreurBancaire("ACCES_VERROUILLE")
        if utilisateur.statut_acces == StatutAcces.TEMPORAIRE and maintenant() > utilisateur.expiration_mdp_temporaire:
            utilisateur.statut_acces = StatutAcces.EXPIRE
            self.db.commit()
        if utilisateur.statut_acces == StatutAcces.EXPIRE:
            raise ErreurBancaire("MOT_DE_PASSE_TEMPORAIRE_EXPIRE")

        if not utilisateur.verifierMotDePasse(mot_de_passe):
            utilisateur.tentatives_echouees += 1
            verrouille = utilisateur.tentatives_echouees >= _parametre_int(self.db, "tentatives_max_connexion")
            if verrouille:
                utilisateur.statut_acces = StatutAcces.VERROUILLE
                self.db.add(JournalAudit(utilisateur_id=utilisateur.id, action="ACCES_VERROUILLE", cible=login))
            self.db.commit()
            raise ErreurBancaire("ACCES_VERROUILLE" if verrouille else "IDENTIFIANTS_INCORRECTS")

        utilisateur.tentatives_echouees = 0
        utilisateur.derniere_connexion = maintenant()
        self.db.add(JournalAudit(utilisateur_id=utilisateur.id, action="CONNEXION", cible=utilisateur.login))
        self.db.commit()
        return utilisateur

    def changerMotDePasse(self, utilisateur: Utilisateur, ancien: str | None, nouveau: str, confirmation: str) -> None:
        if not utilisateur.doit_changer_mdp and not utilisateur.verifierMotDePasse(ancien or ""):
            raise ErreurBancaire("ANCIEN_MDP_INCORRECT")
        if nouveau != confirmation:
            raise ErreurBancaire("CONFIRMATION_DIFFERENTE")
        motif = motif_mot_de_passe_faible(nouveau)
        if motif:
            raise ErreurBancaire(motif)
        if utilisateur.verifierMotDePasse(nouveau):
            raise ErreurBancaire("MOT_DE_PASSE_IDENTIQUE")
        utilisateur.definirMotDePasseDefinitif(nouveau)
        self.db.add(JournalAudit(utilisateur_id=utilisateur.id, action="CHANGEMENT_MDP", cible=utilisateur.login))
        self.db.commit()
