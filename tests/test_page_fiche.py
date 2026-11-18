"""Fiche province (tranche page) : ce qu'une capture d'écran ne prouve pas.

On vérifie ici la grammaire de l'écran — les quatre chiffres clés et leurs infobulles sans icône,
la carte de localisation et sa légende, l'anatomie des barres de contribution (piste, zéro au quart
de la largeur, aucun axe gradué), la hachure et l'astérisque des valeurs estimées, et une phrase
« Lecture : » sous chaque figure.
"""
import pytest

from dcdash import figures as F
from dcdash.meta import nom_propre
from dcdash.pages import fiche


@pytest.fixture()
def rendu(donnees):
    entete, corps = fiche.contenu(donnees, "BF0008", 2022, "T")
    return str(entete), str(corps)


def test_mise_en_page_etat_chargement():
    """Au premier rendu, la page porte déjà sa structure et la hauteur de ses blocs."""
    txt = str(fiche.layout())
    assert "page-fiche" in txt and "fiche-bandeau" in txt
    for champ in ("fic-province", "fic-annee", "fic-sexe", "fic-carte"):
        assert champ in txt
    # état « chargement » : les quatre libellés sont là, les valeurs sont des squelettes
    assert txt.count("squelette-val") == 4 and "fiche-kpis" in txt
    assert all(lib in txt for lib in fiche.LIBELLES_KPI)


def test_un_seul_cadre_une_seule_rangee():
    """Le haut de la page est UN cadre et UNE rangée : les filtres, les chiffres clés et la carte
    partagent le même .carte-bloc, et le titre de page ne coûte aucune hauteur."""
    lay = fiche.layout()
    txt = str(lay)
    # un seul bloc encadré en haut de page (le contenu du bas est rendu par le callback)
    assert txt.count("carte-bloc") == 1 and "fiche-cadre" in txt
    # les trois volets vivent dedans, dans l'ordre : sélecteurs, chiffres clés, puis la carte
    # (la représentation de Dash écrit la classe d'un conteneur APRÈS ses enfants : on lit donc
    # l'ordre sur des contenus, pas sur des noms de classe)
    ordre = [txt.index(m) for m in ("fic-province", "fic-annee", "fic-sexe", fiche.LIBELLES_KPI[0], "fic-carte",
                                    fiche.NOTE_CARTE)]
    assert ordre == sorted(ordre)
    for marque in ("filtres-fiche", "fiche-kpis", "fiche-locali", "fiche-carte"):
        assert marque in txt
    # le titre reste dans le document (hiérarchie des titres, lecteurs d'écran), sans hauteur :
    # c'est le premier enfant de la page, et il est masqué visuellement
    entete = lay.children[0]
    assert entete.className == "visuellement-cache"
    assert "titre-page" in str(entete) and "sous-titre" in str(entete)
    # un seul H1, et plus aucun H2 dans le bandeau
    assert txt.count("H1(") == 1 and "H2(" not in txt


def test_carte_sans_legende_ni_titre():
    """La carte de localisation n'a plus ni légende ni titre de bloc : il reste la phrase qui dit
    ce qu'un clic fait, et l'étiquette du groupe pour qui ne voit pas la carte."""
    txt = str(fiche.layout())
    for mort in ("legende-choisie", "legende-region", "legende-autre", "legende-cles", "legende-locali",
                 "Où se situe la province"):
        assert mort not in txt
    assert "Cliquez sur une province pour ouvrir sa fiche." in txt
    assert "role='group'" in txt and "aria-label" in txt


def test_identite_sans_nom_redit(donnees, rendu):
    """L'identité tient en une ligne : le nom de la province n'y est pas redit (il est dans le
    sélecteur), le nom de la région est un élément à part — c'est lui qui est écrit en bleu — et
    le découpage de 2025 vit dans une infobulle, pas dans un second titre."""
    entete, _ = rendu
    p = donnees.province()
    r = p[(p["pcode_province"] == "BF0008") & (p["annee_debut"] == 2022) & (p["sexe"] == "T")].iloc[0]
    nom = nom_propre(r["nom_officiel_province_ancienne"] or r["province"])
    assert nom not in entete  # plus de second titre avec le nom de la province
    assert "H2(" not in entete  # ni titre du tout dans le bandeau
    assert "className='nom-region'" in entete and nom_propre(r["region"]) in entete
    assert "découpage 2025" in entete or "scindée en 2025" in entete
    assert "Découpage 2025 : " in entete  # le détail et les codes de 2025 restent lisibles au survol


def test_quatre_chiffres_cles_sans_icone(rendu):
    """Quatre chiffres clés en une rangée ; chacun explique sa notion au survol, aucun ne porte
    d'icône « i »."""
    entete, _ = rendu
    assert "fiche-kpis" in entete
    # quatre libellés survolables, plus le découpage 2025 de la ligne d'identité ; chaque cellule
    # porte data-aide (surface de survol) et son libellé aussi (la commande déclarée, focalisable) :
    # quatre notions × 2 attributs, et un seul pour le terme de l'identité
    assert entete.count("terme-aide") == 5 and entete.count("data-aide") == 9
    assert entete.count("role='button'") == 5
    assert "className='aide'" not in entete  # le budget d'icônes du site est tenu ailleurs
    assert "badge-statut" in entete  # la solidité se lit aussi aux points ●/○, jamais à la couleur seule


