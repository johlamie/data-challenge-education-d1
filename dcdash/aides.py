"""Aides de lecture pour un lecteur non initié : définition courte, unité, sens de lecture et source.

Chaque texte s'affiche dans une infobulle (icône « i » grise) au survol sur ordinateur et au toucher sur mobile.
Les lignes « Unité : », « Sens : », « Source : » et « Lecture : » sont mises en forme par assets/aide.js.
"""
from .meta import INDICATEURS

SENS = {"pire": "plus haut = plus de risque (pire)", "mieux": "plus haut = mieux",
        "neutre": "ni mieux ni pire : donne le contexte", "ecart": "plus loin de 0 = plus d'inégalité (pire)"}
SRC_ANNUAIRES = "annuaires statistiques du primaire DGESS/MENAPLN, classeur officiel du Data Challenge"
SRC_SCORE = "calcul Unica Labs (annuaires DGESS/MENAPLN, CONASUR, INSD), détail dans Méthode"
SRC_MODELE = "modèle de prévision Unica Labs (consensus de 3 modèles), détail dans Méthode"
SRC_PDI = "CONASUR via HDX/OCHA ; dernier relevé au 31/03/2023, prolongé ensuite"
SRC_ACLED = "ACLED (agrégats publics via HDX) ; population INSD"
SRC_POP = "INSD, recensement RGPH 2019 et projections 2020-2035"


def texte(definition, unite=None, sens=None, source=None, lecture=None):
    lignes = [definition]
    if unite:
        lignes.append(f"Unité : {unite}")
    if sens:
        lignes.append(f"Sens : {SENS.get(sens, sens)}")
    if source:
        lignes.append(f"Source : {source}")
    if lecture:
        lignes.append(f"Lecture : {lecture}")
    return "\n".join(lignes)


# ---- définitions des indicateurs (fiche, évolution, carte) ----
_DEF = {
    "indice_v2": ("Score de risque avant sa mise à l'échelle 0-100 : somme pondérée de 6 facteurs, chacun exprimé en "
                  "écart à la moyenne des provinces (0 = province moyenne).", "score sans unité (écarts-types)",
                  SRC_SCORE),
    "indice_v2_0_100": ("Résume en un chiffre 6 facteurs de décrochage : abandon 30 %, déplacés 20 %, redoublement "
                        "15 %, élèves par maître 15 %, écoles sans eau 10 %, sans latrines 10 %. 0 = la province la "
                        "moins à risque de l'année, 100 = la plus à risque.", "score sur 100, relatif à l'année",
                        SRC_SCORE),
    "proba_risque_t1": ("Probabilité que la province soit, l'année suivante, parmi le quart des provinces où l'abandon "
                        "est le plus élevé. Calculée pour l'ensemble des élèves, de 2020-2021 à 2024-2025.",
                        "probabilité, de 0 à 100 %", SRC_MODELE),
    "taux_abandon_harmonise": ("Part des élèves du CP1 au CM1 qui quittent l'école au cours de l'année (calcul de "
                               "l'équipe à partir des effectifs d'une année sur l'autre, méthode DGESS). Une valeur "
                               "négative signifie plus d'arrivées que de départs.", "% des élèves", SRC_ANNUAIRES),
    "taux_abandon_moyen_2ans": ("Même taux d'abandon, calculé sur deux années cumulées. Sert de contrôle : s'il "
                                "s'écarte beaucoup du taux annuel, l'année est à lire avec prudence.", "% des élèves",
                                SRC_ANNUAIRES),
    "taux_abandon_publie": ("Taux d'abandon publié dans les annuaires (moyenne simple des classes, ramené à 0 s'il est "
                            "négatif). Donné pour comparaison.", "% des élèves", SRC_ANNUAIRES),
    "taux_redoublement": ("Part des élèves qui refont la même classe l'année suivante.", "% des élèves",
                          SRC_ANNUAIRES),
    "taux_promotion": ("Part des élèves qui passent dans la classe supérieure l'année suivante.", "% des élèves",
                       SRC_ANNUAIRES),
    "tap": ("Taux d'achèvement du primaire : nouveaux élèves en dernière année (CM2) rapportés aux enfants qui ont "
            "l'âge de cette classe. Il peut dépasser 100 % (élèves en retard ou venus d'ailleurs).",
            "% de la classe d'âge", SRC_ANNUAIRES),
    "ratio_eleves_maitre": ("Nombre moyen d'élèves par enseignant.", "élèves par enseignant", SRC_ANNUAIRES),
    "pct_ecoles_eau_potable": ("Part des écoles qui disposent d'un point d'eau potable.", "% des écoles",
                               SRC_ANNUAIRES),
    "pct_ecoles_latrines": ("Part des écoles qui disposent de latrines.", "% des écoles", SRC_ANNUAIRES),
    "pdi_pour_1000_hab": ("Personnes déplacées internes (fuyant l'insécurité) présentes dans la province, pour "
                          "1 000 habitants.", "‰ (pour 1 000 habitants)", SRC_PDI + " ; population INSD"),
    "acled_evenements_pour_100k": ("Incidents violents recensés dans l'année (attaques, affrontements, violences "
                                   "contre les civils), pour 100 000 habitants.", "incidents pour 100 000 habitants",
                                   SRC_ACLED),
    "acled_victimes_pour_100k": ("Personnes tuées lors de ces incidents dans l'année, pour 100 000 habitants.",
                                 "décès pour 100 000 habitants", SRC_ACLED),
    "effectif_eleves": ("Nombre d'élèves inscrits au primaire dans la province.", "élèves", SRC_ANNUAIRES),
    "population_totale": ("Nombre d'habitants de la province.", "habitants", SRC_POP),
}


