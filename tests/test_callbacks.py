"""Rendu des callbacks principaux sur données synthétiques."""
import json

import pytest

from dcdash.app import creer_app
from dcdash.config import Config


@pytest.fixture()
def app(donnees):
    return creer_app(Config(auth_active=False, code_hash="", secret_key=""), donnees)


def cb(app, sortie):
    for k, v in app.callback_map.items():
        if sortie in k:
            return v["callback"].__wrapped__
    raise KeyError(sortie)


def _imputes(fig):
    return [t for t in fig.data if getattr(t, "fillpattern", None) is not None and t.fillpattern.shape == "/"]


@pytest.mark.parametrize("chemin", ["/", "/classement", "/carte", "/evolution", "/fiche", "/qualite", "/methode",
                                    "/inconnue"])
def test_routage(app, chemin):
    r = cb(app, "page.children")(chemin, "")
    assert r is not None


def test_accueil(app):
    (kpis, fig, note, top, note_top, sous,
     explication, titre_top, titre_carte) = cb(app, "acc-kpis.children")(2024, "T", "indice_v2_0_100")
    assert titre_top == "Les 10 provinces les plus à risque"
    assert titre_carte.children[0] == "Carte du risque (45 provinces)"
    assert len(kpis) == 6
    assert len([t for t in fig.data if t.fill == "toself"]) == 45
    assert _imputes(fig)  # PDI imputés en 2024 dans le jeu synthétique
    # périmètre sur une ligne courte, et ce que mesure la carte dit sous les onglets
    assert "2024-2025" in sous and len(sous) < 60 and "score de risque" not in sous
    assert "0 à 100" in explication and "conditions d'accueil" in explication
    # plus de contour noir ni de mention du top 10 : le code visuel n'était pas compris
    assert "Contour noir" not in str(note) and "top 10" not in str(note)
    assert "limites des régions" in str(note)
    assert str(top).count("Tr(") == 11  # en-tête + 10 provinces
    kpis, fig, *_, explication, titre_top, titre_carte = cb(app, "acc-kpis.children")(2017, "F", "proba_risque_t1")
    assert "Prévision disponible" in fig.layout.annotations[0].text
    assert "seuil d'alerte" in explication  # la phrase suit l'onglet, même quand la carte est vide
    assert titre_top == "Les 10 provinces les plus exposées l'an prochain"
    assert titre_carte.children[0] == "Carte du risque l'an prochain (45 provinces)"


def _pcodes(table):
    """Les codes de province des lignes du tableau, dans l'ordre d'affichage (lus dans les liens)."""
    import re
    return re.findall(r"/fiche\?pcode=([A-Z0-9]+)&", str(table))


@pytest.mark.parametrize("mesure,titre_attendu,titre_carte_attendu", [
    ("indice_v2_0_100", "Les 10 provinces les plus à risque", "Carte du risque (45 provinces)"),
    ("taux_abandon_harmonise", "Les 10 provinces au plus fort taux d'abandon",
     "Carte du taux d'abandon (45 provinces)"),
    ("proba_risque_t1", "Les 10 provinces les plus exposées l'an prochain",
     "Carte du risque l'an prochain (45 provinces)")])
def test_top10_suit_la_mesure(app, donnees, mesure, titre_attendu, titre_carte_attendu):
    """La liste de gauche classe la mesure cartographiée : titre, ordre, colonne mise en avant et
    phrase de lecture suivent l'onglet. Le titre du bloc de
    carte suit le même onglet, marqueur d'aide compris."""
    from dcdash.vues import top_n
    *_, top, lecture, _, _, titre_top, titre_carte = cb(app, "acc-kpis.children")(2024, "T", mesure)
    assert titre_top == titre_attendu
    assert titre_carte.children[0] == titre_carte_attendu
    assert "data-aide" in str(titre_carte)  # l'icône « i » de la carte repart avec le titre
    # ordre : tri décroissant indépendant sur la mesure, ex æquo départagés par le rang de score
    t = top_n(donnees, 2024, "T", 10_000)
    t = t[t[mesure] == t[mesure]].sort_values([mesure, "rang_v2"], ascending=[False, True]).head(10)
    assert _pcodes(top) == list(t["pcode_province"])
    assert str(top).count("Tr(") == 11  # en-tête + 10 provinces, à toutes les mesures
    # la colonne de la mesure est celle qui porte la barre ; les autres restent des chiffres simples
    s = str(top)
    assert s.count("cellule-score") == 10 and s.count("barre-score") == 10  # une seule colonne en avant
    entetes = {"indice_v2_0_100": "Score", "taux_abandon_harmonise": "Abandon", "proba_risque_t1": "Risque"}
    libelles = [th.children if isinstance(th.children, str) else th.children[0]
                for th in top.children[0].children.children]
    # les deux colonnes de toujours restent ; celle de la prévision ne s'ajoute que sur son onglet
    attendu = ["#", "Province", "Région", "Score", "Abandon"] + (["Risque"] if mesure == "proba_risque_t1" else [])
    assert libelles == attendu + ["Classement"]
    # la colonne mise en avant (qui porte la barre) est celle de la mesure affichée
    en_avant = [th for th in top.children[0].children.children if getattr(th, "className", "") == "col-score"]
    assert len(en_avant) == 1
    assert (en_avant[0].children if isinstance(en_avant[0].children, str)
            else en_avant[0].children[0]) == entetes[mesure]
    mots = {"indice_v2_0_100": "la barre de score", "taux_abandon_harmonise": "la barre d'abandon",
            "proba_risque_t1": "la barre de risque"}
    assert mots[mesure] in str(lecture) and "contour" not in str(lecture).lower()


