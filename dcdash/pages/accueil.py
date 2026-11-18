"""Page 1 : vue d'ensemble pour les décideurs (tient sur un écran d'ordinateur, sans défilement).

L'écran s'ouvre sur une question en français courant et y répond tout de suite : six chiffres
nationaux, les dix provinces à ouvrir en priorité à gauche, la géographie à droite. La barre de score
d'une province reprend exactement la couleur qu'elle a sur la carte — c'est le moment signature de
l'écran. Chaque panneau porte une phrase « Lecture : ».

Le classement complet des 45 (ou 47) provinces et son export CSV sont sur /classement.
Aides : infobulle au survol des chiffres clés qui en ont besoin, sans icône ; icône « i » seulement
sur le score, la solidité du classement et la légende de la carte.
"""
from plotly.colors import sample_colorscale
from dash import Input, Output, dcc, html

from .. import aides as A
from .. import figures as F
from ..calculs import kpis_decideurs
from ..composants import (aide, alerte, avec_aide, badge_statut, bande_kpi, chip_stale, choix_annee, choix_sexe,
                          cles_legende, contenu_lecture, entete_bloc, erreur_donnees, filtre, kpi, kpi_squelette,
                          legende_carte, lien_discret, segment, squelette, tendance, ticks_echelle, titre, vide)
from ..db import donnees
from ..meta import SEUIL_ALERTE, SEXES, annee_scolaire, fmt_nombre, fmt_valeur, nom_propre
from ..vues import disponible, geoms_provinces, geoms_regions, table_carte, top_n

PREFIXE = "acc"
MESURES = {"indice_v2_0_100": "Score de risque", "taux_abandon_harmonise": "Taux d'abandon",
           "proba_risque_t1": "Risque l'an prochain"}
TITRES_ECHELLE = {"indice_v2_0_100": "Score de risque (0 = le plus faible, 100 = le plus élevé)",
                  "taux_abandon_harmonise": "Taux d'abandon (%)",
                  "proba_risque_t1": "Probabilité d'être parmi les plus touchées l'an prochain (%)"}
LIBELLES_KPI = ["Taux d'abandon national", "Provinces en alerte", "Écart filles – garçons",
                "Province la plus à risque", "Élèves ayant abandonné", "Déplacés internes (PDI)"]
AIDE_PDI_PROLONGE = ("Dernier relevé CONASUR du 31/03/2023, prolongé pour les années suivantes.\n"
                     "Source : CONASUR via HDX/OCHA")
# Une phrase par onglet, sous les onglets : ce que montre la carte affichée. Ce qui était dans le
# sous-titre de l'écran (« score de risque combinant… ») revient ici, à l'endroit où la mesure se
# choisit.
EXPLICATIONS = {
    "indice_v2_0_100": "Note de synthèse de 0 à 100 qui combine abandon, redoublement, personnes déplacées et "
                       "conditions d'accueil.",
    "taux_abandon_harmonise": "Taux brut observé pour l'année, sans pondération.",
    "proba_risque_t1": "Probabilité de passer au-dessus du seuil d'alerte de 50 % l'année suivante.",
}
# La liste de gauche suit l'onglet de la carte (demande utilisateur) : même mesure, même ordre,
# même couleur. Trois titres, un par mesure — le titre dit ce que la liste classe, sinon « les plus
# à risque » mentirait sur un classement par taux d'abandon.
TITRES_TOP10 = {
    "indice_v2_0_100": "Les 10 provinces les plus à risque",
    "taux_abandon_harmonise": "Les 10 provinces au plus fort taux d'abandon",
    "proba_risque_t1": "Les 10 provinces les plus exposées l'an prochain",
}
# Le titre du bloc de carte suit lui aussi l'onglet : « Carte du
# risque » sur un onglet d'abandon annonçait autre chose que ce qui est dessiné. Les mots sont ceux
# des onglets, le périmètre « (45 provinces) » reste, et le titre du score ne change pas.
TITRES_CARTE = {
    "indice_v2_0_100": "Carte du risque (45 provinces)",
    "taux_abandon_harmonise": "Carte du taux d'abandon (45 provinces)",
    "proba_risque_t1": "Carte du risque l'an prochain (45 provinces)",
}
# En-tête de la colonne chiffrée de chaque mesure. Court : un en-tête ne se coupe jamais
# (`white-space: nowrap`), et la colonne de la prévision s'ajoute aux deux autres sur son onglet.
ENTETES_TOP10 = {"indice_v2_0_100": "Score", "taux_abandon_harmonise": "Abandon", "proba_risque_t1": "Risque"}
# Comment la phrase « Lecture : » nomme la barre selon la mesure mise en avant.
BARRES_TOP10 = {"indice_v2_0_100": "la barre de score", "taux_abandon_harmonise": "la barre d'abandon",
                "proba_risque_t1": "la barre de risque"}