def test_ordre_des_blocs_du_bas(rendu):
    """Ordre de lecture du bas de page : les deux graphiques, puis « Indicateurs et rangs », puis
    « Qualité des données » — sous les indicateurs, sur toute la largeur, plus en colonne."""
    _, corps = rendu
    ordre = [corps.index(m) for m in ("Ce qui pèse sur le score de risque", "Insécurité",
                                      "Indicateurs et rangs", "Qualité des données")]
    assert ordre == sorted(ordre)
    # les deux graphiques d'abord, le tableau et la qualité ensuite, dans le même conteneur
    assert corps.index("fiche-graphiques") < corps.index("fiche-bas")
    # la qualité est le dernier bloc : rien ne la remet dans une colonne de droite
    assert corps.rindex("Qualité des données") > corps.rindex("Indicateurs et rangs")


def test_tableau_indicateurs_et_valeurs_estimees(rendu):
    """Une ligne par indicateur, les noms survolables, et une valeur estimée qui se voit autrement
    que par la couleur : hachure sur la cellule et astérisque à côté du nombre."""
    _, corps = rendu
    assert corps.count("Tr(") == len(fiche.INDICS_FICHE) + 1  # en-tête + une ligne par indicateur
    assert corps.count("terme-aide") == len(fiche.INDICS_FICHE)
    assert "impute" in corps and "className='ast'" in corps
    assert "col-num" in corps  # les nombres sont alignés à droite, en chasse fixe


def test_chaque_serie_explique_ses_propres_points_estimes(donnees):
    """Le relevé CONASUR prolongé explique les points estimés des personnes déplacées, jamais ceux
    des incidents violents, qui viennent d'une autre source."""
    P = donnees.province()
    s = P[(P["pcode_province"] == "BF0008") & (P["sexe"] == "T")].sort_values("annee_debut")
    txt = fiche._lecture_insecurite(s)
    # le relevé prolongé est dit une seule fois, dans la phrase des personnes déplacées
    avant, apres = txt.split("courbe des incidents violents")
    assert "CONASUR" in avant and "courbe des personnes déplacées" in avant
    assert "CONASUR" not in apres and txt.count("CONASUR") == 1
    # accord en nombre, jamais « 1 points » ni « 3 point »
    assert "1 points" not in txt and " point de la courbe" in txt.replace("points", "point")


def test_sources_estimees_dites_en_francais(donnees):
    """Une clé technique de la base (« report_dernier_releve_CONASUR_2023-03-31 ») ne s'affiche
    jamais telle quelle : ni dans la colonne « Estimation », ni au survol de l'astérisque."""
    _, corps = fiche.contenu(donnees, "BF0008", 2024, "T")
    txt = str(corps)
    assert "_CONASUR_" not in txt and "releve" not in txt
    assert txt.count("Report du dernier relevé CONASUR (31/03/2023)") >= 2  # colonne + astérisque


def test_une_phrase_de_lecture_sous_chaque_figure(rendu):
    """Deux figures, deux phrases « Lecture : » en français courant, et le jargon dit en toutes lettres."""
    _, corps = rendu
    assert corps.count("lecture-lib") == 2
    assert "personnes déplacées internes" in corps and "incidents violents" in corps
    assert "Poids :" in corps


def test_barres_de_contribution_anatomie():
    """Une piste par composante, le zéro au quart de la largeur, la valeur signée, aucun axe gradué."""
    fig = F.barres_contributions(["Taux d'abandon", "Redoublement"], [0.5, -0.2], 0.3, hauteur=None)
    piste, barres = fig.data
    assert fig.layout.barmode == "overlay" and len(fig.data) == 2
    assert piste.marker.color == F.GRILLE and piste.hoverinfo == "skip"
    assert list(barres.marker.color) == [F.CONTRIB_PLUS, F.CONTRIB_MOINS]
    x0, x1 = fig.layout.xaxis.range
    assert abs((0 - x0) / (x1 - x0) - 0.25) < 1e-9  # le zéro au quart, la place des contributions négatives
    assert fig.layout.xaxis.visible is False  # six contributions à comparer, pas une échelle à lire
    assert fig.layout.height == 2 * (18 + 16) + 16  # piste de 18 px, écart de 16 px
    assert "−0,20" in barres.text[1]  # vrai signe moins, virgule décimale


def test_carte_de_localisation_de_la_page(donnees):
    """La carte de la page : 45 polygones, une seule province en bleu foncé, le nom au survol."""
    fig = fiche.carte_fiche(donnees, "BF0008")
    remplies = [t for t in fig.data if t.fill == "toself"]
    assert len(remplies) == 45
    assert [t.fillcolor for t in remplies].count(F.CARTE_CHOISIE) == 1
    assert any("Cliquer pour ouvrir sa fiche" in (t.text or "") for t in remplies)
    assert fig.layout.height is None and fig.layout.autosize  # la boîte CSS donne le format du pays
