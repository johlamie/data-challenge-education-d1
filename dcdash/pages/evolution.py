"""Page 5 : l'évolution dans le temps, pour comparer jusqu'à huit provinces ou régions.

L'écran répond à une question en français courant — « Le décrochage s'aggrave-t-il, et où ? » — et
dit ses codes visuels en toutes lettres plutôt que de les laisser à une légende : trait plein, tirets,
ligne grise, marqueur creux. Cette clé est dite dans la phrase « Lecture : » du premier graphique,
juste sous le tracé qu'elle décode, et non plus dans la ligne de périmètre : l'entête tient ainsi sur
une ligne et le premier graphique entre dans l'écran sans défilement (1440×900 et 1366×768).
Chaque graphique porte sa phrase « Lecture : ».

Identité des séries : à partir de 1024 px chaque courbe est nommée au bout de son tracé ; en dessous,
les étiquettes ne tiennent pas et ce sont les pastilles nommées (`.legende-series`) qui prennent le
relais. Jamais la couleur seule.

Rien n'est calculé ici : la page compose les composants partagés et les séries renvoyées par `calculs`.
"""
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from .. import aides as A
from .. import figures as F
from ..calculs import ensemble_national, est_impute, source_imputation
from ..composants import (chargement, choix_decoupage, choix_indicateur, choix_sexe, contenu_lecture, entete_bloc,
                          erreur_donnees, filtre, libelle_source_lisible, segment, terme, titre, vide)
from ..db import donnees
from ..meta import DECOUPAGE_REGION, INDICATEURS, colonne_region, fmt_valeur, nom_propre
from ..vues import options_provinces

# définition retenue (décision de l'équipe) : abandon harmonisé ; moyenne sur 2 ans = contrôle de stabilité
ABANDON = [("taux_abandon_harmonise", "taux d'abandon", "solid"),
           ("taux_abandon_moyen_2ans", "moyenne sur 2 ans (contrôle)", "dash")]
MAX_ENTITES = 8
NIVEAUX = {"province": "Provinces", "region": "Régions"}
MOT_NIVEAU = {"province": ("province", "provinces"), "region": ("région", "régions")}
LIBELLES_LISTE = {"select_all": "Tout sélectionner", "deselect_all": "Tout désélectionner",
                  "selected_count": "{num_selected} choisies", "search": "Rechercher",
                  "clear_search": "Effacer la recherche", "clear_selection": "Tout retirer",
                  "no_options_found": "Aucun résultat"}

SOUS_TITRE = "Primaire, de 2017-2018 à 2024-2025."
# la clé des tracés, dite en toutes lettres là où elle sert : dans la phrase de lecture du premier
# graphique. Rien n'est perdu de l'ancienne ligne de périmètre (trait plein, tirets, ligne grise,
# marqueur creux), mais l'entête de page ne coûte plus deux lignes au premier tracé.
CLE_TRAITS = ("Le trait plein donne le taux d'abandon, les tirets sa moyenne sur deux ans (contrôle), "
              "la ligne grise la moyenne du pays, et un marqueur creux une valeur estimée.")
# le plafond de 8 entités est une règle de lisibilité, pas une limite technique : il est dit dans le libellé
# du champ, et rappelé sous le graphique si la sélection reçue en contenait davantage.
TROP_ENTITES = (f"{MAX_ENTITES} entités au maximum, pour que les courbes restent lisibles : seules les "
                f"{MAX_ENTITES} premières sont tracées.")
NOTE_CONTROLE = ("Un taux d'abandon négatif signifie que plus d'élèves sont arrivés (transferts, retours) que partis. "
                 "La moyenne sur 2 ans lisse ces effets : si les deux courbes divergent, l'année est à lire avec "
                 "prudence.")
NOTE_REGION = "Régions : flux sommés des provinces (abandon), moyennes pondérées (autres indicateurs)."

# titres d'axe : l'unité dite en toutes lettres, par unité de `meta.INDICATEURS` puis par exception
TITRES_Y = {"%": "% des élèves", "‰": "pour 1 000 habitants", "score (z)": "écart à la moyenne des provinces",
            "sur 100": "score sur 100", "probabilité": "probabilité", "pour 100 000": "pour 100 000 habitants",
            "élèves": "nombre d'élèves", "habitants": "nombre d'habitants"}
TITRES_Y_CLE = {"pct_ecoles_eau_potable": "% des écoles", "pct_ecoles_latrines": "% des écoles",
                "ratio_eleves_maitre": "élèves par enseignant", "tap": "% de la classe d'âge"}


