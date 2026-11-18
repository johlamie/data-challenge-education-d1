"""Métadonnées des indicateurs : libellés, unités, sens du risque, drapeau et source d'imputation."""

ANNEES = list(range(2017, 2025))
SEXES = {"T": "Ensemble", "F": "Filles", "G": "Garçons"}
DECOUPAGES = {"ancien_45": "Ancien découpage (13 régions, 45 provinces)",
              "2025_47": "Découpage 2025 (17 régions, 47 provinces)"}
DECOUPAGE_REGION = {"ancien_45": "ancien_13", "2025_47": "2025_17"}


def annee_scolaire(a):
    return f"{a}-{a + 1}"


# sens : +1 = une valeur élevée signale plus de risque ; -1 = une valeur élevée est favorable ; 0 = neutre
# flag / source : colonnes de la vue province ; flag_region : colonne de comptage de la vue région
INDICATEURS = {
    "indice_v2": dict(label="Score de risque (indice)", unite="score (z)", fmt=".2f", sens=1,
                      flag="nb_composantes_imputees", source=None, flag_region=None,
                      region_col="indice_v2_moyen_pondere",
                      desc="Somme pondérée de 6 composantes en z-score (année et sexe), bornées à ±3."),
    "indice_v2_0_100": dict(label="Score de risque", unite="sur 100", fmt=".0f", sens=1,
                            flag="nb_composantes_imputees", source=None, flag_region=None,
                            region_col="indice_v2_moyen_pondere",
                            desc="Indice de risque ramené de 0 (province la moins à risque) à 100 (la plus à risque), "
                                 "dans l'année et le sexe."),
    "proba_risque_t1": dict(label="Risque l'an prochain (probabilité)", unite="probabilité", fmt=".0%", sens=1,
                            flag=None, source=None, flag_region=None, region_col="proba_risque_t1_moyenne",
                            desc="Probabilité d'être dans le quart supérieur de l'abandon harmonisé l'année suivante "
                                 "(consensus de 3 modèles, sexe Ensemble, 2020-2024)."),
    "taux_abandon_harmonise": dict(label="Taux d'abandon", unite="%", fmt=".1f", sens=1,
                                   flag="abandon_impute", source="source_imputation_abandon",
                                   flag_region="nb_provinces_abandon_impute",
                                   desc="Taux d'abandon apparent CP1-CM1 pondéré par les flux, non tronqué (jalon b). "
                                        "Définition principale."),
    "taux_abandon_moyen_2ans": dict(label="Taux d'abandon, moyenne sur 2 ans (contrôle)", unite="%", fmt=".1f", sens=1,
                                    flag="abandon_impute", source="source_imputation_abandon",
                                    flag_region="nb_provinces_abandon_impute",
                                    desc="Abandon harmonisé calculé sur les flux poolés de deux années (contrôle)."),
    "taux_abandon_publie": dict(label="Taux d'abandon publié (annuaires)", unite="%", fmt=".1f", sens=1, flag=None, source=None,
                                flag_region=None, desc="Taux publié (moyenne simple des niveaux, tronqué à 0)."),
    "taux_redoublement": dict(label="Redoublement", unite="%", fmt=".1f", sens=1, flag="chiffres_cles_impute",
                              source="source_imputation_chiffres_cles_equipement", flag_region=None, desc=""),
    "taux_promotion": dict(label="Promotion", unite="%", fmt=".1f", sens=-1, flag="chiffres_cles_impute",
                           source="source_imputation_chiffres_cles_equipement", flag_region=None, desc=""),
    "tap": dict(label="Taux d'achèvement du primaire (TAP)", unite="%", fmt=".1f", sens=-1,
                flag="chiffres_cles_impute", source="source_imputation_chiffres_cles_equipement",
                flag_region=None, desc=""),
    "ratio_eleves_maitre": dict(label="Élèves par maître", unite="élèves", fmt=".1f", sens=1,
                                flag="chiffres_cles_impute", source="source_imputation_chiffres_cles_equipement",
                                flag_region=None, desc=""),
    "pct_ecoles_eau_potable": dict(label="Écoles avec eau potable", unite="%", fmt=".1f", sens=-1,
                                   flag="equipement_impute", source="source_imputation_chiffres_cles_equipement",
                                   flag_region=None, desc=""),
    "pct_ecoles_latrines": dict(label="Écoles avec latrines", unite="%", fmt=".1f", sens=-1,
                                flag="equipement_impute", source="source_imputation_chiffres_cles_equipement",
                                flag_region=None, desc=""),
    "pdi_pour_1000_hab": dict(label="Personnes déplacées (PDI) pour 1 000 hab.", unite="‰", fmt=".1f", sens=1, flag="pdi_impute",
                              source="source_imputation_pdi", flag_region="nb_provinces_pdi_impute",
                              desc="Personnes déplacées internes (CONASUR), relevé le plus proche de l'année."),
    "acled_evenements_pour_100k": dict(label="Incidents violents (ACLED) pour 100 000 hab.", unite="pour 100 000", fmt=".1f",
                                       sens=1, flag="pop_impute", source="source_imputation_population",
                                       flag_region="nb_provinces_population_imputee",
                                       desc="Violence politique (agrégats publics ACLED via HDX) ; dénominateur population."),
    "acled_victimes_pour_100k": dict(label="Victimes de violences (ACLED) pour 100 000 hab.", unite="pour 100 000", fmt=".1f",
                                     sens=1, flag="pop_impute", source="source_imputation_population",
                                     flag_region="nb_provinces_population_imputee", desc=""),
    "effectif_eleves": dict(label="Effectif d'élèves", unite="élèves", fmt=",.0f", sens=0,
                            flag="effectif_historique_impute", source="source_imputation_effectifs",
                            flag_region="nb_provinces_effectifs_imputes", desc=""),
    "population_totale": dict(label="Population totale", unite="habitants", fmt=",.0f", sens=0, flag="pop_impute",
                              source="source_imputation_population", flag_region="nb_provinces_population_imputee",
                              desc=""),
}

