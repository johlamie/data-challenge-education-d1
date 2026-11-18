"""Jeux de données SYNTHÉTIQUES (aucune donnée réelle), au schéma des 4 vues dashboard.

- SourceSynthetique : jeu des tests (valeurs aléatoires, contours en carrés).
- SourceDemo : jeu de démonstration du design (DC_EDU_DEMO=1). Valeurs FICTIVES, géographiquement cohérentes pour
  que la carte soit lisible ; noms « Province 01 », « Région A »… Contours : fichier GeoJSON fourni par
  DC_EDU_DEMO_GEO (contours officiels, sans aucun attribut réel) ; à défaut le fichier livré geo_demo.json
  (contours SCHÉMATIQUES approximatifs du pays, générés hors ligne par outils/generer_geo_demo.py, jamais les
  limites officielles) ; en tout dernier recours des carrés synthétiques.
L'application affiche le bandeau « Données fictives » dans ce mode.
"""
import json
import os

import numpy as np
import pandas as pd

from . import calculs

ANNEES = list(range(2017, 2025))
SEXES = ["T", "F", "G"]
NUM = ["taux_abandon_harmonise", "taux_abandon_moyen_2ans", "taux_abandon_publie", "taux_abandon_publie_pondere",
       "taux_abandon_apparent_pondere", "taux_redoublement", "taux_promotion", "tap", "tba", "tbs",
       "ratio_eleves_maitre", "nombre_maitres", "nombre_ecoles", "pct_ecoles_eau_potable", "pct_ecoles_latrines",
       "pdi_pour_1000_hab", "pdi_nombre", "nouveaux_pdi_signales", "acled_evenements_pour_100k",
       "acled_victimes_pour_100k", "population_totale", "population_6_11", "effectif_eleves",
       "effectif_eleves_total_tous_sexes", "effectif_scolarise"]
LETTRES = "ABCDEFGHIJKLMNOPQ"


def carre(x, y, c=0.4):
    return {"type": "MultiPolygon", "coordinates": [[[[x, y], [x + c, y], [x + c, y + c], [x, y + c], [x, y]]]]}


def _valeurs_demo(rng, risque, a, s):
    """Valeurs fictives plausibles pour une province (risque latent dans [0, 1]), une année et un sexe."""
    t = (a - 2017) / 7
    crise = min(1.0, max(0.0, (a - 2018) / 4))  # montée de l'insécurité fictive
    bruit = lambda e: float(rng.normal(0, e))  # noqa: E731
    ab = 3 + 9 * risque * (0.6 + 0.6 * crise) + 1.2 * t + bruit(0.8) + (0.6 if s == "F" else -0.5 if s == "G" else 0)
    r = {c: float(rng.uniform(1, 100)) for c in NUM}
    r.update(taux_abandon_harmonise=ab, taux_abandon_moyen_2ans=ab - 0.4 + bruit(0.3),
             taux_abandon_publie=max(0.0, ab - 1 + bruit(0.5)), taux_abandon_publie_pondere=max(0.0, ab - 0.8),
             taux_abandon_apparent_pondere=ab, taux_redoublement=6 + 6 * risque + bruit(1),
             taux_promotion=88 - 12 * risque + bruit(2), tap=72 - 30 * risque * (0.7 + 0.5 * crise) + bruit(3),
             ratio_eleves_maitre=42 + 18 * risque + bruit(3), pct_ecoles_eau_potable=70 - 35 * risque + bruit(5),
             pct_ecoles_latrines=78 - 30 * risque + bruit(5),
             pdi_pour_1000_hab=max(0.0, 260 * risque ** 2 * crise + bruit(4)),
             acled_evenements_pour_100k=max(0.0, 12 * risque ** 2 * crise + bruit(0.5)),
             acled_victimes_pour_100k=max(0.0, 30 * risque ** 2 * crise + bruit(1)))
    return r


