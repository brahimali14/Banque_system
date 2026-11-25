# poo
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.functional.calculs import convertir
from app.horloge import maintenant


class Client(Base):
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_identite: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(80))
    prenom: Mapped[str] = mapped_column(String(80))
    telephone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    adresse: Mapped[str | None] = mapped_column(String(200), nullable=True)
    date_creation: Mapped[datetime] = mapped_column(default=maintenant)

    comptes = relationship("CompteBancaire", back_populates="client", order_by="CompteBancaire.id")
    utilisateur = relationship("Utilisateur", back_populates="client", uselist=False)

    @property
    def nom_complet(self) -> str:
        return f"{self.prenom} {self.nom.upper()}"

    def identiteMasquee(self) -> str:
        return "*" * max(0, len(self.numero_identite) - 4) + self.numero_identite[-4:]

    def ajouterCompte(self, compte) -> None:
        self.comptes.append(compte)

    def comptesParType(self, type_compte: str) -> list:
        return [compte for compte in self.comptes if compte.type_compte == type_compte]

    def soldeTotalEnDZD(self, taux_vers_dzd: Mapping[str, Decimal]) -> Decimal:
        return sum(
            (convertir(c.solde, c.devise, "DZD", taux_vers_dzd) for c in self.comptes),
            Decimal("0.00"),
        )

    def __repr__(self) -> str:
        return f"<Client {self.id} {self.nom_complet}>"
