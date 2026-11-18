"""Page 4 : fiche province — une province, son niveau de risque et ce qui l'explique.

Le haut de la page est UN seul cadre, UNE seule rangée : ni marge ni répétition superflues.
À gauche les trois sélecteurs, une ligne d'identité — le nom de la province n'y
est jamais redit, il est déjà dans le sélecteur — puis les quatre chiffres clés en une rangée.
Tout à droite, petite, la carte de localisation exigée par l'utilisateur : la province choisie en
bleu foncé, toutes les provinces de sa région en bleu clair avec le contour de la région en bleu
(2 px), le reste du pays en gris. Le nom s'affiche au survol, un clic ouvre la fiche cliquée.

Cette carte n'a plus de légende : le nom de la région, écrit dans le bleu de son contour sur la
carte, porte la correspondance, et la seule phrase conservée dit ce qu'un clic fait. Le titre de
la page ne coûte plus aucune hauteur — il reste dans le document pour les lecteurs d'écran et pour
la hiérarchie des titres, masqué visuellement : l'onglet actif de la barre de navigation le dit
déjà à l'écran.

En dessous, dans l'ordre de lecture : ce qui pèse sur le score de risque, l'insécurité année par
année, les indicateurs comparés aux 45 provinces, puis — sur toute la largeur — ce qui est estimé
plutôt que mesuré.

Aucun marqueur « i » sur cette page : un chiffre clé qui demande une explication porte un
soulignement pointillé et ouvre l'infobulle au survol, au clavier et au toucher. Le budget de 3 à
5 icônes du site entier est déjà pris par la vue d'ensemble et le classement.
"""
import dash
from dash import Input, Output, dcc, html

from .. import aides as A
from .. import figures as F
from ..calculs import contributions, est_impute, rangs, source_imputation
from ..composants import (alerte, asterisque, badge_statut, bloc, chargement, choix_annee, choix_sexe, erreur_donnees,
                          filtre, kpi, kpi_squelette, lecture, libelle_source_lisible, note, squelette, terme, titre)
from ..db import donnees
from ..meta import (COMPOSANTES, INDICATEURS, SEUIL_ALERTE, SEXES, annee_scolaire, fmt_nombre, fmt_valeur,
                    libelle_type_proba, nom_propre)
from ..vues import geoms_provinces, geoms_regions, options_provinces

INDICS_FICHE = ["taux_abandon_harmonise", "taux_abandon_moyen_2ans", "taux_abandon_publie", "taux_redoublement",
                "taux_promotion", "tap", "ratio_eleves_maitre", "pct_ecoles_eau_potable", "pct_ecoles_latrines",
                "pdi_pour_1000_hab", "acled_evenements_pour_100k", "acled_victimes_pour_100k", "effectif_eleves",
                "population_totale"]
DRAPEAUX = {"ok": "aucun", "entrees_nettes": "entrées nettes (abandon négatif)", "valeur_extreme": "valeur extrême",
            "base_effectifs_imputee": "base d'effectifs imputée",
            "effectif_base_<1000": "effectif de base inférieur à 1 000"}
# les quatre chiffres clés, dans l'ordre : ce sont aussi les libellés des squelettes de chargement
LIBELLES_KPI = ["Score de risque", "Solidité du classement", "Risque l'an prochain", "Fiabilité de l'indice"]
SOUS_TITRE = ("Niveau de risque, ce qui l'explique, insécurité et indicateurs comparés aux autres provinces.")
# La seule phrase sous la carte : ce qu'un clic fait. La légende à trois clés a été retirée —
# dans un panneau de 272 px elle pesait plus que la carte, et la correspondance est
# désormais portée par le nom de la région, écrit dans le bleu de son contour (assets/page-fiche.css).
NOTE_CARTE = "Cliquez sur une province pour ouvrir sa fiche."
# ce que la carte montre, pour qui ne la voit pas : l'étiquette du groupe, la légende en toutes lettres
AIDE_CARTE = ("Carte de localisation : la province choisie en bleu foncé, les autres provinces de sa région en "
              "bleu clair avec le contour de la région en bleu, le reste du pays en gris. Cliquez sur une "
              "province pour ouvrir sa fiche.")
# le jargon est dit en toutes lettres la première fois qu'il paraît sur la page
NOTE_INSECURITE = ("PDI : personnes déplacées internes, comptées pour 1 000 habitants. ACLED : base publique "
                   "d'incidents violents, comptés pour 100 000 habitants. Marqueurs creux : valeur estimée.")
