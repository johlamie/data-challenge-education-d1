"""Qualité des données et Méthode (tranche page) : ce qu'une capture d'écran ne prouve pas.

On vérifie ici la grammaire des deux écrans de lecture — la définition de « valeur estimée » dans
la ligne de périmètre, la légende discrète en HTML au lieu de la barre de couleur de Plotly, la
carte qui compte sans hachurer, l'état « rien n'est estimé » qui se lit comme une bonne nouvelle,
les limites connues en liste de définitions, et, côté Méthode, un sommaire dont chaque entrée
tombe sur une section dont le corps est conservé mot pour mot.
"""
import pytest

from dcdash import figures as F
from dcdash.app import creer_app
from dcdash.config import Config
from dcdash.pages import methode, qualite


@pytest.fixture()
def app(donnees):
    return creer_app(Config(auth_active=False, code_hash="", secret_key=""), donnees)


def cb(app, sortie):
    for k, v in app.callback_map.items():
        if sortie in k:
            return v["callback"].__wrapped__
    raise KeyError(sortie)


# --------------------------------------------------------------------- Qualité
def test_qualite_mise_en_page_et_definition():
    """L'écran s'ouvre sur une question et dit, dès la ligne de périmètre, ce qu'est une valeur
    estimée. Aucune icône « i » : le budget du site est tenu par les écrans de décision."""
    txt = str(qualite.layout())
    assert "qualite-donnees" in txt
    for champ in ("qua-annee", "qua-sexe", "qua-type", "qua-carte", "qua-legende", "qua-vide", "qua-detail"):
        assert champ in txt
    assert "imputée" in txt and "n'a pas été relevée" in txt  # le jargon est dit en toutes lettres
    assert "personnes déplacées internes" in txt and "COD-AB" in txt
    assert "className='aide'" not in txt
    # la carte porte sa phrase « Lecture : » et sa note de codes visuels, hors du tracé
    assert txt.count("lecture-lib") == 1 and "Traits gris" in txt
    # les limites connues sont une liste de définitions à filets, pas six encadrés tintés
    assert txt.count("limite-eti") == len(qualite.LIMITES) and "Dl(" in txt


def test_qualite_carte_compte_sans_hachurer(app):
    """La couleur porte un comptage, pas une valeur estimée : aucune hachure, et l'échelle va de 0
    au nombre de types que la sélection peut faire compter — elle garde le même sens d'une année
    à l'autre."""
    fig, synth, data, cols, cont = cb(app, "qua-carte.figure")(2023, "T", "tous")
    remplies = [t for t in fig.data if t.fill == "toself"]
    assert len(remplies) == 45
    assert all(getattr(t, "fillpattern", None) is None or t.fillpattern.shape != "/" for t in remplies)
    assert fig.layout.height is None and fig.layout.autosize  # la boîte CSS donne le format du pays
    assert not any(t.marker.showscale for t in fig.data if t.mode == "markers")  # légende en HTML
    assert remplies[0].fillcolor != F.ECHELLE_RISQUE[-1]  # jamais le rouge du risque ici
    assert data and all("source" in d for d in data)
    assert [c["name"] for c in cols][0] == "Province" and "Fiabilité" in str(cont)
    assert "col-num" in str(synth)  # le nombre de cas est aligné à droite, en chasse fixe


def test_qualite_legende_et_perimetre(app):
    """La légende discrète est graduée en nombres entiers de 0 au maximum possible, et la ligne de
    périmètre nomme l'année et le groupe d'élèves choisis."""
    sous, legende, vide, note = cb(app, "qua-sous-titre.children")(2023, "F", "tous")
    assert "2023-2024" in sous and "filles" in sous
    ticks = str(legende)
    assert ticks.count("ech-neutre-") == 9
    assert "Span('6'" in ticks and "Span('0'" in ticks  # 0 à 6, un repère par type de donnée
    # l'étendue de l'échelle est dite en toutes lettres : une carte pâle est une bonne nouvelle
    assert "de 0 à 6" in str(note) and "6 types de données estimés" in str(note)
    sous, legende, vide, note = cb(app, "qua-sous-titre.children")(2023, "T", "pdi")
    assert "Span('1'" in str(legende) and "Span('2'" not in str(legende)  # un seul type : 0 ou 1
    assert "de 0 à 1" in str(note) and "1 type de donnée estimé" in str(note)