# indicateurs disponibles dans la vue région (colonne de la vue région)
def colonne_region(cle):
    m = INDICATEURS[cle]
    return m.get("region_col", cle)


INDICATEURS_REGION = [k for k in INDICATEURS if k not in ("taux_abandon_moyen_2ans",)] + ["taux_abandon_moyen_2ans"]

# composantes de l'indice v2 (jalon c, poids inchangés)
COMPOSANTES = [
    ("taux_abandon_harmonise", 0.30, 1, "Taux d'abandon"),
    ("taux_redoublement", 0.15, 1, "Redoublement"),
    ("pdi_pour_1000_hab", 0.20, 1, "Personnes déplacées"),
    ("ratio_eleves_maitre", 0.15, 1, "Élèves par maître"),
    ("pct_ecoles_eau_potable", 0.10, -1, "Écoles sans eau potable"),
    ("pct_ecoles_latrines", 0.10, -1, "Écoles sans latrines"),
]

STATUT_TOP10 = {"stable_top10": "Très sûr", "plutot_top10": "Probable",
                "instable_bord": "Incertain", "hors_top10": "Hors top 10"}
STATUT_TOP10_AIDE = {"stable_top10": "Dans le top 10 dans au moins 90 % des variantes de calcul testées",
                     "plutot_top10": "Dans le top 10 dans 50 à 90 % des variantes de calcul testées",
                     "instable_bord": "Dans le top 10 dans 10 à 50 % des variantes : à la limite",
                     "hors_top10": "Rarement dans le top 10"}
EQUIPE = "Unica Labs"
EQUIPE_URL = "https://unicalabs.bf"
SEUIL_ALERTE = 0.5  # province « en alerte » : probabilité ≥ 50 % d'être dans le quart le plus touché l'an prochain

LIBELLES_SOURCES = {
    "interpolation_lineaire_annees_voisines": "Interpolation linéaire entre années voisines",
    "report_annee_voisine": "Report de l'année voisine",
    "reventilation_part_filles_fichier_acces": "Ventilation par sexe d'après la part des filles (fichier accès)",
    "avant_premier_releve_CONASUR_mis_a_0": "Avant le premier relevé CONASUR : mis à 0",
}


def libelle_source(s):
    if s is None or s != s or s == "":
        return ""
    s = str(s)
    for k, v in LIBELLES_SOURCES.items():
        if s.startswith(k):
            return v + s[len(k):]
    return s.replace("_", " ")


def fmt_valeur(v, cle):
    """Formate une valeur pour l'affichage (français : virgule décimale, espace fine pour les milliers)."""
    if v is None or v != v:
        return "n.d."
    f = INDICATEURS[cle]["fmt"] if cle in INDICATEURS else ".2f"
    s = format(float(v), f).replace(",", "\u202f").replace(".", ",")
    if f.endswith("%"):
        s = s[:-1] + "\u00a0%"
    u = INDICATEURS.get(cle, {}).get("unite", "")
    if u in ("%", "‰"):
        s += "\u00a0" + u
    return s


def nom_propre(s):
    """« BOUCLE DU MOUHOUN » → « Boucle du Mouhoun » (les noms déjà en casse mixte sont gardés)."""
    if not isinstance(s, str) or not s.isupper():
        return s
    t = s.title()
    for w in (" Du ", " De ", " Des ", " La ", " Le ", " Les ", " Et "):
        t = t.replace(w, w.lower())
    return t


def fmt_nombre(v, dec=0):
    if v is None or v != v:
        return "n.d."
    return format(float(v), f",.{dec}f").replace(",", "\u202f").replace(".", ",")


TYPE_PROBA = {"hors echantillon (rolling origin)": "hors échantillon (validation rolling origin)",
              "prevision (modele entraine sur toutes les annees)": "prévision pour l'année suivante "
                                                                    "(modèle entraîné sur toutes les années)"}


def libelle_type_proba(t):
    if not isinstance(t, str):
        return ""
    return TYPE_PROBA.get(t, t)
