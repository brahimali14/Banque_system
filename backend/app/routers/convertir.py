from decimal import Decimal

from fastapi import Response

from app.domain import Client, CompteBancaire, DemandeOperation, Transaction, Utilisateur
from app.domain.enums import Role
from app.errors import ErreurBancaire
from app.schemas import (
    ClientResume,
    ClientSortie,
    CompteSortie,
    DemandeSortie,
    IdentifiantsSortie,
    TransactionSortie,
    UtilisateurSortie,
)


def compte_sortie(compte: CompteBancaire) -> CompteSortie:
    return CompteSortie(
        numero=compte.numero,
        type_compte=compte.type_compte,
        libelle=compte.LIBELLE,
        devise=compte.devise,
        solde=compte.solde,
        montant_bloque=compte.montant_bloque,
        solde_disponible=compte.soldeDisponible(),
        statut=compte.statut,
        date_ouverture=compte.date_ouverture,
        decouvert_autorise=compte.decouvert_autorise,
        plafond_retrait_jour=compte.plafond_retrait_jour,
        taux_interet=compte.taux_interet,
        client_id=compte.client_id,
        titulaire=compte.client.nom_complet,
    )


def client_resume(client: Client) -> ClientResume:
    return ClientResume(
        id=client.id,
        numero_identite=client.numero_identite,
        nom=client.nom,
        prenom=client.prenom,
        nom_complet=client.nom_complet,
        telephone=client.telephone,
        email=client.email,
        nombre_comptes=len(client.comptes),
        date_creation=client.date_creation,
    )


def client_sortie(client: Client) -> ClientSortie:
    utilisateur = client.utilisateur
    return ClientSortie(
        **client_resume(client).model_dump(),
        adresse=client.adresse,
        login=utilisateur.login if utilisateur else None,
        statut_acces=utilisateur.statut_acces if utilisateur else None,
        comptes=[compte_sortie(c) for c in client.comptes],
    )


def transaction_sortie(transaction: Transaction) -> TransactionSortie:
    return TransactionSortie(
        reference=transaction.reference,
        numero_compte=transaction.compte.numero,
        type=transaction.type,
        montant=transaction.montant,
        devise=transaction.devise,
        solde_apres=transaction.solde_apres,
        libelle=transaction.libelle,
        compte_contrepartie=transaction.compte_contrepartie,
        date=transaction.date,
    )


def demande_sortie(demande: DemandeOperation) -> DemandeSortie:
    return DemandeSortie(
        numero_bordereau=demande.numero_bordereau,
        type=demande.type,
        montant=demande.montant,
        devise=demande.compte.devise,
        statut=demande.statut,
        numero_compte=demande.compte.numero,
        date_creation=demande.date_creation,
        date_expiration=demande.date_expiration,
        motif_refus=demande.motif_refus,
        reference_transaction=demande.transaction.reference if demande.transaction else None,
    )


def identifiants_sortie(utilisateur: Utilisateur, mot_de_passe: str) -> IdentifiantsSortie:
    return IdentifiantsSortie(
        login=utilisateur.login,
        mot_de_passe_temporaire=mot_de_passe,
        expiration=utilisateur.expiration_mdp_temporaire,
    )


def utilisateur_sortie(utilisateur: Utilisateur) -> UtilisateurSortie:
    return UtilisateurSortie(
        id=utilisateur.id,
        login=utilisateur.login,
        role=utilisateur.role,
        nom_affiche=utilisateur.nom_affiche,
        statut_acces=utilisateur.statut_acces,
        derniere_connexion=utilisateur.derniere_connexion,
        client_id=utilisateur.client_id,
    )


def decimaux_en_texte(valeur):
    if isinstance(valeur, Decimal):
        return str(valeur)
    if isinstance(valeur, dict):
        return {cle: decimaux_en_texte(v) for cle, v in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [decimaux_en_texte(v) for v in valeur]
    return valeur


def verifier_acces_compte(utilisateur: Utilisateur, compte: CompteBancaire) -> None:
    if utilisateur.role == Role.CLIENT and compte.client_id != utilisateur.client_id:
        raise ErreurBancaire("ACCES_INTERDIT")


def reponse_pdf(contenu: bytes, nom_fichier: str) -> Response:
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nom_fichier}"'},
    )
