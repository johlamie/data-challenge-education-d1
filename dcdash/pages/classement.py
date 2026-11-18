"""Page 3 : le classement complet des provinces, en deux panneaux (sans défilement de page sur ordinateur).

L'écran répond à « où se situe chaque province, et comment l'emporter avec soi » : un entête de page qui
donne le périmètre en une ligne, quatre filtres compacts, puis la liste complète triable et filtrable à
gauche et la carte du même critère à droite. Une seule action principale, « Exporter en CSV », qui
télécharge la vue telle qu'elle est triée et filtrée.

Rien de visuel ne vit dans ce fichier : dcdash/composants.py fournit les blocs, et
assets/page-classement.css habille la table Dash, qui ne sait pas se styler autrement qu'en ligne.
"""
from dash import Input, Output, State, dash_table, dcc, html

from .. import aides as A
from .. import figures as F
from ..composants import (bouton, choix_annee, choix_sexe, cles_legende, entete_bloc, erreur_donnees,
                          filtre, lecture, legende_carte, note, ticks_echelle, titre, vide)
from ..db import donnees
from ..meta import ANNEES, DECOUPAGES, SEXES, annee_scolaire, fmt_nombre, fmt_valeur, nom_propre
from ..vues import disponible, geoms_provinces, geoms_regions, table_carte

MESURES = {"indice_v2_0_100": "Score de risque", "taux_abandon_harmonise": "Taux d'abandon",
           "proba_risque_t1": "Risque l'an prochain"}
# libellés courts : la colonne de filtre fait 1/4 de l'entête, et c'est le nombre de provinces
# (45 ou 47) qui distingue les deux découpages pour le lecteur.
DECOUPAGES_COURTS = {"ancien_45": "45 provinces", "2025_47": "47 (2025)"}
COLONNES_EXPORT = ["decoupage", "annee_scolaire", "sexe", "pcode_province_carte", "province_carte",
                   "pcode_region_carte", "region_carte", "pcode_province", "province", "indicateur", "valeur", "rang",
                   "impute", "source", "valeur_heritee_province_mere", "indice_v2", "indice_v2_0_100", "rang_v2",
                   "statut_top10_mc", "proba_risque_t1", "taux_abandon_harmonise", "taux_abandon_moyen_2ans",
                   "taux_abandon_publie"]
TITRES_ECHELLE = {"indice_v2_0_100": "Score de risque (0 = le plus faible, 100 = le plus élevé)",
                  "taux_abandon_harmonise": "Taux d'abandon (%)",
                  "proba_risque_t1": "Probabilité d'être parmi les plus touchées l'an prochain (%)"}
TITRE_LISTE = "Toutes les provinces, classées"


def _liste(id_, options, valeur):
    """Liste déroulante compacte, montée exactement comme les fabriques partagées (ni effaçable ni
    cherchable). Il n'existe pas encore de fabrique pour le critère de classement ni pour le découpage
    en libellés courts : manque signalé, pas inventé ici (aucun style n'est posé dans la page)."""
    return dcc.Dropdown(id=id_, options=[{"label": v, "value": k} for k, v in options.items()],
                        value=valeur, clearable=False, searchable=False)


def _perimetre(annee, sexe, cle, n=None):
    """Le périmètre de l'écran en une ligne : combien de provinces, quelle année, quels élèves,
    selon quel critère."""
    debut = f"{n} provinces · " if n is not None else ""
    return (f"{debut}{annee_scolaire(annee)} · {SEXES[sexe].lower()} · classées selon : "
            f"{MESURES[cle].lower()}" + (" (en %)" if cle == "proba_risque_t1" else "") + ".")


def table_dash(mesure):
    """Tableau de classement complet : le corps défile dans le bloc, jamais la page.
    Aucune couleur ni taille ici — tout vit dans assets/page-classement.css."""
    return dash_table.DataTable(
        id="cla-table", sort_action="native", filter_action="native", page_action="none",
        fixed_rows={"headers": True}, columns=colonnes(mesure),
        sort_by=[{"column_id": "rang", "direction": "asc"}], markdown_options={"link_target": "_self"},
        style_table={"height": "100%", "maxHeight": "100%", "overflowY": "auto"},
        # largeurs : de quoi écrire l'en-tête et son chevron de tri sans rien couper
        style_cell_conditional=[{"if": {"column_id": c}, "textAlign": "right", "width": w}
                                for c, w in (("rang", "10%"), ("score", "12%"), ("abandon", "14%"),
                                             ("valeur_aff", "12%"))]
        + [{"if": {"column_id": "province_carte"}, "width": "26%"},
           {"if": {"column_id": "region_carte"}, "width": "18%"},
           {"if": {"column_id": "imp"}, "width": "10%"}],
        filter_options={"case": "insensitive", "placeholder_text": "filtrer…"})