def sens_indicateur(cle):
    return {1: "pire", -1: "mieux", 0: "neutre"}[INDICATEURS[cle]["sens"]]


def indicateur(cle, lecture=None):
    d, u, s = _DEF[cle]
    return texte(d, u, sens_indicateur(cle), s, lecture)


# ---- chiffres clés de la vue d'ensemble ----
KPI = {
    "abandon": texte("Part des élèves du primaire (CP1 à CM1) qui ont quitté l'école dans l'année, pour tout le pays. "
                     "La flèche compare à l'année précédente.", "% des élèves", "pire", SRC_ANNUAIRES),
    "alerte": texte("Nombre de provinces dont la probabilité d'être l'an prochain parmi le quart le plus touché par "
                    "l'abandon atteint 50 % (seuil choisi par l'équipe).", "provinces, sur 45", "pire", SRC_MODELE),
    "ecart": texte("Taux d'abandon des filles moins celui des garçons. Positif : les filles abandonnent davantage ; "
                   "négatif : les garçons.", "points de pourcentage", "ecart",
                   SRC_ANNUAIRES + " ; répartition par sexe d'après le fichier accès"),
    "province": texte("Province classée n° 1 par le score de risque cette année, avec sa région et son taux "
                      "d'abandon.", None, None, SRC_SCORE),
    "eleves": texte("Estimation du nombre d'élèves qui ont quitté l'école : taux d'abandon de chaque région × nombre "
                    "d'élèves du CP1 au CM1, additionnés. Ordre de grandeur, arrondi à la centaine.", "élèves",
                    "pire", SRC_ANNUAIRES),
    "pdi": texte("Personnes déplacées internes, tous âges, qui ont fui l'insécurité. Elles pèsent sur l'accueil des "
                 "écoles et sur la scolarité.", "personnes ; pour 1 000 habitants", "pire", SRC_PDI),
}

# ---- colonnes du top 10 et du classement ----
COL = {
    "rang": texte("Place de la province selon le critère de classement choisi.", "rang de 1 à 45", None, None,
                  "1 = la province la plus à risque."),
    "province": texte("Nom de la province (ancien découpage en 45 provinces). Cliquez dessus pour ouvrir sa fiche."),
    "region": texte("Région à laquelle appartient la province."),
    "score": texte("Score de risque, de 0 (la moins à risque de l'année) à 100 (la plus à risque). Il combine "
                   "abandon, déplacés, redoublement, élèves par maître, eau et latrines.", "score sur 100", "pire",
                   SRC_SCORE, "la barre reprend la couleur de la carte."),
    "abandon": texte("Part des élèves du CP1 au CM1 qui ont quitté l'école dans l'année.", "% des élèves", "pire",
                     SRC_ANNUAIRES),
    "statut": texte("Solidité de la place dans le top 10 : le score est recalculé avec de nombreuses variantes "
                    "(poids, définitions). Très sûr : top 10 dans au moins 90 % des variantes ; Probable : 50 à 90 % ; "
                    "Incertain : 10 à 50 %.", "part des variantes", None,
                    "simulation de Monte Carlo Unica Labs, détail dans Méthode"),
    "risque": texte("Probabilité d'être l'an prochain parmi le quart des provinces où l'abandon est le plus élevé.",
                    "%", "pire", SRC_MODELE),
    "estime": texte("« oui » : le taux d'abandon de cette province n'a pas pu être calculé directement cette année ; "
                    "il est estimé (année voisine, répartition par sexe…). La source est indiquée dans Qualité des "
                    "données."),
}