def _sous_titre(annee, sexe):
    """Le périmètre de l'écran en une ligne courte : année et élèves.

    Ce que mesure la carte est dit sous les onglets de mesure (`EXPLICATIONS`), là où elle se
    choisit : le périmètre tient alors sur une seule ligne à 1366 px et l'entête garde la hauteur
    du groupe de filtres, à côté duquel il reste sur la même ligne."""
    eleves = "ensemble des élèves" if sexe == "T" else SEXES[sexe].lower()
    return f"Primaire, {annee_scolaire(annee)} · {eleves}"


def layout(**_):
    # la ligne de périmètre et la carte portent déjà leur texte par défaut : aucun bloc ne change
    # de hauteur entre le premier rendu et le retour du callback
    return html.Div([
        titre("Où le risque de décrochage est-il le plus fort ?", sous=_sous_titre(2024, "T"),
              id_sous="acc-sous-titre",
              controles=[filtre("Année scolaire", choix_annee("acc-annee")),
                         filtre("Élèves", choix_sexe("acc-sexe"))]),
        # squelettes aux hauteurs réelles : la page ne saute pas quand le callback revient
        bande_kpi([kpi_squelette(lib) for lib in LIBELLES_KPI], id="acc-kpis"),
        html.Div([
            html.Section([
                entete_bloc("Les 10 provinces les plus à risque",
                            # lien appuyé : il quitte l'écran (classement complet, puis export)
                            lien_discret("Classement complet et export", "/classement",
                                         id_="acc-lien-classement", bleu=True),
                            id_titre="acc-t-top10"),
                html.Div(squelette(n=10), className="zone-top10", id="acc-top10"),
                html.P(id="acc-note-top10", className="lecture"),
            ], className="carte-bloc bloc-top10", **{"aria-labelledby": "acc-t-top10"}),
            html.Section([
                entete_bloc(TITRES_CARTE["indice_v2_0_100"],
                            segment("acc-mesure", MESURES, "indice_v2_0_100"),
                            aide_titre=A.CARTE, id_titre="acc-t-carte"),
                # une phrase sous les onglets dit ce que montre la carte choisie ; sa hauteur est
                # réservée en CSS, donc le bloc ne saute pas quand le callback la remplace
                html.P(EXPLICATIONS["indice_v2_0_100"], id="acc-explication", className="explication-mesure"),
                # la boîte porte le nom de ce qui est dessiné ; un groupe et non une image, parce que
                # le tracé réagit au survol (et au clic sur la fiche)
                html.Div(dcc.Graph(id="acc-carte", config=F.CONFIG_CARTE, style={"height": "100%", "width": "100%"},
                                   responsive=True, figure=F.figure_vide("Chargement de la carte…", hauteur=None)),
                         className="zone-carte", role="group",
                         **{"aria-label": "Carte des 45 provinces du Burkina Faso colorées selon la mesure choisie ; "
                                          "les valeurs chiffrées sont dans la liste à gauche."}),
                # la légende discrète et la note vivent hors du tracé : ni l'une ni l'autre
                # ne peut entrer en collision avec le contour du pays
                html.Div(id="acc-note-carte"),
            ], className="carte-bloc bloc-carte", **{"aria-labelledby": "acc-t-carte"}),
        ], className="ligne-principale"),
    ], className="vue-ensemble")


def _titre_carte(mesure):
    """Titre du bloc de carte pour l'onglet choisi, marqueur d'aide compris : le callback remplace
    le contenu du `h2`, qui porte le nom accessible du bloc — l'icône « i » de la carte doit donc
    repartir avec lui, exactement comme `entete_bloc` l'assemble au premier rendu."""
    return avec_aide(TITRES_CARTE[mesure], A.CARTE)


def _signe(v, dec=1, unite=" pt"):
    if v is None or v != v:
        return None
    pl = "s" if abs(round(v, dec)) >= 2 and unite.strip() == "pt" else ""
    return f"{'+' if v >= 0 else '−'}{fmt_nombre(abs(v), dec)}{unite}{pl}"


