# poo
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, Montant
from app.domain.enums import StatutDemande, TypeOperation
from app.errors import ErreurBancaire
from app.horloge import maintenant

STATUTS_TERMINES = (StatutDemande.VALIDEE, StatutDemande.REFUSEE, StatutDemande.ANNULEE)


class Transaction(Base):

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    compte_id: Mapped[int] = mapped_column(ForeignKey("compte.id"), index=True)
    type: Mapped[str] = mapped_column(String(15))
    montant: Mapped[Decimal] = mapped_column(Montant)
    devise: Mapped[str] = mapped_column(String(3))
    solde_apres: Mapped[Decimal] = mapped_column(Montant)
    libelle: Mapped[str] = mapped_column(String(200))
    compte_contrepartie: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"), nullable=True)
    date: Mapped[datetime] = mapped_column(default=maintenant, index=True)

    compte = relationship("CompteBancaire", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction {self.reference} {self.type} {self.montant}>"


class DemandeOperation(Base):

    __tablename__ = "demande_operation"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_bordereau: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    compte_id: Mapped[int] = mapped_column(ForeignKey("compte.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))
    montant: Mapped[Decimal] = mapped_column(Montant)
    statut: Mapped[str] = mapped_column(String(25), default=StatutDemande.EN_ATTENTE)
    date_creation: Mapped[datetime] = mapped_column(default=maintenant)
    date_expiration: Mapped[datetime]
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"), nullable=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"), nullable=True)
    superviseur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id"), nullable=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    motif_refus: Mapped[str | None] = mapped_column(String(300), nullable=True)
    date_traitement: Mapped[datetime | None] = mapped_column(nullable=True)

    compte = relationship("CompteBancaire", back_populates="demandes")
    transaction = relationship("Transaction")

    def estRetrait(self) -> bool:
        return self.type == TypeOperation.RETRAIT

    def estExpiree(self, instant: datetime) -> bool:
        return self.statut == StatutDemande.EN_ATTENTE and instant > self.date_expiration

    def verifierTraitable(self) -> None:
        if self.statut in STATUTS_TERMINES:
            raise ErreurBancaire("BORDEREAU_DEJA_TRAITE")
        if self.statut == StatutDemande.EXPIREE:
            raise ErreurBancaire("BORDEREAU_EXPIRE")

    def _terminer(self, statut: StatutDemande, utilisateur_id: int | None, motif: str | None = None) -> None:
        if self.estRetrait():
            self.compte.liberer(self.montant)
        self.statut = statut
        self.motif_refus = motif
        self.date_traitement = maintenant()
        if utilisateur_id is not None:
            self.agent_id = self.agent_id or utilisateur_id

    def refuser(self, utilisateur_id: int, motif: str) -> None:
        self.verifierTraitable()
        self._terminer(StatutDemande.REFUSEE, utilisateur_id, motif)

    def annuler(self) -> None:
        if self.statut != StatutDemande.EN_ATTENTE:
            raise ErreurBancaire("BORDEREAU_DEJA_TRAITE")
        self._terminer(StatutDemande.ANNULEE, None)

    def expirer(self) -> None:
        self._terminer(StatutDemande.EXPIREE, None)

    def marquerValidee(self, transaction: Transaction, agent_id: int, superviseur_id: int | None = None) -> None:
        self.statut = StatutDemande.VALIDEE
        self.transaction = transaction
        self.agent_id = self.agent_id or agent_id
        self.superviseur_id = superviseur_id
        self.date_traitement = maintenant()

    def __repr__(self) -> str:
        return f"<DemandeOperation {self.numero_bordereau} {self.type} {self.montant} {self.statut}>"