def layout(annee=None, sexe=None, mesure=None, decoupage=None, **_):
    try:
        annee = int(annee) if annee else 2024
    except ValueError:
        annee = 2024
    annee = annee if annee in ANNEES else 2024
    sexe = sexe if sexe in SEXES else "T"
    mesure = mesure if mesure in MESURES else "indice_v2_0_100"
    decoupage = decoupage if decoupage in DECOUPAGES else "ancien_45"
    return html.Div([
        html.Div([
            titre("Le classement complet des provinces", sous=_perimetre(annee, sexe, mesure),
                  id_sous="cla-resume"),
            # quatre filtres compacts : le libellé est toujours visible, et une seule icône « i »
            # sur toute la page, sur le critère de classement
            html.Div([
                filtre("Année scolaire", choix_annee("cla-annee", annee)),
                filtre("Élèves", choix_sexe("cla-sexe", sexe)),
                # le critère de classement porte les libellés les plus longs (« Risque l'an prochain ») :
                # sa colonne est la plus large de la rangée, et à 390 px il prend la ligne entière
                filtre("Classer selon", _liste("cla-mesure", MESURES, mesure), aide_lib=A.MESURES,
                       classe="filtre-mesure"),
                filtre("Découpage", _liste("cla-decoupage", DECOUPAGES_COURTS, decoupage)),
            ], className="filtres-compacts"),
        ], className="cla-entete"),
        html.Div([
            html.Section([
                entete_bloc(TITRE_LISTE,
                            bouton("Exporter en CSV", "cla-export-btn", nom_icone="telecharger",
                                   title="Télécharge la liste telle qu'elle est triée et filtrée"),
                            id_titre="cla-t-liste"),
                html.Div(table_dash(mesure), className="zone-liste"),
                # filtre sans résultat : la phrase dit pourquoi et comment en sortir ; elle n'apparaît
                # que si un champ de filtre est rempli et que la liste est vide (règle CSS :has)
                html.Div(vide("Aucune province ne correspond à ce filtre. Effacez le texte saisi dans la "
                              "ligne « filtrer… » pour revoir la liste complète."), className="vide-filtre"),
                lecture(html.Span(id="cla-note")),
                dcc.Download(id="cla-download"),
            ], className="carte-bloc bloc-liste", **{"aria-labelledby": "cla-t-liste"}),
            html.Section([
                entete_bloc(f"Carte : {MESURES[mesure].lower()}", id_titre="cla-titre-carte"),
                # la boîte porte le nom de ce qui est dessiné ; un groupe et non une image, parce que
                # le tracé réagit au survol (et au clic sur la fiche)
                html.Div(dcc.Graph(id="cla-carte", config=F.CONFIG_CARTE, style={"height": "100%", "width": "100%"},
                                   responsive=True,
                                   figure=F.figure_vide("Chargement de la carte…", hauteur=None)),
                         className="zone-carte", role="group",
                         **{"aria-label": "Carte des provinces du Burkina Faso colorées selon le critère choisi ; "
                                          "les valeurs chiffrées sont dans la liste à gauche."}),
                # la légende discrète et la note vivent hors du tracé : le contour du pays ne peut
                # entrer en collision ni avec l'une ni avec l'autre
                html.Div(id="cla-lecture-carte"),
            ], className="carte-bloc bloc-carte", **{"aria-labelledby": "cla-titre-carte"}),
        ], className="ligne-principale ligne-classement"),
    ], className="page-classement")


def _fmt(dec):
    return {"locale": {"decimal": ",", "group": " "}, "specifier": f",.{dec}f"}


def colonnes(cle):
    cols = [{"name": "Rang", "id": "rang", "type": "numeric"},
            {"name": "Province", "id": "province_carte", "presentation": "markdown"},
            {"name": "Région", "id": "region_carte"},
            {"name": "Score", "id": "score", "type": "numeric", "format": _fmt(0)},
            {"name": "Abandon %", "id": "abandon", "type": "numeric", "format": _fmt(1)}]
    if cle == "proba_risque_t1":
        cols.append({"name": "Risque %", "id": "valeur_aff", "type": "numeric", "format": _fmt(0)})
    cols.append({"name": "Estimé", "id": "imp"})
    return cols


def _r(v, n=1):
    return None if v is None or v != v else round(float(v), n)


def table_classement(d, decoupage, annee, sexe, cle):
    return table_carte(d, decoupage, annee, sexe, cle)


def _cle(mesure, annee, sexe):
    return mesure if disponible(mesure, annee, sexe) else "indice_v2_0_100"


def lignes(t, cle, annee, sexe):
    out = []
    for _, r in t.iterrows():
        nom = nom_propre(r["province_carte"]) + (" ↳" if r.get("valeur_heritee_province_mere") == 1 else "")
        out.append({"rang": None if r["rang"] != r["rang"] else int(r["rang"]),
                    "province_carte": f"[{nom}](/fiche?pcode={r['pcode_province']}&annee={annee}&sexe={sexe})",
                    "region_carte": nom_propre(r["region_carte"]),
                    "valeur_aff": _r(100 * r["valeur"] if cle == "proba_risque_t1" else r["valeur"],
                                     0 if cle != "taux_abandon_harmonise" else 1),
                    "score": _r(r["indice_v2_0_100"], 0), "abandon": _r(r["taux_abandon_harmonise"]),
                    "imp": "oui" if (r.get("abandon_impute") or 0) > 0 else "", "pcode": r["pcode_province_carte"]})
    return out