def _champ_entites():
    """Multi-sélection des entités comparées. Le libellé est renseigné par un rappel (provinces ou régions)."""
    return filtre(html.Span("Provinces à comparer (8 au plus)", id="evo-lib-entites"),
                  dcc.Dropdown(id="evo-entites", multi=True, labels=LIBELLES_LISTE,
                               placeholder="Choisissez dans la liste"),
                  classe="filtre-entites")


def layout(**_):
    return html.Div([
        titre("Le décrochage s'aggrave-t-il, et où ?", sous=SOUS_TITRE),
        html.Div([
            filtre("Comparer", segment("evo-niveau", NIVEAUX, "province"), classe="filtre-niveau"),
            # libellés courts : le champ fait deux colonnes sur douze, et c'est le nombre de régions
            # qui distingue les deux découpages pour le lecteur
            filtre("Découpage des régions", choix_decoupage("evo-decoupage", courts=True),
                   classe="filtre-decoupage"),
            filtre("Élèves", choix_sexe("evo-sexe"), classe="filtre-sexe"),
            _champ_entites(),
            filtre("Second indicateur", choix_indicateur("evo-indic", "indice_v2",
                                                         exclure=("taux_abandon_harmonise", "taux_abandon_moyen_2ans",
                                                                  "taux_abandon_publie", "indice_v2_0_100")),
                   classe="filtre-indic"),
            # l'interrupteur est un réglage d'affichage comme les autres : il tient dans la rangée de
            # filtres (une seule ligne à partir de 1280 px) au lieu de prendre une ligne pour lui seul,
            # ce qui rendait le premier graphique invisible sans défiler sur un portable.
            html.Div(dbc.Checklist(id="evo-national", value=["nat"], switch=True,
                                   options=[{"label": "Afficher la moyenne du Burkina Faso", "value": "nat"}]),
                     className="interrupteur-national"),
        ], className="filtres-evolution"),
        html.Section([
            entete_bloc("Taux d'abandon, année par année", id_titre="evo-t1"),
            html.Div(chargement(dcc.Graph(id="evo-abandon", config=F.CONFIG, responsive=True,
                                          style={"height": "100%", "width": "100%"},
                                          figure=F.figure_vide("Chargement du graphique…", hauteur=None))),
                     className="graphique", role="img",
                     **{"aria-label": "Courbes du taux d'abandon, année par année, pour les entités choisies ; "
                                      "la phrase de lecture sous le graphique en donne la clé."}),
            html.Div(id="evo-legende1", className="legende-series"),
            html.Div(id="evo-lecture1", className="lecture"),
            html.Div(id="evo-note", className="note"),
        ], className="carte-bloc bloc-graphique", **{"aria-labelledby": "evo-t1"}),
        html.Section([
            entete_bloc("Second indicateur", id_titre="evo-titre2"),
            html.Div(chargement(dcc.Graph(id="evo-second", config=F.CONFIG, responsive=True,
                                          style={"height": "100%", "width": "100%"},
                                          figure=F.figure_vide("Chargement du graphique…", hauteur=None))),
                     className="graphique", role="img",
                     **{"aria-label": "Courbes du second indicateur choisi, année par année, pour les mêmes "
                                      "entités ; la phrase de lecture sous le graphique en donne la clé."}),
            html.Div(id="evo-legende2", className="legende-series"),
            html.Div(id="evo-lecture2", className="lecture"),
        ], className="carte-bloc bloc-graphique", **{"aria-labelledby": "evo-titre2"}),
    ], className="page-evolution")


def _defaut_provinces(d):
    p = d.province()
    p = p[(p["annee_debut"] == p["annee_debut"].max()) & (p["sexe"] == "T")].sort_values("rang_v2")
    return p["pcode_province"].head(3).tolist()


def _series(df, code_col, nom_col, codes, cle, couleurs, niveau):
    out = []
    for i, c in enumerate(codes):
        s = df[df[code_col] == c].sort_values("annee_debut")
        if s.empty:
            continue
        col = cle if niveau == "province" else colonne_region(cle)
        if col not in s.columns:
            continue
        if niveau == "province":
            imp = est_impute(s, cle).tolist()
            src = source_imputation(s, cle).map(libelle_source_lisible).tolist()
        else:
            fr = INDICATEURS[cle].get("flag_region")
            imp = (s[fr].fillna(0) > 0).tolist() if fr and fr in s.columns else [False] * len(s)
            src = [f"{int(n)} province(s) imputée(s)" if fr and n == n and n > 0 else ""
                   for n in (s[fr] if fr and fr in s.columns else [0] * len(s))]
        out.append(dict(nom=nom_propre(s[nom_col].iloc[0]), x=s["annee_debut"].tolist(), y=s[col].astype(float).tolist(),
                        couleur=couleurs[i % len(couleurs)], imputes=imp, sources=src))
    return out


