# declaratif
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

TOTAUX_PAR_TYPE = text(
    """
    SELECT type,
           COUNT(*)     AS nombre,
           SUM(montant) AS total_centimes
    FROM   transactions
    WHERE  compte_id = :compte_id
      AND  date >= :debut
      AND  date <= :fin
    GROUP  BY type
    ORDER  BY total_centimes DESC
    """
)

EVOLUTION_MENSUELLE = text(
    """
    SELECT strftime('%Y-%m', date) AS mois,
           SUM(CASE WHEN type IN ('DEPOT', 'VIREMENT_RECU', 'INTERETS') THEN montant ELSE 0 END) AS credits_centimes,
           SUM(CASE WHEN type IN ('RETRAIT', 'VIREMENT_EMIS', 'FRAIS')   THEN montant ELSE 0 END) AS debits_centimes
    FROM   transactions
    WHERE  compte_id = :compte_id
    GROUP  BY mois
    ORDER  BY mois
    """
)

ACTIVITE_DU_JOUR = text(
    """
    SELECT t.type,
           c.devise,
           COUNT(*)       AS nombre,
           SUM(t.montant) AS total_centimes
    FROM   transactions t
    JOIN   compte c ON c.id = t.compte_id
    WHERE  date(t.date) = date(:jour)
    GROUP  BY t.type, c.devise
    ORDER  BY t.type
    """
)

DEMANDES_PAR_STATUT = text(
    """
    SELECT statut, COUNT(*) AS nombre
    FROM   demande_operation
    GROUP  BY statut
    """
)

CLIENTS_ET_COMPTES = text(
    """
    SELECT (SELECT COUNT(*) FROM client)                          AS clients,
           (SELECT COUNT(*) FROM compte WHERE statut = 'ACTIF')   AS comptes_actifs
    """
)


def _texte(instant: datetime) -> str:
    return instant.strftime("%Y-%m-%d %H:%M:%S.%f")


def _montant(centimes) -> Decimal:
    return (Decimal(centimes or 0) / 100).quantize(Decimal("0.01"))


def totaux_par_type(db: Session, compte_id: int, debut: datetime, fin: datetime) -> list[dict]:
    lignes = db.execute(TOTAUX_PAR_TYPE, {"compte_id": compte_id, "debut": _texte(debut), "fin": _texte(fin)}).mappings()
    return [{"type": l["type"], "nombre": l["nombre"], "total": _montant(l["total_centimes"])} for l in lignes]


def evolution_mensuelle(db: Session, compte_id: int) -> list[dict]:
    lignes = db.execute(EVOLUTION_MENSUELLE, {"compte_id": compte_id}).mappings()
    return [
        {"mois": l["mois"], "credits": _montant(l["credits_centimes"]), "debits": _montant(l["debits_centimes"])}
        for l in lignes
    ]


def tableau_de_bord_agence(db: Session, jour: datetime) -> dict:
    activite = db.execute(ACTIVITE_DU_JOUR, {"jour": _texte(jour)}).mappings()
    demandes = db.execute(DEMANDES_PAR_STATUT).mappings()
    compteurs = db.execute(CLIENTS_ET_COMPTES).mappings().one()
    return {
        "jour": jour.date().isoformat(),
        "clients": compteurs["clients"],
        "comptes_actifs": compteurs["comptes_actifs"],
        "activite_du_jour": [
            {"type": l["type"], "devise": l["devise"], "nombre": l["nombre"], "total": _montant(l["total_centimes"])}
            for l in activite
        ],
        "demandes_par_statut": {l["statut"]: l["nombre"] for l in demandes},
    }