# ---- cartes, graphiques et fiche ----
CARTE = texte("Chaque province est colorée selon la mesure choisie : du rose très pâle (risque faible) au rouge sombre "
              "(risque élevé). Score de risque : synthèse de 6 facteurs, de 0 à 100. Taux d'abandon : part des élèves "
              "qui quittent l'école dans l'année. Risque l'an prochain : probabilité d'être parmi le quart des "
              "provinces les plus touchées l'année suivante.", None, None, None,
              "traits gris = limites des régions ; hachures = taux d'abandon estimé.")
MESURES = texte("Score de risque : synthèse de 6 facteurs, de 0 à 100. Taux d'abandon : part des élèves qui quittent "
                "l'école dans l'année. Risque l'an prochain : probabilité d'être parmi le quart le plus touché l'année "
                "suivante (ensemble des élèves, 2020-2021 à 2024-2025).")
DECOUPAGE = texte("Ancien découpage : 13 régions et 45 provinces (celui des données). Découpage 2025 : 17 régions et "
                  "47 provinces ; les provinces issues d'une scission portent la valeur de leur province mère (↳).")
SOLIDITE = COL["statut"]
CARTE_FICHE = texte("Les 45 provinces colorées selon le score de risque de l'année et du sexe choisis : du rose très pâle "
                    "(risque faible) au rouge foncé (risque élevé).",
                    "score sur 100", "pire", SRC_SCORE, "cliquez sur une autre province pour ouvrir sa fiche.")
FIABILITE = texte("Correcte : le score repose surtout sur des valeurs observées. Faible : trop de facteurs ont dû être "
                  "estimés cette année ; le rang est à lire avec prudence.", None, None,
                  "Qualité des données (imputations)")
CONTRIBUTIONS = texte("Montre ce qui fait monter ou baisser le score de la province, facteur par facteur, par "
                      "rapport à une province moyenne.", "points d'indice (somme = indice)", None, SRC_SCORE,
                      "une barre rouge vers la droite pousse le risque vers le haut ; une barre bleue vers la gauche "
                      "le réduit.")
INSECURITE = texte("Évolution de deux signes de l'insécurité dans la province : incidents violents pour 100 000 "
                   "habitants (orange) et personnes déplacées pour 1 000 habitants (bleu, tirets).",
                   "pour 100 000 hab. et pour 1 000 hab.", "pire", SRC_ACLED + " ; " + SRC_PDI,
                   "marqueur creux = valeur estimée ou relevé prolongé.")
TABLE_FICHE = {
    "valeur": texte("Valeur de l'indicateur pour la province, l'année et le sexe choisis.", None, None, None,
                    "cellule hachurée et * = valeur estimée (source au survol de *)."),
    "rang": texte("Place de la province parmi les 45 pour cet indicateur.", "rang de 1 à 45", None, None,
                  "1 = la situation la plus défavorable (plus d'abandon, moins d'écoles équipées…)."),
    "mediane": texte("Valeur de la province du milieu : la moitié des provinces sont au-dessus, la moitié en dessous. "
                     "Sert de point de comparaison."),
    "imputation": texte("Si la valeur a été estimée, d'où vient l'estimation (année voisine, dernier relevé…). "
                        "« — » : valeur observée."),
}
EVO_ABANDON = texte("Taux d'abandon de chaque province ou région choisie, année par année. Trait plein : taux de "
                    "l'année ; tirets : moyenne sur 2 ans (contrôle) ; gris épais : moyenne du Burkina Faso.",
                    "% des élèves", "pire", SRC_ANNUAIRES, "marqueur creux = valeur estimée.")