NOTE_TABLE = ("Rang parmi les 45 provinces, 1 = la situation la plus défavorable. Bande hachurée au bord de la "
              "cellule et * : valeur estimée, sa source s'affiche au survol de *. Colonne « Estimation » : d'où "
              "vient la valeur quand elle n'a pas pu être mesurée, « — » quand elle est mesurée. Survolez le nom "
              "d'un indicateur pour sa définition.")
POIDS = ("Poids : abandon 30 %, déplacés 20 %, redoublement 15 %, élèves par maître 15 %, eau 10 %, "
         "latrines 10 % (détail dans Méthode).")


def layout(pcode=None, annee=None, sexe=None, **_):
    try:
        opts = options_provinces(donnees())
    except Exception:
        opts = []
    defaut = pcode if pcode and any(o["value"] == pcode for o in opts) else _plus_a_risque(opts)
    try:
        annee = int(annee) if annee else 2024
    except ValueError:
        annee = 2024
    sexe = sexe if sexe in SEXES else "T"
    filtres = html.Div([
        filtre("Province", dcc.Dropdown(id="fic-province", options=opts, value=defaut, clearable=False),
               classe="filtre-province"),
        filtre("Année scolaire", choix_annee("fic-annee", annee)),
        filtre("Élèves", choix_sexe("fic-sexe", sexe)),
    ], className="filtres-fiche")
    return html.Div([
        # le titre de la page ne coûte aucune hauteur : il reste dans le document (hiérarchie des
        # titres, lecteurs d'écran), l'onglet actif de la barre de navigation le dit à l'écran
        html.Div(titre("Fiche province", sous=SOUS_TITRE), className="visuellement-cache"),
        html.Section(html.Div([
            html.Div([filtres, chargement(html.Div(_entete_squelette(), id="fic-entete"))],
                     className="fiche-pilote"),
            html.Div([
                # le tracé vit dans une boîte au format du pays : ni bande vide ni pays écrasé
                html.Div(dcc.Graph(id="fic-carte", config=F.CONFIG_CARTE, responsive=True,
                                   style={"height": "100%", "width": "100%"},
                                   figure=F.figure_vide("Chargement de la carte…", hauteur=None)),
                         # un groupe, pas une image : la carte se survole et se clique, et
                         # `role="img"` rendrait ses enfants invisibles aux technologies d'assistance
                         className="fiche-carte", role="group", **{"aria-label": AIDE_CARTE}),
                html.P(NOTE_CARTE, id="fic-lecture-carte", className="note"),
            ], className="fiche-locali"),
        ], className="fiche-bandeau"), className="carte-bloc fiche-cadre"),
        chargement(html.Div(id="fic-contenu")),
    ], className="page-fiche")


def _entete_squelette():
    """Hauteurs réelles dès le premier rendu : la page ne saute pas quand le callback revient."""
    return [html.P(squelette("squelette-ligne"), className="fiche-identite note"),
            html.Div([kpi_squelette(lib) for lib in LIBELLES_KPI], className="fiche-kpis")]


def _plus_a_risque(opts):
    """Par défaut, la fiche s'ouvre sur la province la plus à risque de la dernière année (ensemble)."""
    try:
        P = donnees().province()
        p = P[(P["annee_debut"] == P["annee_debut"].max()) & (P["sexe"] == "T")].sort_values("rang_v2")
        return p["pcode_province"].iloc[0]
    except Exception:
        return opts[0]["value"] if opts else None


# ---------------------------------------------------------------- identité et chiffres clés
def _identite(r, pcode):
    """L'identité de la province en UNE ligne, sous les sélecteurs.

    Le nom de la province n'y est pas redit : le sélecteur l'affiche déjà, et le voir deux fois
    (« Soum (Sahel) » puis « Soum » avec ses codes) n'apportait rien. Reste ce que
    le sélecteur ne dit pas : la région — écrite dans le bleu de son contour sur la carte —, les
    codes administratifs, et le découpage de 2025 replié dans une infobulle plutôt qu'étalé sur
    une seconde ligne. Rien n'est perdu : le découpage s'ouvre au survol, au clavier et au toucher,
    et une province scindée le dit en clair dans le mot souligné.
    """
    decoupage = (f"Découpage 2025 : {r['provinces_2025']}, région {nom_propre(r['region_2025'])} "
                 f"({r['pcode_region_2025']}).")
    scindee = r["scission_2025"] == 1
    if scindee:
        decoupage += " Scindée en 2025 : les valeurs affichées restent celles de la province entière."
    return html.P([
        "Région ", html.Span(nom_propre(r["region"]), className="nom-region"),
        f" ({r['pcode_region']}) · code {pcode} · ",
        terme("scindée en 2025" if scindee else "découpage 2025", decoupage),
    ], className="fiche-identite note")


