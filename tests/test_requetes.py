"""Tests d'intégration sur la vraie base (lecture seule). Ignorés sans DC_EDU_PG_PASSWORD.

N'affichent jamais de valeurs : uniquement des comptes et des contrôles de structure.
"""
import os

import pytest

from dcdash.config import Config
from dcdash.db import Donnees, SourcePostgres

pytestmark = pytest.mark.skipif(not os.environ.get("DC_EDU_PG_PASSWORD"), reason="base non configurée")


@pytest.fixture(scope="module")
def src():
    return SourcePostgres(Config())


def test_comptes_vues(src):
    n = src.requete('SELECT (SELECT count(*) FROM "analyse".v_dashboard_province_annee) a, '
                    '(SELECT count(*) FROM "analyse".v_dashboard_region_annee) b, '
                    '(SELECT count(*) FROM "analyse".v_dashboard_geo_province) c, '
                    '(SELECT count(*) FROM "analyse".v_dashboard_geo_region) d').iloc[0].tolist()
    assert n == [1080, 720, 2208, 720]


def test_chargement_et_structure(src):
    d = Donnees(src)
    x = d.get()
    assert len(x["province"]) == 1080 and len(x["region"]) == 720 and len(x["geo_province"]) == 2208
    g = x["geo_province_geom"]
    assert sorted(g.groupby("decoupage").size().tolist()) == [45, 47]
    assert all(t["type"] in ("Polygon", "MultiPolygon") for t in g["geometrie"])
    assert sorted(x["geo_region_geom"].groupby("decoupage").size().tolist()) == [13, 17]
    p = x["province"]
    assert p.groupby(["annee_debut", "sexe"]).size().eq(45).all()
    from dcdash.calculs import contributions
    for (a, s), q in p.groupby(["annee_debut", "sexe"]):
        c = contributions(q)
        assert (c["total"] - q.set_index("pcode_province")["indice_v2"]).abs().max() < 1e-6


def test_lecture_seule_et_perimetre(src):
    import psycopg
    with pytest.raises(psycopg.Error):
        src.requete('CREATE TABLE "analyse".zz_test_ro (x int)')
    with pytest.raises(psycopg.Error):
        src.requete("SELECT 1 FROM clean.cln_d_correspondance_communes_decoupage_2025 LIMIT 1")
    with pytest.raises(psycopg.Error):
        src.requete('SELECT 1 FROM "analyse".controles_jalon_d LIMIT 1')
    r = src.requete("SELECT current_setting('transaction_read_only') ro, current_user u").iloc[0]
    assert r["ro"] == "on" and r["u"] == "dc_edu_ro"