def _provinces(realiste=False, risques=None):
    rng = np.random.default_rng(42)
    rows = []
    for i in range(45):
        pc = f"BF{i + 1:04d}"
        reg = f"BF{(i % 13) + 46:02d}" if risques is None else f"BF{risques[i][1] + 46:02d}"
        nom_reg = f"REGION {reg}" if not realiste else f"Région {LETTRES[int(reg[2:]) - 46]}"
        nom = f"PROVINCE {i + 1:02d}" if not realiste else f"Province {i + 1:02d}"
        risque = risques[i][0] if risques is not None else float(rng.uniform(0, 1))
        pop = float(rng.uniform(1e5, 1e6)) if realiste else None
        for a in ANNEES:
            for s in SEXES:
                r = {"pcode_province": pc, "province": nom,
                     "nom_officiel_province_ancienne": nom.title(), "pcode_region": reg,
                     "region": nom_reg, "pcodes_province_2025": pc + ("a | " + pc + "b" if i < 2 else ""),
                     "provinces_2025": f"Nouvelle {i + 1}" + (f"A + Nouvelle {i + 1}B" if i < 2 else ""),
                     "pcode_region_2025": f"BF7{i % 17:02d}", "region_2025": f"Région 2025 {LETTRES[i % 17]}",
                     "scission_2025": 1 if i < 2 else 0, "annee_debut": a, "annee_scolaire": f"{a}-{a + 1}",
                     "sexe": s}
                if realiste:
                    r.update(_valeurs_demo(rng, risque, a, s))
                    part = 1.0 if s == "T" else 0.5
                    r["population_totale"] = pop * (1 + 0.03 * (a - 2017)) * part
                    r["population_6_11"] = r["population_totale"] * 0.18
                    r["effectif_eleves"] = r["population_6_11"] * (0.85 - 0.35 * risque)
                    r["nombre_maitres"] = r["effectif_eleves"] / r["ratio_eleves_maitre"]
                else:
                    for c in NUM:
                        r[c] = float(rng.uniform(1, 100))
                    r["population_totale"] = float(rng.uniform(1e5, 1e6))
                    r["population_6_11"] = r["population_totale"] * 0.18
                    r["effectif_eleves"] = float(rng.uniform(1e4, 1e5))
                    r["nombre_maitres"] = r["effectif_eleves"] / 50
                r["pdi_nombre"] = r["pdi_pour_1000_hab"] * r["population_totale"] / 1000
                r["acled_evenements"] = int(rng.integers(0, 50))
                r["acled_victimes"] = int(rng.integers(0, 80))
                r["abandon_impute"] = int(rng.random() < 0.1)
                r["source_imputation_abandon"] = "report_annee_voisine" if r["abandon_impute"] else None
                r["pdi_impute"] = int(a >= 2023)
                r["source_imputation_pdi"] = "report_dernier_releve_CONASUR_2023-03-31" if a >= 2023 else None
                r["pop_impute"] = int(rng.random() < 0.2)
                r["source_imputation_population"] = "retropolation_test" if r["pop_impute"] else None
                r["effectif_historique_impute"] = int(a == 2024 and s != "T")
                r["source_imputation_effectifs"] = ("reventilation_part_filles_fichier_acces"
                                                    if r["effectif_historique_impute"] else None)
                r["chiffres_cles_impute"] = r["equipement_impute"] = int(i == 7 and a == 2022)
                r["source_imputation_chiffres_cles_equipement"] = "interpolation_test" if i == 7 and a == 2022 else None
                r["drapeau_abandon"] = "ok"
                r["contient_valeur_douteuse"] = 0
                r["nb_niveaux_abandon_zero"] = 0
                r["fiabilite_indice"] = ("faible : abandon par sexe majoritairement impute" if (a == 2024 and s != "T")
                                         else "ok")
                r["version_vue"] = "synthetique"
                rows.append(r)
    p = pd.DataFrame(rows)
    if not realiste:
        p.loc[5, "tap"] = np.nan
    out = []
    for (a, s), g in p.groupby(["annee_debut", "sexe"]):
        g = g.copy()
        c = calculs.contributions(g)
        g["indice_v2"] = g["pcode_province"].map(c["total"])
        g["rang_v2"] = g["indice_v2"].rank(ascending=False, method="min").astype(int)
        g["indice_v2_0_100"] = 100 * (g["indice_v2"] - g["indice_v2"].min()) / (g["indice_v2"].max() - g["indice_v2"].min())
        g["top10_v2"] = (g["rang_v2"] <= 10).astype(int)
        g["top15_v2"] = (g["rang_v2"] <= 15).astype(int)
        g["indice_v2_moy2ans"] = g["indice_v2"] * 0.9
        g["rang_v2_moy2ans"] = g["rang_v2"]
        g["indice_v1_publie"] = g["indice_v2"] * 0.8
        g["rang_v1_publie"] = g["rang_v2"]
        tt = s == "T"
        g["freq_top10_mc"] = np.where(tt, np.clip(1.1 - g["rang_v2"] / 12, 0, 1), np.nan)
        g["freq_top15_mc"] = g["freq_top10_mc"]
        g["rang_p05_mc"] = np.where(tt, np.maximum(1, g["rang_v2"] - 2), np.nan)
        g["rang_p95_mc"] = np.where(tt, g["rang_v2"] + 3, np.nan)
        f = g["freq_top10_mc"]
        g["statut_top10_mc"] = (np.select([f >= .9, f >= .5, f >= .1], ["stable_top10", "plutot_top10", "instable_bord"],
                                          "hors_top10") if tt else None)
        g["freq_top10_mc_moy2ans"] = g["freq_top10_mc"]
        ok = tt and a >= 2020
        if realiste:
            z = (g["indice_v2"] - g["indice_v2"].mean()) / (g["indice_v2"].std() or 1)
            g["proba_risque_t1"] = np.where(ok, 1 / (1 + np.exp(-(1.6 * z - 1.0))), np.nan)
        else:
            g["proba_risque_t1"] = np.where(ok, np.linspace(0.05, 0.9, 45), np.nan)
        g["rang_risque_t1"] = np.where(ok, g["proba_risque_t1"].rank(ascending=False), np.nan)
        g["proba_risque_t1_moy2ans"] = g["proba_risque_t1"]
        g["risque_t1_observe"] = np.where(ok and a < 2024, (g["proba_risque_t1"] > 0.6).astype(float), np.nan)
        g["type_proba_t1"] = None if not ok else ("prevision (modele entraine sur toutes les annees)" if a == 2024
                                                  else "hors echantillon (rolling origin)")
        g["nb_composantes_imputees"] = g[["abandon_impute", "pdi_impute", "chiffres_cles_impute",
                                          "equipement_impute"]].sum(axis=1)
        g["nb_imputations"] = g[["abandon_impute", "pdi_impute", "pop_impute", "chiffres_cles_impute",
                                 "effectif_historique_impute"]].sum(axis=1)
        out.append(g)
    return pd.concat(out, ignore_index=True)


