"""Composants d'interface partagés : jetons, fabriques et vue d'ensemble.

Ces tests verrouillent ce que la revue de design ne peut pas voir dans une capture : que les deux
feuilles existent et sont reliées, qu'aucune couleur en clair ne traîne hors du fichier de jetons,
qu'un chiffre clé n'a jamais d'icône « i », et que la carte de localisation porte bien les trois
remplissages et le contour de région exigés.
"""
import os
import re

import pytest

from dcdash import composants as C
from dcdash import figures as F
from dcdash.app import creer_app
from dcdash.auth import CHEMINS_LIBRES, PAGE
from dcdash.config import Config

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS = os.path.join(RACINE, "assets", "tokens.css")
STYLE = os.path.join(RACINE, "assets", "style.css")
ICONES = os.path.join(RACINE, "assets", "icones")
HEX = re.compile(r"(?<![\w&/#-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")


@pytest.fixture()
def app(donnees):
    return creer_app(Config(auth_active=False, code_hash="", secret_key=""), donnees)


def _cb(app, sortie):
    for k, v in app.callback_map.items():
        if sortie in k:
            return v["callback"].__wrapped__
    raise KeyError(sortie)


def test_feuilles_de_style():
    """tokens.css est le seul fichier où une couleur est écrite en clair, et style.css n'utilise
    que des var(). Hors commentaires : la même règle que le contrôle des styles."""
    jetons = open(TOKENS, encoding="utf-8").read()
    for nom in ("--accent", "--surface-page", "--risque-9", "--carte-choisie", "--fs-chiffre", "--r-md"):
        assert nom in jetons
    assert "100vh" not in jetons and "100vh" not in open(STYLE, encoding="utf-8").read()
    for ligne in open(STYLE, encoding="utf-8"):
        nu = ligne.strip()
        if nu.startswith(("/*", "*")) or "design-lint-allow" in nu:
            continue
        assert not HEX.search(nu), f"couleur en clair hors des jetons : {nu}"


def test_page_de_connexion_relie_les_deux_feuilles():
    """Sans ces deux lignes la connexion serait la seule page sans style (elle n'est pas servie par Dash)."""
    assert "/assets/tokens.css" in CHEMINS_LIBRES
    assert PAGE.index("/assets/tokens.css") < PAGE.index("/assets/style.css")
    assert "carte-connexion" in PAGE and "champ-dc" in PAGE and "btn-dc" in PAGE


def test_jeu_d_icones():
    """Dix contours, un seul jeu ; les six icônes décoratives des chiffres clés ont disparu."""
    fichiers = sorted(f[:-4] for f in os.listdir(ICONES) if f.endswith(".svg"))
    assert fichiers == ["chevron-down", "chevron-up-down", "clock", "download", "info", "lock", "log-out",
                        "menu", "triangle-alert", "x"]


def test_chiffre_cle_sans_icone_avec_soulignement():
    """Un chiffre clé qui a besoin d'une explication porte un pointillé, jamais une icône « i ».

    La commande déclarée est le libellé (role + aria-expanded) ; la cellule n'est que la surface de
    survol. Sans cela, la pastille « relevé prolongé » serait un bouton dans un bouton — invisible
    pour un lecteur d'écran."""
    avec = str(C.kpi("Déplacés internes (PDI)", "2 381 000", "83 / 1 000 hab.", aide_kpi="Définition…",
                     chip=C.chip_stale("Relevé prolongé"), etat="stale"))
    assert "terme-aide" in avec and "data-aide" in avec and "chip-stale" in avec
    assert "className='aide'" not in avec and "data-state='stale'" in avec
    assert avec.count("role='button'") == 2 and avec.count("aria-expanded='false'") == 2
    sans = str(C.kpi("Province la plus à risque", "Province 21", "Région C", critique=True))
    assert "terme-aide" not in sans and "data-aide" not in sans and "kpi-critique" in sans


