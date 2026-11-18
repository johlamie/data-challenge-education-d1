"""Création de l'application Dash (fabrique), routage et assemblage des pages."""
import logging
import os
from urllib.parse import parse_qs

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from . import __version__, db
from .auth import installer_auth, installer_entetes
from .composants import bandeau, barre_navigation, page_404
from .config import Config
from .pages import accueil, classement, evolution, fiche, methode, qualite

# l'ancienne page « Carte et classement » (/carte) n'existe plus : ce chemin mène au classement complet
ROUTES = {"/": accueil, "/classement": classement, "/carte": classement, "/evolution": evolution, "/fiche": fiche,
          "/qualite": qualite, "/methode": methode}
MODULES = (accueil, classement, evolution, fiche, qualite, methode)
PLEIN_ECRAN = (accueil, classement)
ICI = os.path.dirname(os.path.abspath(__file__))

INDEX = """<!DOCTYPE html>
<html lang="fr">
<head>
{%metas%}
<title>{%title%}</title>
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{%css%}
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""


def creer_app(cfg=None, donnees=None):
    cfg = cfg or Config()
    if donnees is not None:
        db.installer(donnees)
    app = dash.Dash(
        __name__, title="Décrochage scolaire au primaire · Burkina Faso", update_title="Chargement…",
        assets_folder=os.path.join(os.path.dirname(ICI), "assets"), serve_locally=True,
        suppress_callback_exceptions=True, compress=True, external_stylesheets=[], external_scripts=[],
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"},
                   {"name": "robots", "content": "noindex, nofollow"}])
    app.index_string = INDEX
    app.layout = html.Div([
        dcc.Location(id="url", refresh=False),
        # premier arrêt du clavier : sauter la navigation pour aller droit au contenu
        html.A("Aller au contenu", href="#page", className="lien-evitement"),
        # le bandeau est le premier élément de chaque page, au-dessus du masthead, dans tous les états
        bandeau(cfg.demo, __version__),
        barre_navigation(cfg.auth_active),
        # tabIndex=-1 : la cible du lien d'évitement doit pouvoir recevoir le focus, sinon le clavier
        # reprend sa course au début de la page
        html.Main(id="page", className="page", tabIndex="-1"),
    ], id="racine", className="racine")

    @app.callback(Output("page", "children"), Output("racine", "className"),
                  Input("url", "pathname"), Input("url", "search"))
    def router(chemin, recherche):
        mod = ROUTES.get((chemin or "/").rstrip("/") or "/")
        if mod is None:
            return page_404(), "racine"
        q = {k: v[0] for k, v in parse_qs((recherche or "").lstrip("?")).items()}
        # la vue d'ensemble et le classement tiennent sur un écran d'ordinateur (plein écran, sans défilement)
        return mod.layout(**q), ("racine racine-pleine" if mod in PLEIN_ECRAN else "racine")

    @app.callback(Output("nav-menu", "is_open"), Input("nav-bascule", "n_clicks"), State("nav-menu", "is_open"),
                  prevent_initial_call=True)
    def bascule(n, ouvert):
        return not ouvert

    for mod in MODULES:
        mod.register(app)
    installer_auth(app.server, cfg)
    try:
        hashes = app.csp_hashes()
    except Exception:
        hashes = []
    installer_entetes(app.server, hashes)
    return app


def creer_app_production():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cfg = Config()
    if cfg.demo:
        from .demo import SourceDemo
        logging.getLogger("dcdash").warning("MODE DÉMO : données synthétiques fictives, aucune connexion à la base")
        d = db.Donnees(SourceDemo(cfg.demo_geo or None), ttl_s=10 ** 9)
        return creer_app(cfg, d)
    d = db.Donnees(db.SourcePostgres(cfg), ttl_s=cfg.cache_ttl_s)
    app = creer_app(cfg, d)
    try:
        d.get()  # préchargement ; en cas d'échec, nouvel essai à la première requête
        logging.getLogger("dcdash").info("données chargées")
    except Exception as e:
        logging.getLogger("dcdash").error("préchargement impossible : %s", type(e).__name__)
    return app
