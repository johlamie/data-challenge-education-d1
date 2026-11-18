"""Calculs dérivés des vues (aucune donnée n'est lue ailleurs)."""
import numpy as np
import pandas as pd

from .meta import COMPOSANTES, INDICATEURS


def zscore(s):
    """z-score dans l'année et le sexe, borné à ±3 (même définition que l'indice v2 du jalon c)."""
    s = s.astype(float)
    sd = s.std(ddof=0)
    if not sd or sd != sd or sd == 0:
        return s * 0.0
    return ((s - s.mean()) / sd).clip(-3, 3)


def contributions(df_annee_sexe):
    """Contribution de chaque composante à l'indice v2 : poids × z (valeurs manquantes à la moyenne).

    df_annee_sexe : une ligne par province (45) pour une année et un sexe.
    Renvoie un DataFrame indexé par pcode_province, une colonne par composante, plus 'total'.
    """
    d = df_annee_sexe.set_index("pcode_province")
    tot_poids = sum(w for _, w, _, _ in COMPOSANTES)
    out = {}
    for col, w, sens, _ in COMPOSANTES:
        z = zscore(d[col] * sens)
        out[col] = w * z.fillna(z.mean()) / tot_poids
    r = pd.DataFrame(out)
    r["total"] = r.sum(axis=1)
    return r


def rangs(df, col, sens):
    """Rang 1 = situation la plus à risque (ou la plus grande valeur pour un indicateur neutre)."""
    s = df[col].astype(float)
    asc = sens < 0
    return s.rank(ascending=asc, method="min")


def est_impute(df, cle):
    """Série booléenne : la valeur de l'indicateur est imputée (ou l'indice contient une composante imputée)."""
    m = INDICATEURS[cle]
    f = m.get("flag")
    if not f or f not in df.columns:
        return pd.Series(False, index=df.index)
    return df[f].fillna(0).astype(float) > 0


def source_imputation(df, cle):
    m = INDICATEURS[cle]
    s = m.get("source")
    if cle == "indice_v2":
        return df["nb_composantes_imputees"].fillna(0).map(
            lambda n: f"{int(n)} composante(s) imputée(s)" if n > 0 else "")
    if not s or s not in df.columns:
        return pd.Series("", index=df.index)
    return df[s].fillna("")


def nationaux(region, province, annee, sexe):
    """Chiffres clés nationaux pour une année et un sexe (agrégés depuis la vue région, ancien découpage).

    - abandon harmonisé : flux sommés (somme des taux régionaux pondérés par l'effectif de base des flux), exact ;
    - élèves par maître : somme des effectifs / somme des maîtres ;
    - TAP : moyenne pondérée par la population 6-11 ans (approximation) ;
    - PDI et ACLED : totaux rapportés à la population.
    """
    r = region[(region["decoupage"] == "ancien_13") & (region["annee_debut"] == annee) & (region["sexe"] == sexe)]
    if r.empty:
        return {}
    b = r["effectif_base_flux_cp1_cm1"]
    rt = region[(region["decoupage"] == "ancien_13") & (region["annee_debut"] == annee) & (region["sexe"] == "T")]
    pop_t = rt["population_totale"].sum()

    def wmean(col, w):
        m = r[col].notna() & w.notna()
        return float((r.loc[m, col] * w[m]).sum() / w[m].sum()) if w[m].sum() > 0 else np.nan

    p = province[(province["annee_debut"] == annee) & (province["sexe"] == sexe)]
    pt = province[(province["annee_debut"] == annee) & (province["sexe"] == "T")]
    return {
        "taux_abandon_harmonise": wmean("taux_abandon_harmonise", b),
        "taux_abandon_publie": wmean("taux_abandon_publie", r["effectif_eleves"]),
        "effectif_eleves": float(r["effectif_eleves"].sum()),
        "ratio_eleves_maitre": float(rt["effectif_eleves"].sum() / rt["nombre_maitres"].sum()),
        "tap": wmean("tap", r["population_6_11"]),
        "pdi_nombre": float(rt["pdi_nombre"].sum()),
        "pdi_pour_1000_hab": float(1000 * rt["pdi_nombre"].sum() / pop_t) if pop_t else np.nan,
        "acled_evenements": float(rt["acled_evenements"].sum()),
        "acled_victimes": float(rt["acled_victimes"].sum()),
        "nb_province_imputations": int((p["nb_imputations"].fillna(0) > 0).sum()),
        "nb_top10_stables": int((pt["statut_top10_mc"] == "stable_top10").sum()),
    }


def ensemble_national(region, sexe):
    """Série nationale de l'abandon harmonisé (flux sommés) par année."""
    r = region[(region["decoupage"] == "ancien_13") & (region["sexe"] == sexe)]
    g = r.assign(_n=r["taux_abandon_harmonise"] * r["effectif_base_flux_cp1_cm1"]).groupby("annee_debut")
    return (g["_n"].sum() / g["effectif_base_flux_cp1_cm1"].sum()).rename("taux_abandon_harmonise")


