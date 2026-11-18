"""Page Classement refondue : ce qu'une capture d'écran ne montre pas.

Ces tests verrouillent les décisions de conception de la page — une seule action principale, la
légende discrète en HTML plutôt que la barre continue de Plotly, la phrase « Lecture : » sous le
classement — et les dettes effacées : plus de capitales en en-tête de tableau, plus aucune couleur
ni taille écrite en clair dans le Python ou dans la feuille de la page.
"""
import os
import re

import pytest

from dcdash.app import creer_app
from dcdash.config import Config
from dcdash.pages import classement as C

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(RACINE, "assets", "page-classement.css")
HEX = re.compile(r"(?<![\w&/#-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")


@pytest.fixture()
def app(donnees):
    return creer_app(Config(auth_active=False, code_hash="", secret_key=""), donnees)


def cb(app, sortie):
    for k, v in app.callback_map.items():
        if sortie in k:
            return v["callback"].__wrapped__
    raise KeyError(sortie)


def test_entete_de_page_et_action_unique():
    """Titre en français courant, périmètre en une ligne, quatre filtres, une seule action."""
    txt = str(C.layout(annee="2023", sexe="F", mesure="taux_abandon_harmonise", decoupage="2025_47"))
    assert "titre-page" in txt and "Classement des provinces" not in txt  # pas le nom de l'onglet
    assert "cla-resume" in txt and "2023-2024" in txt and "filles" in txt
    assert "filtres-compacts" in txt and txt.count("filtre-lib") == 4
    # une seule action principale, portant l'icône maison (jamais un bouton Bootstrap)
    assert txt.count("btn-dc") == 1 and "ico-telecharger" in txt
    assert "btn-outline-primary" not in txt
    # la phrase de lecture du classement est posée dès le premier rendu, le callback la remplit
    assert "lecture-lib" in txt and txt.index("zone-liste") < txt.index("cla-note")


def test_table_sans_style_en_ligne():
    """Les couleurs et les tailles de la table vivent dans la feuille de la page, plus dans le Python,
    et l'en-tête n'est plus en capitales."""
    rendu = str(C.table_dash("indice_v2_0_100"))
    for interdit in ("style_header", "style_data", "style_filter", "textTransform", "fontSize", "fontFamily",
                     "letterSpacing", "backgroundColor", "borderBottom"):
        assert interdit not in rendu, interdit
    assert not HEX.search(rendu)


def test_feuille_de_page_en_jetons():
    css = open(CSS, encoding="utf-8").read()
    assert not HEX.search(css), HEX.findall(css)
    # tout est porté par la racine de page : aucune règle ne peut déborder ailleurs
    nu = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for regle in (s.strip() for s in re.findall(r"([^{}]+)\{", nu)):
        assert regle.startswith("@") or ".page-classement" in regle, regle
    assert "text-transform: none" in css and "uppercase" not in css
    assert "transition: all" not in css and "100vh" not in css
    # même plancher « un seul écran » que la feuille commune : 1366 × 768 est une taille d'écran, la fenêtre
    # n'en montre que ~650 px, et au-dessous de ce plancher la page se remettait à défiler (mesuré)
    assert "@media (min-width: 1280px) and (min-height: 600px) {" in css and "min-height: 720px" not in css


def test_legende_discrete_et_lecture(app):
    """La carte porte la légende partagée en neuf pas (pas la barre continue de Plotly) et sa note
    nomme chaque code visuel ; le classement porte sa phrase « Lecture : »."""
    data, cols, resume, fig, titre, lect, note = cb(app, "cla-table.data")(2024, "T", "ancien_45",
                                                                           "indice_v2_0_100")
    s = str(lect)
    assert "legende-carte" in s and "ech-risque-9" in s
    # mêmes règles que sur la vue d'ensemble : plus de contour noir ni de clé « top 10 », et
    # « non disponible » n'apparaît que si la carte affichée contient vraiment une province sans
    # valeur — ce n'est pas le cas du jeu de démonstration
    assert "Contour noir" not in s and "top 10" not in s and "legende-top10" not in s
    assert "non disponible" not in s and "limites des régions" in s
    assert all(t.line.width < 1 for t in fig.data if t.fill == "toself")
    assert not any(getattr(t.marker, "showscale", None) for t in fig.data)
    assert "Carte : score de risque (45 provinces)" == titre
    assert "cliquez sur une province" in note and len(data) == 45
