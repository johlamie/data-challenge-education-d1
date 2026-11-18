import numpy as np

from dcdash import calculs
from dcdash.meta import fmt_valeur


def test_contributions_reconstituent_indice(donnees):
    p = donnees.province()
    for (a, s), g in p.groupby(["annee_debut", "sexe"]):
        c = calculs.contributions(g)
        ecart = (c["total"] - g.set_index("pcode_province")["indice_v2"]).abs().max()
        assert ecart < 1e-9


def test_rangs_sens(donnees):
    p = donnees.province()
    g = p[(p["annee_debut"] == 2024) & (p["sexe"] == "T")]
    r = calculs.rangs(g, "pct_ecoles_eau_potable", -1)
    assert g.loc[r.idxmin(), "pct_ecoles_eau_potable"] == g["pct_ecoles_eau_potable"].min()


def test_nationaux(donnees):
    n = calculs.nationaux(donnees.region(), donnees.province(), 2024, "T")
    p = donnees.province()
    g = p[(p["annee_debut"] == 2024) & (p["sexe"] == "T")]
    attendu = (g["taux_abandon_harmonise"] * g["effectif_eleves"]).sum() / g["effectif_eleves"].sum()
    assert abs(n["taux_abandon_harmonise"] - attendu) < 1e-9
    assert abs(n["effectif_eleves"] - g["effectif_eleves"].sum()) < 1e-6


def test_format_francais():
    assert fmt_valeur(12.345, "taux_abandon_harmonise") == "12,3\u00a0%"
    assert fmt_valeur(0.456, "proba_risque_t1") == "46\u00a0%"
    assert fmt_valeur(np.nan, "tap") == "n.d."
    assert fmt_valeur(1234567, "effectif_eleves") == "1\u202f234\u202f567"


def test_cache_ttl(source):
    from dcdash.db import Donnees
    d = Donnees(source, ttl_s=3600)
    n0 = source.appels
    d.get()
    d.get()
    assert source.appels == n0 + 1