def test_qualite_rien_estime_est_une_bonne_nouvelle(app):
    """Un vide dit pourquoi. Ici il dit que tout a été relevé, et il le dit comme une bonne
    nouvelle (alerte neutre), jamais comme une erreur."""
    _, _, vide, _ = cb(app, "qua-sous-titre.children")(2017, "T", "chiffres_cles")
    txt = str(vide)
    assert "Aucune valeur estimée en 2017-2018" in txt and "ont été relevées" in txt
    assert "alerte-neutre" in txt and "danger" not in txt


def test_qualite_sources_et_jargon_en_francais(app):
    """Une clé technique de la base ne s'affiche jamais telle quelle, et le jargon des limites
    connues est dit en toutes lettres — sans toucher à un chiffre, une date ou une référence."""
    _, _, data, cols, _ = cb(app, "qua-carte.figure")(2023, "T", "pdi")
    affichees = {d["source_affichee"] for d in data}
    assert affichees == {"Report du dernier relevé CONASUR (31/03/2023)"}
    assert not any("_" in s for s in affichees)
    # c'est bien la colonne lisible qui est montrée, pas la colonne de donnée
    assert [c["id"] for c in cols if c["name"] == "Source / méthode"] == ["source_affichee"]
    txt = " ".join(x for _, x in qualite.LIMITES)
    for mot in ("Institut national de la statistique", "recensement de la population",
                "observatoire international des déplacements", "étape b", "validé par l'équipe"):
        assert mot in txt, mot
    # les chiffres, dates et références ne bougent pas
    for valeur in ("2 062 534", "31/03/2023", "COD-AB v03", "2025-1012", "15/11/2026", "42 provinces sur 45"):
        assert valeur in txt, valeur


# --------------------------------------------------------------------- Méthode
def test_export_csv_garde_la_donnee_brute(app):
    """Règle de périmètre : l'interface ne change que l'affichage. Le CSV exporté garde exactement les
    colonnes et les valeurs du modèle — la clé technique de la source, telle que le modèle la
    nomme — pendant que le tableau, lui, montre le libellé lisible."""
    from dcdash.meta import libelle_source
    from dcdash.pages.qualite import COLONNES_CSV
    brut = "report_dernier_releve_CONASUR_2023-03-31"
    _, _, data, _, _ = cb(app, "qua-carte.figure")(2023, "T", "pdi")
    r = cb(app, "qua-download.data")(1, data, "T")
    entete, *lignes = r["content"].splitlines()
    # les colonnes du modèle, dans le même ordre, et pas la colonne d'affichage
    assert entete.lstrip("﻿").split(";") == COLONNES_CSV
    assert "source_affichee" not in r["content"]
    # la valeur exportée est celle que le modèle produit pour la clé brute, inchangée
    assert all(l.endswith(";" + libelle_source(brut)) for l in lignes)
    assert "CONASUR 2023-03-31" in r["content"] and "Report du dernier relevé" not in r["content"]
    # … et à l'écran, c'est le libellé lisible qui s'affiche pour cette même ligne
    assert {d["source_affichee"] for d in data} == {"Report du dernier relevé CONASUR (31/03/2023)"}
    assert {d["source"] for d in data} == {libelle_source(brut)}