def test_aucune_bulle_native_sur_un_chiffre_cle():
    """Sur « Province la plus à risque », rien ne s'ouvre — ni infobulle du produit,
    ni bulle native du navigateur. Et nulle part un chiffre clé ne porte les deux à la fois."""
    sans = str(C.kpi("Province la plus à risque", "Province 21", "Région C", critique=True))
    assert "title=" not in sans
    avec = str(C.kpi("Déplacés internes (PDI)", "2 381 000", "83 / 1 000 hab.", aide_kpi="Définition…",
                     evolution=C.tendance(0.4, "+0,4 pt en un an")))
    assert "title=" not in avec  # la tendance dit son sens en toutes lettres, pas dans un title
    assert "évolution défavorable" in avec and "visuellement-cache" in avec
    # le badge de solidité garde sa bulle native dans un tableau, jamais dans un chiffre clé
    assert "title=" in str(C.badge_statut("stable_top10"))
    assert "title=" not in str(C.badge_statut("stable_top10", titre=False))


def test_valeur_longue_ne_tronque_pas():
    """Une valeur longue descend d'un cran dans l'échelle ; elle n'est jamais coupée — elle n'a donc
    rien à redire dans une bulle native."""
    long = str(C.kpi("Province la plus à risque", "Dyamongou-et-Gobnangou"))
    assert "data-long='true'" in long and "title=" not in long
    assert "data-long" not in str(C.kpi("Taux d'abandon national", "9,2 %"))


def test_source_technique_dite_en_francais():
    """Une clé de base de données n'est pas une phrase : l'affichage la traduit, la donnée ne bouge
    pas (meta.libelle_source reste la référence des exports)."""
    assert C.libelle_source_lisible("report_dernier_releve_CONASUR_2023-03-31") == \
        "Report du dernier relevé CONASUR (31/03/2023)"
    assert C.libelle_source_lisible("retropolation_test") == "Rétropolation test"
    # clé déjà traduite par le modèle : inchangée ; clé inconnue : comportement actuel conservé
    assert C.libelle_source_lisible("reventilation_part_filles_fichier_acces").startswith("Ventilation par sexe")
    assert C.libelle_source_lisible("interpolation_test") == "interpolation test"
    assert C.libelle_source_lisible(None) == "" and C.libelle_source_lisible(float("nan")) == ""
    # l'astérisque ouvre l'infobulle du produit, pas une bulle native inatteignable au clavier
    ast = str(C.asterisque("report_dernier_releve_CONASUR_2023-03-31"))
    assert "data-aide" in ast and "31/03/2023" in ast and "title=" not in ast


def test_echelles_de_couleur():
    """Une seule teinte séquentielle pour le risque, et l'accent n'encode jamais une donnée."""
    assert len(F.ECHELLE_RISQUE) == 9 and F.ECHELLE_RISQUE[-1] == "#67000D"
    assert len(F.ECHELLE_NEUTRE) == 9
    accent = C.chargement(None).color.lower()
    assert accent == "#0f6a5a"
    assert accent not in [c.lower() for c in F.ECHELLE_RISQUE + F.ECHELLE_NEUTRE + F.OKABE_ITO]


def test_vue_ensemble_rendue(app):
    """Parcours heureux : six chiffres clés, un tableau de 11 lignes, une légende discrète à neuf
    pas, la phrase de lecture et le segment de mesure."""
    (kpis, fig, legende_note, top, lecture, sous,
     explication, titre_top, titre_carte) = _cb(app, "acc-kpis.children")(2024, "T", "indice_v2_0_100")
    assert titre_top == "Les 10 provinces les plus à risque"
    assert titre_carte.children[0] == "Carte du risque (45 provinces)"  # titre du score inchangé
    assert len(kpis) == 6
    assert str(top).count("Tr(") == 11 and "table-top10" in str(top)
    txt = str(legende_note)
    assert "legende-echelle" in txt and txt.count("ech-risque-") == 9 and "limites des régions" in txt
    assert "Lecture : " in str(lecture) and "cle-mobile" in str(lecture)
    assert explication.startswith("Note de synthèse")
    mise_en_page = str(app.callback_map and _cb(app, "page.children")("/", "")[0])
    assert "segment" in mise_en_page and "squelette" in mise_en_page  # états prêt et chargement
    # la phrase d'explication est posée dès le premier rendu : sa hauteur est réservée, le bloc
    # ne saute pas quand le callback la remplace
    assert "explication-mesure" in mise_en_page and "lien-bleu" in mise_en_page


