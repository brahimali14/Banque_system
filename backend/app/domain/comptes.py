# poo
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import config
from app.database import Base, DecimalTexte, Montant
from app.domain.enums import Devise, StatutCompte, TypeCompte, TypeOperation
from app.domain.operations import Transaction
from app.errors import ErreurBancaire
from app.functional.calculs import frais_virement_courant, frais_virement_devise, interets_mensuels
from app.horloge import maintenant
from app.rules.imperative import calculer_nouveau_solde

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class ContexteRetrait:

    retire_aujourdhui: Decimal = ZERO
    retraits_ce_mois: int = 0
    retrait_especes: bool = True


class CompteBancaire(Base):

    __tablename__ = "compte"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), index=True)
    type_compte: Mapped[str] = mapped_column(String(10))
    devise: Mapped[str] = mapped_column(String(3))
    solde: Mapped[Decimal] = mapped_column(Montant)
    montant_bloque: Mapped[Decimal] = mapped_column(Montant)
    statut: Mapped[str] = mapped_column(String(10))
    date_ouverture: Mapped[datetime] = mapped_column(default=maintenant)
    decouvert_autorise: Mapped[Decimal | None] = mapped_column(Montant, nullable=True)
    plafond_retrait_jour: Mapped[Decimal | None] = mapped_column(Montant, nullable=True)
    taux_interet: Mapped[Decimal | None] = mapped_column(DecimalTexte, nullable=True)

    client = relationship("Client", back_populates="comptes")
    transactions = relationship(
        "Transaction", back_populates="compte", order_by="Transaction.id", cascade="all, delete-orphan"
    )
    demandes = relationship("DemandeOperation", back_populates="compte", order_by="DemandeOperation.id")

    __mapper_args__ = {"polymorphic_on": "type_compte", "polymorphic_abstract": True}

    PREFIXE = "XX"
    LIBELLE = "Compte"
    DEVISES_AUTORISEES = (Devise.DZD,)

    def __init__(self, **kwargs):
        kwargs.setdefault("devise", self.DEVISES_AUTORISEES[0])
        kwargs.setdefault("solde", ZERO)
        kwargs.setdefault("montant_bloque", ZERO)
        kwargs.setdefault("statut", StatutCompte.ACTIF)
        kwargs.setdefault("date_ouverture", maintenant())
        for cle, valeur in self.valeurs_par_defaut().items():
            kwargs.setdefault(cle, valeur)
        if kwargs["devise"] not in self.DEVISES_AUTORISEES:
            raise ErreurBancaire("DEVISE_INVALIDE")
        super().__init__(**kwargs)

    @classmethod
    def valeurs_par_defaut(cls) -> dict:
        return {}

    def motifRefusRetrait(self, montant: Decimal, contexte: ContexteRetrait) -> str | None:
        raise NotImplementedError("Chaque type de compte définit sa propre règle de retrait.")

    def calculerFrais(self, type_operation: TypeOperation, montant: Decimal) -> Decimal:
        return ZERO

    def motifRefusVirementVers(self, destination: CompteBancaire) -> str | None:
        return None

    def soldeDisponible(self) -> Decimal:
        return self.solde - self.montant_bloque

    def estActif(self) -> bool:
        return self.statut == StatutCompte.ACTIF

    def verifierActif(self) -> None:
        if not self.estActif():
            raise ErreurBancaire("COMPTE_BLOQUE")

    def peutRetirer(self, montant: Decimal, contexte: ContexteRetrait | None = None) -> bool:
        return self.motifRefusRetrait(montant, contexte or ContexteRetrait()) is None

    def verifierRetrait(self, montant: Decimal, contexte: ContexteRetrait | None = None) -> None:
        motif = self.motifRefusRetrait(montant, contexte or ContexteRetrait())
        if motif:
            raise ErreurBancaire(motif)

    def bloquer(self, montant: Decimal) -> None:
        self.montant_bloque = self.montant_bloque + montant

    def liberer(self, montant: Decimal) -> None:
        self.montant_bloque = max(ZERO, self.montant_bloque - montant)

    def crediter(self, montant, type_operation, libelle, agent_id=None, contrepartie=None) -> Transaction:
        self.verifierActif()
        return self._enregistrer(montant, type_operation, libelle, agent_id, contrepartie)

    def debiter(self, montant, type_operation, libelle, agent_id=None, contrepartie=None) -> Transaction:
        self.verifierActif()
        return self._enregistrer(montant, type_operation, libelle, agent_id, contrepartie)

    def _enregistrer(self, montant, type_operation, libelle, agent_id, contrepartie) -> Transaction:
        from app.services.numeros import tirer_numero

        self.solde = calculer_nouveau_solde(self.solde, montant, type_operation)
        transaction = Transaction(
            reference=tirer_numero("TRX"),
            type=type_operation,
            montant=montant,
            devise=self.devise,
            solde_apres=self.solde,
            libelle=libelle,
            agent_id=agent_id,
            compte_contrepartie=contrepartie,
            date=maintenant(),
        )
        self.transactions.append(transaction)
        return transaction

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.numero} {self.solde} {self.devise}>"


