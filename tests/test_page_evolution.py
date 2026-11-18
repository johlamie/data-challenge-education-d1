"""Page Évolution : ce qu'une capture d'écran ne montre pas.

Ces tests verrouillent les décisions de conception de la page — identité des séries sans la couleur
seule, état vide qui dit pourquoi, titres d'axe avec leur unité, plafond de 8 entités annoncé — et le
fait que la feuille de page n'écrit aucune couleur en clair.

Ils verrouillent aussi la densité de l'entête : une ligne
de périmètre courte, l'interrupteur de la moyenne nationale dans la rangée de filtres, et la clé des
tracés (trait plein, tirets, ligne grise, marqueur creux) conservée dans la phrase de lecture.
"""
import os
import re

import pytest

from dcdash import figures as F
from dcdash.app import creer_app
from dcdash.config import Config
from dcdash.pages import evolution as E

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(RACINE, "assets", "page-evolution.css")
HEX = re.compile(r"(?<![\w&/#-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")


@pytest.fixture()
def app(donnees):
    return creer_app(Config(auth_active=False, code_hash="", secret_key=""), donnees)


def _cb(app, sortie):
    for k, v in app.callback_map.items():
        if sortie in k:
            return v["callback"].__wrapped__
    raise KeyError(sortie)


def _noeud(racine, classe):
    """Premier nœud de l'arbre de composants portant cette classe CSS (recherche en profondeur)."""
    enfants = getattr(racine, "children", None)
    if classe in (getattr(racine, "className", "") or "").split():
        return racine
    if isinstance(enfants, (list, tuple)):
        for e in enfants:
            trouve = _noeud(e, classe)
            if trouve is not None:
                return trouve
    elif enfants is not None and not isinstance(enfants, str):
        return _noeud(enfants, classe)
    return None


def test_page_composee_du_kit(app):
    """L'entête est une question, les cinq filtres portent un libellé visible, et la page n'ajoute
    aucune icône « i » (le budget du site est déjà tenu ailleurs)."""
    page = str(_cb(app, "page.children")("/evolution", "")[0])
    assert "Le décrochage s'aggrave-t-il, et où ?" in page
    assert page.count("filtre-lib") == 5 and "className='aide'" not in page
    assert "segment" in page and "legende-series" in page


def test_entete_court_et_interrupteur_dans_la_rangee():
    """Densité : la ligne de périmètre tient sur une ligne courte, et
    l'interrupteur de la moyenne nationale est un enfant de la rangée de filtres — il ne prend plus
    une ligne pour lui seul, ce qui repoussait le premier graphique hors de l'écran sur un portable."""
    assert len(E.SOUS_TITRE) <= 60 and "\n" not in E.SOUS_TITRE
    assert "trait plein" not in E.SOUS_TITRE.lower()  # la clé est descendue sous le graphique

    rangee = _noeud(E.layout(), "filtres-evolution")
    assert rangee is not None
    interrupteur = _noeud(rangee, "interrupteur-national")
    assert interrupteur is not None and interrupteur.children.id == "evo-national"
    # la commande garde son libellé visible : rien n'est troqué contre la densité
    assert interrupteur.children.options[0]["label"] == "Afficher la moyenne du Burkina Faso"

    css = open(CSS, encoding="utf-8").read()
    assert "min-width: 1280px" in css and ".filtres-evolution > .interrupteur-national" in css


def test_cle_des_traces_conservee_sous_le_graphique(app):
    """La clé « trait plein / tirets / ligne grise / marqueur creux » a quitté l'entête, mais aucun
    code visuel n'est perdu : elle est dite dans la phrase de lecture du premier graphique."""
    options, valeurs, _ = _cb(app, "evo-entites.options")("province", "ancien_45")
    *_, l1 = _cb(app, "evo-abandon.figure")("province", "ancien_45", "T", valeurs, "indice_v2", ["nat"])
    texte = str(l1)
    for code in ("trait plein", "tirets", "ligne grise", "marqueur creux"):
        assert code in texte
    assert "Lecture" in texte


def test_series_nommees_et_etat_vide(app):
    """Cas nominal : chaque entité est nommée au bout de sa courbe et dans les pastilles ; la courbe
    de contrôle, elle, ne l'est pas. Sans sélection, un vide dit quoi faire et aucune figure n'invente
    de courbe."""
    options, valeurs, _ = _cb(app, "evo-entites.options")("province", "ancien_45")
    f1, f2, t2, note, l1 = _cb(app, "evo-abandon.figure")("province", "ancien_45", "T", valeurs, "indice_v2", ["nat"])
    noms = [a.text for a in f1.layout.annotations]
    assert len(noms) == len(valeurs) + 1 and "Burkina Faso" in noms  # une étiquette par entité + le pays
    assert all("contrôle" not in n for n in noms)
    assert [t.showlegend for t in f1.data].count(False) == len(valeurs)  # la série de contrôle reste muette
    assert "Second indicateur" in t2 and f2.layout.yaxis.title.text == "écart à la moyenne des provinces"

    lib, leg1, leg2, lec2 = _cb(app, "evo-lib-entites.children")("province", options, valeurs, ["nat"], "indice_v2")
    assert lib == "Provinces à comparer (8 au plus)"
    assert len(leg1) == len(valeurs) + 1 and len(leg2) == len(valeurs)
    assert "serie-1" in str(leg1) and "serie-nat" in str(leg1)  # couleurs par jeton, pas en clair
    assert "Lecture" in str(lec2) and "estimée" in str(lec2)

    # sans sélection ET sans moyenne du pays, il n'y a rien à tracer : le vide dit quoi faire
    f1, f2, t2, note, l1 = _cb(app, "evo-abandon.figure")("province", "ancien_45", "T", [], "indice_v2", [])
    assert not f1.data and not f2.data and "vide" in str(l1) and "Choisissez au moins une province" in str(l1)
    *_, lec2 = _cb(app, "evo-lib-entites.children")("region", [], [], [], "indice_v2")
    assert "Choisissez au moins une région" in str(lec2)