def abandons_estimes(region, annee, sexe):
    """Nombre estimé d'élèves ayant abandonné : Σ taux harmonisé × effectif de base des flux CP1-CM1 / 100
    (13 régions, ancien découpage). Même pondération que le taux national."""
    r = region[(region["decoupage"] == "ancien_13") & (region["annee_debut"] == annee) & (region["sexe"] == sexe)]
    m = r["taux_abandon_harmonise"].notna() & r["effectif_base_flux_cp1_cm1"].notna()
    if not m.any():
        return np.nan
    return float((r.loc[m, "taux_abandon_harmonise"] * r.loc[m, "effectif_base_flux_cp1_cm1"]).sum() / 100)


def kpis_decideurs(region, province, annee, sexe, seuil_alerte=0.5):
    """Chiffres clés de la vue d'ensemble, tous calculés depuis les vues dashboard (aucune valeur en dur).

    - abandon : taux national harmonisé (année, sexe) et variation sur un an (points) ;
    - alerte : provinces dont la probabilité d'être dans le quart le plus touché l'an prochain ≥ seuil (sexe T) ;
    - écart F-G : abandon harmonisé national filles − garçons (points) ;
    - province la plus à risque : rang 1 de l'indice v2 (année, sexe) ;
    - abandons estimés : voir abandons_estimes ;
    - PDI : stock total (sexe T) et taux pour 1 000 habitants.
    """
    n = nationaux(region, province, annee, sexe)
    if not n:
        return {}
    n0 = nationaux(region, province, annee - 1, sexe)
    nf = nationaux(region, province, annee, "F")
    ng = nationaux(region, province, annee, "G")
    nf0 = nationaux(region, province, annee - 1, "F")
    ng0 = nationaux(region, province, annee - 1, "G")
    pt0 = province[(province["annee_debut"] == annee - 1) & (province["sexe"] == "T")]
    proba0 = pt0["proba_risque_t1"]
    p = province[(province["annee_debut"] == annee) & (province["sexe"] == sexe)]
    pt = province[(province["annee_debut"] == annee) & (province["sexe"] == "T")]
    pf = province[(province["annee_debut"] == annee) & (province["sexe"] == "F")]
    proba = pt["proba_risque_t1"]
    top = p.sort_values("rang_v2").head(1)
    rt = region[(region["decoupage"] == "ancien_13") & (region["annee_debut"] == annee) & (region["sexe"] == "T")]
    ab = abandons_estimes(region, annee, sexe)
    ab0 = abandons_estimes(region, annee - 1, sexe)
    v0 = n0.get("taux_abandon_harmonise") if n0 else np.nan
    return {
        "abandon": n["taux_abandon_harmonise"],
        "abandon_variation": (n["taux_abandon_harmonise"] - v0) if v0 == v0 and v0 is not None else np.nan,
        "nb_alerte": int((proba >= seuil_alerte).sum()) if proba.notna().any() else None,
        "nb_provinces": int(len(pt)),
        "abandon_filles": nf.get("taux_abandon_harmonise", np.nan) if nf else np.nan,
        "abandon_garcons": ng.get("taux_abandon_harmonise", np.nan) if ng else np.nan,
        "nb_provinces_abandon_filles_impute": int((pf["abandon_impute"].fillna(0) > 0).sum()),
        "province_top": (top["nom_officiel_province_ancienne"].fillna(top["province"]).iloc[0]
                         if "nom_officiel_province_ancienne" in top and len(top) else
                         (top["province"].iloc[0] if len(top) else None)),
        "region_top": top["region"].iloc[0] if len(top) else None,
        "pcode_top": top["pcode_province"].iloc[0] if len(top) else None,
        "abandon_top": float(top["taux_abandon_harmonise"].iloc[0]) if len(top) else np.nan,
        "abandons_estimes": ab,
        "abandons_estimes_variation": (ab - ab0) if ab == ab and ab0 == ab0 else np.nan,
        "pdi_nombre": n["pdi_nombre"],
        "pdi_pour_1000_hab": n["pdi_pour_1000_hab"],
        # valeurs de l'année précédente (pour les flèches de tendance ; NaN / None si non disponible)
        "ecart_fg_prec": ((nf0.get("taux_abandon_harmonise", np.nan) - ng0.get("taux_abandon_harmonise", np.nan))
                          if nf0 and ng0 else np.nan),
        "nb_alerte_prec": int((proba0 >= seuil_alerte).sum()) if proba0.notna().any() else None,
        "pdi_nombre_prec": n0.get("pdi_nombre", np.nan) if n0 else np.nan,
        "pdi_prolonge": bool((rt["nb_provinces_pdi_impute"].fillna(0) > 0).any()) if "nb_provinces_pdi_impute" in rt else False,
    }
