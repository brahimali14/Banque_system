from enum import StrEnum


class Devise(StrEnum):
    DZD = "DZD"
    EUR = "EUR"
    USD = "USD"


class TypeCompte(StrEnum):
    COURANT = "COURANT"
    EPARGNE = "EPARGNE"
    DEVISE = "DEVISE"


class StatutCompte(StrEnum):
    ACTIF = "ACTIF"
    BLOQUE = "BLOQUE"
    CLOTURE = "CLOTURE"


class TypeOperation(StrEnum):
    DEPOT = "DEPOT"
    RETRAIT = "RETRAIT"
    VIREMENT_EMIS = "VIREMENT_EMIS"
    VIREMENT_RECU = "VIREMENT_RECU"
    FRAIS = "FRAIS"
    INTERETS = "INTERETS"


CREDITS = frozenset({TypeOperation.DEPOT, TypeOperation.VIREMENT_RECU, TypeOperation.INTERETS})
DEBITS = frozenset({TypeOperation.RETRAIT, TypeOperation.VIREMENT_EMIS, TypeOperation.FRAIS})


class StatutDemande(StrEnum):
    EN_ATTENTE = "EN_ATTENTE"
    EN_ATTENTE_SUPERVISEUR = "EN_ATTENTE_SUPERVISEUR"
    VALIDEE = "VALIDEE"
    REFUSEE = "REFUSEE"
    ANNULEE = "ANNULEE"
    EXPIREE = "EXPIREE"


class Role(StrEnum):
    CLIENT = "CLIENT"
    AGENT = "AGENT"
    SUPERVISEUR = "SUPERVISEUR"
    ADMIN = "ADMIN"


class StatutAcces(StrEnum):
    TEMPORAIRE = "TEMPORAIRE"
    ACTIF = "ACTIF"
    VERROUILLE = "VERROUILLE"
    EXPIRE = "EXPIRE"
    DESACTIVE = "DESACTIVE"