def _chiffres_cles(r, pt, sexe):
    """Quatre chiffres clés en 2×2, dans une seule surface divisée par des filets de 1 px.

    Les quatre libellés ouvrent une infobulle au survol (soulignement pointillé, jamais d'icône) :
    aucun des quatre ne se comprend seul pour un lecteur non initié."""
    ensemble = "" if sexe == "T" else " · calculé pour l'ensemble des élèves"
    rang = r["rang_v2"]
    rang_txt = "n.d." if rang != rang else f"{int(rang)} / 45"
    # solidité du classement : la part des variantes de calcul qui gardent la province dans le top 10
    freq = pt["freq_top10_mc"]
    fourchette = ("" if pt["rang_p05_mc"] != pt["rang_p05_mc"]
                  else f" (rang entre {int(round(pt['rang_p05_mc']))} et {int(round(pt['rang_p95_mc']))})")
    solidite = ("classement non simulé pour cette sélection" if freq != freq
                else f"dans les 10 plus à risque pour {round(100 * freq)} % des variantes")
    # risque l'an prochain
    proba = pt["proba_risque_t1"]
    obs = pt["risque_t1_observe"]
    contexte_proba = (f"rang {int(pt['rang_risque_t1'])} / 45 · " if pt["rang_risque_t1"] == pt["rang_risque_t1"]
                      else "")
    contexte_proba += libelle_type_proba(pt["type_proba_t1"]) or "non calculée pour cette année"
    if obs == obs:
        contexte_proba += (" · observé l'année suivante : dans le quart supérieur" if obs >= 0.5
                           else " · observé l'année suivante : hors du quart supérieur")
    # fiabilité de l'indice
    faible = str(r["fiabilite_indice"]).startswith("faible")
    nb_imp = int(r["nb_composantes_imputees"] or 0)
    contexte_fiab = r["fiabilite_indice"] if faible else _composantes_estimees(nb_imp)
    return html.Div([
        kpi("Score de risque", f"{fmt_nombre(r['indice_v2_0_100'], 0)} / 100",
            f"rang {rang_txt} (1 = la plus à risque) · indice {fmt_valeur(r['indice_v2'], 'indice_v2')}",
            critique=rang == rang and rang <= 10, aide_kpi=A.indicateur("indice_v2_0_100")),
        # badge sans bulle native : la cellule ouvre déjà l'infobulle du produit, et le mot n'est pas un chiffre
        kpi("Solidité du classement", badge_statut(pt["statut_top10_mc"], titre=False),
            solidite + fourchette + ensemble, aide_kpi=A.SOLIDITE, petit=True),
        kpi("Risque l'an prochain", fmt_valeur(proba, "proba_risque_t1"), contexte_proba + ensemble,
            critique=proba == proba and proba >= SEUIL_ALERTE, aide_kpi=A.indicateur("proba_risque_t1")),
        # la valeur est un mot, pas un chiffre : elle prend la variante basse de l'échelle (mock .kpi-val.petit)
        kpi("Fiabilité de l'indice", "faible" if faible else "correcte", contexte_fiab, critique=faible,
            aide_kpi=A.FIABILITE, id_="fic-kpi-fiabilite", petit=True),
    ], className="fiche-kpis")


def _composantes_estimees(n):
    """Accord en nombre : « aucune composante estimée », « 1 composante estimée », « 3 composantes estimées »."""
    if n <= 0:
        return "aucune des 6 composantes n'est estimée"
    return f"{n} composante{'s' if n > 1 else ''} estimée{'s' if n > 1 else ''} sur 6"


