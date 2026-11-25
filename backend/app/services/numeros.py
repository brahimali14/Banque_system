import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.functional.numeros import ALPHABET, LONGUEUR_CORPS, composer_numero


def tirer_numero(prefixe: str) -> str:
    corps = "".join(secrets.choice(ALPHABET) for _ in range(LONGUEUR_CORPS))
    return composer_numero(prefixe, corps)


def nouveau_numero_bordereau(db: Session, prefixe: str) -> str:
    from app.domain import DemandeOperation

    while True:
        numero = tirer_numero(prefixe)
        existe = db.scalar(select(DemandeOperation.id).where(DemandeOperation.numero_bordereau == numero))
        if existe is None:
            return numero