def _regions(p):
    rows = []
    for dec, col_code, col_nom in [("ancien_13", "pcode_region", "region"), ("2025_17", "pcode_region_2025", "region_2025")]:
        for (code, nom, a, s), g in p.groupby([col_code, col_nom, "annee_debut", "sexe"]):
            base = g["effectif_eleves"]
            rows.append({"decoupage": dec, "pcode_region": code, "region": nom, "annee_debut": a,
                         "annee_scolaire": f"{a}-{a + 1}", "sexe": s, "nb_provinces_anciennes": len(g),
                         "provinces_anciennes": ", ".join(g["province"]),
                         "taux_abandon_harmonise": float((g["taux_abandon_harmonise"] * base).sum() / base.sum()),
                         "taux_abandon_moyen_2ans": float(g["taux_abandon_moyen_2ans"].mean()),
                         "effectif_base_flux_cp1_cm1": float(base.sum()),
                         "taux_abandon_harmonise_moyenne_provinces": float(g["taux_abandon_harmonise"].mean()),
                         **{c: float(g[c].mean()) for c in ["taux_abandon_publie", "taux_redoublement", "taux_promotion",
                                                            "tap", "ratio_eleves_maitre", "pct_ecoles_eau_potable",
                                                            "pct_ecoles_latrines", "pdi_pour_1000_hab",
                                                            "acled_evenements_pour_100k", "acled_victimes_pour_100k"]},
                         "pdi_nombre": float(g["pdi_nombre"].sum()),
                         "acled_evenements": float(g["acled_evenements"].sum()),
                         "acled_victimes": float(g["acled_victimes"].sum()),
                         "population_totale": float(g["population_totale"].sum()),
                         "population_6_11": float(g["population_6_11"].sum()),
                         "effectif_eleves": float(g["effectif_eleves"].sum()),
                         "nombre_maitres": float(g["nombre_maitres"].sum()), "nombre_ecoles": 10.0,
                         "indice_v2_moyen_pondere": float(g["indice_v2"].mean()),
                         "nb_provinces_top10_v2": float(g["top10_v2"].sum()),
                         "proba_risque_t1_moyenne": (float(g["proba_risque_t1"].mean())
                                                     if g["proba_risque_t1"].notna().any() else np.nan),
                         "nb_provinces_abandon_impute": int(g["abandon_impute"].sum()),
                         "nb_provinces_pdi_impute": int(g["pdi_impute"].sum()),
                         "nb_provinces_effectifs_imputes": int(g["effectif_historique_impute"].sum()),
                         "nb_provinces_population_imputee": int(g["pop_impute"].sum()),
                         "nb_imputations": int(g["nb_imputations"].sum())})
    return pd.DataFrame(rows)