# ---------------------------------------------------------------- indicateurs et rangs
def _ligne_indicateur(p, r, cle, n_prov):
    m = INDICATEURS[cle]
    imp = bool(est_impute(r.to_frame().T, cle).iloc[0]) if m.get("flag") else False
    src = libelle_source_lisible(source_imputation(r.to_frame().T, cle).iloc[0]) if imp else ""
    rg = rangs(p, cle, m["sens"] if m["sens"] != 0 else 1)
    rang = rg.loc[r.name] if r.name in rg.index else None
    med = p[cle].median()
    sens = {1: "1 = valeur la plus élevée (plus de risque)", -1: "1 = valeur la plus faible (plus de risque)",
            0: "1 = valeur la plus élevée"}[m["sens"]]
    return html.Tr([
        html.Td(terme(m["label"], A.indicateur(cle)), className="col-indic"),
        # la valeur reste lisible sous la hachure : c'est le fond du bloc qui est texturé, pas l'encre
        html.Td([fmt_valeur(r[cle], cle), asterisque(src) if imp else None],
                className="col-num" + (" impute" if imp else "")),
        html.Td(f"{int(rang)} / {n_prov}" if rang == rang and rang is not None else "n.d.", title=sens,
                className="col-num"),
        html.Td(fmt_valeur(med, cle), className="col-num"),
        html.Td(src or "—", className="col-source"),
    ])


def _table_indicateurs(p, r, n_prov):
    entete = html.Thead(html.Tr([
        html.Th("Indicateur"), html.Th("Valeur", className="col-num"), html.Th("Rang", className="col-num"),
        html.Th(f"Médiane des {n_prov} provinces", className="col-num"), html.Th("Estimation")]))
    lignes = [_ligne_indicateur(p, r, k, n_prov) for k in INDICS_FICHE]
    return html.Div(html.Table([entete, html.Tbody(lignes)], className="table-dc table-fiche"),
                    className="zone-table")


# ---------------------------------------------------------------- phrases de lecture
def _lecture_contributions(noms, vals):
    v = [(n, x) for n, x in zip(noms, vals) if x == x]
    if not v:
        return "contributions non disponibles pour cette sélection."
    hausse = max(v, key=lambda t: t[1])
    baisse = min(v, key=lambda t: t[1])
    txt = (f"le facteur qui pousse le plus le score vers le haut est « {hausse[0].lower()} » "
           f"({_signe(hausse[1])})") if hausse[1] > 0 else "aucun facteur n'est au-dessus de la moyenne des provinces"
    if baisse[1] < 0:
        nb = len([x for _, x in v if x < 0])
        seul = "le seul qui le fait baisser est" if nb == 1 else "celui qui le fait le plus baisser est"
        txt += f", {seul} « {baisse[0].lower()} » ({_signe(baisse[1])})"
    return txt + ". " + POIDS


def _signe(v, dec=2):
    """Valeur signée à la française : virgule décimale et vrai signe moins (−), jamais un trait d'union."""
    if v is None or v != v:
        return "n.d."
    return format(float(v), f"+.{dec}f").replace(".", ",").replace("-", "−")


def _points(s, cle):
    return [(a, v) for a, v in zip(s["annee_debut"], s[cle]) if v == v]


def _lecture_insecurite(s):
    """Dit en français courant ce que les deux courbes montrent, à partir des valeurs réellement tracées."""
    morceaux, bornes = [], None
    for cle, mot, unite in [("pdi_pour_1000_hab", "les personnes déplacées", "pour 1 000 habitants"),
                            ("acled_evenements_pour_100k", "les incidents violents", "pour 100 000 habitants")]:
        pts = _points(s, cle)
        if len(pts) < 2:
            continue
        (a0, v0), (a1, v1) = pts[0], pts[-1]
        bornes = bornes or (a0, a1)
        if abs(v1 - v0) < 0.05:
            morceaux.append(f"{mot} restent autour de {fmt_nombre(v1, 1)} {unite}")
        else:
            morceaux.append(f"{mot} passent de {fmt_nombre(v0, 1)} à {fmt_nombre(v1, 1)} {unite}")
    if not morceaux:
        return "les relevés d'insécurité ne sont pas disponibles pour cette province."
    txt = f"entre {annee_scolaire(bornes[0])} et {annee_scolaire(bornes[1])}, " + " et ".join(morceaux) + "."
    # chaque série dit ce qui la concerne : le relevé CONASUR prolongé explique les points estimés des
    # personnes déplacées, jamais ceux des incidents violents, qui viennent d'une autre source
    n_pdi = int(est_impute(s, "pdi_pour_1000_hab").sum())
    n_acled = int(est_impute(s, "acled_evenements_pour_100k").sum())
    if n_pdi:
        txt += (f" {_points_estimes(n_pdi, 'des personnes déplacées')} (marqueurs creux) : après le 31/03/2023, "
                "le dernier relevé CONASUR est prolongé.")
    if n_acled:
        txt += f" {_points_estimes(n_acled, 'des incidents violents')} (marqueurs creux), faute de relevé publié."
    return txt


