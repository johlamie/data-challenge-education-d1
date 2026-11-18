"""Composants d'interface partagés.

Les pages composent ces fabriques et ne redéfinissent jamais le style interne d'un composant :
tout ce qui est visuel vit ici et dans assets/style.css, qui ne lit que les jetons de
assets/tokens.css. Un bloc dont une page a besoin et qui n'est pas ici manque à ce module :
il se signale, il ne s'invente pas dans la page.
"""
import re

import dash_bootstrap_components as dbc
from dash import dcc, html

from .figures import ACCENT
from .meta import (ANNEES, DECOUPAGES, EQUIPE, EQUIPE_URL, INDICATEURS, SEXES, STATUT_TOP10, STATUT_TOP10_AIDE, annee_scolaire,
                   fmt_nombre, libelle_source)

# pages principales (décideurs) ; Qualité des données et Méthode sont regroupées dans « À propos et méthode »
PAGES = [("/", "Vue d'ensemble"), ("/classement", "Classement"), ("/fiche", "Fiche province"),
         ("/evolution", "Évolution")]
PAGES_SECONDAIRES = [("/methode", "Méthode et définitions"), ("/qualite", "Qualité des données")]

NOM_PRODUIT = "Décrochage scolaire au primaire · Burkina Faso"
NOM_PRODUIT_COURT = "Décrochage primaire · BF"


# ---------------------------------------------------------------- icônes
def icone(nom, taille=16, **kw):
    """Contour Lucide local peint par un masque CSS : il hérite de la couleur du texte.
    Deux tailles seulement, 16 et 20."""
    classe = f"ico ico-{nom}" + (" ico-20" if taille == 20 else "")
    return html.Span(className=classe, **{"aria-hidden": "true"}, **kw)


# ---------------------------------------------------------------- bandeau et entête
def bandeau(demo, version=""):
    """Bandeau d'état, premier élément de chaque page, au-dessus de l'entête. Jamais masquable."""
    if demo:
        return html.Div([icone("alerte"),
                         html.Span([html.B("Données fictives"),
                                    " · démonstration du design : aucun chiffre, nom ou classement affiché "
                                    "n'est réel · " + EQUIPE])],
                        className="bandeau bandeau-demo", role="status")
    return html.Div([icone("verrou"),
                     html.Span(f"Données confidentielles · usage interne · {EQUIPE} · version {version}")],
                    className="bandeau bandeau-conf", role="status")


def barre_navigation(auth_active):
    """Masthead clair : lockup typographique à gauche, onglets en toutes lettres à droite.
    Sous 992 px les onglets passent derrière une bascule 44×44 qui ouvre une feuille.

    Les deux pages secondaires existent en deux exemplaires : un menu déroulant sur grand écran, et
    deux liens posés à plat dans la feuille mobile. Un menu dans un menu n'est pas tenable au doigt
    (le premier geste referme la feuille) ; à plat, chaque page est à un seul toucher. Le lien à plat
    porte l'état « page courante », ce qui permet aussi de marquer l'entrée déroulante sur grand écran."""
    liens = [dbc.NavItem(dbc.NavLink(t, href=h, id=f"nav-{h.strip('/') or 'accueil'}", active="exact"))
             for h, t in PAGES]
    liens.append(dbc.DropdownMenu([dbc.DropdownMenuItem(t, href=h, id=f"nav-{h.strip('/')}")
                                   for h, t in PAGES_SECONDAIRES],
                                  label="À propos et méthode", nav=True, in_navbar=True, align_end=True,
                                  id="nav-apropos", className="nav-secondaire"))
    liens += [dbc.NavItem(dbc.NavLink(t, href=h, id=f"navm-{h.strip('/')}", active="exact"),
                          className="nav-a-plat") for h, t in PAGES_SECONDAIRES]
    if auth_active:
        liens.append(html.Span(className="nav-separateur", **{"aria-hidden": "true"}))
        liens.append(dbc.NavItem(dbc.NavLink([icone("deconnexion"), "Se déconnecter"], href="/deconnexion",
                                             external_link=True), className="deconnexion"))
    return dbc.Navbar(dbc.Container([
        html.Div([dbc.NavbarBrand([html.Span(NOM_PRODUIT, className="marque-long"),
                                   html.Span(NOM_PRODUIT_COURT, className="marque-court")], href="/"),
                  html.A(EQUIPE, href=EQUIPE_URL, target="_blank", rel="noopener", className="marque-equipe")],
                 className="marque-groupe"),
        dbc.NavbarToggler(id="nav-bascule"),
        dbc.Collapse(dbc.Nav(liens, className="ms-auto", navbar=True), id="nav-menu", navbar=True),
    ], fluid=True), color=None, className="navbar-dc entete-site", expand="lg")


