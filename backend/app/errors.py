
MESSAGES = {
    "MONTANT_INVALIDE": "Le montant doit être strictement positif.",
    "PRECISION_INVALIDE": "Le montant ne peut pas avoir plus de 2 décimales.",
    "SOLDE_INSUFFISANT": "Solde disponible insuffisant pour cette opération.",
    "PLAFOND_DEPASSE": "Le plafond de retrait journalier est atteint.",
    "LIMITE_RETRAITS_EPARGNE": "Un compte épargne est limité à 2 retraits par mois.",
    "SOLDE_MINIMUM_EPARGNE": "Le solde d'un compte épargne ne peut pas descendre sous 1 000 DA.",
    "COMPTES_IDENTIQUES": "Un virement doit concerner deux comptes distincts.",
    "VIREMENT_EPARGNE_INTERDIT": "Un compte épargne ne peut virer que vers un compte du même client.",
    "COMPTE_BLOQUE": "Ce compte est bloqué ou clôturé.",
    "COMPTE_INTROUVABLE": "Aucun compte ne correspond à ce numéro.",
    "COMPTE_NON_VIDE": "Le compte doit avoir un solde nul et aucune demande en cours pour être clôturé.",
    "CLIENT_INTROUVABLE": "Client introuvable.",
    "IDENTITE_DEJA_UTILISEE": "Un client avec ce numéro d'identité existe déjà.",
    "TYPE_COMPTE_INVALIDE": "Type de compte inconnu.",
    "DEVISE_INVALIDE": "Devise non prise en charge pour ce type de compte.",
    "EPARGNE_DEJA_EXISTANT": "Ce client possède déjà un compte épargne.",
    "DEVISE_DEJA_EXISTANT": "Ce client possède déjà un compte dans cette devise.",
    "NUMERO_INVALIDE": "Numéro de bordereau mal saisi, vérifiez les caractères.",
    "BORDEREAU_INTROUVABLE": "Aucun bordereau ne correspond à ce numéro.",
    "BORDEREAU_EXPIRE": "Ce bordereau a expiré, le client doit refaire une demande.",
    "BORDEREAU_DEJA_TRAITE": "Ce bordereau a déjà été traité.",
    "APPROBATION_SUPERVISEUR": "Ce montant dépasse le seuil : l'approbation d'un superviseur est nécessaire.",
    "TYPE_OPERATION_INVALIDE": "Type d'opération non autorisé ici.",
    "TRANSACTION_INTROUVABLE": "Aucune transaction ne correspond à cette référence.",
    "IDENTIFIANTS_INCORRECTS": "Nom d'utilisateur ou mot de passe incorrect.",
    "ACCES_VERROUILLE": "Accès verrouillé après plusieurs tentatives, contactez votre agence.",
    "ACCES_DESACTIVE": "Cet accès est désactivé.",
    "MOT_DE_PASSE_TEMPORAIRE_EXPIRE": "Votre mot de passe temporaire a expiré, demandez-en un nouveau à l'agence.",
    "CHANGEMENT_MDP_REQUIS": "Vous devez choisir un nouveau mot de passe avant de continuer.",
    "MOT_DE_PASSE_FAIBLE": "Au moins 8 caractères, une majuscule, une minuscule et un chiffre.",
    "MOT_DE_PASSE_IDENTIQUE": "Le nouveau mot de passe doit être différent de l'ancien.",
    "CONFIRMATION_DIFFERENTE": "La confirmation ne correspond pas au nouveau mot de passe.",
    "ANCIEN_MDP_INCORRECT": "L'ancien mot de passe est incorrect.",
    "NON_AUTHENTIFIE": "Veuillez vous connecter.",
    "ACCES_INTERDIT": "Vous n'avez pas les droits pour cette action.",
    "LOGIN_DEJA_UTILISE": "Ce nom d'utilisateur existe déjà.",
    "PARAMETRE_INCONNU": "Paramètre inconnu.",
    "PARAMETRE_INVALIDE": "Valeur invalide pour ce paramètre.",
    "STATUT_INVALIDE": "Statut de compte inconnu.",
    "COMPTE_CLOTURE": "Ce compte est clôturé : il ne peut plus être modifié.",
    "TACHE_DEJA_EXECUTEE": "Cette tâche mensuelle a déjà été exécutée ce mois-ci.",
    "MONTANT_TROP_PETIT": "Montant trop petit : après conversion, le compte destinataire ne recevrait rien.",
}

STATUTS_HTTP = {
    "COMPTE_INTROUVABLE": 404,
    "CLIENT_INTROUVABLE": 404,
    "BORDEREAU_INTROUVABLE": 404,
    "TRANSACTION_INTROUVABLE": 404,
    "IDENTITE_DEJA_UTILISEE": 409,
    "EPARGNE_DEJA_EXISTANT": 409,
    "DEVISE_DEJA_EXISTANT": 409,
    "LOGIN_DEJA_UTILISE": 409,
    "BORDEREAU_DEJA_TRAITE": 409,
    "TACHE_DEJA_EXECUTEE": 409,
    "BORDEREAU_EXPIRE": 410,
    "IDENTIFIANTS_INCORRECTS": 401,
    "NON_AUTHENTIFIE": 401,
    "ACCES_VERROUILLE": 423,
    "ACCES_DESACTIVE": 403,
    "MOT_DE_PASSE_TEMPORAIRE_EXPIRE": 401,
    "CHANGEMENT_MDP_REQUIS": 403,
    "ACCES_INTERDIT": 403,
}


class ErreurBancaire(Exception):

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        self.message = message or MESSAGES.get(code, code)
        self.status_http = STATUTS_HTTP.get(code, 422)
        super().__init__(f"{code}: {self.message}")