def test_carte_de_localisation_region(app, donnees):
    """Exigence utilisateur : la province choisie en bleu foncé, toute sa région en bleu clair,
    le reste du pays en gris, et le contour extérieur de la région en bleu, 2 px."""
    from dcdash.vues import geoms_provinces, geoms_regions
    g = geoms_provinces(donnees, "ancien_45")
    code = g["code"].iloc[0]
    region = g["pcode_region_carte"].iloc[0]
    fig = F.carte_localisation(g, code, geoms_regions(donnees, "ancien_45"), hauteur=None)
    remplis = [t for t in fig.data if t.fill == "toself"]
    couleurs = [t.fillcolor for t in remplis]
    assert len(remplis) == len(g)
    assert couleurs.count(F.CARTE_CHOISIE) == 1
    assert couleurs.count(F.CARTE_REGION) == int((g["pcode_region_carte"] == region).sum()) - 1
    assert couleurs.count(F.CARTE_AUTRE) == len(g) - couleurs.count(F.CARTE_REGION) - 1
    contour = [t for t in fig.data if t.fill is None and t.line.width == 2]
    assert len(contour) == 1 and contour[0].line.color == F.CARTE_REGION_TRAIT


def test_boite_de_carte_dimensionnee_pour_le_pays():
    """Ce qui est dessiné est le pays, un contour d'environ 1,4:1, jamais une grille de carrés :
    la boîte est dimensionnée pour lui. Empilée elle tient son rapport (aucune bande vide), en
    deux panneaux elle prend la hauteur qui reste, et sur un écran court la légende passe dans
    une colonne à droite au lieu de voler la hauteur de la carte."""
    css = open(STYLE, encoding="utf-8").read()
    empile = re.search(r"\.zone-carte, \.fiche-carte \{([^}]*)\}", css).group(1)
    assert "aspect-ratio: 1.4 / 1" in empile and "flex: 0 0 auto" in empile
    deux = re.search(r"@media \(min-width: 1280px\) \{\s*\.racine-pleine \.zone-carte \{([^}]*)\}", css).group(1)
    assert "flex: 1 1 auto" in deux and "min-height: 180px" in deux and "max-height: 560px" in deux
    court = css.split("@media (min-width: 1280px) and (max-height: 860px) {")[1].split("\n}\n")[0]
    assert "grid-template-columns: minmax(0, 1fr) 200px" in court
    assert ".bloc-carte > .zone-carte" in court and "flex-direction: column" in court
    # le classement n'a pas de bande de chiffres clés : la colonne latérale y creuserait la bande
    # vide qu'elle est censée supprimer, il garde donc sa légende sous la carte
    assert court.count(":not(.ligne-classement)") >= 4
    # la liste prend la part la plus large : le panneau de carte n'a besoin que de « hauteur × 1,4 »
    assert "grid-template-columns: minmax(0, 6fr) minmax(0, 5fr)" in css


def test_le_kit_tient_face_aux_regles_du_cadriciel():
    """Dash repeint l'option survolée avec sa propre teinte (spécificité 0,3,1) : sans ces états
    l'option choisie vire au violet du cadriciel après un clic. Le mot du badge n'est masqué que
    dans le tableau dense du top 10, la hachure passe derrière le texte, et l'anneau de focus
    d'un chiffre clé se dessine à l'intérieur d'une bande qui rogne ses coins."""
    css = open(STYLE, encoding="utf-8").read()
    for etat in (".selected", ".selected:hover", ".selected:focus-within"):
        assert f".segment.dash-options-list .dash-options-list-option{etat}" in css
    assert ".table-top10 .badge-statut .mot {" in css and css.count(".badge-statut .mot {") == 1
    assert ".kpi:focus-visible { outline-offset: -3px; }" in css
    assert ".kpi-val.petit" in css
    # la hachure reste le code « estimé » du produit, mais dans une bande au bord de la cellule :
    # jamais sous le texte, où elle rendait « 247,3 ‰ » pénible à lire
    bande = re.search(r"\n\.impute::before \{([^}]*)\}", css).group(1)
    assert "width: 4px" in bande and "left: 0" in bande and "var(--hachure)" in bande
    assert "position: relative" in re.search(r"\n\.impute \{([^}]*)\}", css).group(1)
    assert "background-image" not in re.search(r"\n\.impute \{([^}]*)\}", css).group(1)