def _delta(a, b):
    return (a - b) if (a is not None and b is not None and a == a and b == b) else None


def bloc_kpis(d, annee, sexe):
    k = kpis_decideurs(d.region(), d.province(), annee, sexe, SEUIL_ALERTE)
    if not k:
        return alerte("Pas de données pour cette sélection.",
                      "Choisissez une autre année scolaire ou un autre groupe d'élèves.", variante="neutre")
    cible = {"T": "", "F": " (filles)", "G": " (garçons)"}[sexe]
    ecart = _delta(k["abandon_filles"], k["abandon_garcons"])
    ecart_estime = k["nb_provinces_abandon_filles_impute"] > k["nb_provinces"] / 2
    # écart filles-garçons : il « empire » si sa valeur absolue augmente
    d_ecart = _delta(abs(ecart) if ecart is not None else None,
                     abs(k["ecart_fg_prec"]) if k["ecart_fg_prec"] == k["ecart_fg_prec"] else None)
    d_alerte = _delta(k["nb_alerte"], k["nb_alerte_prec"])
    d_pdi = _delta(k["pdi_nombre"], k["pdi_nombre_prec"])
    d_ab = k["abandons_estimes_variation"]
    cartes = [
        kpi("Taux d'abandon national" + cible, fmt_valeur(k["abandon"], "taux_abandon_harmonise"),
            "du CP1 au CM1", aide_kpi=A.KPI["abandon"],
            evolution=tendance(k["abandon_variation"], f"{_signe(k['abandon_variation'])} en un an")),
        kpi("Provinces en alerte",
            "n.d." if k["nb_alerte"] is None else f"{k['nb_alerte']} sur {k['nb_provinces']}",
            ("risque ≥ 50 % l'an prochain" if k["nb_alerte"] is not None
             else "prévision de 2020-21 à 2024-25"), aide_kpi=A.KPI["alerte"],
            evolution=tendance(d_alerte, f"{_signe(d_alerte, 0, '')} en un an"),
            critique=bool(k["nb_alerte"])),
        kpi("Écart filles – garçons", _signe(ecart) or "n.d.",
            f"F {fmt_valeur(k['abandon_filles'], 'taux_abandon_harmonise')} · G "
            f"{fmt_valeur(k['abandon_garcons'], 'taux_abandon_harmonise')}" + (" · estimé" if ecart_estime else ""),
            aide_kpi=A.KPI["ecart"],
            evolution=tendance(d_ecart, f"{_signe(d_ecart)} d'écart en un an")),
        # libellé qui se comprend seul : ni infobulle, ni soulignement, ni icône — et surtout aucune
        # bulle native : l'utilisateur a demandé que rien ne s'ouvre sur ce chiffre clé
        kpi("Province la plus à risque", nom_propre(k["province_top"] or "n.d."),
            f"{nom_propre(k['region_top'] or '')} · abandon {fmt_valeur(k['abandon_top'], 'taux_abandon_harmonise')}",
            critique=True),
        kpi("Élèves ayant abandonné" + cible,
            "≈ " + fmt_nombre(round(k["abandons_estimes"], -2)) if k["abandons_estimes"] == k["abandons_estimes"]
            else "n.d.", "estimation pour l'année", aide_kpi=A.KPI["eleves"],
            evolution=tendance(d_ab, f"{_signe(round(d_ab, -2), 0, '')} en un an" if d_ab == d_ab else "")),
        # un relevé reporté est un état (« périmé »), pas une note de bas de page
        kpi("Déplacés internes (PDI)", fmt_nombre(round(k["pdi_nombre"], -3)),
            f"{fmt_nombre(k['pdi_pour_1000_hab'], 0)} / 1 000 hab.", aide_kpi=A.KPI["pdi"],
            chip=chip_stale(AIDE_PDI_PROLONGE) if k["pdi_prolonge"] else None,
            etat="stale" if k["pdi_prolonge"] else "ready",
            evolution=tendance(d_pdi, "inchangé en un an" if d_pdi is not None and abs(d_pdi) < 0.5
                               else f"{_signe(round(d_pdi, -3) if d_pdi is not None else None, 0, '')} en un an",
                               seuil=0.5)),
    ]
    return cartes