def test_methode_sommaire_et_sections():
    """Un document : un sommaire dont chaque entrée tombe sur une section existante, une seule
    hiérarchie de titres, et une phrase d'introduction en français courant par section."""
    txt = str(methode.layout())
    assert "methode-doc" in txt and "methode-grille" in txt and "toc-liste" in txt
    for ancre, titre, intro, _ in methode.SECTIONS:
        assert f"href='#{ancre}'" in txt and f"id='{ancre}'" in txt
        assert titre in txt and intro in txt
    assert txt.count("methode-lead") == len(methode.SECTIONS)
    assert txt.count("markdown-methode") == len(methode.SECTIONS)
    # une hiérarchie simple : un h1 de page, un h2 par section, rien d'autre
    assert txt.count("H1(") == 1 and txt.count("H2(") == len(methode.SECTIONS)
    assert all("##" not in corps for _, _, _, corps in methode.SECTIONS)


def test_methode_contenu_conserve_mot_pour_mot():
    """L'interface ne touche à aucun chiffre, poids, formule ni licence : ils sont le contenu."""
    corps = "\n".join(c for _, _, _, c in methode.SECTIONS)
    for valeur in ("0,30", "0,15", "0,20", "0,10", "0,965", "0,88", "0,77", "0,54", "0,56",
                   "2 000 tirages", "Dirichlet κ = 50", "CC BY-IGO",
                   "Décret n° 2025-1012/PF/PRIM/MATM/MEF du 7 août 2025",
                   "analyse.v_dashboard_*", "rolling origin"):
        assert valeur in corps, valeur
    # et, sur Qualité, le stock national cité dans les limites connues
    assert "2 062 534" in "\n".join(x for _, x in qualite.LIMITES)
    # les six composantes de l'indice et leur sens sont tous présents
    for composante in ("Abandon harmonisé", "Redoublement", "PDI pour 1 000 habitants",
                       "Élèves par maître", "Écoles avec eau potable", "Écoles avec latrines"):
        assert composante in corps


# les scripts de nettoyage, tels qu'ils existent sur le disque de l'auteur
SCRIPTS_NETTOYAGE = (
    "01_excel_officiel.py", "02_annuaires_primaire.py", "03_tableaux_geo_generiques.py",
    "04_pdi_communes.py", "05_geo_referentiel.py", "06_rgph_population.py", "07_ecoles_osm.py",
    "08_jalon_b_complements.py", "09_jalon_c_insecurite.py", "10_jalon_c_recettes_dss",
    "11_jalon_d_contours.py", "12_jalon_d_sql_dss", "commun.py", "geo.py",
)


def test_methode_declaration_ia_en_trois_points():
    """La déclaration d'usage de l'IA dit qui a fait quoi, en trois points : les scripts de
    nettoyage (nommés, sans IA), l'indice et les modèles, puis le tableau de bord. Aucun produit
    tiers n'y est nommé en dehors d'Anthropic."""
    corps = next(c for ancre, _, _, c in methode.SECTIONS if ancre == "ia")
    for tete in ("Nettoyage des données", "Indice v2, tests de robustesse et modèles",
                 "Construction du tableau de bord"):
        assert f"**1. {tete}" in corps or f"**2. {tete}" in corps or f"**3. {tete}" in corps, tete
    for nom in SCRIPTS_NETTOYAGE:
        assert nom in corps, nom
    # les deux dossiers sont signalés comme tels, pas comme des fichiers
    assert "10_jalon_c_recettes_dss/` (dossier)" in corps and "12_jalon_d_sql_dss/` (dossier)" in corps
    # le point 1 parle de scripts, pas d'IA ni d'assistant
    point1 = corps.split("**2.")[0]
    assert "IA" not in point1 and "assistant" not in point1
    # points 2 et 3 : un assistant et un kit agentiques de l'auteur, modèles d'Anthropic
    assert corps.count("développé par John Lamien lui-même") == 2
    assert "les modèles d'Anthropic" in corps
    # aucun autre produit nommé : plus aucune trace de l'ancienne déclaration dans tout le module
    module = (methode.__file__ and open(methode.__file__, encoding="utf-8").read()) or ""
    assert "Grok" not in module and "Grok" not in str(methode.layout())