def _points_estimes(n, quoi):
    """Accord en nombre : « 1 point de la courbe … est estimé », « 3 points … sont estimés »."""
    if n > 1:
        return f"{n} points de la courbe {quoi} sont estimés"
    return f"1 point de la courbe {quoi} est estimé"


# ---------------------------------------------------------------- contenu de la page
def contenu(d, pcode, annee, sexe):
    P = d.province()
    p = P[(P["annee_debut"] == annee) & (P["sexe"] == sexe)].set_index("pcode_province")
    if pcode not in p.index:
        return alerte("Province introuvable.",
                      "Cette province n'a pas de ligne pour l'année scolaire et le groupe d'élèves choisis. "
                      "Choisissez-en une autre dans la liste.", variante="neutre")
    r = p.loc[pcode]
    pt = P[(P["annee_debut"] == annee) & (P["sexe"] == "T")].set_index("pcode_province").loc[pcode]
    entete = [_identite(r, pcode), _chiffres_cles(r, pt, sexe)]

    # ---- ce qui pèse sur le score de risque
    cc = contributions(p.reset_index()).loc[pcode]
    noms_c = [lib for _, _, _, lib in COMPOSANTES]
    vals_c = [cc[col] for col, _, _, _ in COMPOSANTES]
    fig_c = F.barres_contributions(noms_c, vals_c, cc["total"], hauteur=None)
    note_c = (f"Indice = {_signe(cc['total'])} (somme des contributions). Rouge : le facteur rend la province plus "
              "à risque que la moyenne · bleu : moins à risque. Le trait vertical marque le zéro.")
    ecart = abs(cc["total"] - r["indice_v2"]) if r["indice_v2"] == r["indice_v2"] else 0
    if ecart > 1e-6:
        note_c += f" (écart de recalcul {ecart:.1e})"

    # ---- insécurité
    s = P[(P["pcode_province"] == pcode) & (P["sexe"] == "T")].sort_values("annee_debut")
    fig_i = F.evolution([
        dict(nom="Incidents violents (ACLED) pour 100 000 hab.", x=s["annee_debut"].tolist(),
             y=s["acled_evenements_pour_100k"].tolist(), couleur=F.SERIE_ACLED,
             imputes=est_impute(s, "acled_evenements_pour_100k").tolist(),
             sources=source_imputation(s, "acled_evenements_pour_100k").map(libelle_source_lisible).tolist()),
        dict(nom="Déplacés (PDI) pour 1 000 hab.", x=s["annee_debut"].tolist(),
             y=s["pdi_pour_1000_hab"].tolist(), couleur=F.SERIE_PDI, tiret="dash",
             imputes=est_impute(s, "pdi_pour_1000_hab").tolist(),
             sources=source_imputation(s, "pdi_pour_1000_hab").map(libelle_source_lisible).tolist()),
        # pas de titre d'axe : les deux unités sont dans le nom de chaque courbe, dans la légende et
        # dans la note du bloc. Un titre qui les répétait toutes les deux ne tenait pas dans la marge.
    ], "", hauteur=None)

    # ---- qualité des données, en toutes lettres
    imps = []
    for lib, f, so in [("Taux d'abandon", "abandon_impute", "source_imputation_abandon"),
                       ("Effectifs d'élèves", "effectif_historique_impute", "source_imputation_effectifs"),
                       ("Déplacés (PDI)", "pdi_impute", "source_imputation_pdi"),
                       ("Population", "pop_impute", "source_imputation_population"),
                       ("Chiffres clés", "chiffres_cles_impute", "source_imputation_chiffres_cles_equipement"),
                       ("Équipement des écoles", "equipement_impute", "source_imputation_chiffres_cles_equipement")]:
        if (r[f] or 0) > 0:
            imps.append(html.Li([html.B(lib + " : "), libelle_source_lisible(r[so]) or "source non précisée"]))
    # deux volets de lecture, parce que le bloc occupe maintenant toute la largeur : les
    # signalements d'un côté, la liste des valeurs estimées de l'autre
    signalements = [html.P([html.B("Signalement sur le taux d'abandon : "),
                            DRAPEAUX.get(r["drapeau_abandon"], r["drapeau_abandon"])]),
                    html.P([html.B("Classes où l'abandon calculé est nul : "),
                            fmt_nombre(int(r["nb_niveaux_abandon_zero"] or 0))])]
    if (r["contient_valeur_douteuse"] or 0) > 0:
        signalements.append(html.P("Au moins une valeur douteuse est signalée dans les données de cette province."))
    estimees = [html.P(html.B(f"Valeurs estimées ({annee_scolaire(annee)}, {SEXES[sexe].lower()}) :"),
                       className="titre-liste"),
                html.Ul(imps, className="liste-qualite") if imps
                else note("Aucune : toutes les valeurs affichées pour cette sélection sont mesurées.")]
    qual = [html.Div(signalements, className="qualite-volet"), html.Div(estimees, className="qualite-volet")]
    if r["scission_2025"] == 1:
        qual.append(alerte("Découpage de 2025",
                           f"{r['provinces_2025']} portent la valeur de "
                           f"{nom_propre(r['nom_officiel_province_ancienne'] or r['province'])}, non répartie entre "
                           "les nouvelles provinces.", variante="neutre"))

    corps = html.Div([
        html.Div([
            bloc("Ce qui pèse sur le score de risque",
                 note(note_c),
                 # les pistes se dimensionnent sur leurs six lignes : la figure porte sa hauteur
                 html.Div(dcc.Graph(figure=fig_c, config=F.CONFIG, responsive=True, style={"width": "100%"}),
                          className="zone-barres", role="img",
                          **{"aria-label": "Barres de contribution : ce que chaque facteur ajoute ou retire au "
                                           "score de risque de la province. Les valeurs sont dites dans la phrase "
                                           "de lecture sous le graphique."}),
                 lecture(_lecture_contributions(noms_c, vals_c))),
            bloc("Insécurité",
                 note(NOTE_INSECURITE),
                 html.Div(dcc.Graph(figure=fig_i, config=F.CONFIG, responsive=True,
                                    style={"height": "100%", "width": "100%"}), className="zone-courbes", role="img",
                          **{"aria-label": "Courbes d'insécurité, année par année : incidents violents pour "
                                           "100 000 habitants et personnes déplacées pour 1 000 habitants. "
                                           "La phrase de lecture sous le graphique en donne les valeurs."}),
                 lecture(_lecture_insecurite(s))),
        ], className="fiche-graphiques"),
        html.Div([
            bloc(f"Indicateurs et rangs ({annee_scolaire(annee)}, {SEXES[sexe].lower()})",
                 _table_indicateurs(p, r, len(p)), note(NOTE_TABLE)),
            bloc("Qualité des données", html.Div(qual, className="bloc-qualite")),
        ], className="fiche-bas"),
    ])
    return entete, corps