def _bornes_barre(mesure, bornes=None):
    """Bornes de la piste d'une barre : celles de l'échelle de couleur de la carte affichée, pour
    qu'une province ait exactement la même teinte des deux côtés de l'écran.

    Le score fait exception, et c'est voulu : c'est un indice absolu de 0 à 100 dans l'année et le
    sexe, donc son échelle est fixe — la barre d'un score de 50 est à la moitié de sa piste, que la
    sélection affichée monte à 100 ou s'arrête à 80."""
    if mesure == "indice_v2_0_100":
        return 0.0, 100.0
    return bornes if bornes else F.bornes([], mesure)


def _barre(v, mesure, lo, hi):
    """Largeur (en % de la piste) et couleur d'une barre : la même normalisation que la carte."""
    if v is None or v != v:
        return 0.0, F.GRIS_ND
    x = min(max((float(v) - lo) / (hi - lo), 0), 1) if hi > lo else 0.0
    return 100 * x, sample_colorscale(F.echelle(mesure), [x])[0]


def _texte_mesure(v, cle):
    """Le chiffre d'une colonne de mesure, dans l'unité de cette mesure (le score est sans unité)."""
    if cle == "indice_v2_0_100":
        return "n.d." if v != v else fmt_nombre(v, 0)
    return fmt_valeur(v, cle)


def _colonnes_top10(mesure):
    """Colonnes chiffrées du tableau, dans l'ordre : les deux colonnes de toujours, plus celle de la
    mesure choisie si elle n'en fait pas partie. On n'enlève jamais une colonne — on déplace
    l'accent (la barre) sur la colonne de la mesure cartographiée."""
    base = ["indice_v2_0_100", "taux_abandon_harmonise"]
    return tuple(base if mesure in base else base + [mesure])


def _lignes_top10(d, annee, sexe, mesure):
    """Les dix provinces en tête pour la mesure choisie.

    Tri décroissant sur la mesure (pour les trois, « plus haut = pire »), les ex æquo départagés par
    le rang de score : deux appels successifs donnent toujours la même liste. Une province sans
    valeur pour la mesure n'est jamais classée — elle sort de la liste, elle n'y prend pas la
    dernière place. Le classement par score reste exactement celui de la vue (`top_n`)."""
    if mesure == "indice_v2_0_100":
        return top_n(d, annee, sexe, 10)
    t = top_n(d, annee, sexe, 10_000)  # la vue entière de l'année et du sexe, déjà filtrée
    t = t[t[mesure] == t[mesure]]
    return t.sort_values([mesure, "rang_v2"], ascending=[False, True]).head(10)


def _vide_top10(mesure):
    """Un vide dit pourquoi, et garde la hauteur du cadre de la liste."""
    if mesure == "proba_risque_t1":
        return vide("La prévision n'est calculée que pour l'ensemble des élèves, de 2020-2021 à 2024-2025. "
                    "Choisissez une autre année scolaire ou l'ensemble des élèves.")
    return vide(f"Aucune province n'a de valeur de {MESURES[mesure].lower()} pour cette sélection.")


def _cellule_statut(statut, sexe, mesure):
    """Contenu de la colonne « Classement » : la solidité est mesurée sur le classement par score.

    Sur un autre onglet, une province qui n'est pas dans ce top 10 de score y recevait le badge
    « Hors top 10 » alors qu'elle est justement dans la liste affichée : le badge disparaît
    et la cellule porte le tiret des valeurs absentes. Les
    provinces du top 10 de score gardent leur badge, et l'onglet du score ne change pas."""
    if sexe != "T":
        return "—"
    absent = not statut or statut != statut or statut == "hors_top10"
    if mesure != "indice_v2_0_100" and absent:
        return "—"
    return badge_statut(statut)


