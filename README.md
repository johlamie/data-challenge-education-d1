# Tableau de bord « Décrochage scolaire au primaire · Burkina Faso » – code de l'application (Unica Labs)

Data Challenge Éducation, défi 1. Ce dossier contient le code de l'application web déployée sur
https://decrochage.unicalabs.bf (accès par code, communiqué au jury), avec le jeu de **données fictives**
de son mode démonstration.

- Aucune donnée réelle du concours, aucun mot de passe, aucun code d'accès n'est présent ici.
- Le code source complet du défi (scripts Python de nettoyage et de transformation, équivalents des recettes
  Dataiku DSS, modèles, application) est publié sur https://github.com/johlamie/data-challenge-education-d1.

## Lancer en local sur les données fictives

Prérequis : Python 3.12 (les versions des bibliothèques sont figées pour cette version).

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest                    # 107 tests passent, 3 sont ignorés (ils demandent la base réelle)
python outils/demo_fictif.py        # puis ouvrir http://127.0.0.1:8050
```

Le mode démonstration n'a besoin ni de base de données ni de réseau. Il désactive le code d'accès, n'écoute
que sur `127.0.0.1` et affiche un bandeau « Données fictives » sur chaque page :

- les valeurs sont générées par `dcdash/demo.py` (cohérentes entre pages, mais inventées) ;
- la carte utilise `dcdash/geo_demo.json`, des contours **schématiques** du Burkina Faso (45 provinces,
  13 régions) produits hors ligne par `outils/generer_geo_demo.py` ; ce ne sont pas les limites officielles.

Aucun chiffre, nom de province en tête ou classement vu en mode démonstration n'est un résultat du défi.

## Pages

| Chemin | Contenu |
|---|---|
| `/` | Vue d'ensemble sur un écran : 6 chiffres clés, 10 provinces les plus à risque, carte (score de risque, taux d'abandon ou risque l'an prochain). |
| `/classement` | Classement complet, triable et filtrable, export CSV, carte du critère choisi ; découpage ancien (45 provinces) ou 2025 (47 provinces). |
| `/fiche?pcode=…` | Fiche d'une province : chiffres clés, carte de localisation, contributions au score, insécurité, indicateurs et rangs, qualité des données. |
| `/evolution` | Séries par province ou par région, comparaison de 8 entités au plus. |
| `/qualite` | Valeurs estimées par source, limites connues, fiabilité des contours. |
| `/methode` | Définitions, poids, robustesse, modèle, sources et licences, déclaration d'usage de l'IA. |

## Structure

| Élément | Rôle |
|---|---|
| `wsgi.py` | Point d'entrée de production (`gunicorn wsgi:server`). |
| `dcdash/app.py` | Création de l'application Dash, routage des pages. |
| `dcdash/config.py` | Configuration lue dans l'environnement ; aucun secret n'a de valeur par défaut. |
| `dcdash/auth.py` | Code d'accès partagé (empreinte scrypt), session signée, limite d'essais par adresse, en-têtes de sécurité et CSP. |
| `dcdash/db.py`, `dcdash/vues.py` | Lecture seule des quatre vues PostgreSQL `analyse.v_dashboard_*` (production). |
| `dcdash/demo.py`, `dcdash/geo_demo.json` | Données et contours fictifs du mode démonstration. |
| `dcdash/calculs.py`, `dcdash/meta.py` | Calculs d'affichage (rangs, tendances), libellés et définitions des indicateurs. |
| `dcdash/figures.py`, `dcdash/composants.py`, `dcdash/aides.py` | Cartes et graphiques (Plotly), composants d'interface, textes des infobulles. |
| `dcdash/pages/` | Une page par fichier : `accueil`, `classement`, `fiche`, `evolution`, `qualite`, `methode`. |
| `assets/` | Feuilles de style (`tokens.css` : couleurs et tailles ; `style.css` ; une feuille par page), scripts, icônes, Bootstrap servi localement. |
| `outils/` | `demo_fictif.py` (lancement local), `generer_geo_demo.py` (contours fictifs), `demo_synthetique.py` (jeu des tests), `captures.py` et `verifier_refonte.py` (contrôles dans un navigateur sans écran, demandent Playwright). |
| `tests/` | Tests `pytest` sur données synthétiques : authentification, calculs, pages, rappels Dash, requêtes. |
| `requirements*.txt` | Versions figées (`requirements.in` et `requirements-dev.in` : listes d'origine). |
| `.env.example` | Variables d'environnement, sans valeur réelle. |

L'application ne charge aucune ressource externe : cartes dessinées en polygones (sans tuiles), polices du système,
politique CSP `default-src 'self'`.

## Avec une base réelle (production)

L'application lit quatre vues PostgreSQL par un rôle en lecture seule. La connexion, l'empreinte du code d'accès
et la clé de session se donnent uniquement par l'environnement (voir `.env.example` et `dcdash/config.py`).
Les fichiers de déploiement du serveur (service, proxy, génération des secrets) ne font pas partie de ce dossier.

## Ce qui a été retiré par rapport au dépôt de travail

Historique Git, fichiers de déploiement, notes et spécifications internes de conception, fichiers de l'outillage de
développement.