def _survol(r):
    txt = (f"<b>{nom_propre(r['province_carte'])}</b> · {nom_propre(r['region_carte'])}<br>"
           f"Rang : {'n.d.' if r['rang'] != r['rang'] else int(r['rang'])}<br>"
           f"Score de risque : {fmt_nombre(r['indice_v2_0_100'], 0)} / 100<br>"
           f"Taux d'abandon : {fmt_valeur(r['taux_abandon_harmonise'], 'taux_abandon_harmonise')}")
    if r["proba_risque_t1"] == r["proba_risque_t1"]:
        txt += f"<br>Risque l'an prochain : {fmt_valeur(r['proba_risque_t1'], 'proba_risque_t1')}"
    if r.get("valeur_heritee_province_mere") == 1:
        txt += f"<br><i>Valeur de la province mère ({nom_propre(r['province'])}), non répartie</i>"
    return txt


def register(app):
    @app.callback(Output("cla-table", "data"), Output("cla-table", "columns"), Output("cla-resume", "children"),
                  Output("cla-carte", "figure"), Output("cla-titre-carte", "children"),
                  Output("cla-lecture-carte", "children"), Output("cla-note", "children"),
                  Input("cla-annee", "value"), Input("cla-sexe", "value"), Input("cla-decoupage", "value"),
                  Input("cla-mesure", "value"))
    def maj(annee, sexe, decoupage, mesure):
        try:
            d = donnees()
            d.get()
        except Exception:
            # l'erreur nomme une cause et une suite à faire ; elle prend la place de la carte,
            # le panneau de liste garde son cadre
            return ([], [], "", F.figure_vide("Données indisponibles", hauteur=None), "Carte du classement",
                    erreur_donnees(), "les données ne sont pas disponibles pour le moment.")
        cle = _cle(mesure, annee, sexe)
        t = table_classement(d, decoupage, annee, sexe, cle)
        n = len(t)
        resume = _perimetre(annee, sexe, cle, n)
        note_liste = ["cliquez sur une province pour ouvrir sa fiche, sur un en-tête de colonne pour trier. "
                      "Colonne « Estimé » : le taux d'abandon de l'année a été estimé, faute de relevé."]
        if cle != mesure:
            note_liste.insert(0, "« Risque l'an prochain » n'existe que pour l'ensemble des élèves, de 2020-2021 à "
                                 "2024-2025 : le classement reprend le score de risque. ")
        if decoupage == "2025_47":
            note_liste.append(" ↳ : province créée en 2025, qui porte la valeur de sa province mère.")
        vals = {}
        for _, r in t.iterrows():
            imp = cle != "proba_risque_t1" and (r.get("abandon_impute") or 0) > 0
            vals[r["pcode_province_carte"]] = dict(valeur=r["valeur"], impute=bool(imp), survol=_survol(r))
        geoms = geoms_provinces(d, decoupage)
        fig = F.carte(geoms, vals, cle, contours_regions=geoms_regions(d, decoupage),
                      hauteur=None, titre_echelle=TITRES_ECHELLE[cle], note_haut=False, legende=False)
        titre_carte = f"Carte : {MESURES[cle].lower()} ({n} provinces)"
        # Mêmes règles que sur la vue d'ensemble : plus de contour noir du top 10, et une clé de
        # légende n'apparaît que si la carte affichée contient vraiment ce code visuel.
        cles = cles_legende(vals, geoms["code"])
        codes = ["Traits gris : limites des régions"]
        if "nd" in cles:
            codes.append("gris clair : non disponible")
        if "estime" in cles:
            codes.append("hachures : taux d'abandon estimé")
        txt_carte = " · ".join(codes) + "."
        lo, hi = F.bornes([v["valeur"] for v in vals.values()], cle)
        legende = [legende_carte(TITRES_ECHELLE[cle], ticks_echelle(lo, hi, cle), cles=cles), note(txt_carte)]
        return lignes(t, cle, annee, sexe), colonnes(cle), resume, fig, titre_carte, legende, "".join(note_liste)

    @app.callback(Output("cla-download", "data"), Input("cla-export-btn", "n_clicks"),
                  State("cla-table", "derived_virtual_data"), State("cla-annee", "value"), State("cla-sexe", "value"),
                  State("cla-decoupage", "value"), State("cla-mesure", "value"), prevent_initial_call=True)
    def export(n, vues, annee, sexe, decoupage, mesure):
        d = donnees()
        cle = _cle(mesure, annee, sexe)
        t = table_classement(d, decoupage, annee, sexe, cle)
        if vues:
            ordre = [r["pcode"] for r in vues]
            t = t.set_index("pcode_province_carte").loc[[c for c in ordre if c in set(t["pcode_province_carte"])]]
            t = t.reset_index()
        t = t.assign(indicateur=cle)
        cols = [c for c in COLONNES_EXPORT if c in t.columns]
        return dcc.send_data_frame(t[cols].to_csv, f"classement_{cle}_{decoupage}_{annee}_{sexe}.csv", index=False,
                                   sep=";", decimal=",", encoding="utf-8-sig")