def test_groupe_de_boutons_radio_nomme():
    """Un conteneur de boutons radio n'est pas étiquetable : `htmlFor` y pointerait dans le vide.
    Le libellé le nomme alors par `aria-labelledby` sur un `role="group"`."""
    radio = str(C.filtre("Comparer", C.segment("evo-niveau", {"province": "Provinces"}, "province")))
    assert "htmlFor" not in radio and "role='group'" in radio
    assert "aria-labelledby='evo-niveau-lib'" in radio and "id='evo-niveau-lib'" in radio
    assert "htmlFor='acc-sexe'" in str(C.filtre("Élèves", C.choix_sexe("acc-sexe")))
    assert "aria-label='Mesure cartographiée'" in str(C.segment("m", {"a": "A"}, "a", nom="Mesure cartographiée"))
    # les appels existants continuent de fonctionner
    assert "RadioItems" in str(C.segment("m", {"a": "A"}, "a"))[:12]
    assert "kpi-val petit" in str(C.kpi("Solidité du classement", "Probable", petit=True))
    assert "ligne-kpi fiche-kpis" in str(C.bande_kpi([], classe="fiche-kpis"))


def test_cle_de_legende_montre_la_hachure():
    """La pastille « valeur estimée » porte la hachure elle-même : le libellé n'a pas à la nommer."""
    assert C.CLES_CARTE["estime"][1] == "valeur estimée"
    assert "hachures" not in str(C.legende_carte("Score de risque", ["0", "100"]))


def test_cles_de_legende_suivent_la_carte_affichee():
    """Une légende ne nomme que ce qui est à l'écran. Pas de
    province sans valeur, pas de clé « non disponible » ; pas de hachure, pas de « valeur
    estimée ». Et la clé « top 10 » n'existe plus du tout."""
    assert "top10" not in C.CLES_CARTE
    nan = float("nan")
    pleine = {"A": dict(valeur=12.0, impute=False), "B": dict(valeur=3.0, impute=False)}
    assert C.cles_legende(pleine) == ()
    assert C.cles_legende(pleine, ["A", "B"]) == ()
    # une province dessinée mais absente du dict est tracée en gris : la clé revient
    assert C.cles_legende(pleine, ["A", "B", "C"]) == ("nd",)
    assert C.cles_legende({"A": dict(valeur=nan, impute=False)}) == ("nd",)
    assert C.cles_legende({"A": dict(valeur=1.0, impute=True)}) == ("estime",)
    assert C.cles_legende({"A": dict(valeur=nan, impute=False),
                           "B": dict(valeur=1.0, impute=True)}) == ("nd", "estime")
    # aucune clé : pas de rangée vide sous l'échelle
    assert "legende-cles" not in str(C.legende_carte("Score de risque", ["0", "100"], cles=()))
    assert "legende-cles" in str(C.legende_carte("Score de risque", ["0", "100"], cles=("estime",)))


def test_lien_bleu_du_classement():
    """Le lien qui emmène vers le classement complet et son export se voit : bleu, souligné au
    repos. Les autres liens gardent l'accent du produit."""
    bleu = str(C.lien_discret("Classement complet et export", "/classement", bleu=True))
    assert "lien-discret lien-bleu" in bleu
    assert "lien-bleu" not in str(C.lien_discret("Autre", "/autre"))
    css = open(STYLE, encoding="utf-8").read()
    regle = re.search(r"\n\.lien-bleu \{([^}]*)\}", css).group(1)
    assert "var(--lien)" in regle and "text-decoration: underline" in regle
    assert "--lien:" in open(TOKENS, encoding="utf-8").read()


def test_chiffre_cle_tient_en_deux_lignes():
    """Au plus deux lignes sous la valeur. La cellule n'a que
    deux emplacements sous la valeur (tendance, contexte) et la pastille d'un relevé prolongé tient
    dans le contexte — son mot est court, son nom accessible reste la phrase entière."""
    cell = C.kpi("Déplacés internes (PDI)", "1 954 000", "25 / 1 000 hab.", aide_kpi="Définition…",
                 evolution=C.tendance(0.0, "inchangé en un an"),
                 chip=C.chip_stale("Dernier relevé CONASUR du 31/03/2023, prolongé pour les années suivantes."))
    sous = [e for e in cell.children[2:] if e is not None]
    assert len(sous) == 2  # tendance + contexte, jamais une troisième ligne
    txt = str(cell)
    assert "prolongé" in txt and "relevé prolongé" not in txt.replace("aria-label='relevé prolongé'", "")
    assert "aria-label='relevé prolongé'" in txt
    css = open(STYLE, encoding="utf-8").read()
    assert ".racine-pleine .kpi { padding: 8px 12px; }" in css


