"""Schémas Pydantic : données reçues et renvoyées par l'API.

Les montants sont renvoyés en texte (ex. "12000.00") pour garder la précision décimale.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import Role


class ConnexionEntree(BaseModel):
    login: str = Field(min_length=1, max_length=60)
    mot_de_passe: str = Field(min_length=1, max_length=100)


class ConnexionSortie(BaseModel):
    jeton: str
    login: str
    role: str
    nom_affiche: str
    doit_changer_mdp: bool


class ChangementMdpEntree(BaseModel):
    ancien: str | None = None
    nouveau: str = Field(max_length=100)
    confirmation: str = Field(max_length=100)


class IdentifiantsSortie(BaseModel):
    login: str
    mot_de_passe_temporaire: str
    expiration: datetime


class FicheIdentifiantsEntree(BaseModel):
    mot_de_passe_temporaire: str


class ClientEntree(BaseModel):
    numero_identite: str = Field(min_length=6, max_length=30)
    nom: str = Field(min_length=1, max_length=80)
    prenom: str = Field(min_length=1, max_length=80)
    telephone: str = Field(min_length=6, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    adresse: str | None = Field(default=None, max_length=200)


class ClientModification(BaseModel):
    numero_identite: str | None = Field(default=None, min_length=6, max_length=30)
    nom: str | None = Field(default=None, min_length=1, max_length=80)
    prenom: str | None = Field(default=None, min_length=1, max_length=80)
    telephone: str | None = Field(default=None, min_length=6, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    adresse: str | None = Field(default=None, max_length=200)


class CoordonneesEntree(BaseModel):
    telephone: str | None = Field(default=None, min_length=6, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    adresse: str | None = Field(default=None, max_length=200)


class CompteSortie(BaseModel):
    numero: str
    type_compte: str
    libelle: str
    devise: str
    solde: Decimal
    montant_bloque: Decimal
    solde_disponible: Decimal
    statut: str
    date_ouverture: datetime
    decouvert_autorise: Decimal | None
    plafond_retrait_jour: Decimal | None
    taux_interet: Decimal | None
    client_id: int
    titulaire: str


class ClientResume(BaseModel):
    id: int
    numero_identite: str
    nom: str
    prenom: str
    nom_complet: str
    telephone: str
    email: str | None
    nombre_comptes: int
    date_creation: datetime


class ClientSortie(ClientResume):
    adresse: str | None
    login: str | None
    statut_acces: str | None
    comptes: list[CompteSortie]


class ClientCreeSortie(BaseModel):
    client: ClientSortie
    identifiants: IdentifiantsSortie


class OuvertureCompteEntree(BaseModel):
    type_compte: str
    devise: str | None = None


class StatutCompteEntree(BaseModel):
    statut: str


class DecouvertEntree(BaseModel):
    decouvert_autorise: Decimal


class TransactionSortie(BaseModel):
    reference: str
    numero_compte: str
    type: str
    montant: Decimal
    devise: str
    solde_apres: Decimal
    libelle: str
    compte_contrepartie: str | None
    date: datetime


class DemandeEntree(BaseModel):
    numero_compte: str
    type: str
    montant: Decimal


class DemandeSortie(BaseModel):
    numero_bordereau: str
    type: str
    montant: Decimal
    devise: str
    statut: str
    numero_compte: str
    date_creation: datetime
    date_expiration: datetime
    motif_refus: str | None
    reference_transaction: str | None


class BordereauAgentSortie(BaseModel):

    demande: DemandeSortie
    client_nom: str
    client_numero_identite: str
    client_telephone: str
    compte_libelle: str
    solde: Decimal
    solde_disponible: Decimal
    solde_apres_operation: Decimal
    depasse_seuil: bool
    minutes_restantes: int


class ResultatValidation(BaseModel):
    demande: DemandeSortie
    transaction: TransactionSortie | None
    message: str


class RefusEntree(BaseModel):
    motif: str = Field(min_length=3, max_length=300)


class OperationGuichetEntree(BaseModel):
    numero_compte: str
    type: str
    montant: Decimal


class VirementEntree(BaseModel):
    compte_source: str
    compte_destination: str
    montant: Decimal


class VirementSortie(BaseModel):
    reference: str
    reference_credit: str
    montant_debite: Decimal
    frais: Decimal
    devise_source: str
    montant_credite: Decimal
    devise_destination: str
    nouveau_solde_source: Decimal
    message: str


class ParametreEntree(BaseModel):
    valeur: str = Field(min_length=1, max_length=50)


class TauxEntree(BaseModel):
    taux_vers_dzd: Decimal


class PersonnelEntree(BaseModel):
    login: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9._-]+$")
    nom_affiche: str = Field(min_length=2, max_length=120)
    role: Role


class UtilisateurSortie(BaseModel):
    id: int
    login: str
    role: str
    nom_affiche: str
    statut_acces: str
    derniere_connexion: datetime | None
    client_id: int | None


class StatutAccesEntree(BaseModel):
    actif: bool


class JournalSortie(BaseModel):
    id: int
    date: datetime
    utilisateur: str | None
    action: str
    cible: str | None
    details: str | None