def _geo(p, formes=None):
    lignes, geoms = [], []
    base = p.copy()
    for dec in ("ancien_45", "2025_47"):
        for i, pc in enumerate(sorted(base["pcode_province"].unique())):
            x, y = -5.5 + (i % 9) * 0.5, 9.5 + (i // 9) * 0.5
            parts = [(pc, 0)] if (dec == "ancien_45" or i >= 2) else [(pc + "a", 1), (pc + "b", 1)]
            for k, (code, herite) in enumerate(parts):
                if formes is not None:
                    g = formes[i]
                else:
                    g = carre(x + k * 0.2, y, 0.4 if len(parts) == 1 else 0.2)
                sub = base[base["pcode_province"] == pc]
                reg_code = sub["pcode_region"].iloc[0] if dec == "ancien_45" else sub["pcode_region_2025"].iloc[0]
                reg_nom = sub["region"].iloc[0] if dec == "ancien_45" else sub["region_2025"].iloc[0]
                fiab = ("exact : contour COD-AB v03 inchange (province 1 pour 1)" if dec == "ancien_45"
                        else "officiel COD-AB v03")
                geoms.append({"decoupage": dec, "pcode_province_carte": code,
                              "province_carte": f"{sub['province'].iloc[0]}{k or ''}",
                              "pcode_region_carte": reg_code, "region_carte": reg_nom, "fiabilite_contour": fiab,
                              "valeur_heritee_province_mere": herite, "surface_km2": 1000.0,
                              "geometrie_geojson": json.dumps(g)})
                s = sub.assign(decoupage=dec, pcode_province_carte=code, province_carte=geoms[-1]["province_carte"],
                               pcode_region_carte=reg_code, region_carte=reg_nom, valeur_heritee_province_mere=herite,
                               fiabilite_contour=fiab, surface_km2=1000.0)
                lignes.append(s)
    return pd.concat(lignes, ignore_index=True), pd.DataFrame(geoms)


def _geo_regions(r, formes_regions=None):
    rows = []
    for (dec, code, nom), _ in r.groupby(["decoupage", "pcode_region", "region"]):
        if formes_regions is not None and dec == "ancien_13":
            g = formes_regions[int(code[2:]) - 46]
        elif formes_regions is not None:
            g = formes_regions[int(code[3:]) % len(formes_regions)]
        else:
            g = carre(-5.5, 9.5, 4.5)
        rows.append({"decoupage": dec, "pcode_region": code, "region": nom, "fiabilite_contour": "officiel",
                     "surface_km2": 1.0, "geometrie_geojson": json.dumps(g)})
    return pd.DataFrame(rows)


class SourceSynthetique:
    """Jeu des tests unitaires."""

    def __init__(self):
        self.p = _provinces()
        self.r = _regions(self.p)
        self.g, self.gg = _geo(self.p)
        self.gr = _geo_regions(self.r)
        self.appels = 0

    def charger(self):
        self.appels += 1
        return {"province": self.p.copy(), "region": self.r.copy(), "geo_province": self.g.copy(),
                "geo_province_geom": self.gg.copy(), "geo_region_geom": self.gr.copy()}


def _centre(geom):
    pts = [pt for poly in (geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]])
           for pt in poly[0]]
    return float(np.mean([p[0] for p in pts])), float(np.mean([p[1] for p in pts]))


GEO_LIVRE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo_demo.json")


class SourceDemo(SourceSynthetique):
    """Jeu de démonstration FICTIF. chemin_geo : GeoJSON {"provinces": [{"geometry", "region"}] × 45,
    "regions": [{"geometry"}] × 13} sans aucun attribut réel ; à défaut le fichier livré geo_demo.json
    (contours schématiques approximatifs, pas les limites officielles), sinon carrés synthétiques."""

    def __init__(self, chemin_geo=None):
        formes = formes_reg = None
        risques = None
        if not chemin_geo and os.path.exists(GEO_LIVRE):
            chemin_geo = GEO_LIVRE
        if chemin_geo:
            with open(chemin_geo, encoding="utf-8") as f:
                g = json.load(f)
            if len(g.get("provinces", [])) != 45 or len(g.get("regions", [])) != 13:
                raise ValueError("GeoJSON de démo : 45 provinces et 13 régions attendues")
            formes = [x["geometry"] for x in g["provinces"]]
            formes_reg = [x["geometry"] for x in g["regions"]]
            centres = [_centre(f) for f in formes]
            xs, ys = np.array([c[0] for c in centres]), np.array([c[1] for c in centres])
            # risque fictif : croît vers le nord et l'est (gradient arbitraire, pour une carte lisible)
            lat = (ys - ys.min()) / (np.ptp(ys) or 1)
            lon = (xs - xs.min()) / (np.ptp(xs) or 1)
            rng = np.random.default_rng(7)
            rq = np.clip(0.65 * lat + 0.35 * lon + rng.normal(0, 0.08, 45), 0, 1)
            risques = [(float(rq[i]), int(x["region"])) for i, x in enumerate(g["provinces"])]
        else:
            rng = np.random.default_rng(7)
            risques = [(float((i // 9) / 4 * 0.7 + rng.uniform(0, 0.3)), i % 13) for i in range(45)]
        self.p = _provinces(realiste=True, risques=risques)
        self.r = _regions(self.p)
        self.g, self.gg = _geo(self.p, formes)
        self.gr = _geo_regions(self.r, formes_reg)
        self.appels = 0
