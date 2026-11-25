from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Integer, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator

from app import config

CENTIME = Decimal("0.01")


class Base(DeclarativeBase):
    pass


class Montant(TypeDecorator):

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return int((Decimal(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return (Decimal(value) / 100).quantize(CENTIME)


class DecimalTexte(TypeDecorator):

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(Decimal(value))

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)


def creer_moteur(url: str = config.DATABASE_URL, **options):
    moteur = create_engine(url, connect_args={"check_same_thread": False}, **options)

    @event.listens_for(moteur, "connect")
    def _activer_cles_etrangeres(connexion, _):
        connexion.execute("PRAGMA foreign_keys=ON")

    return moteur


moteur = creer_moteur()
SessionLocale = sessionmaker(bind=moteur, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()