def tableau_top10(d, annee, sexe, mesure="indice_v2_0_100", bornes=None):
    """Les dix provinces en tête pour la mesure cartographiée.

    `mesure` : la mesure de l'onglet de carte ; elle décide du tri, de la colonne qui porte la barre
    et du titre du bloc. `bornes` : les bornes de couleur de la carte affichée, pour que la barre
    reprenne la teinte de la province sur la carte."""
    t = _lignes_top10(d, annee, sexe, mesure)
    if not len(t):
        return _vide_top10(mesure)
    colonnes = _colonnes_top10(mesure)
    lo, hi = _bornes_barre(mesure, bornes)
    pt = d.province()
    pt = pt[(pt["annee_debut"] == annee) & (pt["sexe"] == "T")].set_index("pcode_province")
    lignes = []
    for place, (_, r) in enumerate(t.iterrows(), start=1):
        statut = pt["statut_top10_mc"].get(r["pcode_province"]) if sexe == "T" else None
        # le rang de score est une grandeur publiée (c'est celui de la fiche) : il reste affiché tel
        # quel sur son propre classement ; sur une autre mesure, la colonne donne la place dans
        # cette liste-là, pas un rang qui viendrait d'un autre classement
        rang = int(r["rang_v2"]) if mesure == "indice_v2_0_100" else place
        cellules = [
            html.Td(rang, className="col-rang"),
            html.Td(dcc.Link(nom_propre(r.get("nom_officiel_province_ancienne") or r["province"]),
                             href=f"/fiche?pcode={r['pcode_province']}&annee={annee}&sexe={sexe}"),
                    className="col-prov"),
            html.Td(nom_propre(r["region"]), className="col-reg"),
        ]
        for cle in colonnes:
            txt = _texte_mesure(r[cle], cle)
            if cle != mesure:
                cellules.append(html.Td(txt, className="col-num"))
                continue
            largeur, couleur = _barre(r[cle], cle, lo, hi)
            cellules.append(html.Td(
                html.Span([html.Span(html.Span(className="barre-score",
                                               style={"width": f"{largeur:.0f}%", "background": couleur}),
                                     className="piste-score"),
                           html.Span(txt, className="val-score")], className="cellule-score"),
                className="col-score"))
        cellules.append(html.Td(_cellule_statut(statut, sexe, mesure), className="col-statut"))
        lignes.append(html.Tr(cellules))
    titres = [html.Th("#", className="col-rang"), html.Th("Province"), html.Th("Région", className="col-reg")]
    for cle in colonnes:
        # l'icône « i » appartient au score (budget de marqueurs d'aide) : elle reste sur sa colonne,
        # que celle-ci porte la barre ou le simple chiffre
        contenu = ([ENTETES_TOP10[cle], aide(A.COL["score"], "Score de risque")]
                   if cle == "indice_v2_0_100" else ENTETES_TOP10[cle])
        titres.append(html.Th(contenu, className="col-score" if cle == mesure else "col-num"))
    titres.append(html.Th(["Classement", aide(A.COL["statut"], "Classement")], className="col-statut"))
    return html.Table([html.Thead(html.Tr(titres)), html.Tbody(lignes)], className="table-dc table-top10")


# sous 576 px le mot du badge est lu mais plus affiché : la clé revient dans la phrase de lecture
CLE_MOBILE = html.Span("Colonne « Classement » : ●●● très sûr · ●●○ probable · ●○○ incertain.",
                       className="cle-mobile")


def _lecture_top10(sexe, mesure="indice_v2_0_100"):
    txt = [f"{BARRES_TOP10[mesure]} reprend exactement la couleur de la province sur la carte. Cliquez sur une "
           "province pour ouvrir sa fiche. "]
    if sexe != "T":
        txt.append("La solidité du classement est calculée pour l'ensemble des élèves. ")
    txt.append(CLE_MOBILE)
    return contenu_lecture(txt)


def _lecture_vide(mesure):
    """Phrase de lecture quand la liste n'a rien à classer : une ligne, pour que le bloc garde sa
    hauteur (le cadre de la liste ne doit pas grandir d'une ligne en changeant d'onglet)."""
    if mesure == "proba_risque_t1":
        return contenu_lecture("ce classement demande une prévision, qui n'existe pas pour cette sélection.")
    return contenu_lecture("aucune valeur à classer pour cette sélection.")


def _lecture_liste(bloc, sexe, mesure):
    """La phrase de lecture suit ce que la liste montre vraiment : un vide n'a ni barre ni ligne à
    cliquer, donc il n'a pas la phrase du tableau."""
    if getattr(bloc, "className", "") == "vide":
        return _lecture_vide(mesure)
    return _lecture_top10(sexe, mesure)


