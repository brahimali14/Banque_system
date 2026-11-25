# BankServices

Application Web de gestion des services bancaires — TP *Génie Logiciel : paradigmes de programmation*.
Simulateur pédagogique : **toutes les données sont fictives**.

| Partie | Technologies | État |
|---|---|---|
| Étude et conception | Markdown + Mermaid → PDF | ✅ [docs/ETUDE_SYSTEME.pdf](docs/ETUDE_SYSTEME.pdf) |
| Rapport sur les paradigmes | Markdown + Mermaid → PDF | ✅ [docs/RAPPORT_PARADIGMES.pdf](docs/RAPPORT_PARADIGMES.pdf) · explication en arabe : [docs/RAPPORT_PARADIGMES_AR.pdf](docs/RAPPORT_PARADIGMES_AR.pdf) |
| Backend | Python 3.12+ · FastAPI · SQLAlchemy · SQLite · ReportLab | ✅ |
| Tests backend | Pytest (124 tests) | ✅ |
| Frontend | React 19 · Vite · React Router · Recharts | ✅ |
| Tests frontend | Vitest + Testing Library (23 tests) | ✅ |
| Langues de l'interface | Français · English · العربية (de droite à gauche) | ✅ |

Les sources des documents sont les fichiers `.md` de `docs/`. Pour régénérer les PDF après une modification
(Microsoft Edge ou Google Chrome et une connexion Internet sont nécessaires) :

```bash
python docs/build_pdf.py
```

## Installation et lancement du backend

Prérequis : Python 3.12 ou plus récent.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux / macOS : source .venv/bin/activate)
pip install -r requirements.txt
python -m app.seed --reset      # crée la base SQLite avec les données fictives
uvicorn app.main:app --reload   # API sur http://localhost:8000
```

Documentation interactive de l'API (Swagger) : **http://localhost:8000/docs**
(bouton *Authorize* : coller le `jeton` renvoyé par `POST /api/auth/connexion`).

## Installation et lancement du frontend

Prérequis : Node.js 20 ou plus récent. L'API doit tourner sur le port 8000 (Vite lui redirige les appels `/api`).

```bash
cd frontend
npm install
npm run dev                     # interface sur http://localhost:5173
```

La langue se choisit en haut de l'écran (français, anglais ou arabe) et reste mémorisée.
Les documents PDF (bordereaux, reçus, relevés) et les libellés enregistrés en base restent en français.

### Lancer les tests

```bash
cd backend
python -m pytest
```

```bash
cd frontend
npm test
```

## Comptes de démonstration

Mots de passe **de test uniquement**, définis dans [backend/app/seed.py](backend/app/seed.py).

| Rôle | Nom d'utilisateur | Mot de passe |
|---|---|---|
| Administrateur | `admin` | `12345678` |
| Superviseur | `s.haddad` | `12345678` |
| Agent | `a.mansouri` / `k.belkacem` | `12345678` |
| Client | `amine.benali`, `sara.boudiaf`, `karim.ziani`… | `12345678` |
| Client en **première connexion** | `yasmine.kaci` | `12345678` (doit le changer) |

Ce mot de passe simple est enregistré directement par `seed.py`. Un mot de passe choisi depuis l'application (première connexion, « Changer mon mot de passe ») doit respecter les règles de robustesse.

`python -m app.seed --reset` affiche aussi 3 numéros de bordereaux en attente à saisir au guichet.

## Fonctionnalités principales

- **Clients** : ajout (avec génération automatique du nom d'utilisateur et d'un mot de passe temporaire), modification, fiche, recherche.
- **Première connexion** : changement de mot de passe obligatoire, verrouillage après 5 échecs, réinitialisation par l'agent.
- **Comptes** : courant (pas de découvert, sauf s'il est accordé par le superviseur), épargne (intérêts, 2 retraits / mois, solde minimum), devise (EUR / USD).
- **Bordereaux** : le client demande un dépôt / retrait en ligne → PDF avec un **numéro unique** (ex. `RET-K7M2-9QXB`) → l'agent **tape le numéro** au guichet (pas besoin de caméra) → Accepter / Refuser → reçu PDF.
- **Retrait** : le montant est réservé dès la demande, libéré en cas de refus, d'annulation ou d'expiration (24 h).
- **Superviseur** : approbation au-dessus de 500 000 DA, blocage / clôture de compte, tableau de bord.
- **Virement atomique** avec frais et conversion de devise.
- **Statistiques** : historique filtrable, totaux, évolution mensuelle, relevé PDF.
- **Administration** : agents, paramètres (valeurs contrôlées), taux de change, journal d'audit, tâches mensuelles (une seule fois par mois ; les frais ne rendent jamais un solde négatif).

## Où trouver chaque paradigme

| Paradigme | Fichiers |
|---|---|
| Impératif | [backend/app/rules/imperative.py](backend/app/rules/imperative.py) |
| Procédural | [backend/app/services/procedures.py](backend/app/services/procedures.py) — `calculerSolde`, `verifierMontant`, `effectuerDepot`, `effectuerRetrait`, `calculerTotalOperations` |
| Orienté objet | [backend/app/domain/](backend/app/domain/) (`CompteBancaire` → `CompteCourant`, `CompteEpargne`, `CompteDevise`) et [backend/app/services/banque.py](backend/app/services/banque.py) |
| Fonctionnel | [backend/app/functional/](backend/app/functional/) et [frontend/src/utils/](frontend/src/utils/) — `filter` / `map` / `reduce`, frais, conversion, numéros, montant en lettres |
| Déclaratif | [backend/app/services/statistiques.py](backend/app/services/statistiques.py) (requêtes SQL) · composants React, ex. [Interface.jsx](frontend/src/components/Interface.jsx) (`Tableau` décrit par ses colonnes) |
| Événementiel | [Guichet.jsx](frontend/src/pages/agent/Guichet.jsx) (`onChange`, `onKeyDown`, `onClick`), [Session.jsx](frontend/src/auth/Session.jsx) (événements `session-expiree`), filtres de [DetailCompte.jsx](frontend/src/pages/DetailCompte.jsx) |

## Structure

```
Banque_system/
├── docs/                    étude, rapport sur les paradigmes (fr + ar) : sources .md, PDF (python docs/build_pdf.py)
└── backend/
    ├── app/
    │   ├── domain/          classes métier (POO) = tables SQLAlchemy
    │   ├── rules/           paradigme impératif
    │   ├── services/        procédures, classe Banque, accès, statistiques SQL
    │   ├── functional/      fonctions pures
    │   ├── security/        mots de passe (bcrypt), JWT, rôles
    │   ├── pdf/             bordereau, reçu, fiche d'identifiants, relevé
    │   ├── routers/         routes de l'API REST
    │   ├── main.py          application FastAPI
    │   └── seed.py          données fictives
    └── tests/               tests Pytest
frontend/
    ├── src/
    │   ├── api/             appels à l'API (erreurs { code, message })
    │   ├── auth/            session, déconnexion automatique
    │   ├── i18n/            français / anglais / arabe
    │   ├── components/      composants déclaratifs (Tableau, Badge, Alerte…)
    │   ├── pages/           client/, agent/, superviseur/, admin/
    │   ├── utils/           fonctions pures (montants, statistiques, numéros)
    │   └── __tests__/       tests Vitest
    └── vite.config.js
```
