"""Contours schématiques de la démo (dcdash/geo_demo.json) : pavage exact, cohérence provinces/régions, déterminisme.

Aucune donnée réelle : le fichier ne contient que des géométries approximatives et un indice de région.
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER = os.path.join(RACINE, "dcdash", "geo_demo.json")
GENERATEUR = os.path.join(RACINE, "outils", "generer_geo_demo.py")


def _module():
    spec = importlib.util.spec_from_file_location("generer_geo_demo", GENERATEUR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def geo():
    with open(FICHIER, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def gen():
    return _module()


def _anneaux(g):
    return [poly[0] for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]])]


def _aire(anneau):
    s = 0.0
    for i in range(len(anneau) - 1):
        s += anneau[i][0] * anneau[i + 1][1] - anneau[i + 1][0] * anneau[i][1]
    return abs(s) / 2


def _dedans(point, anneaux):
    x, y = point
    r = False
    for anneau in anneaux:
        for i in range(len(anneau) - 1):
            x1, y1 = anneau[i]
            x2, y2 = anneau[i + 1]
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                r = not r
    return r


def test_structure(geo):
    assert len(geo["provinces"]) == 45 and len(geo["regions"]) == 13
    assert "approximatifs" in geo["note"].lower() and "DC_EDU_DEMO_GEO" in geo["note"]
    # nombre de provinces par région, structure des 13 anciennes régions
    comptes = [sum(1 for p in geo["provinces"] if p["region"] == k) for k in range(13)]
    assert comptes == [6, 2, 1, 3, 3, 4, 3, 5, 3, 4, 3, 4, 4] and sum(comptes) == 45
    assert all(set(p) == {"geometry", "region"} for p in geo["provinces"])
    assert all(set(r) == {"geometry"} for r in geo["regions"])


def test_polygones_valides(geo):
    for entite in geo["provinces"] + geo["regions"]:
        anneaux = _anneaux(entite["geometry"])
        assert anneaux
        for a in anneaux:
            assert len(a) >= 4 and a[0] == a[-1]
            assert _aire(a) > 1e-6
            assert all(len(p) == 2 for p in a)


def test_emprise_burkina(geo):
    pts = [p for e in geo["provinces"] for a in _anneaux(e["geometry"]) for p in a]
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    assert -5.6 <= min(lons) and max(lons) <= 2.5
    assert 9.3 <= min(lats) and max(lats) <= 15.2
    # pays reconnaissable : il occupe bien son emprise (≈ 274 000 km2)
    aire = sum(_aire(a) for e in geo["provinces"] for a in _anneaux(e["geometry"])) * 111.32 * 110.57 * 0.9771
    assert 240_000 < aire < 310_000


def test_pavage_exact(geo, gen):
    pays = abs(gen.aire(gen.contour()))
    prov = sum(_aire(a) for e in geo["provinces"] for a in _anneaux(e["geometry"])) * 0.9771
    reg = sum(_aire(a) for e in geo["regions"] for a in _anneaux(e["geometry"])) * 0.9771
    assert abs(prov - pays) / pays < 0.005
    assert abs(reg - pays) / pays < 0.005


def test_provinces_dans_leur_region(geo):
    for i, p in enumerate(geo["provinces"]):
        anneaux = _anneaux(p["geometry"])
        grand = max(anneaux, key=_aire)
        c = (sum(x for x, _ in grand[:-1]) / (len(grand) - 1), sum(y for _, y in grand[:-1]) / (len(grand) - 1))
        if not _dedans(c, [grand]):  # centre de gravité hors d'un contour très concave : on prend un sommet décalé
            c = ((grand[0][0] + c[0]) / 2, (grand[0][1] + c[1]) / 2)
        assert _dedans(c, _anneaux(geo["regions"][p["region"]]["geometry"])), f"province {i} hors de sa région"


def test_generateur_deterministe(tmp_path, geo):
    cible = tmp_path / "geo.json"
    subprocess.run([sys.executable, GENERATEUR, str(cible)], check=True, cwd=RACINE, capture_output=True)
    assert json.loads(cible.read_text(encoding="utf-8")) == geo


def test_source_demo_utilise_les_contours():
    from dcdash.demo import SourceDemo
    s = SourceDemo()
    g = s.gg[s.gg["decoupage"] == "ancien_45"]
    assert len(g) == 45
    formes = [json.loads(x) for x in g["geometrie_geojson"]]
    pts = [p for f in formes for poly in f["coordinates"] for p in poly[0]]
    assert len({(round(p[0], 2), round(p[1], 2)) for p in pts}) > 500  # pas une grille de carrés
    assert min(p[1] for p in pts) < 10 and max(p[1] for p in pts) > 15