# ---------------------------------------------------------------- entête de page
def titre(t, sous=None, controles=None, id_sous=None):
    """Entête de page : un titre en français courant (souvent une question) et une ligne de périmètre.
    `controles` : le groupe de filtres aligné à droite, en bas."""
    gauche = html.Div([html.H1(t, className="titre-page"),
                       html.P(sous, className="sous-titre", **({"id": id_sous} if id_sous else {}))
                       if (sous is not None or id_sous) else None], className="entete-titre")
    return html.Div([gauche, html.Div(controles, className="entete-filtres") if controles else None],
                    className="entete-vue")


# ---------------------------------------------------------------- aides de lecture
def aide(texte_aide, lib=None):
    """Marqueur « i » : budget de 3 à 5 sur tout le site, sur les notions clés seulement.
    Jamais sur un chiffre clé, jamais sur un libellé qui se comprend seul."""
    if not texte_aide:
        return None
    return html.Span(className="aide", tabIndex="0", role="button",
                     **{"data-aide": texte_aide, "aria-label": "Aide : " + (lib or texte_aide.split("\n")[0][:80]),
                        "aria-expanded": "false"})


def terme(contenu, texte_aide, **kw):
    """Terme survolable : pointillé = « il y a une définition ici ». Ouvre la même bulle, sans icône.
    C'est une commande déclarée (`role="button"`), sinon `aria-expanded` porterait dans le vide."""
    return html.Span(contenu, className="terme-aide", tabIndex="0", role="button",
                     **{"data-aide": texte_aide, "aria-expanded": "false"}, **kw)


def avec_aide(contenu, texte_aide, lib=None):
    """Libellé suivi de son marqueur « i » (espace sécable : sur écran étroit l'icône passe à la ligne)."""
    return html.Span([contenu, " ", aide(texte_aide, lib or (contenu if isinstance(contenu, str) else None))],
                     className="avec-aide")


# ---------------------------------------------------------------- libellés de source lisibles
# Présentation seulement : une clé technique de la base (« report_dernier_releve_CONASUR_2023-03-31 »)
# n'est pas une phrase française. La donnée, elle, ne bouge pas — les exports gardent la valeur
# telle quelle, et `meta.libelle_source` (le modèle) n'est pas touché.
_SOURCES_LISIBLES = [
    ("report_dernier_releve_CONASUR", "Report du dernier relevé CONASUR"),
    ("retropolation", "Rétropolation"),
]
_DATE_FIN = re.compile(r"[ _](\d{4})-(\d{2})-(\d{2})$")


def libelle_source_lisible(cle):
    """Nom lisible d'une source d'estimation, pour l'affichage seulement.

    Les clés déjà traduites par le modèle gardent leur libellé ; celles qui n'y sont pas passent par
    cette table (accents, mot « du », date à la française) ; les autres gardent exactement le
    comportement actuel. Une date collée à la fin d'une clé devient une parenthèse : « (31/03/2023) ».
    """
    if cle is None or cle != cle or cle == "":
        return ""
    brut = str(cle)
    lisible = None
    for prefixe, texte in _SOURCES_LISIBLES:
        if brut.startswith(prefixe):
            lisible = texte + brut[len(prefixe):]
            break
    if lisible is None:
        return libelle_source(brut)
    m = _DATE_FIN.search(lisible)
    if m:
        lisible = lisible[:m.start()] + f" ({m.group(3)}/{m.group(2)}/{m.group(1)})"
    return lisible.replace("_", " ")


def ticks_echelle(lo, hi, cle):
    """Six repères de l'échelle d'une carte, dans l'unité affichée. Aucun arrondi « joli » : ce sont
    les bornes réelles du tracé, pour qu'un lecteur puisse nommer une classe à voix haute."""
    pas = (hi - lo) / 5
    vals = [lo + i * pas for i in range(6)]
    if cle == "proba_risque_t1":
        return [fmt_nombre(100 * v, 0) for v in vals]
    return [fmt_nombre(v, 1 if cle == "taux_abandon_harmonise" else 0) for v in vals]