def carte_fiche(d, pcode):
    """Carte de localisation : la province choisie en bleu foncé, toutes les provinces de sa région en bleu clair
    (contour de la région en bleu, 2 px), le reste du pays en gris. Le nom s'affiche au survol ; un clic ouvre la
    fiche de la province."""
    g = geoms_provinces(d, "ancien_45")
    survols = {c: f"<b>{nom_propre(n)}</b>" + ("" if c == pcode else "<br><i>Cliquer pour ouvrir sa fiche</i>")
               for c, n in zip(g["code"], g["nom"])}
    return F.carte_localisation(g, pcode, geoms_regions(d, "ancien_45"), hauteur=None, survols=survols)


def register(app):
    @app.callback(Output("fic-entete", "children"), Output("fic-contenu", "children"), Output("fic-carte", "figure"),
                  Output("fic-lecture-carte", "children"),
                  Input("fic-province", "value"), Input("fic-annee", "value"), Input("fic-sexe", "value"))
    def maj(pcode, annee, sexe):
        try:
            d = donnees()
            d.get()
        except Exception:
            e = erreur_donnees()
            return e, None, F.figure_vide("Données indisponibles", hauteur=None), ""
        if not pcode:
            return (alerte("Aucune province choisie.", "Choisissez une province dans la liste ci-dessus pour voir "
                           "sa fiche.", variante="neutre"), None,
                    F.figure_vide("Choisissez une province", hauteur=None), "")
        r = contenu(d, pcode, annee, sexe)
        if not isinstance(r, tuple):
            return r, None, F.figure_vide("Province introuvable", hauteur=None), ""
        entete, corps = r
        return entete, corps, carte_fiche(d, pcode), NOTE_CARTE

    @app.callback(Output("fic-province", "value"), Input("fic-carte", "clickData"), prevent_initial_call=True)
    def clic_carte(clic):
        try:
            courbe = int(clic["points"][0]["curveNumber"])
            codes = geoms_provinces(donnees(), "ancien_45")["code"].tolist()  # même ordre que les tracés de la carte
        except Exception:
            return dash.no_update
        return codes[courbe] if 0 <= courbe < len(codes) else dash.no_update
