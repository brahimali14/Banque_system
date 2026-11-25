from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import config
from app.database import Base, moteur
from app.domain import Parametre, TauxChange
from app.errors import ErreurBancaire
from app.routers import admin, auth, clients, comptes, espace_client, guichet


def initialiser_base(moteur_bd) -> None:
    Base.metadata.create_all(moteur_bd)
    with Session(moteur_bd) as db:
        for cle, valeur in config.PARAMETRES_PAR_DEFAUT.items():
            if db.get(Parametre, cle) is None:
                db.add(Parametre(cle=cle, valeur=valeur))
        for devise, taux in config.TAUX_CHANGE_PAR_DEFAUT.items():
            if devise != "DZD" and db.get(TauxChange, devise) is None:
                db.add(TauxChange(devise=devise, taux_vers_dzd=taux))
        db.commit()


def creer_application(moteur_bd=moteur) -> FastAPI:
    @asynccontextmanager
    async def cycle_de_vie(_):
        initialiser_base(moteur_bd)
        yield

    application = FastAPI(
        title="BankServices API",
        description="Simulateur bancaire pédagogique — paradigmes de programmation. Données fictives.",
        version="1.0.0",
        lifespan=cycle_de_vie,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    @application.exception_handler(ErreurBancaire)
    async def erreur_bancaire(_: Request, erreur: ErreurBancaire):
        return JSONResponse(status_code=erreur.status_http, content={"code": erreur.code, "message": erreur.message})

    @application.exception_handler(RequestValidationError)
    async def donnees_invalides(_: Request, erreur: RequestValidationError):
        champs = [".".join(str(p) for p in e["loc"][1:]) for e in erreur.errors()]
        return JSONResponse(
            status_code=422,
            content={
                "code": "DONNEES_INVALIDES",
                "message": "Certaines données sont manquantes ou invalides : " + ", ".join(champs),
                "champs": champs,
            },
        )

    @application.get("/api/sante", tags=["Santé"])
    def sante():
        return {"statut": "ok", "application": config.NOM_BANQUE}

    for module in (auth, clients, espace_client, comptes, admin):
        application.include_router(module.routeur)
    application.include_router(guichet.routeur_agent)
    application.include_router(guichet.routeur_superviseur)
    return application


app = creer_application()
