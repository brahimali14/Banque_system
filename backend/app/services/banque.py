# poo
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import config
from app.domain import (
    CLASSES_COMPTE,
    Client,
    CompteBancaire,
    CompteCourant,
    CompteEpargne,
    ContexteRetrait,
    DemandeOperation,
    JournalAudit,
    Parametre,
    TauxChange,
    Transaction,
    Utilisateur,
)
from app.domain.enums import Role, StatutCompte, StatutDemande, TypeCompte, TypeOperation
from app.errors import ErreurBancaire
from app.functional.calculs import convertir
from app.functional.numeros import est_numero_valide, normaliser
from app.horloge import maintenant
from app.rules.imperative import nombre_retraits_du_mois, total_retire_le
from app.services.acces import ServiceAcces
from app.services.numeros import nouveau_numero_bordereau
from app.services.procedures import effectuerDepot, effectuerRetrait, verifierMontant

DEMANDES_EN_COURS = (StatutDemande.EN_ATTENTE, StatutDemande.EN_ATTENTE_SUPERVISEUR)
CHAMPS_CLIENT = ("numero_identite", "nom", "prenom", "telephone", "email", "adresse")
CHAMPS_MODIFIABLES_PAR_CLIENT = ("telephone", "email", "adresse")


class Banque:
    def __init__(self, db: Session):
        self.db = db
        self.acces = ServiceAcces(db)

    @contextmanager
    def atomique(self):
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def journaliser(self, utilisateur: Utilisateur | None, action: str, cible: str | None = None, details: str | None = None):
        self.db.add(
            JournalAudit(
                utilisateur_id=utilisateur.id if utilisateur else None,
                action=action,
                cible=cible,
                details=details,
                date=maintenant(),
            )
        )

    def parametre(self, cle: str) -> str:
        enregistrement = self.db.get(Parametre, cle)
        return enregistrement.valeur if enregistrement else config.PARAMETRES_PAR_DEFAUT[cle]

    def parametres(self) -> dict[str, str]:
        return {cle: self.parametre(cle) for cle in config.PARAMETRES_PAR_DEFAUT}

    def modifierParametre(self, cle: str, valeur: str, admin: Utilisateur) -> None:
        if cle not in config.PARAMETRES_PAR_DEFAUT:
            raise ErreurBancaire("PARAMETRE_INCONNU")
        Decimal(valeur)
        with self.atomique():
            enregistrement = self.db.get(Parametre, cle) or Parametre(cle=cle, valeur=valeur)
            enregistrement.valeur = valeur
            self.db.add(enregistrement)
            self.journaliser(admin, "MODIFICATION_PARAMETRE", cle, valeur)

    def seuilSuperviseur(self) -> Decimal:
        return Decimal(self.parametre("seuil_superviseur_dzd"))

    def tauxDeChange(self) -> dict[str, Decimal]:
        taux = {t.devise: t.taux_vers_dzd for t in self.db.scalars(select(TauxChange))}
        return {**config.TAUX_CHANGE_PAR_DEFAUT, **taux}

    def mettreAJourTaux(self, devise: str, taux: Decimal, admin: Utilisateur) -> None:
        if devise not in ("EUR", "USD") or taux <= 0:
            raise ErreurBancaire("DEVISE_INVALIDE")
        with self.atomique():
            enregistrement = self.db.get(TauxChange, devise) or TauxChange(devise=devise, taux_vers_dzd=taux)
            enregistrement.taux_vers_dzd = taux
            enregistrement.date_maj = maintenant()
            self.db.add(enregistrement)
            self.journaliser(admin, "MODIFICATION_TAUX", devise, str(taux))

    def enDinars(self, montant: Decimal, devise: str) -> Decimal:
        return convertir(montant, devise, "DZD", self.tauxDeChange())

    def ajouterClient(self, donnees: dict, agent: Utilisateur) -> tuple[Client, Utilisateur, str]:
        with self.atomique():
            if self.db.scalar(select(Client.id).where(Client.numero_identite == donnees["numero_identite"])):
                raise ErreurBancaire("IDENTITE_DEJA_UTILISEE")
            client = Client(**{cle: donnees.get(cle) for cle in CHAMPS_CLIENT}, date_creation=maintenant())
            self.db.add(client)
            self.db.flush()
            utilisateur, mot_de_passe = self.acces.creerAccesClient(client)
            self.journaliser(agent, "AJOUT_CLIENT", f"client:{client.id}", utilisateur.login)
        return client, utilisateur, mot_de_passe

    def modifierClient(self, client: Client, donnees: dict, auteur: Utilisateur) -> Client:
        champs = CHAMPS_MODIFIABLES_PAR_CLIENT if auteur.role == Role.CLIENT else CHAMPS_CLIENT
        with self.atomique():
            nouvelle_identite = donnees.get("numero_identite")
            if nouvelle_identite and nouvelle_identite != client.numero_identite:
                if self.db.scalar(select(Client.id).where(Client.numero_identite == nouvelle_identite)):
                    raise ErreurBancaire("IDENTITE_DEJA_UTILISEE")
            for cle in champs:
                if donnees.get(cle) is not None:
                    setattr(client, cle, donnees[cle])
            if client.utilisateur:
                client.utilisateur.nom_affiche = client.nom_complet
            self.journaliser(auteur, "MODIFICATION_CLIENT", f"client:{client.id}")
        return client

    def trouverClient(self, client_id: int) -> Client:
        client = self.db.get(Client, client_id)
        if client is None:
            raise ErreurBancaire("CLIENT_INTROUVABLE")
        return client

    def rechercherClients(self, terme: str | None = None) -> list[Client]:
        requete = select(Client).order_by(Client.nom, Client.prenom)
        if terme:
            motif = f"%{terme.strip()}%"
            requete = (
                requete.outerjoin(CompteBancaire)
                .where(
                    or_(
                        Client.nom.ilike(motif),
                        Client.prenom.ilike(motif),
                        Client.telephone.ilike(motif),
                        Client.numero_identite.ilike(motif),
                        CompteBancaire.numero.ilike(motif),
                    )
                )
                .distinct()
            )
        return list(self.db.scalars(requete))

    def reinitialiserAcces(self, client: Client, agent: Utilisateur) -> tuple[Utilisateur, str]:
        with self.atomique():
            if client.utilisateur is None:
                utilisateur, mot_de_passe = self.acces.creerAccesClient(client)
            else:
                utilisateur = client.utilisateur
                mot_de_passe = self.acces.reinitialiser(utilisateur)
            self.journaliser(agent, "REINITIALISATION_ACCES", utilisateur.login)
        return utilisateur, mot_de_passe

    def ouvrirCompte(self, client: Client, type_compte: str, devise: str | None, agent: Utilisateur) -> CompteBancaire:
        classe = CLASSES_COMPTE.get(type_compte)
        if classe is None:
            raise ErreurBancaire("TYPE_COMPTE_INVALIDE")
        devise = devise or classe.DEVISES_AUTORISEES[0]
        actifs = [c for c in client.comptes if c.statut != StatutCompte.CLOTURE]
        if classe is CompteEpargne and any(c.type_compte == TypeCompte.EPARGNE for c in actifs):
            raise ErreurBancaire("EPARGNE_DEJA_EXISTANT")
        if type_compte == TypeCompte.DEVISE and any(
            c.type_compte == TypeCompte.DEVISE and c.devise == devise for c in actifs
        ):
            raise ErreurBancaire("DEVISE_DEJA_EXISTANT")
        with self.atomique():
            compte = classe(devise=devise, numero=f"TMP-{secrets.token_hex(6)}")
            client.ajouterCompte(compte)
            self.db.flush()
            compte.numero = f"BS-{classe.PREFIXE}-{compte.id:06d}"
            self.journaliser(agent, "OUVERTURE_COMPTE", compte.numero, compte.LIBELLE)
        return compte

    def trouverCompte(self, numero: str) -> CompteBancaire:
        compte = self.db.scalar(select(CompteBancaire).where(CompteBancaire.numero == numero.strip().upper()))
        if compte is None:
            raise ErreurBancaire("COMPTE_INTROUVABLE")
        return compte

    def changerStatutCompte(self, compte: CompteBancaire, statut: str, superviseur: Utilisateur) -> CompteBancaire:
        statut = StatutCompte(statut)
        if statut == StatutCompte.CLOTURE:
            en_cours = any(d.statut in DEMANDES_EN_COURS for d in compte.demandes)
            if compte.solde != 0 or compte.montant_bloque != 0 or en_cours:
                raise ErreurBancaire("COMPTE_NON_VIDE")
        with self.atomique():
            compte.statut = statut
            self.journaliser(superviseur, f"COMPTE_{statut}", compte.numero)
        return compte

    def modifierDecouvert(self, compte: CompteBancaire, decouvert: Decimal, superviseur: Utilisateur) -> CompteBancaire:
        if not isinstance(compte, CompteCourant) or decouvert < 0:
            raise ErreurBancaire("TYPE_COMPTE_INVALIDE", "Seul un compte courant a un découvert autorisé.")
        with self.atomique():
            compte.decouvert_autorise = decouvert
            self.journaliser(superviseur, "MODIFICATION_DECOUVERT", compte.numero, str(decouvert))
        return compte

    def contexteRetrait(self, compte: CompteBancaire, instant: datetime) -> ContexteRetrait:
        en_cours = [d for d in compte.demandes if d.estRetrait() and d.statut in DEMANDES_EN_COURS]
        return ContexteRetrait(
            retire_aujourdhui=total_retire_le(compte.transactions, instant.date()) + compte.montant_bloque,
            retraits_ce_mois=nombre_retraits_du_mois(compte.transactions, instant.year, instant.month) + len(en_cours),
        )

    def creerDemande(self, compte: CompteBancaire, type_operation: str, montant, auteur: Utilisateur) -> DemandeOperation:
        if type_operation not in (TypeOperation.DEPOT, TypeOperation.RETRAIT):
            raise ErreurBancaire("TYPE_OPERATION_INVALIDE")
        valeur = verifierMontant(montant)
        compte.verifierActif()
        instant = maintenant()
        with self.atomique():
            if type_operation == TypeOperation.RETRAIT:
                compte.verifierRetrait(valeur, self.contexteRetrait(compte, instant))
                compte.bloquer(valeur)
            prefixe = "DEP" if type_operation == TypeOperation.DEPOT else "RET"
            demande = DemandeOperation(
                numero_bordereau=nouveau_numero_bordereau(self.db, prefixe),
                compte=compte,
                type=type_operation,
                montant=valeur,
                statut=StatutDemande.EN_ATTENTE,
                date_creation=instant,
                date_expiration=instant + timedelta(hours=int(self.parametre("validite_bordereau_heures"))),
                cree_par_id=auteur.id,
            )
            self.db.add(demande)
            self.journaliser(auteur, "CREATION_BORDEREAU", demande.numero_bordereau, f"{type_operation} {valeur}")
        return demande

    def trouverDemande(self, numero: str) -> DemandeOperation:
        demande = self.db.scalar(select(DemandeOperation).where(DemandeOperation.numero_bordereau == numero))
        if demande is None:
            raise ErreurBancaire("BORDEREAU_INTROUVABLE")
        return demande

    def _expirerSiNecessaire(self, demande: DemandeOperation) -> bool:
        if demande.estExpiree(maintenant()):
            demande.expirer()
            self.journaliser(None, "EXPIRATION_BORDEREAU", demande.numero_bordereau)
            self.db.commit()
            return True
        return False

    def _alerterSiEssaisRepetes(self, agent: Utilisateur) -> None:
        depuis = maintenant() - timedelta(minutes=5)
        essais = self.db.scalar(
            select(func.count(JournalAudit.id)).where(
                JournalAudit.utilisateur_id == agent.id,
                JournalAudit.action == "BORDEREAU_INTROUVABLE",
                JournalAudit.date >= depuis,
            )
        )
        if essais and essais >= 10:
            self.journaliser(agent, "ALERTE_ESSAIS_REPETES", details=f"{essais} numéros introuvables en 5 minutes")

    def _chargerBordereau(self, saisie: str, agent: Utilisateur) -> DemandeOperation:
        if not est_numero_valide(saisie):
            raise ErreurBancaire("NUMERO_INVALIDE")
        numero = normaliser(saisie)
        demande = self.db.scalar(select(DemandeOperation).where(DemandeOperation.numero_bordereau == numero))
        if demande is None:
            self.journaliser(agent, "BORDEREAU_INTROUVABLE", numero)
            self.db.flush()
            self._alerterSiEssaisRepetes(agent)
            self.db.commit()
            raise ErreurBancaire("BORDEREAU_INTROUVABLE")
        if self._expirerSiNecessaire(demande):
            raise ErreurBancaire("BORDEREAU_EXPIRE")
        demande.verifierTraitable()
        return demande

    def rechercherBordereau(self, saisie: str, agent: Utilisateur) -> DemandeOperation:
        demande = self._chargerBordereau(saisie, agent)
        self.journaliser(agent, "RECHERCHE_BORDEREAU", demande.numero_bordereau)
        self.db.commit()
        return demande

    def validerDemande(self, saisie: str, agent: Utilisateur) -> DemandeOperation:
        demande = self._chargerBordereau(saisie, agent)
        if demande.statut == StatutDemande.EN_ATTENTE_SUPERVISEUR and agent.role != Role.SUPERVISEUR:
            raise ErreurBancaire("APPROBATION_SUPERVISEUR")
        with self.atomique():
            depasse_seuil = self.enDinars(demande.montant, demande.compte.devise) > self.seuilSuperviseur()
            if depasse_seuil and agent.role != Role.SUPERVISEUR:
                demande.statut = StatutDemande.EN_ATTENTE_SUPERVISEUR
                demande.agent_id = agent.id
                self.journaliser(agent, "TRANSMISSION_SUPERVISEUR", demande.numero_bordereau)
            else:
                self._executerDemande(demande, agent)
        return demande

    def _executerDemande(self, demande: DemandeOperation, utilisateur: Utilisateur) -> Transaction:
        compte = demande.compte
        libelle = f"{'Dépôt' if demande.type == TypeOperation.DEPOT else 'Retrait'} — bordereau {demande.numero_bordereau}"
        if demande.type == TypeOperation.DEPOT:
            transaction = effectuerDepot(compte, demande.montant, libelle, utilisateur.id)
        else:
            compte.liberer(demande.montant)
            transaction = effectuerRetrait(
                compte, demande.montant, ContexteRetrait(retrait_especes=False), libelle, utilisateur.id
            )
        superviseur_id = utilisateur.id if utilisateur.role == Role.SUPERVISEUR else None
        demande.marquerValidee(transaction, utilisateur.id, superviseur_id)
        self.journaliser(utilisateur, "VALIDATION_BORDEREAU", demande.numero_bordereau, transaction.reference)
        return transaction

    def refuserDemande(self, saisie: str, agent: Utilisateur, motif: str) -> DemandeOperation:
        demande = self._chargerBordereau(saisie, agent)
        if demande.statut == StatutDemande.EN_ATTENTE_SUPERVISEUR and agent.role != Role.SUPERVISEUR:
            raise ErreurBancaire("APPROBATION_SUPERVISEUR")
        with self.atomique():
            demande.refuser(agent.id, motif.strip() or "Non précisé")
            self.journaliser(agent, "REFUS_BORDEREAU", demande.numero_bordereau, motif)
        return demande

    def demandesASuperviser(self) -> list[DemandeOperation]:
        return list(
            self.db.scalars(
                select(DemandeOperation)
                .where(DemandeOperation.statut == StatutDemande.EN_ATTENTE_SUPERVISEUR)
                .order_by(DemandeOperation.date_creation)
            )
        )

    def annulerDemande(self, demande: DemandeOperation, client: Utilisateur) -> DemandeOperation:
        with self.atomique():
            demande.annuler()
            self.journaliser(client, "ANNULATION_BORDEREAU", demande.numero_bordereau)
        return demande

    def expirerDemandes(self) -> int:
        instant = maintenant()
        demandes = self.db.scalars(
            select(DemandeOperation).where(
                DemandeOperation.statut == StatutDemande.EN_ATTENTE,
                DemandeOperation.date_expiration < instant,
            )
        ).all()
        with self.atomique():
            for demande in demandes:
                demande.expirer()
                self.journaliser(None, "EXPIRATION_BORDEREAU", demande.numero_bordereau)
        return len(demandes)

    def operationGuichet(self, compte: CompteBancaire, type_operation: str, montant, agent: Utilisateur) -> Transaction:
        valeur = verifierMontant(montant)
        if agent.role != Role.SUPERVISEUR and self.enDinars(valeur, compte.devise) > self.seuilSuperviseur():
            raise ErreurBancaire("APPROBATION_SUPERVISEUR")
        with self.atomique():
            if type_operation == TypeOperation.DEPOT:
                transaction = effectuerDepot(compte, valeur, "Dépôt au guichet", agent.id)
            elif type_operation == TypeOperation.RETRAIT:
                contexte = self.contexteRetrait(compte, maintenant())
                transaction = effectuerRetrait(compte, valeur, contexte, "Retrait au guichet", agent.id)
            else:
                raise ErreurBancaire("TYPE_OPERATION_INVALIDE")
            self.journaliser(agent, f"GUICHET_{type_operation}", compte.numero, str(valeur))
        return transaction

    def virement(self, source: CompteBancaire, destination: CompteBancaire, montant, auteur: Utilisateur) -> dict:
        valeur = verifierMontant(montant)
        if source.id == destination.id:
            raise ErreurBancaire("COMPTES_IDENTIQUES")
        agent_id = auteur.id if auteur.estPersonnel() else None
        with self.atomique():
            source.verifierActif()
            destination.verifierActif()
            motif = source.motifRefusVirementVers(destination)
            if motif:
                raise ErreurBancaire(motif)
            frais = source.calculerFrais(TypeOperation.VIREMENT_EMIS, valeur)
            montant_credite = convertir(valeur, source.devise, destination.devise, self.tauxDeChange())
            source.verifierRetrait(valeur + frais, ContexteRetrait(retrait_especes=False))

            emis = source.debiter(
                valeur, TypeOperation.VIREMENT_EMIS, f"Virement vers {destination.numero}", agent_id, destination.numero
            )
            if frais > 0:
                source.debiter(frais, TypeOperation.FRAIS, "Frais de virement", agent_id, destination.numero)
            recu = destination.crediter(
                montant_credite, TypeOperation.VIREMENT_RECU, f"Virement de {source.numero}", agent_id, source.numero
            )
            self.journaliser(auteur, "VIREMENT", f"{source.numero}->{destination.numero}", str(valeur))
        return {
            "reference": emis.reference,
            "reference_credit": recu.reference,
            "montant_debite": valeur,
            "frais": frais,
            "devise_source": source.devise,
            "montant_credite": montant_credite,
            "devise_destination": destination.devise,
            "nouveau_solde_source": source.solde,
        }

    def trouverTransaction(self, reference: str) -> Transaction:
        transaction = self.db.scalar(select(Transaction).where(Transaction.reference == reference.strip().upper()))
        if transaction is None:
            raise ErreurBancaire("TRANSACTION_INTROUVABLE")
        return transaction

    def verserInterets(self, admin: Utilisateur | None = None) -> int:
        comptes = self.db.scalars(select(CompteEpargne).where(CompteEpargne.statut == StatutCompte.ACTIF)).all()
        nombre = 0
        with self.atomique():
            for compte in comptes:
                interets = compte.calculerInteretsMensuels()
                if interets > 0:
                    compte.crediter(interets, TypeOperation.INTERETS, "Intérêts mensuels")
                    nombre += 1
            self.journaliser(admin, "TACHE_INTERETS", details=f"{nombre} comptes")
        return nombre

    def preleverFraisTenue(self, admin: Utilisateur | None = None) -> int:
        comptes = self.db.scalars(select(CompteCourant).where(CompteCourant.statut == StatutCompte.ACTIF)).all()
        with self.atomique():
            for compte in comptes:
                compte.debiter(compte.fraisTenueCompte(), TypeOperation.FRAIS, "Frais de tenue de compte")
            self.journaliser(admin, "TACHE_FRAIS_TENUE", details=f"{len(comptes)} comptes")
        return len(comptes)