def test_top10_du_score_inchange(app, donnees):
    """Sur l'onglet « Score de risque », la liste est exactement celle d'avant : mêmes provinces dans
    le même ordre, rang de score affiché tel quel, six colonnes, barre de score à la même largeur et
    à la même couleur qu'avant le passage au classement par mesure."""
    from plotly.colors import sample_colorscale

    from dcdash import figures as F
    from dcdash.meta import fmt_nombre, fmt_valeur
    from dcdash.pages import accueil as P
    from dcdash.vues import top_n
    attendu = top_n(donnees, 2024, "T", 10)
    table = P.tableau_top10(donnees, 2024, "T")
    assert _pcodes(table) == list(attendu["pcode_province"])
    entete, corps = table.children
    assert [str(th.children if not isinstance(th.children, list) else th.children[0])
            for th in entete.children.children] == ["#", "Province", "Région", "Score", "Abandon", "Classement"]
    for tr, (_, r) in zip(corps.children, attendu.iterrows()):
        cells = tr.children
        assert cells[0].children == int(r["rang_v2"])          # le rang publié, pas la place dans la liste
        assert cells[3].className == "col-score"               # la barre est sur le score
        barre = cells[3].children.children[0].children
        sc = r["indice_v2_0_100"]
        assert barre.style == {"width": f"{sc:.0f}%",
                               "background": sample_colorscale(F.ECHELLE_RISQUE, [min(max(sc / 100, 0), 1)])[0]}
        assert cells[3].children.children[1].children == fmt_nombre(sc, 0)
        assert cells[4].children == fmt_valeur(r["taux_abandon_harmonise"], "taux_abandon_harmonise")


@pytest.mark.parametrize("mesure", ["taux_abandon_harmonise", "proba_risque_t1"])
def test_pas_de_badge_hors_top10_hors_score(app, donnees, mesure):
    """« Hors top 10 » sur une province que la liste affiche est
    une contradiction. Hors de l'onglet du score, la colonne « Classement » n'a plus ce badge : la
    cellule porte le tiret, et les provinces du top 10 de score gardent leur badge."""
    from dcdash.pages import accueil as P
    s = str(P.tableau_top10(donnees, 2024, "T", mesure))
    assert "Hors top 10" not in s and "statut-hors_top10" not in s
    # l'onglet du score, lui, ne change pas : son badge « hors top 10 » n'a jamais lieu d'être non
    # plus, mais le badge de solidité y reste sur chaque ligne
    score = str(P.tableau_top10(donnees, 2024, "T"))
    assert score.count("badge-statut") == 10
    # une province du top 10 de score classée par une autre mesure garde sa solidité
    assert "badge-statut" in s


def test_top10_sans_valeur(app):
    """Mesure sans valeur pour la sélection : le cadre de la liste porte l'état vide partagé, qui dit
    pourquoi et quoi faire — jamais une liste vide ni un zéro."""
    *_, top, lecture, _, _, titre_top, _ = cb(app, "acc-kpis.children")(2017, "F", "proba_risque_t1")
    assert top.className == "vide"
    assert "2020-2021 à 2024-2025" in str(top) and "Choisissez" in str(top)
    assert titre_top == "Les 10 provinces les plus exposées l'an prochain"
    # une seule ligne de lecture, sans promesse de barre ni de clic : le bloc garde sa hauteur
    assert "barre" not in str(lecture) and "prévision" in str(lecture)