class CompteCourant(CompteBancaire):
    __mapper_args__ = {"polymorphic_identity": TypeCompte.COURANT}

    PREFIXE = "CC"
    LIBELLE = "Compte courant"
    DEVISES_AUTORISEES = (Devise.DZD,)

    @classmethod
    def valeurs_par_defaut(cls) -> dict:
        return {
            "decouvert_autorise": config.DECOUVERT_COURANT,
            "plafond_retrait_jour": config.PLAFOND_RETRAIT_JOUR_COURANT,
        }

    def motifRefusRetrait(self, montant, contexte):
        if montant > self.soldeDisponible() + self.decouvert_autorise:
            return "SOLDE_INSUFFISANT"
        if contexte.retrait_especes and contexte.retire_aujourdhui + montant > self.plafond_retrait_jour:
            return "PLAFOND_DEPASSE"
        return None

    def calculerFrais(self, type_operation, montant):
        if type_operation == TypeOperation.VIREMENT_EMIS:
            return frais_virement_courant(montant)
        return ZERO

    def fraisTenueCompte(self) -> Decimal:
        return config.FRAIS_TENUE_COMPTE_COURANT


class CompteEpargne(CompteBancaire):
    __mapper_args__ = {"polymorphic_identity": TypeCompte.EPARGNE}

    PREFIXE = "CE"
    LIBELLE = "Compte épargne"
    DEVISES_AUTORISEES = (Devise.DZD,)
    SOLDE_MINIMUM = config.SOLDE_MINIMUM_EPARGNE
    RETRAITS_MAX_MOIS = config.RETRAITS_MAX_MOIS_EPARGNE

    @classmethod
    def valeurs_par_defaut(cls) -> dict:
        return {"taux_interet": config.TAUX_INTERET_EPARGNE}

    def motifRefusRetrait(self, montant, contexte):
        if contexte.retrait_especes and contexte.retraits_ce_mois >= self.RETRAITS_MAX_MOIS:
            return "LIMITE_RETRAITS_EPARGNE"
        if montant > self.soldeDisponible():
            return "SOLDE_INSUFFISANT"
        if self.soldeDisponible() - montant < self.SOLDE_MINIMUM:
            return "SOLDE_MINIMUM_EPARGNE"
        return None

    def motifRefusVirementVers(self, destination):
        if destination.client_id != self.client_id:
            return "VIREMENT_EPARGNE_INTERDIT"
        return None

    def calculerInteretsMensuels(self) -> Decimal:
        return interets_mensuels(self.solde, self.taux_interet)


class CompteDevise(CompteBancaire):
    __mapper_args__ = {"polymorphic_identity": TypeCompte.DEVISE}

    PREFIXE = "CD"
    LIBELLE = "Compte devise"
    DEVISES_AUTORISEES = (Devise.EUR, Devise.USD)

    @classmethod
    def valeurs_par_defaut(cls) -> dict:
        return {"plafond_retrait_jour": config.PLAFOND_RETRAIT_JOUR_DEVISE}

    def motifRefusRetrait(self, montant, contexte):
        if montant > self.soldeDisponible():
            return "SOLDE_INSUFFISANT"
        if contexte.retrait_especes and contexte.retire_aujourdhui + montant > self.plafond_retrait_jour:
            return "PLAFOND_DEPASSE"
        return None

    def calculerFrais(self, type_operation, montant):
        if type_operation == TypeOperation.VIREMENT_EMIS:
            return frais_virement_devise(montant)
        return ZERO


CLASSES_COMPTE = {
    TypeCompte.COURANT: CompteCourant,
    TypeCompte.EPARGNE: CompteEpargne,
    TypeCompte.DEVISE: CompteDevise,
}