def contenu_lecture(txt):
    """Contenu d'une phrase de lecture, pour un callback qui remplit un `.lecture` déjà posé.
    La liste est aplatie : le moteur de rendu n'accepte pas une liste imbriquée comme enfant."""
    suite = list(txt) if isinstance(txt, (list, tuple)) else [txt]
    return [html.Span("Lecture : ", className="lecture-lib"), *suite]


def lecture(txt, **kw):
    """Phrase « Lecture : » — exactement une sous chaque carte, graphique et classement."""
    return html.P(contenu_lecture(txt), className="lecture", **kw)


def note(txt, **kw):
    """Ligne de note sous un bloc : chaque code visuel dit en toutes lettres."""
    return html.P(txt, className="note", **kw)


# ---------------------------------------------------------------- blocs
def entete_bloc(titre_bloc, *droite, aide_titre=None, id_titre=None):
    t = html.H2(avec_aide(titre_bloc, aide_titre) if aide_titre else titre_bloc,
                **({"id": id_titre} if id_titre else {}))
    return html.Div([t, *[d for d in droite if d is not None]], className="bloc-entete")


def bloc(titre_bloc, *enfants, aide_titre=None, **kw):
    t = None
    if titre_bloc:
        t = html.H2(avec_aide(titre_bloc, aide_titre) if aide_titre else titre_bloc)
    return html.Section([t, *enfants], className="carte-bloc", **kw)


# ---------------------------------------------------------------- filtres
def filtre(lib, composant, aide_lib=None, classe=""):
    """Champ de filtre : libellé toujours visible au-dessus du contrôle (jamais un libellé-fantôme).

    Un groupe de boutons radio (`segment`) est un conteneur, pas un contrôle étiquetable : `htmlFor`
    y pointerait dans le vide. Le libellé le nomme alors par `aria-labelledby` sur un `role="group"`.
    """
    contenu = [lib, aide(aide_lib, lib)] if aide_lib else lib
    cible = getattr(composant, "id", None)
    if isinstance(cible, str) and not isinstance(composant, dcc.RadioItems):
        etiquette = html.Label(contenu, htmlFor=cible, className="filtre-lib")
        corps = composant
    else:
        id_lib = (cible or classe or "filtre") + "-lib"
        etiquette = html.Span(contenu, className="filtre-lib", id=id_lib)
        corps = html.Div(composant, role="group", **{"aria-labelledby": id_lib})
    return html.Div([etiquette, corps], className=("filtre " + classe).strip())


def choix_annee(id_, valeur=2024):
    return dcc.Dropdown(id=id_, options=[{"label": annee_scolaire(a), "value": a} for a in ANNEES[::-1]],
                        value=valeur, clearable=False, searchable=False)


def choix_sexe(id_, valeur="T"):
    return dcc.Dropdown(id=id_, options=[{"label": v, "value": k} for k, v in SEXES.items()], value=valeur,
                        clearable=False, searchable=False)


# libellés courts du découpage, côté régions : « Ancien découpage (13 régions, 45 provinces) » ne
# tient pas dans un champ de filtre, et c'est le nombre de régions qui distingue les deux choix
# pour le lecteur. La valeur envoyée au calcul, elle, ne change pas.
DECOUPAGES_REGIONS = {"ancien_45": "13 régions (ancien)", "2025_47": "17 régions (2025)"}


def choix_decoupage(id_, valeur="ancien_45", courts=False):
    options = DECOUPAGES_REGIONS if courts else DECOUPAGES
    return dcc.Dropdown(id=id_, options=[{"label": v, "value": k} for k, v in options.items()], value=valeur,
                        clearable=False, searchable=False)


def choix_indicateur(id_, valeur="indice_v2", exclure=()):
    return dcc.Dropdown(id=id_, options=[{"label": m["label"], "value": k} for k, m in INDICATEURS.items()
                                         if k not in exclure], value=valeur, clearable=False)


