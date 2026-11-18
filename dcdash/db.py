"""Accès aux données : uniquement les 4 vues dashboard du schéma "analyse", via le rôle lecture seule dc_edu_ro.

Les vues sont petites (≈ 1 Mo au total) : elles sont chargées en mémoire et rafraîchies toutes les
`cache_ttl_s` secondes. Si un rafraîchissement échoue, les données précédentes sont conservées.
"""
import json
import logging
import threading
import time

import pandas as pd

log = logging.getLogger("dcdash.db")

VUES = ("v_dashboard_province_annee", "v_dashboard_region_annee",
        "v_dashboard_geo_province", "v_dashboard_geo_region")

SQL = {
    "province": 'SELECT * FROM "analyse".v_dashboard_province_annee ORDER BY sexe, annee_debut, pcode_province',
    "region": 'SELECT * FROM "analyse".v_dashboard_region_annee ORDER BY decoupage, sexe, annee_debut, pcode_region',
    # attributs de la vue géo province sans les géométries (répétées pour chaque année et sexe)
    "geo_province_cols": ("SELECT column_name FROM information_schema.columns WHERE table_schema = 'analyse' "
                          "AND table_name = 'v_dashboard_geo_province' AND column_name NOT IN "
                          "('geometrie_geojson', 'geom_web') ORDER BY ordinal_position"),
    "geo_province_geom": ('SELECT DISTINCT ON (decoupage, pcode_province_carte) decoupage, pcode_province_carte, '
                          'province_carte, pcode_region_carte, region_carte, fiabilite_contour, '
                          'valeur_heritee_province_mere, surface_km2, geometrie_geojson '
                          'FROM "analyse".v_dashboard_geo_province ORDER BY decoupage, pcode_province_carte'),
    "geo_region_geom": ('SELECT DISTINCT ON (decoupage, pcode_region) decoupage, pcode_region, region, '
                        'fiabilite_contour, surface_km2, geometrie_geojson '
                        'FROM "analyse".v_dashboard_geo_region ORDER BY decoupage, pcode_region'),
}


class SourcePostgres:
    """Exécute les requêtes en lecture seule. Compatible pooler en mode transaction (pas de requêtes préparées)."""

    def __init__(self, cfg):
        self.cfg = cfg

    def _connexion(self):
        import psycopg
        return psycopg.connect(host=self.cfg.pg_host, port=self.cfg.pg_port, dbname=self.cfg.pg_db,
                               user=self.cfg.pg_user, password=self.cfg.pg_password, connect_timeout=10,
                               autocommit=True, prepare_threshold=None, application_name="dc-edu-dashboard")

    def requete(self, sql):
        with self._connexion() as cx, cx.cursor() as cur:
            cur.execute(sql)
            cols = [d.name for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)

    def charger(self):
        geo_cols = self.requete(SQL["geo_province_cols"])["column_name"].tolist()
        sql_geo_attr = ('SELECT ' + ", ".join(f'"{c}"' for c in geo_cols) +
                        ' FROM "analyse".v_dashboard_geo_province ORDER BY decoupage, sexe, annee_debut, pcode_province_carte')
        return {
            "province": self.requete(SQL["province"]),
            "region": self.requete(SQL["region"]),
            "geo_province": self.requete(sql_geo_attr),
            "geo_province_geom": self.requete(SQL["geo_province_geom"]),
            "geo_region_geom": self.requete(SQL["geo_region_geom"]),
        }


def _normaliser(df):
    """Convertit les colonnes numériques (Decimal, entiers nullables) en float, sauf identifiants texte."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == object:
            s = df[c].dropna()
            if len(s) and not isinstance(s.iloc[0], str):
                df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
        elif str(df[c].dtype) not in ("float64",) and pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].astype(float)
    for c in ("annee_debut",):
        if c in df.columns:
            df[c] = df[c].astype(int)
    return df


class Donnees:
    """Cache mémoire thread-safe des vues dashboard."""

    def __init__(self, source, ttl_s=900):
        self.source = source
        self.ttl_s = ttl_s
        self._verrou = threading.Lock()
        self._d = None
        self._t = 0.0
        self.derniere_erreur = None

    def _rafraichir(self):
        brut = self.source.charger()
        d = {k: _normaliser(v) for k, v in brut.items()}
        for k in ("geo_province_geom", "geo_region_geom"):
            d[k]["geometrie"] = d[k]["geometrie_geojson"].map(json.loads)
            d[k] = d[k].drop(columns=["geometrie_geojson"])
        self._d = d
        self._t = time.time()
        self.derniere_erreur = None

    def get(self):
        if self._d is not None and time.time() - self._t < self.ttl_s:
            return self._d
        with self._verrou:
            if self._d is None or time.time() - self._t >= self.ttl_s:
                try:
                    self._rafraichir()
                except Exception as e:  # garder les données précédentes
                    self.derniere_erreur = type(e).__name__
                    log.error("rafraichissement impossible : %s", type(e).__name__)
                    if self._d is None:
                        raise
                    self._t = time.time() - self.ttl_s + 60  # nouvel essai dans 60 s
        return self._d

    @property
    def horodatage(self):
        return self._t

    # accès pratiques -------------------------------------------------------
    def province(self):
        return self.get()["province"]

    def region(self):
        return self.get()["region"]

    def geo_province(self):
        return self.get()["geo_province"]

    def geometries_provinces(self, decoupage):
        g = self.get()["geo_province_geom"]
        return g[g["decoupage"] == decoupage]

    def geometries_regions(self, decoupage_region):
        g = self.get()["geo_region_geom"]
        return g[g["decoupage"] == decoupage_region]


_DONNEES = None


def installer(donnees):
    global _DONNEES
    _DONNEES = donnees


def donnees():
    if _DONNEES is None:
        raise RuntimeError("source de données non installée")
    return _DONNEES