def test_lien_classement_suit_la_mesure(app):
    """Le lien bleu emmène le classement complet sur la sélection affichée ; /classement relit bien
    ces trois paramètres dans son `layout`."""
    from dcdash.pages import classement as CL
    href = cb(app, "acc-lien-classement.href")(2022, "F", "taux_abandon_harmonise")
    assert href == "/classement?annee=2022&sexe=F&mesure=taux_abandon_harmonise"
    rendu = str(CL.layout(annee="2022", sexe="F", mesure="taux_abandon_harmonise"))
    assert "2022-2023" in rendu and "filles" in rendu and "taux d'abandon" in rendu


def test_carte_sans_contour_noir(app):
    """Le contour noir du top 10 est retiré de la carte, et la
    légende ne nomme plus que les codes visuels réellement présents sur la carte affichée."""
    from dcdash import figures as F
    _, fig, note, *_ = cb(app, "acc-kpis.children")(2024, "T", "indice_v2_0_100")
    remplies = [t for t in fig.data if t.fill == "toself"]
    assert remplies and all(t.line.color == F.CARTE_TRAIT and t.line.width < 1 for t in remplies)
    s = str(note)
    assert "legende-top10" not in s and "top 10" not in s
    # jeu de démonstration : toutes les provinces ont une valeur, donc aucune clé « non disponible »
    assert "non disponible" not in s
    assert "valeur estimée" in s and "legende-estime" in s  # il existe des provinces hachurées


def test_carte_verrouillee(app):
    _, fig, *_ = cb(app, "acc-kpis.children")(2023, "T", "taux_abandon_harmonise")
    assert fig.layout.dragmode is False
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange
    assert fig.layout.xaxis.range is not None and fig.layout.yaxis.range is not None
    from dcdash import figures as F
    assert F.CONFIG_CARTE["scrollZoom"] is False and F.CONFIG_CARTE["doubleClick"] == "reset"


def test_kpis_decideurs(donnees):
    from dcdash.calculs import kpis_decideurs, nationaux
    k = kpis_decideurs(donnees.region(), donnees.province(), 2024, "T")
    n = nationaux(donnees.region(), donnees.province(), 2024, "T")
    n0 = nationaux(donnees.region(), donnees.province(), 2023, "T")
    assert abs(k["abandon"] - n["taux_abandon_harmonise"]) < 1e-9
    assert abs(k["abandon_variation"] - (n["taux_abandon_harmonise"] - n0["taux_abandon_harmonise"])) < 1e-9
    p = donnees.province()
    pt = p[(p["annee_debut"] == 2024) & (p["sexe"] == "T")]
    assert k["nb_alerte"] == int((pt["proba_risque_t1"] >= 0.5).sum())
    assert k["province_top"] == pt.sort_values("rang_v2")["nom_officiel_province_ancienne"].iloc[0]
    r = donnees.region()
    r = r[(r["decoupage"] == "ancien_13") & (r["annee_debut"] == 2024) & (r["sexe"] == "T")]
    assert abs(k["abandons_estimes"] - (r["taux_abandon_harmonise"] * r["effectif_base_flux_cp1_cm1"]).sum() / 100) < 1e-6
    assert abs(k["pdi_nombre"] - r["pdi_nombre"].sum()) < 1e-6
    assert kpis_decideurs(donnees.region(), donnees.province(), 2019, "T")["nb_alerte"] is None


def test_classement_complet_2025(app):
    f = cb(app, "cla-table.data")
    data, cols, resume, fig, titre, lect, note = f(2023, "T", "2025_47", "taux_abandon_harmonise")
    assert len(data) == 47 and "47 provinces" in resume
    assert len([d for d in data if "↳]" in d["province_carte"]]) == 4
    assert all(d["province_carte"].startswith("[") and "](/fiche?pcode=" in d["province_carte"] for d in data)
    assert len([t for t in fig.data if t.fill == "toself"]) == 47
    data, cols, resume, fig, *_ = f(2024, "T", "ancien_45", "proba_risque_t1")
    assert len(data) == 45 and any(c["id"] == "valeur_aff" for c in cols)
    # probabilité indisponible : repli sur le score, signalé dans la note
    data, cols, resume, fig, titre, lect, note = f(2017, "F", "ancien_45", "proba_risque_t1")
    assert "score de risque" in resume and "n'existe que" in note


def test_classement_deux_colonnes(app):
    from dcdash.pages import classement
    lay = classement.layout(annee="2022", sexe="F", mesure="taux_abandon_harmonise")
    txt = str(lay)
    assert "ligne-classement" in txt and "bloc-liste" in txt and "bloc-carte" in txt
    assert txt.index("cla-annee") < txt.index("cla-table") < txt.index("cla-carte")
    assert classement.layout(annee="abc").children[0].children[1].children[0].children[1].value == 2024