def segment(id_, options, valeur, nom=None):
    """Interrupteur segmenté : remplace des boutons radio nus. L'entrée reste focalisable (jamais
    display:none), c'est l'étiquette qui porte le contrôle.

    `nom` donne son nom accessible au groupe. `dcc.RadioItems` n'accepte aucun attribut `aria-*`
    (il n'autorise que className/id/inline/inputClassName/inputStyle/componentPath) : le nom est
    donc porté par un conteneur `role="group"`. Sans `nom`, le composant est rendu tel quel — un
    appel existant continue de fonctionner, et un `filtre()` qui l'enveloppe le nomme déjà.
    """
    radio = dcc.RadioItems(id=id_, value=valeur, inline=True,
                           options=[{"label": v, "value": k} for k, v in options.items()],
                           className="segment", inputClassName="segment-input", labelClassName="segment-item")
    if not nom:
        return radio
    return html.Div(radio, className="segment-groupe", role="group", **{"aria-label": nom})


# ---------------------------------------------------------------- chiffres clés
FLECHES = {"hausse": "▲", "baisse": "▼", "stable": "▶"}


SENS_TENDANCE = {"pire": "Évolution défavorable sur un an", "mieux": "Évolution favorable sur un an",
                 "neutre": "Stable sur un an"}


def tendance(delta, texte, mauvais_si_hausse=True, seuil=1e-9):
    """Tendance sur un an : flèche ▲/▼/▶ et encre. Ni rouge ni vert appariés — l'amélioration est
    portée par la flèche et les mots, pas par une seconde couleur.
    Renvoie None si la comparaison n'existe pas : aucune valeur inventée.

    Le sens de l'encre est dit en toutes lettres pour les lecteurs d'écran, jamais par un `title` :
    dans un chiffre clé, une bulle native en recouvrirait une du produit."""
    if delta is None or delta != delta:
        return None
    sens = "stable" if abs(delta) <= seuil else ("hausse" if delta > 0 else "baisse")
    if sens == "stable":
        effet = "neutre"
    else:
        effet = "pire" if (sens == "hausse") == mauvais_si_hausse else "mieux"
    return html.Span([html.Span(FLECHES[sens], className="fleche", **{"aria-hidden": "true"}), " ", texte,
                      html.Span(" (" + SENS_TENDANCE[effet].lower() + ")", className="visuellement-cache")],
                     className=f"kpi-tendance t-{effet}")


def chip_stale(texte_aide, libelle="prolongé", nom="relevé prolongé"):
    """Pastille « prolongé » : un relevé reporté est un état, pas une note de bas de page.

    Le mot affiché est court pour que le contexte et la pastille tiennent sur une seule ligne dans
    une cellule de chiffre clé à 1366 px (au plus deux lignes sous la valeur).
    Le nom accessible, lui, reste la phrase entière, et l'infobulle dit la date
    du dernier relevé."""
    return html.Span([icone("horloge"), libelle], className="chip-stale", tabIndex="0", role="button",
                     **{"data-aide": texte_aide, "aria-expanded": "false", "aria-label": nom})


def kpi(libelle, valeur, variation=None, id_=None, evolution=None, critique=False,
        aide_kpi=None, chip=None, etat="ready", petit=False, **_):
    """Cellule de chiffre clé : quatre emplacements, toujours dans cet ordre (libellé, valeur, tendance,
    contexte) et jamais plus. Avec `aide_kpi`, toute la cellule ouvre l'infobulle au survol, au clavier
    et au toucher : le libellé prend un soulignement pointillé, et il n'y a jamais d'icône « i » sur un
    chiffre clé. Une valeur longue passe à la ligne ou descend d'un cran : elle n'est jamais coupée.
    `petit` : la valeur est un mot, pas un chiffre (un badge, « correcte / faible ») — elle prend la
    variante basse de l'échelle, jamais le corps de 28 px réservé aux chiffres.

    Aucune bulle native (`title`) nulle part dans la cellule : un chiffre clé a l'infobulle du
    produit ou rien. Un libellé qui se comprend seul (« Province la plus à risque ») n'ouvre rien du tout.

    Accessibilité : la cellule entière reste la surface de survol (elle porte `data-aide`), mais la
    commande déclarée — focalisable, `role="button"`, `aria-expanded` — est le libellé souligné.
    Une pastille (« relevé prolongé ») est elle aussi une commande : si la cellule entière en était
    une, cette pastille se retrouverait imbriquée dans un bouton et disparaîtrait des lecteurs d'écran."""
    txt = valeur if isinstance(valeur, str) else ""
    # le soulignement pointillé est la seule affordance : jamais d'icône « i » sur un chiffre clé
    lib = html.Span(html.Span(libelle, className="terme-aide", tabIndex="0", role="button",
                              **{"data-aide": aide_kpi, "aria-expanded": "false"}) if aide_kpi else libelle,
                    className="kpi-lib")
    # une valeur longue passe à la ligne et descend d'un cran : rien n'est coupé, donc rien à redire
    # dans une bulle native
    val = html.Span(valeur, className="kpi-val" + (" kpi-critique" if critique else "") + (" petit" if petit else ""),
                    **({"data-long": "true"} if len(txt) > 16 else {}))
    contexte = None
    if variation or chip is not None:
        contenu = [variation] if variation else []
        if chip is not None:
            contenu += [" ", chip]
        contexte = html.Span(contenu, className="kpi-var")
    return html.Div([lib, val, evolution, contexte],
                    className="kpi kpi-info" if aide_kpi else "kpi",
                    **{"data-state": etat},
                    **({"data-aide": aide_kpi} if aide_kpi else {}),
                    **({"id": id_} if id_ else {}))


