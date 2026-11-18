"""Mise en forme des données des vues pour les pages (filtrage, rangs, textes de survol)."""
import pandas as pd

from .calculs import est_impute, rangs, source_imputation
from .meta import DECOUPAGE_REGION, INDICATEURS, fmt_valeur, libelle_source, nom_propre


def disponible(cle, annee, sexe):
    if cle == "proba_risque_t1":
        return sexe == "T" and 2020 <= annee <= 2024
    return True


def message_indisponible(cle):
    if cle == "proba_risque_t1":
        return "Probabilité t+1 disponible uniquement pour l'ensemble (T), années 2020-2021 à 2024-2025."
    return "Indicateur non disponible pour cette sélection."


def classement(d, annee, sexe, cle):
    """Rang national sur les 45 provinces (vue province) pour l'indicateur choisi."""
    p = d.province()
    p = p[(p["annee_debut"] == annee) & (p["sexe"] == sexe)].copy()
    sens = INDICATEURS[cle]["sens"]
    p["_rang"] = rangs(p, cle, sens if sens != 0 else 1)
    return p.set_index("pcode_province")["_rang"]


def table_carte(d, decoupage, annee, sexe, cle, regions=None):
    """Lignes de la vue géo province pour un découpage, une année, un sexe ; colonnes prêtes pour la carte."""
    g = d.geo_province()
    g = g[(g["decoupage"] == decoupage) & (g["annee_debut"] == annee) & (g["sexe"] == sexe)].copy()
    if regions:
        g = g[g["pcode_region_carte"].isin(regions)]
    rg = classement(d, annee, sexe, cle)
    g["rang"] = g["pcode_province"].map(rg)
    g["valeur"] = g[cle].astype(float)
    g["impute"] = est_impute(g, cle)
    g["source"] = source_imputation(g, cle).map(libelle_source)
    g.loc[~g["impute"], "source"] = ""
    return g.sort_values(["rang", "province_carte"], na_position="last")


def survol(row, cle, n=45):
    m = INDICATEURS[cle]
    t = f"<b>{row['province_carte']}</b> · {row['region_carte']}<br>{m['label']} : {fmt_valeur(row['valeur'], cle)}"
    if row.get("rang") == row.get("rang") and row.get("rang") is not None:
        t += f"<br>Rang : {int(row['rang'])} / {n}"
    if row.get("impute"):
        t += f"<br><i>* Valeur imputée : {row.get('source') or 'voir Qualité des données'}</i>"
    if row.get("valeur_heritee_province_mere") == 1:
        t += f"<br><i>Valeur de la province mère ({row['province']}), non répartie</i>"
    return t


def geoms_provinces(d, decoupage, codes=None):
    g = d.geometries_provinces(decoupage).rename(columns={"pcode_province_carte": "code", "province_carte": "nom"})
    if codes is not None:
        g = g[g["code"].isin(codes)]
    return g[["code", "nom", "geometrie", "pcode_region_carte"]]


def geoms_regions(d, decoupage, codes_regions=None):
    g = d.geometries_regions(DECOUPAGE_REGION[decoupage])
    if codes_regions:
        g = g[g["pcode_region"].isin(codes_regions)]
    return g


def valeurs_carte(t, cle, n=45):
    return {r["pcode_province_carte"]: dict(valeur=r["valeur"], impute=bool(r["impute"]), survol=survol(r, cle, n))
            for _, r in t.iterrows()}


def options_regions(d, decoupage):
    g = d.geometries_provinces(decoupage)[["pcode_region_carte", "region_carte"]].drop_duplicates()
    g = g.sort_values("region_carte")
    return [{"label": r.region_carte.title() if r.region_carte.isupper() else r.region_carte,
             "value": r.pcode_region_carte} for r in g.itertuples()]


def options_provinces(d):
    p = d.province()[["pcode_province", "province", "nom_officiel_province_ancienne", "region"]]
    p = p.drop_duplicates("pcode_province").sort_values("province")
    return [{"label": f"{nom_propre(r.nom_officiel_province_ancienne or r.province)} ({nom_propre(r.region)})",
             "value": r.pcode_province} for r in p.itertuples()]


def top_n(d, annee, sexe, n=10):
    p = d.province()
    p = p[(p["annee_debut"] == annee) & (p["sexe"] == sexe)]
    return p.sort_values("rang_v2").head(n)


def nom_province(d, pcode):
    p = d.province()
    s = p.loc[p["pcode_province"] == pcode, "province"]
    return s.iloc[0] if len(s) else pcode
