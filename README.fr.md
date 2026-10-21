[English](README.md) | Français

# Pyxel AI Playground

Une application web où des collégiens créent un jeu rétro avec le moteur [Pyxel](https://github.com/kitao/pyxel) en discutant avec Pix, un tuteur IA qui construit le jeu étape par étape.

[![Licence Apache-2.0](https://img.shields.io/badge/licence-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/dmetzler/pyxel-ai-playground/actions/workflows/ci.yml/badge.svg)](https://github.com/dmetzler/pyxel-ai-playground/actions/workflows/ci.yml)

![Une session en français : l'élève discute avec Pix à gauche, le jeu « Le Serpent » tourne à droite, avec les boutons Exporter et Mon histoire (PDF) dans la barre du haut.](docs/images/serpent.png)

*Une session en cours : le jeu « Le Serpent » prend forme. À gauche, la discussion avec Pix. À droite, l'aperçu du jeu en direct.*

## Pourquoi {#pourquoi}

Ce projet est un outil pour les enseignants. Il sert à montrer aux élèves, dès le collège (vers 11 ans), comment on construit un logiciel aujourd'hui : **avec un agent IA**.

L'élève décrit ce qu'il veut. L'agent (Pix) fait un plan, modifie le code, teste le jeu, puis explique chaque changement en langage simple. L'élève garde la main : il peut lire et modifier le code, annuler une étape, dessiner ses propres sprites.

C'est un outil de classe ou d'atelier. Une séance typique ressemble à ceci :

1. L'élève crée un jeu et écrit une idée, par exemple « Je veux créer un jeu de labyrinthe ».
2. Pix propose une première version jouable et explique ce qu'il a fait.
3. L'élève joue, demande des changements (« les cailloux sont trop petits »), regarde le code, dessine un sprite.
4. Quand une idée ne marche pas, un clic sur **Annuler** revient à la version d'avant.
5. En fin de séance, l'élève repart avec son jeu en zip et le livret PDF de sa création.

## Fonctionnalités {#fonctionnalites}

### Les points forts {#points-forts}

- **Plusieurs jeux par élève.** L'écran d'accueil permet de créer un jeu, d'en rouvrir un ancien ou de le supprimer (avec confirmation, et refusé pendant que Pix y travaille). Chaque jeu a son adresse (`http://localhost:8080/serpent/`), donc on peut le mettre en favori ou rafraîchir la page sans le perdre.
- **Chaque jeu est un dépôt git.** Avant chaque tour de Pix, les modifications de l'élève sont enregistrées, puis celles de Pix. Le bouton **Annuler** sur un message de l'élève remet le jeu (code, ressources et mémoire de Pix) dans l'état d'avant et efface la suite de la discussion. L'annulation est elle-même un nouveau commit : rien n'est jamais perdu, `git log` dans le dossier du jeu montre tout.
- **Exporter et importer un jeu en zip.** **Exporter** dans la barre du haut télécharge le dossier complet du jeu (code, sprites, discussion, mémoire de Pix, historique git). **Importer un jeu** sur l'écran d'accueil recrée un jeu à partir d'un zip, sans jamais en écraser un existant. Un zip d'un simple dossier contenant un `game.py` fonctionne aussi. Les zips importés sont vérifiés (aucun chemin hors du dossier, aucun lien, tailles limitées) et leurs hooks et leur configuration git sont supprimés.
- **« Mon histoire » : un livret PDF de la création.** Le bouton **Mon histoire (PDF)** génère un livret que l'élève emporte chez lui (`backend/story.py`, WeasyPrint) : une couverture avec une capture de l'application et du jeu terminé, une page par message de l'élève (ce qu'il a demandé, l'explication de Pix, une capture du jeu après l'étape, les lignes de code ajoutées ou modifiées en vert), le code final complet, et la marche à suivre pour installer Pyxel et continuer à la maison. Chaque capture vient de l'exécution du `game.py` de ce commit, sans écran, pendant 30 images (`res_tool.py screenshot`).
- **Trois langues : français, anglais, polonais.** L'interface, le tuteur et le PDF existent en `fr`, `en` et `pl`. Un sélecteur de langue se trouve sur l'écran d'accueil et dans la barre du haut d'un jeu. Chaque jeu garde la langue dans laquelle il a été créé : c'est elle qui fixe la langue de Pix, des messages de commit et du livret PDF.

### Et aussi {#et-aussi}

- **Aperçu en direct.** Le vrai Pyxel tourne dans le navigateur (Pyodide et la roue Pyxel), dans un iframe isolé. Le jeu se recharge à la fin de chaque tour de Pix.
- **Onglet Code avec marge des changements.** L'élève lit et modifie `game.py`. Une fine marge colorée marque les lignes ajoutées (vert), modifiées (jaune) ou supprimées (rouge) par le dernier commit, pour voir ce que Pix vient de faire. Le code affiché est enregistré avant chaque message, et Pix doit le relire avant de s'en servir.
- **Éditeur de sprites et de sons.** L'onglet Sprites intègre l'éditeur de ressources officiel de Pyxel (images, tilemaps, sons, musiques). Son bouton de sauvegarde écrit `res.pyxres` dans le dossier du jeu, et l'aperçu le charge (`pyxel.load("res.pyxres")`, `pyxel.blt(...)`). **Recharger** relit le fichier enregistré.
- **Pix dessine et teste.** L'outil `edit_resources` exécute un petit script Python avec Pyxel sans écran (`backend/res_tool.py`, limite de 20 s, sur une copie : si le script échoue, le fichier reste intact et Pix reçoit l'erreur pour corriger). Il dessine des sprites pixel par pixel, compose des tilemaps, écrit sons et musiques dans `res.pyxres`, que l'élève retouche ensuite dans l'onglet Sprites. `view_resources` donne à Pix une description du fichier actuel, donc les retouches de l'élève sont conservées. `test_game` lance le jeu 60 images et renvoie le plantage éventuel.
- **Bouton Arrêter.** Il coupe Pix en plein tour. Ce qu'il a déjà fait est gardé et enregistré.

## Comment ça marche {#fonctionnement}

- **Frontend** (`frontend/`) : Vite, React et TypeScript. À gauche, la discussion avec Pix. À droite, les onglets Aperçu, Code et Sprites.
- **Backend** (`backend/`) : FastAPI. Pix est un agent [Strands harness](https://strandsagents.com/docs/user-guide/harness/) (`backend/pix_agent.py`) dont le modèle est un endpoint compatible OpenAI, typiquement [LiteLLM](https://docs.litellm.ai/). La clé d'API n'arrive jamais dans le navigateur.
- **Modèle d'édition.** Pix travaille comme un agent de code, directement dans le dossier du jeu : `read`, `write` et `edit` sur `game.py` (fournis par le harness), plus `view_resources`, `edit_resources` et `test_game`. Lors d'un tour, il peut enchaîner plusieurs appels d'outils (lire, modifier, tester, corriger), puis écrit une courte explication pour l'élève. À la fin, le backend envoie le nouveau `game.py` et `res.pyxres` à l'interface, qui met à jour l'éditeur et recharge l'aperçu.
- **Sécurité.** Les outils de fichiers sont limités au dossier du jeu (`GameFolderSandbox`) et il n'y a pas de shell. La conversation de Pix, appels d'outils compris, est conservée dans `games/<nom>/.pix/` : elle reprend là où elle s'était arrêtée après un redémarrage.
- **Stockage.** Chaque jeu est un dossier `games/<nom>/` (et un dépôt git) avec `game.py` (aussi exécutable avec Pyxel de bureau : `pyxel run games/<nom>/game.py`), `chat.json`, `meta.json` (dont la langue du jeu) et `res.pyxres` dès que l'élève a dessiné. Pour les ranger ailleurs, définissez `GAMES_DIR`.

## Démarrage rapide avec Docker {#docker}

```bash
cp backend/.env.example backend/.env   # renseignez LITELLM_API_KEY et LITELLM_MODEL
docker compose up -d --build
```

Ouvrez ensuite http://localhost:8080 (changez le port avec `PORT=9000 docker compose up -d`).

- `frontend` : l'application construite, servie par nginx, qui relaie `/api` vers `backend` (sans mise en mémoire tampon, pour le flux des réponses).
- `backend` : FastAPI et Pyxel sans écran. Les jeux sont stockés dans `./games` sur votre disque (volume monté).
- LiteLLM est attendu sur la machine hôte : par défaut, le backend appelle `http://host.docker.internal:4001`. Si LiteLLM tourne ailleurs, définissez `LITELLM_BASE_URL` dans votre shell ou dans un fichier `.env` à côté de `docker-compose.yml` (par exemple `LITELLM_BASE_URL=http://host.docker.internal:4000`). La valeur `localhost` de `backend/.env` est ignorée par Docker, car `localhost` désigne alors le conteneur lui-même.

## Déploiement sur Kubernetes (Helm) {#kubernetes}

Le chart `charts/pyxel-ai-playground` déploie l'application pour une classe ou un établissement. Les élèves s'y connectent avec le compte de votre fournisseur d'identité (Keycloak, Google, tout fournisseur OIDC).

La connexion est assurée par un sidecar [oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/) placé dans le pod du frontend, devant nginx. Le Service et l'Ingress parlent à oauth2-proxy : personne n'atteint l'application sans s'être authentifié. Le backend, lui, n'est joignable que depuis nginx, et garde les jeux sur un volume de 5 Gi.

```
Ingress -> oauth2-proxy (:4180) -> nginx (SPA + /api) -> backend (:8000) -> volume des jeux
```

Exemple d'installation :

```bash
helm install pyxel charts/pyxel-ai-playground -n pyxel --create-namespace \
  --set oauth2Proxy.issuerUrl=https://keycloak.example.com/realms/school \
  --set oauth2Proxy.clientId=pyxel \
  --set oauth2Proxy.clientSecret=<secret> \
  --set oauth2Proxy.cookieSecret=$(openssl rand -base64 32 | tr -- '+/' '-_' | head -c 32) \
  --set openai.baseUrl=http://litellm:4000 \
  --set openai.apiKey=<cle> \
  --set ingress.enabled=true \
  --set ingress.host=pyxel.example.com
```

Les valeurs à connaître (toutes dans `charts/pyxel-ai-playground/values.yaml`) :

| Clé | Rôle |
|---|---|
| `oauth2Proxy.issuerUrl`, `oauth2Proxy.clientId`, `oauth2Proxy.clientSecret`, `oauth2Proxy.cookieSecret` | Connexion OIDC (obligatoires quand `auth.enabled=true`) |
| `oauth2Proxy.existingSecret` | Secret existant avec les clés `client-id`, `client-secret` et `cookie-secret` |
| `oauth2Proxy.emailDomains`, `oauth2Proxy.allowedGroups` | Restreindre l'accès à des domaines de messagerie ou à des groupes du fournisseur |
| `openai.baseUrl`, `openai.model`, `openai.apiKey` | Endpoint compatible OpenAI (LiteLLM) utilisé par Pix |
| `openai.existingSecret` | Secret existant contenant la clé d'API sous la clé `api-key` |
| `maxTokens` | Nombre maximal de tokens par réponse de Pix |
| `persistence.size`, `persistence.storageClass`, `persistence.existingClaim` | Volume des jeux |
| `ingress.enabled`, `ingress.className`, `ingress.host`, `ingress.tls` | Exposition HTTP(S) |
| `auth.enabled` | `false` retire oauth2-proxy : réservé aux essais locaux, l'application n'est alors plus protégée |

`ingress.host` ou `oauth2Proxy.redirectUrl` est nécessaire pour construire l'adresse de retour de la connexion. Sans aucune valeur, l'installation échoue avec le message `openai.apiKey is required (or set openai.existingSecret)`.

Les images sont publiées sur GitHub Container Registry : `ghcr.io/dmetzler/pyxel-ai-playground-backend` et `ghcr.io/dmetzler/pyxel-ai-playground-frontend`.

## Développement {#developpement}

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # renseignez LITELLM_BASE_URL, LITELLM_API_KEY, LITELLM_MODEL
uvicorn app:app --reload --port 8000
```

Le livret PDF a besoin de Pango sur la machine (WeasyPrint) : `brew install pango` sur macOS, `apt install libpango-1.0-0 libpangoft2-1.0-0` sur Debian ou Ubuntu.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, relaie /api vers :8000
```

Ouvrez le navigateur, tapez « Je veux créer un jeu de labyrinthe », et c'est parti.

### Ajouter une langue

Côté frontend, ajoutez la langue dans `frontend/src/i18n.ts` (TypeScript signale toute clé manquante) et dans `frontend/src/starter.ts`. Côté backend, ajoutez `backend/prompt_<langue>.md`, les chaînes de `backend/i18n.py`, puis autorisez la langue dans l'API.

## Tests {#tests}

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q
cd frontend && npm test
```

- Backend (`backend/tests/`) : la vraie application FastAPI, le harness Strands, git et Pyxel sans écran, avec un modèle scripté à la place de LiteLLM (ni réseau, ni clé d'API). Les tests couvrent l'enregistrement et le chargement des jeux, le flux du chat et ses commits, le bac à sable des fichiers, l'arrêt, l'annulation, la suppression, l'export et l'import (zips dangereux compris), le livret PDF, les langues et `res_tool.py`.
- Frontend (`frontend/src/*.test.ts`, Vitest) : le calcul de la marge des changements, le nettoyage du texte du chat, l'analyse du flux SSE, les appels à l'API et la complétude des traductions.

## Organisation du projet {#organisation}

```
backend/
  app.py          API : jeux sur disque, historique git, flux du chat (SSE), arrêt, annulation, export/import
  pix_agent.py    l'agent Pix : harness Strands, bac à sable, outils de ressources et de test
  res_tool.py     Pyxel sans écran : dessiner dans res.pyxres, le décrire, tester ou capturer un jeu
  story.py        le livret PDF d'un jeu (WeasyPrint)
  i18n.py         textes du backend en fr, en, pl
  assets/         la capture de l'application utilisée sur la couverture du PDF
  prompt_*.md     le prompt du tuteur, une version par langue
  tests/          suite pytest
frontend/src/
  App.tsx         choix du jeu, routage par URL, tour de chat, annulation, boutons Exporter et PDF
  GamePicker.tsx  écran d'accueil : créer, ouvrir, supprimer, importer
  ChatPane.tsx    la discussion (boutons Arrêter et Annuler)
  RightPane.tsx   onglets Aperçu, Code, Sprites
  changeGutter.ts la marge « ce qui a changé » dans l'éditeur de code
  pyxelFrame.ts   Pyxel dans le navigateur (Pyodide) pour l'aperçu et l'éditeur de ressources
  api.ts          appels au backend et analyse du flux SSE
  i18n.ts         dictionnaires fr, en, pl
charts/           chart Helm pyxel-ai-playground
docs/images/      capture d'écran du README
games/            un dossier (et un dépôt git) par jeu, non versionné ici
```

## Licence {#licence}

Ce projet est publié sous licence [Apache 2.0](LICENSE).