def kpi_squelette(libelle):
    """Chiffre clé en cours de chargement : le libellé reste, la valeur devient une barre de la même
    hauteur. Pas de spinner, pas de scintillement — dans un document ce serait le seul élément mobile."""
    return html.Div([html.Span(libelle, className="kpi-lib"),
                     html.Span(className="squelette squelette-val")],
                    className="kpi", **{"data-state": "loading", "aria-busy": "true"})


def bande_kpi(cellules, classe="", **kw):
    """Bande de chiffres clés : une seule surface divisée par des filets de 1 px, pas six cartes.
    `classe` : variante de grille partagée (par ex. `fiche-kpis`, la bande 2×2 de la fiche)."""
    return html.Div(cellules, className=("ligne-kpi " + classe).strip(), **kw)


# ---------------------------------------------------------------- badges, marques
def badge_statut(s, titre=True):
    """Solidité du classement. La couleur n'est jamais le seul canal : les points ●/○ portent le niveau
    et le mot est toujours présent (masqué visuellement sous 576 px, toujours lu par les lecteurs d'écran).

    `titre=False` dans un chiffre clé : la cellule y ouvre déjà l'infobulle du produit, et une bulle
    native par-dessus ferait deux explications concurrentes pour le même badge."""
    if not s or s != s:
        return html.Span([html.Span("○○○", className="points", **{"aria-hidden": "true"}),
                          html.Span("n.d.", className="mot")], className="badge-statut statut-hors_top10")
    points = {"stable_top10": "●●●", "plutot_top10": "●●○", "instable_bord": "●○○", "hors_top10": "○○○"}.get(s, "")
    return html.Span([html.Span(points, className="points", **{"aria-hidden": "true"}),
                      html.Span(STATUT_TOP10.get(s, s), className="mot")],
                     className=f"badge-statut statut-{s}",
                     **({"title": STATUT_TOP10_AIDE.get(s, "")} if titre else {}))


def asterisque(source):
    """Astérisque d'une valeur estimée : il ouvre l'infobulle du produit, comme tout le reste du site —
    une bulle native ne s'ouvrirait ni au clavier ni au toucher."""
    texte_aide = "Valeur estimée : " + (libelle_source_lisible(source) or "source non précisée")
    return html.Span("*", className="ast", tabIndex="0", role="button",
                     **{"data-aide": texte_aide, "aria-expanded": "false",
                        "aria-label": "valeur estimée, source au survol"})


# ---------------------------------------------------------------- boutons
def bouton(label, id_=None, nom_icone=None, **kw):
    """Action principale d'une zone : une seule par zone, et son libellé est un verbe."""
    contenu = [icone(nom_icone), label] if nom_icone else label
    return html.Button(contenu, className="btn-dc", type="button", **({"id": id_} if id_ else {}), **kw)


def bouton_2(label, id_=None, nom_icone=None, **kw):
    contenu = [icone(nom_icone), label] if nom_icone else label
    return html.Button(contenu, className="btn-dc-2", type="button", **({"id": id_} if id_ else {}), **kw)


