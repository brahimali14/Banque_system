# poo
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain.enums import Role, StatutAcces
from app.horloge import maintenant
from app.security import mots_de_passe


class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(12))
    nom_affiche: Mapped[str] = mapped_column(String(120))
    client_id: Mapped[int | None] = mapped_column(ForeignKey("client.id"), unique=True, nullable=True)
    statut_acces: Mapped[str] = mapped_column(String(12), default=StatutAcces.TEMPORAIRE)
    doit_changer_mdp: Mapped[bool] = mapped_column(default=True)
    tentatives_echouees: Mapped[int] = mapped_column(default=0)
    expiration_mdp_temporaire: Mapped[datetime | None] = mapped_column(nullable=True)
    derniere_connexion: Mapped[datetime | None] = mapped_column(nullable=True)
    date_creation: Mapped[datetime] = mapped_column(default=maintenant)

    client = relationship("Client", back_populates="utilisateur")

    def estPersonnel(self) -> bool:
        return self.role in (Role.AGENT, Role.SUPERVISEUR, Role.ADMIN)

    def verifierMotDePasse(self, mot_de_passe: str) -> bool:
        return mots_de_passe.verifier(mot_de_passe, self.mot_de_passe_hash)

    def definirMotDePasseTemporaire(self, mot_de_passe: str, expiration: datetime) -> None:
        self.mot_de_passe_hash = mots_de_passe.hacher(mot_de_passe)
        self.statut_acces = StatutAcces.TEMPORAIRE
        self.doit_changer_mdp = True
        self.tentatives_echouees = 0
        self.expiration_mdp_temporaire = expiration

    def definirMotDePasseDefinitif(self, mot_de_passe: str) -> None:
        self.mot_de_passe_hash = mots_de_passe.hacher(mot_de_passe)
        self.statut_acces = StatutAcces.ACTIF
        self.doit_changer_mdp = False
        self.tentatives_echouees = 0
        self.expiration_mdp_temporaire = None

    def __repr__(self) -> str:
        return f"<Utilisateur {self.login} {self.role} {self.statut_acces}>"