def _nom_court(libelle):
    """Nom de l'entité sans sa parenthèse de contexte : « Province 38 (Région L) » → « Province 38 ».
    Le libellé entier reste lisible dans l'attribut `title` de la pastille — rien n'est perdu."""
    return libelle.rsplit(" (", 1)[0] if libelle.endswith(")") and " (" in libelle else libelle


def _pastilles(options, codes, national=False):
    """Légende en pastilles nommées : elle prend le relais des étiquettes de bout de courbe sous 1024 px.
    Les couleurs suivent l'ordre de la sélection, exactement comme les séries tracées."""
    noms = {o["value"]: o["label"] for o in (options or [])}
    chips = []
    for i, code in enumerate(codes):
        lib = noms.get(code, code)
        chips.append(html.Span([html.I(className=f"pastille serie-{i % 8 + 1}", **{"aria-hidden": "true"}),
                                _nom_court(lib)], title=lib))
    if national:
        chips.append(html.Span([html.I(className="pastille serie-nat", **{"aria-hidden": "true"}),
                                "Burkina Faso (moyenne)"]))
    return chips


def _aide_indicateur(cle):
    try:
        return A.indicateur(cle)
    except KeyError:
        return None


def register(app):
    @app.callback(Output("evo-entites", "options"), Output("evo-entites", "value"), Output("evo-decoupage", "disabled"),
                  Input("evo-niveau", "value"), Input("evo-decoupage", "value"))
    def entites(niveau, decoupage):
        try:
            d = donnees()
            if niveau == "province":
                return options_provinces(d), _defaut_provinces(d), True
            r = d.region()
            r = r[r["decoupage"] == DECOUPAGE_REGION[decoupage]][["pcode_region", "region"]].drop_duplicates()
            r = r.sort_values("region")
            opts = [{"label": nom_propre(x.region), "value": x.pcode_region} for x in r.itertuples()]
            return opts, [o["value"] for o in opts[:3]], False
        except Exception:
            return [], [], False

    @app.callback(Output("evo-abandon", "figure"), Output("evo-second", "figure"), Output("evo-titre2", "children"),
                  Output("evo-note", "children"), Output("evo-lecture1", "children"),
                  Input("evo-niveau", "value"), Input("evo-decoupage", "value"), Input("evo-sexe", "value"),
                  Input("evo-entites", "value"), Input("evo-indic", "value"), Input("evo-national", "value"))
    def maj(niveau, decoupage, sexe, codes, cle, nat):
        m = INDICATEURS[cle]
        t2 = f"Second indicateur : {m['label']}"
        try:
            d = donnees()
            d.get()
        except Exception:
            v = F.figure_vide("Données indisponibles", hauteur=None)
            return v, v, t2, erreur_donnees(), ""
        recues = len(codes or [])
        codes = (codes or [])[:MAX_ENTITES]
        if niveau == "province":
            df = d.province()
            df = df[df["sexe"] == sexe]
            code_col, nom_col = "pcode_province", "province"
        else:
            df = d.region()
            df = df[(df["sexe"] == sexe) & (df["decoupage"] == DECOUPAGE_REGION[decoupage])]
            code_col, nom_col = "pcode_region", "region"
        series = []
        for j, (col, lib, tiret) in enumerate(ABANDON):
            for s in _series(df, code_col, nom_col, codes, col, F.OKABE_ITO, niveau):
                # la courbe de contrôle partage la couleur de son entité, et elle seule porte le mot
                # « contrôle » : au bout du tracé comme dans la légende, c'est le nom de l'entité qui
                # est lu une seule fois, le trait en tirets disant déjà ce qu'est la seconde courbe
                s.update(groupe=s["nom"], tiret=tiret, epaisseur=2.6 if j == 0 else 1.8,
                         etiquette=j == 0, legende=j == 0)
                if j:
                    s["nom"] = f"{s['nom']} · {lib}"
                series.append(s)
        n = None
        if nat and "nat" in nat:
            n = ensemble_national(d.region(), sexe)
            series.append(dict(nom="Burkina Faso", x=n.index.tolist(), y=n.tolist(), couleur=F.SERIE_NATIONALE,
                               tiret="solid", epaisseur=3.5, groupe="national"))
        un, des = MOT_NIVEAU.get(niveau, MOT_NIVEAU["province"])
        invite = vide(f"Choisissez au moins une {un} à comparer, "
                      f"dans le champ « {des.capitalize()} à comparer » ci-dessus.")
        if not codes and not series:
            # rien à montrer du tout : un vide dit pourquoi et garde la hauteur du bloc (CSS)
            v = F.figure_vide("", hauteur=None)
            return v, v, t2, "", invite
        if not codes:
            # sans sélection mais avec la moyenne du pays, la courbe nationale se trace seule :
            # c'est la lecture que l'écran sait encore donner, et l'invitation reste sous le tracé
            f1 = F.evolution(series, "% des élèves (CP1 à CM1)", hauteur=None, etiquettes_fin=True)
            f2 = F.figure_vide(f"{m['label']} : choisissez au moins une {un} à comparer.", hauteur=None)
            l1 = ["seule la moyenne du Burkina Faso est tracée. Ajoutez une " + un +
                  " dans le champ ci-dessus pour la comparer au pays."]
            l1 += _fin_nationale(n)
            return f1, f2, t2, NOTE_CONTROLE, contenu_lecture(l1)
        f1 = F.evolution(series, "% des élèves (CP1 à CM1)", hauteur=None, etiquettes_fin=True)
        s2 = _series(df, code_col, nom_col, codes, cle, F.OKABE_ITO, niveau)
        f2 = (F.evolution(s2, _titre_y(cle, m), hauteur=None, etiquettes_fin=True,
                          fmt=".2f" if m["fmt"] in (".2f", ".0%") else ".1f")
              if s2 else F.figure_vide(f"{m['label']} : pas de série disponible pour des {des}.", hauteur=None))
        if cle == "proba_risque_t1":
            f2.update_yaxes(tickformat=".0%", range=[0, 1])
        note = NOTE_CONTROLE + (" " + NOTE_REGION if niveau == "region" else "")
        if recues > MAX_ENTITES:
            note = TROP_ENTITES + " " + note
        l1 = ["une courbe au-dessus de la grise signale plus d'abandon que la moyenne du pays. " + CLE_TRAITS]
        l1 += _fin_nationale(n)
        return f1, f2, t2, note, contenu_lecture(l1)

    @app.callback(Output("evo-lib-entites", "children"), Output("evo-legende1", "children"),
                  Output("evo-legende2", "children"), Output("evo-lecture2", "children"),
                  Input("evo-niveau", "value"), Input("evo-entites", "options"), Input("evo-entites", "value"),
                  Input("evo-national", "value"), Input("evo-indic", "value"))
    def reperes(niveau, options, codes, nat, cle):
        """Repères de lecture de la sélection en cours : libellé du champ, pastilles nommées et phrase de
        lecture du second graphique. Aucune donnée n'est lue ici, seulement la sélection."""
        un, des = MOT_NIVEAU.get(niveau, MOT_NIVEAU["province"])
        recues = len(codes or [])
        codes = (codes or [])[:MAX_ENTITES]
        lib = f"{des.capitalize()} à comparer ({MAX_ENTITES} au plus)"
        if recues > MAX_ENTITES:
            # le champ annonce « 14 choisies » : le plafond doit se lire là, pas seulement sous le tracé
            lib = [lib, html.Span(f"{recues} choisies, {MAX_ENTITES} tracées", className="filtre-avis")]
        national = bool(nat and "nat" in nat)
        if not codes:
            return (lib, _pastilles([], [], national=national), [],
                    vide(f"Choisissez au moins une {un} à comparer."))
        m, texte_aide = INDICATEURS[cle], _aide_indicateur(cle)
        nom = terme(m["label"], texte_aide) if texte_aide else m["label"]
        sens = {1: " ; une courbe qui monte va dans le sens d'un risque plus fort.",
                -1: " ; une courbe qui monte va dans le sens d'une situation plus favorable.",
                0: " ; cet indicateur donne le contexte, il n'est ni bon ni mauvais en soi."}[m["sens"]]
        return (lib, _pastilles(options, codes, national=national), _pastilles(options, codes),
                contenu_lecture(["chaque courbe suit une ", un, " pour ", nom, sens,
                                 " Un marqueur creux signale une valeur estimée."]))


def _fin_nationale(n):
    """Dernière valeur du pays, dite en toutes lettres sous le graphique. Liste vide s'il n'y a pas
    de courbe nationale : aucune valeur n'est inventée."""
    if n is None or not len(n.dropna()):
        return []
    nn = n.dropna()
    return [f" Burkina Faso en {int(nn.index[-1])}-{int(nn.index[-1]) + 1} : "
            f"{fmt_valeur(nn.iloc[-1], 'taux_abandon_harmonise')}."]


def _titre_y(cle, m):
    """Titre d'axe : l'unité en toutes lettres (« % des écoles »), pas un nom de colonne. Le titre du
    bloc nomme déjà l'indicateur ; l'axe dit de quoi on compte des pour cent."""
    return TITRES_Y_CLE.get(cle) or TITRES_Y.get(m["unite"]) or m["label"]