def lien_discret(label, href, id_=None, bleu=False, **kw):
    """Lien de navigation sans boîte. `bleu=True` : la variante appuyée (bleu, soulignée au
    repos), pour un lien qui emmène vers un autre écran ou vers un export — il doit se voir
    que c'est cliquable. Les autres liens gardent l'accent."""
    classe = "lien-discret lien-bleu" if bleu else "lien-discret"
    return dcc.Link(label, href=href, className=classe, **({"id": id_} if id_ else {}), **kw)


# ---------------------------------------------------------------- cartes : légende discrète
# Deux clés seulement, et chacune n'apparaît que si la carte affichée la contient vraiment
# (quand tout est disponible, la clé « non disponible » ne doit pas s'afficher).
# La clé « top 10 » et le contour noir qu'elle décrivait sont retirés.
CLES_CARTE = {"nd": ("legende-nd", "non disponible"),
              # la pastille porte la hachure elle-même : le libellé n'a pas à la nommer
              "estime": ("legende-estime", "valeur estimée")}


def cles_legende(valeurs, codes=None):
    """Clés de légende à montrer pour la carte telle qu'elle est dessinée.

    `valeurs` : le dict code -> dict(valeur, impute, …) passé à la figure ; `codes` : les codes
    réellement tracés (une province absente du dict est dessinée en gris « non disponible »).
    Une légende ne nomme que ce qui est à l'écran : pas de province sans valeur, pas de clé
    « non disponible » ; pas de province hachurée, pas de clé « valeur estimée »."""
    codes = list(codes) if codes is not None else list(valeurs)
    nd = any((c not in valeurs) or _manquante(valeurs[c].get("valeur")) for c in codes)
    estime = any(bool(valeurs[c].get("impute")) for c in codes if c in valeurs)
    return tuple(c for c, present in (("nd", nd), ("estime", estime)) if present)


def _manquante(v):
    """Vrai si la valeur n'existe pas (None ou NaN) — le test NaN se fait sans importer numpy."""
    return v is None or v != v


def legende_carte(titre_echelle, ticks, cles=("nd", "estime"), echelle="risque"):
    """Légende discrète : neuf pas de couleur à largeur égale, pas une barre continue — un lecteur doit
    pouvoir nommer une classe à voix haute en réunion. `cles` vient de `cles_legende()` : elle ne
    nomme que les codes visuels présents sur la carte affichée."""
    pas = [html.Span(className=f"ech-{echelle}-{i}") for i in range(1, 10)]
    return html.Div([
        html.P(titre_echelle, className="legende-titre"),
        html.Div(pas, className="legende-echelle", **{"aria-hidden": "true"}),
        html.Div([html.Span(t) for t in ticks], className="legende-ticks"),
        # aucune clé à montrer : pas de rangée vide sous l'échelle
        html.Div([html.Span([html.I(className=CLES_CARTE[c][0]), CLES_CARTE[c][1]]) for c in cles],
                 className="legende-cles") if cles else None,
    ], className="legende-carte")


# ---------------------------------------------------------------- états
def squelette(classe="squelette-ligne", n=1):
    return [html.Span(className=f"squelette {classe}") for _ in range(n)]


def chargement(enfant):
    # la couleur du tourniquet est le jeton d'accent, pris à figures.py (miroir de assets/tokens.css)
    return dcc.Loading(enfant, type="circle", color=ACCENT, delay_show=250)


def alerte(titre_alerte, texte, variante="erreur", **kw):
    """Alerte : elle nomme une cause et la suite à faire. Pas de barre latérale colorée."""
    classe = "alerte-dc" + ("" if variante == "erreur" else " alerte-neutre")
    return html.Div([icone("alerte", 20),
                     html.Div([html.P(titre_alerte, className="titre"), html.P(texte)])],
                    className=classe, role="alert", **kw)


def erreur_donnees():
    return alerte("Données indisponibles",
                  "Les données ne sont pas disponibles pour le moment (connexion à la base). "
                  "Réessayez dans une minute ; si le problème persiste, consultez le journal du service.")


def vide(message, action=None, **kw):
    """Un vide dit pourquoi, et garde la hauteur du bloc qu'il remplace."""
    return html.Div([html.P(message)] + ([action] if action is not None else []), className="vide", **kw)


def page_404():
    return html.Div([html.H1("Page introuvable", className="titre-page"),
                     html.P("Cette adresse ne correspond à aucune page du tableau de bord."),
                     dcc.Link("Retour à la vue d'ensemble", href="/", className="btn-dc")],
                    className="bloc-404")