def test_moyenne_nationale_seule_reste_tracee(app):
    """Sans sélection mais avec l'interrupteur « moyenne du Burkina Faso », la courbe nationale se
    trace seule : l'écran garde la lecture qu'il sait donner.
    L'état vide ne prend la place que lorsqu'il n'y a vraiment rien à montrer."""
    f1, f2, t2, note, l1 = _cb(app, "evo-abandon.figure")("province", "ancien_45", "T", [], "indice_v2", ["nat"])
    assert len(f1.data) == 1 and f1.data[0].name == "Burkina Faso"
    assert "vide" not in str(l1) and "Burkina Faso en" in str(l1)
    assert not f2.data and "choisissez au moins une province" in f2.layout.annotations[0].text.lower()
    # la pastille du pays reste dans la légende, même sans entité choisie
    lib, leg1, leg2, lec2 = _cb(app, "evo-lib-entites.children")("province", [], [], ["nat"], "indice_v2")
    assert len(leg1) == 1 and "serie-nat" in str(leg1) and leg2 == []


def test_plafond_dit_en_toutes_lettres(app):
    """Au-delà de huit entités, la page trace les huit premières et le dit, au lieu d'en perdre en
    silence — sous le tracé, et à côté du champ, qui annonce « 12 choisies »."""
    options, _, _ = _cb(app, "evo-entites.options")("province", "ancien_45")
    codes = [o["value"] for o in options[:12]]
    f1, f2, t2, note, l1 = _cb(app, "evo-abandon.figure")("province", "ancien_45", "T", codes, "indice_v2", [])
    assert len(f1.data) == 2 * E.MAX_ENTITES and str(E.MAX_ENTITES) in note and "maximum" in note
    lib, *_ = _cb(app, "evo-lib-entites.children")("province", options, codes, [], "indice_v2")
    assert "12 choisies, 8 tracées" in str(lib)


def test_etiquettes_de_fin_cedent_la_place_a_la_legende(app):
    """Huit courbes ne peuvent pas être nommées au bout de leur tracé sans se chevaucher : au-delà
    de cinq, c'est la légende qui porte l'identité des séries (aucune ne repose sur la couleur seule)."""
    options, _, _ = _cb(app, "evo-entites.options")("province", "ancien_45")
    codes = [o["value"] for o in options[:8]]
    f1, *_ = _cb(app, "evo-abandon.figure")("province", "ancien_45", "T", codes, "indice_v2", ["nat"])
    assert not f1.layout.annotations and f1.layout.showlegend is True
    assert len([t for t in f1.data if t.showlegend]) == E.MAX_ENTITES + 1  # 8 entités + le pays
    # cinq étiquettes au plus : elles restent, et elles ne se superposent pas
    f1, *_ = _cb(app, "evo-abandon.figure")("province", "ancien_45", "T", codes[:4], "indice_v2", ["nat"])
    ys = sorted(a.y for a in f1.layout.annotations)
    assert len(ys) == 5 and f1.layout.showlegend is False
    bas, haut = f1.layout.yaxis.range
    ecart_mini = (haut - bas) * F.HAUTEUR_LIGNE_ETIQUETTE / (440 - 48)
    assert all(b - a >= ecart_mini - 1e-9 for a, b in zip(ys, ys[1:]))


def test_etiquettes_lisibles_meme_superposees():
    """Deux courbes qui finissent au même niveau gardent deux étiquettes distinctes, et un nom long
    passe à la ligne au lieu d'être coupé."""
    s = [dict(nom="Province 01", x=[2017, 2018], y=[5.0, 7.0], couleur=F.OKABE_ITO[0]),
         dict(nom="Province de Dyamongou-et-Gobnangou", x=[2017, 2018], y=[5.0, 7.0], couleur=F.OKABE_ITO[1])]
    fig = F.evolution(s, "% des élèves", etiquettes_fin=True)
    ys = sorted(a.y for a in fig.layout.annotations)
    assert len(ys) == 2 and ys[1] - ys[0] > 0  # écartées à la verticale
    assert any("<br>" in a.text for a in fig.layout.annotations)  # nom long plié, jamais tronqué
    assert fig.layout.showlegend is False and fig.layout.margin.r >= 128


def test_feuille_de_page_sans_couleur_en_clair():
    """La feuille de la page ne contient que des var(--…) : aucune couleur écrite en clair."""
    css = re.sub(r"/\*.*?\*/", "", open(CSS, encoding="utf-8").read(), flags=re.S)
    assert not HEX.findall(css) and "rgb" not in css
    assert ".page-evolution" in css and css.count("--cat-") == 8