def test_explication_de_la_mesure_cartographiee(app):
    """Une phrase par onglet, sous les onglets, remplacée par le callback existant : chaque mesure
    a la sienne, et la place réservée en CSS vaut deux lignes — la plus longue des trois en occupe
    deux dans la colonne de 1366 px, les deux autres une seule, donc le bloc ne saute pas."""
    from dcdash.pages import accueil as P
    attendu = {"indice_v2_0_100": "Note de synthèse de 0 à 100 qui combine abandon, redoublement, personnes "
                                  "déplacées et conditions d'accueil.",
               "taux_abandon_harmonise": "Taux brut observé pour l'année, sans pondération.",
               "proba_risque_t1": "Probabilité de passer au-dessus du seuil d'alerte de 50 % l'année suivante."}
    assert P.EXPLICATIONS == attendu
    assert set(P.MESURES) == set(attendu)  # les trois onglets restent, chacun avec sa phrase
    maj = _cb(app, "acc-explication.children")
    for mesure, phrase in attendu.items():
        assert maj(2024, "T", mesure)[6] == phrase
    # même quand la carte est vide (prévision absente pour cette sélection), la phrase suit l'onglet
    assert maj(2017, "F", "proba_risque_t1")[6] == attendu["proba_risque_t1"]
    css = open(STYLE, encoding="utf-8").read()
    regle = re.search(r"\n\.explication-mesure \{([^}]*)\}", css).group(1)
    assert "min-height: 36px" in regle  # hauteur mesurée de la phrase la plus longue sur deux lignes


def test_un_seul_ecran_des_600px_de_hauteur():
    """1440 × 900 et 1366 × 768 sont des tailles d'écran : barres du navigateur prises, la fenêtre
    n'en montre que ~780 et ~650 px. Le plancher de la propriété « un seul écran » descend donc à
    600 px de hauteur, sinon les deux écrans de décision se remettent à défiler (mesuré)."""
    css = open(STYLE, encoding="utf-8").read()
    assert "@media (min-width: 1280px) and (min-height: 600px) {" in css
    assert "min-height: 720px" not in css
    regle = css.split("@media (min-width: 1280px) and (min-height: 600px) {")[1].split("\n}\n")[0]
    assert ".racine-pleine { height: 100dvh; }" in regle


def test_densite_de_la_coque():
    """Navbar compacte sur toutes les vues et marges serrées : ce sont ces pixels qui rendent au
    panneau de gauche ses dix lignes à 1366 × 768."""
    css = open(STYLE, encoding="utf-8").read()
    nav = re.search(r"\n\.entete-site\.navbar \{([^}]*)\}", css).group(1)
    assert "height: 44px" in nav and "padding: 0 16px" in nav
    petit = css.split("@media (max-width: 991px) {")[1].split("\n}\n")[0]
    assert "height: 48px" in petit  # la bascule tactile fait 44 × 44 : la barre lui laisse son filet
    assert "width: 44px" in css and "height: 44px" in css  # cible tactile de la bascule, inchangée
    pleine = re.search(r"\n\.racine-pleine \.page \{([^}]*)\}", css).group(1)
    assert "gap: 8px" in pleine and "padding: 8px 16px 12px" in pleine
    assert ".racine-pleine .carte-bloc { margin-bottom: 0; padding: 8px 12px; }" in css
    bandeau = re.search(r"\n\.bandeau \{([^}]*)\}", css).group(1)
    assert "padding: 4px 16px" in bandeau
    # titre et filtres sur la même ligne : à partir de 992 px la rangée ne se coupe plus
    large = css.split("@media (min-width: 992px) {")[1].split("\n}\n")[0]
    assert "flex-wrap: nowrap" in large


def test_bandeau_et_404():
    assert "Données fictives" in str(C.bandeau(True, "1.4.0"))
    conf = str(C.bandeau(False, "1.4.0"))
    assert "bandeau-conf" in conf and "1.4.0" in conf and "ico-verrou" in conf
    assert "Retour à la vue d'ensemble" in str(C.page_404())