def register(app):
    @app.callback(Output("acc-kpis", "children"), Output("acc-carte", "figure"), Output("acc-note-carte", "children"),
                  Output("acc-top10", "children"), Output("acc-note-top10", "children"),
                  Output("acc-sous-titre", "children"), Output("acc-explication", "children"),
                  Output("acc-t-top10", "children"), Output("acc-t-carte", "children"),
                  Input("acc-annee", "value"), Input("acc-sexe", "value"), Input("acc-mesure", "value"))
    def maj(annee, sexe, mesure):
        explication = EXPLICATIONS[mesure]
        # la liste de gauche classe la mesure cartographiée : son titre le dit
        titre_top = TITRES_TOP10[mesure]
        # le titre du bloc de carte nomme la mesure dessinée, dans les mots de l'onglet
        titre_carte = _titre_carte(mesure)
        try:
            d = donnees()
            d.get()
        except Exception:
            e = erreur_donnees()
            return (e, F.figure_vide("Données indisponibles"), "", e, "", "", explication, titre_top, titre_carte)
        kp = bloc_kpis(d, annee, sexe)
        sous = _sous_titre(annee, sexe)
        if not disponible(mesure, annee, sexe):
            # un vide dit pourquoi : la prévision n'existe pas pour cette sélection
            fig = F.figure_vide("Prévision disponible pour l'ensemble des élèves, de 2020-2021 à 2024-2025.",
                                hauteur=None)
            vide_liste = _vide_top10(mesure)
            return (kp, fig, "", vide_liste, _lecture_liste(vide_liste, sexe, mesure), sous, explication, titre_top,
                    titre_carte)
        t = table_carte(d, "ancien_45", annee, sexe, mesure)
        vals = {}
        for _, r in t.iterrows():
            txt = (f"<b>{nom_propre(r['province_carte'])}</b> · {nom_propre(r['region_carte'])}<br>"
                   f"Score de risque : {fmt_nombre(r['indice_v2_0_100'], 0)} / 100 (rang {int(r['rang_v2'])})<br>"
                   f"Taux d'abandon : {fmt_valeur(r['taux_abandon_harmonise'], 'taux_abandon_harmonise')}")
            if r["proba_risque_t1"] == r["proba_risque_t1"]:
                txt += f"<br>Risque l'an prochain : {fmt_valeur(r['proba_risque_t1'], 'proba_risque_t1')}"
            # hachures : seulement si le taux d'abandon lui-même est estimé (les PDI prolongés après mars 2023
            # concernent toutes les provinces et sont expliqués dans Qualité des données)
            imp = mesure != "proba_risque_t1" and (r.get("abandon_impute") or 0) > 0
            if imp:
                txt += "<br><i>Taux d'abandon estimé (voir Qualité des données)</i>"
            vals[r["pcode_province_carte"]] = dict(valeur=r["valeur"], impute=bool(imp), survol=txt)
        geoms = geoms_provinces(d, "ancien_45")
        fig = F.carte(geoms, vals, mesure, contours_regions=geoms_regions(d, "ancien_45"),
                      hauteur=None, titre_echelle=TITRES_ECHELLE[mesure], note_haut=False, legende=False)
        # La note ne nomme que les codes visuels réellement présents sur la carte affichée : plus
        # aucun contour noir (retiré de la carte), et le gris clair comme les hachures ne
        # s'écrivent que s'il existe vraiment des provinces concernées.
        # Espace insécable avant les deux-points : la note ne commence jamais une ligne par « : ».
        cles = cles_legende(vals, geoms["code"])
        codes = ["Traits gris : limites des régions"]
        if "nd" in cles:
            codes.append("gris clair : non disponible")
        if "estime" in cles:
            codes.append("hachures : taux d'abandon estimé")
        note = " · ".join(codes) + "."
        lo, hi = F.bornes([v["valeur"] for v in vals.values()], mesure)
        legende = legende_carte(TITRES_ECHELLE[mesure], ticks_echelle(lo, hi, mesure), cles=cles)
        # la liste est construite avec les bornes de couleur de la carte : une barre et la province
        # qu'elle désigne portent alors exactement la même teinte
        top = tableau_top10(d, annee, sexe, mesure, bornes=(lo, hi))
        note_top = _lecture_liste(top, sexe, mesure)
        return (kp, fig, [legende, html.P(note, className="note")], top, note_top, sous, explication, titre_top,
                titre_carte)

    @app.callback(Output("acc-lien-classement", "href"), Input("acc-annee", "value"), Input("acc-sexe", "value"),
                  Input("acc-mesure", "value"))
    def lien_classement(annee, sexe, mesure):
        return f"/classement?annee={annee}&sexe={sexe}&mesure={mesure}"