def test_export_csv(app):
    f = cb(app, "cla-download.data")
    r = f(1, None, 2024, "T", "ancien_45", "indice_v2_0_100")
    assert r["filename"].endswith(".csv") and "pcode_province_carte" in r["content"]


def test_navigation_et_marque(app):
    txt = str(app.layout)
    assert "Unica Labs" in txt and "À propos et méthode" in txt and "Carte et classement" not in txt
    assert "A(children='Unica Labs'" in txt and "href='https://unicalabs.bf'" in txt
    assert "target='_blank'" in txt and "rel='noopener'" in txt


def test_mode_demo():
    from dcdash import db
    from dcdash.demo import SourceDemo
    d = db.Donnees(SourceDemo(), ttl_s=10 ** 9)
    a = creer_app(Config(auth_active=False, code_hash="", secret_key="", demo=True), d)
    assert "Données fictives" in str(a.layout)
    k = cb(a, "acc-kpis.children")(2024, "T", "indice_v2_0_100")
    assert len(k[0]) == 6


def test_evolution(app):
    opts, val, dis = cb(app, "evo-entites.options")("province", "ancien_45")
    assert len(opts) == 45 and len(val) == 3
    f1, f2, t2, note, l1 = cb(app, "evo-abandon.figure")("province", "ancien_45", "T", val, "pdi_pour_1000_hab",
                                                        ["nat"])
    assert "Burkina Faso en" in str(l1) and "data-aide" not in str(t2)
    tirets = {tr.line.dash for tr in f1.data}
    assert {"solid", "dash"} <= tirets and "dot" not in tirets
    assert any("circle-open" in list(tr.marker.symbol) for tr in f2.data)
    opts, val, dis = cb(app, "evo-entites.options")("region", "2025_47")
    f1, f2, *_ = cb(app, "evo-abandon.figure")("region", "2025_47", "F", val, "indice_v2", [])
    assert len(f1.data) == 6


def test_fiche(app, donnees):
    r = cb(app, "fic-contenu.children")("BF0008", 2022, "T")
    txt = str(r)
    assert "Ce qui pèse sur le score" in txt and "interpolation test" in txt
    entete, corps, fig, lect = r
    assert "fiche-kpis" in str(entete) and "Lecture" in str(corps)
    remplies = [t for t in fig.data if t.fill == "toself"]
    assert len(remplies) == 45 and [t.fillcolor for t in remplies].count("#1d3f6e") == 1  # province choisie en bleu
    assert "data-aide" in str(corps) and "class_name='aide'" not in str(corps)  # libellés survolables, sans icône
    assert cb(app, "fic-province.value")({"points": [{"curveNumber": 3}]}) is not None
    r = cb(app, "fic-contenu.children")("BF0001", 2024, "F")
    txt = str(r)
    assert "non répartie" in txt and "Ventilation par sexe" in txt


def test_qualite(app):
    fig, synth, data, cols, cont = cb(app, "qua-carte.figure")(2023, "T", "tous")
    assert data and all("source" in d for d in data)
    fig, synth, data, cols, cont = cb(app, "qua-carte.figure")(2023, "T", "pdi")
    assert {d["type"] for d in data} == {"PDI"}


def test_aides_de_lecture(app):
    """Arbitrage v4 : chiffres clés survolables sans icône (sauf « province la plus à risque »), et 5 icônes « i » au
    plus sur tout le site (score, solidité du classement, légende de carte, critère du classement)."""
    from dcdash import aides as A
    kpis, fig, note, top, *_ = cb(app, "acc-kpis.children")(2024, "T", "indice_v2_0_100")
    avec = [k for k in kpis if "data-aide" in str(k)]
    assert len(avec) == 5 and "Province la plus à risque" not in str(avec)
    assert all("className='aide'" not in str(k) for k in kpis)

    def icones(composant):
        return str(composant).count("className='aide'")
    n = icones(top) + icones(cb(app, "page.children")("/", "")[0])
    n += icones(cb(app, "page.children")("/classement", "")[0])
    n += icones(cb(app, "fic-contenu.children")("BF0008", 2022, "T"))
    n += icones(cb(app, "page.children")("/fiche", "")[0]) + icones(cb(app, "page.children")("/evolution", "")[0])
    assert 3 <= n <= 5, n
    for cle in A._DEF:
        t = A.indicateur(cle)
        assert "Unité : " in t and "Sens : " in t and "Source : " in t
