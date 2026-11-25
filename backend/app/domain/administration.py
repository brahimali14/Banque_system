# poo
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, DecimalTexte
from app.horloge import maintenant


class TauxChange(Base):
    __tablename__ = "taux_change"

    devise: Mapped[str] = mapped_column(String(3), primary_key=True)
    taux_vers_dzd: Mapped[Decimal] = mapped_column(DecimalTexte)
    date_maj: Mapped[datetime] = mapped_column(default=maintenant)


class Parametre(Base):
    __tablename__ = "parametre"

    cle: Mapped[str] = mapped_column(String(50), primary_key=True)
    valeur: Mapped[str] = mapped_column(String(100))


class JournalAudit(Base):
    __tablename__ = "journal_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    cible: Mapped[str | None] = mapped_column(String(60), nullable=True)
    details: Mapped[str | None] = mapped_column(String(300), nullable=True)
    date: Mapped[datetime] = mapped_column(default=maintenant, index=True)
