"""Page 6 : méthode, sources, licences et déclaration d'usage de l'IA.

C'est un document, pas un tableau de bord : un sommaire qui reste à l'écran à gauche, une colonne
de texte mesurée à 72 caractères à droite, une section par question qu'on vient y chercher. Chaque
section s'ouvre sur une phrase en français courant qui dit ce qu'on va y trouver ; le corps, lui,
est conservé mot pour mot — chiffres, poids, formules, sources et licences sont le contenu, pas
de la mise en forme, et aucun n'est reformulé.

Les ancres sont de simples liens « # » : aucun script, aucune bibliothèque, rien à charger.
"""
from dash import dcc, html

from ..composants import bloc, titre

# ---------------------------------------------------------------------------
# (ancre, titre de section, phrase d'introduction ajoutée, corps conservé mot pour mot)
# Le corps vient du jalon c : ne rien y recalculer, ne rien y arrondir, ne rien y renommer.
# ---------------------------------------------------------------------------
SECTIONS = [
    ("chiffres-cles", "Chiffres clés de la vue d'ensemble",
     "Chaque chiffre de la page d'accueil, avec son mode de calcul et la vue de la base d'où il sort.",
     r"""
Tous les chiffres sont calculés à l'affichage à partir des vues `analyse.v_dashboard_*` (aucune valeur saisie à la main).

| Chiffre | Calcul | Vue source |
|---|---|---|
| Taux d'abandon national | Abandon harmonisé des 13 régions (ancien découpage), pondéré par l'effectif de base des flux CP1-CM1 ; évolution = écart en points avec l'année précédente | `v_dashboard_region_annee` |
| Provinces en alerte pour l'an prochain | Nombre de provinces dont la probabilité d'être dans le quart le plus touché par l'abandon l'année suivante est ≥ 50 % (sexe Ensemble ; disponible de 2020-2021 à 2024-2025) | `v_dashboard_province_annee` |
| Écart filles – garçons | Taux national des filles moins taux national des garçons (points) ; « estimé » si la ventilation par sexe est imputée pour la majorité des provinces | `v_dashboard_region_annee` |
| Province la plus à risque | Rang 1 de l'indice de risque v2 pour l'année et le sexe choisis | `v_dashboard_province_annee` |
| Élèves ayant abandonné (estimation) | Σ (taux d'abandon harmonisé de la région × effectif de base des flux CP1-CM1) / 100, arrondi à la centaine | `v_dashboard_region_annee` |
| Personnes déplacées internes | Somme des PDI des régions (sexe Ensemble) et taux pour 1 000 habitants | `v_dashboard_region_annee` |

Le **score de risque (0-100)** est l'indice de risque v2 ramené entre 0 (province la moins à risque de l'année)
et 100 (la plus à risque). La colonne **Classement** du top 10 indique la robustesse du rang : *très sûr* = dans le
top 10 pour au moins 90 % des 2 000 jeux de poids tirés au hasard ; *probable* = 50 à 90 % ; *incertain* = 10 à 50 %.
"""),
    ("abandon", "Arbitrage : définition de l'abandon",
     "Deux façons de mesurer l'abandon étaient possibles ; voici celle qui a été retenue, et pourquoi.",
     r"""
| Option | Description | Retenue |
|---|---|---|
| Abandon harmonisé | Taux résiduel pondéré par les flux d'effectifs (CP1-CM1), sans plancher à 0 | **Oui** : indice, ciblage et vue d'ensemble |
| Moyenne sur 2 ans | Même calcul sur les flux poolés de deux années | Contrôle de stabilité seulement |

Raison : le taux harmonisé réagit à l'année en cours et reste comparable entre provinces, ce qui permet le mieux de
décider en situation réelle. La moyenne sur 2 ans, plus lisse, sert à repérer les années atypiques.
"""),
    ("definitions", "Définitions",
     "Le sens exact des termes employés partout ailleurs dans le tableau de bord.",
     r"""
- **Abandon harmonisé (définition retenue)** : taux d'abandon résiduel (apparent) CP1-CM1 calculé sur les flux
  d'effectifs (méthode DGESS), pondéré par les flux et sans plancher (non tronqué à 0). Une valeur négative signale des entrées nettes. Aux niveaux
  région et national, les flux des provinces sont sommés avant le calcul.
- **Abandon moyenne 2 ans (contrôle)** : même calcul sur les flux poolés de deux années consécutives ; plus lisse.
- **Abandon publié (référence)** : taux publié dans les annuaires (moyenne simple des niveaux, tronquée à 0).
- **Indice de risque v2** : moyenne pondérée de six composantes standardisées (z-score dans l'année et le sexe,
  borné à ±3 ; valeurs manquantes remplacées par la moyenne). Une valeur positive signale un risque supérieur à la
  moyenne des provinces. L'échelle 0-100 est un min-max dans l'année et le sexe.
- **Probabilité de risque en t+1** : probabilité qu'une province soit dans le quart supérieur (12 provinces sur 45)
  de l'abandon harmonisé l'année suivante. Consensus de trois modèles (régression logistique, forêt aléatoire,
  gradient boosting), sexe Ensemble. 2020-2023 : prédictions hors échantillon (rolling origin) ; 2024-2025 :
  prévision pour 2025-2026 (modèle entraîné sur toutes les années).
"""),
    ("poids", "Poids de l'indice v2",
     "Ce que pèse chacune des six composantes dans le score de risque.",
     r"""
| Composante | Poids | Sens |
|---|---|---|
| Abandon harmonisé | 0,30 | + |
| Redoublement | 0,15 | + |
| PDI pour 1 000 habitants | 0,20 | + |
| Élèves par maître | 0,15 | + |
| Écoles avec eau potable | 0,10 | − (inversé) |
| Écoles avec latrines | 0,10 | − (inversé) |
"""),
    ("robustesse", "Robustesse (sexe Ensemble, moyenne 2017-2024)",
     "Ce que devient le classement quand on change les poids ou la méthode : s'il bouge peu, il est solide. "
     "Le coefficient de Spearman compare deux classements — 1 signifie identiques, 0 sans rapport.",
     r"""
| Test | Spearman | Recouvrement du top 10 |
|---|---|---|
| Poids perturbés, Dirichlet κ = 50 (2 000 tirages) | 0,965 | 0,90 |
| Poids fortement perturbés, Dirichlet κ = 10 | 0,88 | 0,78 |
| Sans la composante abandon | 0,71 | — |
| Sans une autre composante | 0,91 à 0,96 | — |
| Normalisation min-max / rangs | 0,99 / 0,87 | — |
| v2 contre variante moyenne 2 ans | 0,88 | 0,81 |
| v2 contre v1 (taux publié) | 0,92 | 0,85 |

Statut de stabilité : fréquence dans le top 10 sur les tirages κ = 50 — **stable** ≥ 0,9 ; **plutôt** ≥ 0,5 ;
**instable, au bord** ≥ 0,1 ; **hors top 10** sinon.
"""),
    ("modele", "Modèle t+1 contre les baselines (honnête)",
     "Ce que la prévision apporte face à une règle simple, sans embellir le résultat. L'AUC mesure la capacité à "
     "distinguer les provinces à risque des autres : 0,5 vaut un tirage au sort, 1 serait parfait.",
     r"""
Validation rolling origin, cibles 2021-2024, 180 province-années. Rappel au top 12 = part des provinces à risque
retrouvées parmi les 12 scores les plus élevés.

| Cible : abandon harmonisé | AUC | PR-AUC | Rappel top 12 |
|---|---|---|---|
| Persistance (baseline : rang de l'année t) | 0,68 | 0,45 | 0,48 |
| Régression logistique | 0,72 | 0,46 | 0,56 |
| Gradient boosting | 0,75 | 0,52 | 0,56 |
| Forêt aléatoire | 0,76 | 0,53 | 0,56 |
| **Consensus (affiché)** | **0,77** | **0,54** | **0,56** |

- Gain d'AUC du consensus sur la persistance : +0,09 (IC 95 % bootstrap 0,01 ; 0,16) ; forêt aléatoire +0,07
  (0,02 ; 0,13) ; logistique et gradient boosting : gain non significatif.
- Sur la variante moyenne 2 ans, **la persistance n'est pas battue** (AUC 0,92, rappel 0,79) : cette série partage
  la moitié de ses flux entre t et t+1. C'est pourquoi la probabilité affichée cible l'abandon harmonisé.
- Calibration correcte entre 0 et 0,6 ; **surestimée entre 0,6 et 0,8** (0,70 prévu pour 0,47 observé). Lire les
  probabilités élevées comme un classement plus que comme une fréquence.
- Échantillon petit (45 provinces, 4 années de validation) : intervalles larges, à confirmer sur les années suivantes.
"""),
    ("sources", "Sources et licences",
     "D'où vient chaque donnée, et à quelles conditions elle peut être réutilisée.",
     r"""
| Donnée | Source | Licence / conditions |
|---|---|---|
| Effectifs, abandon, redoublement, promotion, TAP, maîtres, équipement | Annuaires statistiques du primaire DGESS/MENAPLN (CNS) ; classeur officiel du Data Challenge | Données publiques nationales ; usage selon le règlement du challenge |
| Contours (ancien et 2025) | OCHA COD-AB Burkina Faso v03, IGB, via HDX | CC BY-IGO |
| Découpage 2025 | Décret n° 2025-1012/PF/PRIM/MATM/MEF du 7 août 2025 | Texte officiel |
| Personnes déplacées internes | CONASUR, via HDX / OCHA ; stock national IDMC | Conditions HDX de chaque jeu |
| Insécurité | ACLED, agrégats publics via HDX | Conditions d'utilisation ACLED (attribution obligatoire) |
| Population | INSD, RGPH 2019 et projections 2020-2035 | Données publiques INSD |
| Contrôle des contours | geoBoundaries (comparaison seulement) | CC BY 4.0 |

Attribution des contours : « Limites administratives : OCHA, IGB – COD-AB Burkina Faso, via HDX (CC BY-IGO) ».
Les frontières affichées n'impliquent aucune prise de position officielle.
"""),
    ("ia", "Déclaration d'usage de l'IA",
     "Comment le projet a été produit, étape par étape.",
     r"""
**1. Nettoyage des données** : effectué au travers de scripts, exécutés dans l'ordre —
`01_excel_officiel.py`, `02_annuaires_primaire.py`, `03_tableaux_geo_generiques.py`,
`04_pdi_communes.py`, `05_geo_referentiel.py`, `06_rgph_population.py`, `07_ecoles_osm.py`,
`08_jalon_b_complements.py`, `09_jalon_c_insecurite.py`, `10_jalon_c_recettes_dss/` (dossier),
`11_jalon_d_contours.py`, `12_jalon_d_sql_dss/` (dossier), `commun.py`, `geo.py`.

**2. Indice v2, tests de robustesse et modèles** : produits en utilisant un assistant agentique
personnalisé développé par John Lamien lui-même.

**3. Construction du tableau de bord** (et des pages associées) : réalisée au travers d'un kit
agentique développé par John Lamien lui-même, en utilisant les modèles d'Anthropic, sur données
fictives pendant la construction.
"""),
    ("application", "Fonctionnement de l'application",
     "Comment l'application lit les données, et pourquoi elle fonctionne sans Internet.",
     r"""
Données lues uniquement dans quatre vues PostgreSQL (`analyse.v_dashboard_*`) par un rôle en lecture seule.
L'application fonctionne entièrement hors ligne côté navigateur : aucune police, tuile, carte ou bibliothèque
n'est chargée depuis Internet.
"""),
]

SOUS_TITRE = ("Le détail de ce qui est calculé et comment : chiffres clés, arbitrages, définitions, poids, "
              "robustesse, performance du modèle, sources, licences et usage de l'IA.")


def sommaire():
    """Sommaire : des ancres de page, sans script. La liste reste ordonnée pour les lecteurs d'écran,
    mais ses numéros ne s'affichent pas — ce n'est pas une suite d'étapes à suivre."""
    return html.Nav(
        [html.P("Sur cette page", className="toc-titre"),
         html.Ol([html.Li(html.A(t, href=f"#{ancre}")) for ancre, t, _, _ in SECTIONS], className="toc-liste")],
        className="carte-bloc methode-toc", **{"aria-label": "Sommaire de la page"})


def layout(**_):
    return html.Div([
        titre("Méthode et définitions", sous=SOUS_TITRE),
        html.Div([
            sommaire(),
            html.Div([bloc(t, html.P(intro, className="methode-lead"),
                           dcc.Markdown(corps, className="markdown-methode"), id=ancre)
                      for ancre, t, intro, corps in SECTIONS], className="methode-corps"),
        ], className="methode-grille"),
    ], className="methode-doc")


def register(app):
    return None
