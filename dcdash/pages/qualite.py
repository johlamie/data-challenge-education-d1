"""Page 5 : ce qui est mesuré, ce qui est estimé.

L'écran s'ouvre sur la question qu'un lecteur se pose avant de citer un chiffre, et dit dès la
ligne de périmètre ce qu'est une valeur estimée (« imputée »). Viennent ensuite la géographie des
estimations, leur provenance, le détail exportable, puis les limites connues et la fiabilité des
contours. Aucun jargon n'est laissé nu : PDI, ACLED, COD-AB et « imputation » sont dits en toutes
lettres la première fois qu'ils apparaissent sur la page.

Aucune icône « i » ici : le budget du site (3 à 5) est déjà pris par les pages de décision.
"""
import pandas as pd
from dash import Input, Output, State, dash_table, dcc, html

from .. import figures as F
from ..composants import (alerte, bouton, chargement, choix_annee, choix_sexe, entete_bloc, erreur_donnees, filtre,
                          lecture, legende_carte, libelle_source_lisible, note, titre)
from ..db import donnees
from ..meta import SEXES, annee_scolaire, fmt_nombre, libelle_source, nom_propre
from ..vues import geoms_provinces, geoms_regions

# clé -> (libellé de donnée, colonne « nombre d'imputations », colonne « source de l'imputation »)
# Le libellé est aussi celui de la colonne « Type » du tableau et de l'export CSV : il ne change pas.
TYPES = {
    "abandon": ("Abandon", "abandon_impute", "source_imputation_abandon"),
    "effectifs": ("Effectifs", "effectif_historique_impute", "source_imputation_effectifs"),
    "pdi": ("PDI", "pdi_impute", "source_imputation_pdi"),
    "population": ("Population", "pop_impute", "source_imputation_population"),
    "chiffres_cles": ("Chiffres clés", "chiffres_cles_impute", "source_imputation_chiffres_cles_equipement"),
    "equipement": ("Équipement (eau, latrines)", "equipement_impute", "source_imputation_chiffres_cles_equipement"),
}

# colonnes de l'export CSV, dans cet ordre : c'est le contrat de l'export, il ne change pas
# (les évolutions d'interface ne touchent qu'à l'affichage, jamais aux colonnes ni aux valeurs)
COLONNES_CSV = ["province", "pcode_province", "region", "annee_debut", "annee_scolaire", "type", "cle", "source"]

# libellés du sélecteur : le jargon y est dit en toutes lettres, la valeur envoyée au calcul est inchangée
LIBELLES_CHOIX = {"pdi": "PDI (personnes déplacées internes)",
                  "chiffres_cles": "Chiffres clés des écoles"}

LIMITES = [
    ("Déplacés internes (PDI) : relevé prolongé après mars 2023",
     "Les PDI — les personnes déplacées internes — sont recensées par le CONASUR. Le dernier relevé publié date du "
     "31/03/2023. Pour 2023-2024 et 2024-2025, ce relevé est prolongé (le total national suivi par l'IDMC, "
     "l'observatoire international des déplacements internes, reste inchangé de 2023 à 2025, à 2 062 534 personnes). "
     "Avant le premier relevé, les PDI sont mis à 0."),
    ("Répartition filles / garçons estimée en 2024-2025",
     "La répartition filles / garçons des effectifs 2024-2025 est reconstituée (part des filles du fichier accès) : "
     "l'abandon par sexe est estimé pour 42 provinces sur 45. Les indices F et G de 2024-2025 ont une fiabilité "
     "faible."),
    ("Tambaga et Tongomayel : rattachement validé par l'équipe",
     "Source COD-AB v03 — le jeu de limites administratives publié par OCHA, valide au 2025-08-01 ; la commune est "
     "absente des art. 2 et 6 du décret 2025-1012 ; rattachement validé par l'équipe le 15/11/2026 "
     "(Tambaga → Gobnangou, Tongomayel → Djelgodji). Fiabilité du contour : « validé par l'équipe » "
     "(valide_equipe dans le tableau ci-contre), c'est-à-dire décidé par l'équipe faute de mention dans le "
     "décret, et non repris tel quel de celui-ci (« exact »)."),
    ("Provinces scindées en 2025",
     "SOUM (→ Djelgodji + Karo-Peli) et TAPOA (→ Dyamongou + Gobnangou) : dans le découpage 2025, les nouvelles "
     "provinces portent la valeur de la province mère (non répartie). Les cartes 2025 l'indiquent au survol."),
    ("Abandon « apparent » : ce que mesure le taux harmonisé",
     "Le taux harmonisé est un taux apparent calculé sur les flux d'effectifs : il peut être négatif (entrées nettes, "
     "retours de déplacés) et il bouge avec les corrections d'effectifs apportées à l'étape b de la préparation des "
     "données (le « jalon b » de la méthode). La moyenne sur 2 ans sert de contrôle."),
    ("Population : chiffres reconstitués depuis 2019",
     "La population des années passées est reconstituée (« rétropolée ») à partir du recensement de la population de "
     "2019 — le RGPH — et des projections 2020 de l'INSD, l'Institut national de la statistique et de la démographie ; "
     "la ventilation par sexe vient des mêmes projections 2020. Les taux d'incidents violents (ACLED, une base "
     "publique d'incidents) et de personnes déplacées (PDI) en dépendent, puisqu'ils sont rapportés à la population."),
]

DEF_ESTIMEE = ("une valeur estimée — on dit « imputée » — n'a pas été relevée cette année-là : elle est "
               "reconstituée à partir d'une année voisine ou d'une autre source, et signalée partout où elle "
               "apparaît.")
TITRE_ECHELLE = "Nombre de types de données estimés dans la province"


def _note_carte(nb):
    """L'échelle va de 0 au nombre de types que la sélection peut faire compter : sans cette phrase,
    une carte presque uniforme se lit comme une carte ratée au lieu d'une bonne nouvelle."""
    haut = "1 type de donnée estimé" if nb == 1 else f"{nb} types de données estimés"
    return (f"Traits gris : limites des régions. L'échelle va de 0 à {nb} : le bleu le plus pâle = aucune valeur "
            f"estimée dans la province, le plus foncé = {haut}.")


def _sous_titre(annee, sexe):
    """Le périmètre de l'écran en une ligne, et la seule définition dont tout le reste dépend."""
    return f"Primaire, {annee_scolaire(annee)} · {SEXES[sexe].lower()} · {DEF_ESTIMEE}"


def _options_type():
    return [{"label": "Tous les types", "value": "tous"}] + \
           [{"label": LIBELLES_CHOIX.get(k, v[0]), "value": k} for k, v in TYPES.items()]


def _tableau(entetes, lignes):
    """Tableau de données partagé : mêmes filets, mêmes chiffres en chasse fixe que le top 10."""
    return html.Div(html.Table([html.Thead(html.Tr(entetes)), html.Tbody(lignes)], className="table-dc"),
                    className="zone-tableau")


def layout(**_):
    # la ligne de périmètre, la légende et la carte portent déjà leur texte par défaut :
    # aucun bloc ne change de hauteur entre le premier rendu et le retour du callback
    return html.Div([
        titre("Qu'est-ce qui est mesuré, qu'est-ce qui est estimé ?", sous=_sous_titre(2024, "T"),
              id_sous="qua-sous-titre",
              controles=[filtre("Année scolaire", choix_annee("qua-annee")),
                         filtre("Élèves", choix_sexe("qua-sexe")),
                         filtre("Type de donnée", dcc.Dropdown(id="qua-type", value="tous", clearable=False,
                                                               searchable=False, options=_options_type()))]),
        html.Div([
            html.Section([
                entete_bloc("Où les valeurs sont-elles estimées ?", id_titre="qua-t-carte"),
                # l'année ne filtre que la carte : c'est donc ici que vit l'état « rien n'est estimé »
                html.Div(id="qua-vide"),
                html.Div(dcc.Graph(id="qua-carte", config=F.CONFIG_CARTE, responsive=True,
                                   style={"height": "100%", "width": "100%"},
                                   figure=F.figure_vide("Chargement de la carte…", hauteur=None)),
                         className="zone-carte", role="group",
                         **{"aria-label": "Carte des 45 provinces, colorées selon le nombre de types de données "
                                          "estimés ; le détail chiffré est dans les tableaux ci-dessous."}),
                # la légende discrète et la note vivent hors du tracé : le contour du pays
                # ne peut entrer en collision avec aucune des deux
                html.Div(id="qua-legende"),
                # l'étendue de l'échelle est dite ici : une carte toute pâle est une bonne nouvelle,
                # pas une carte ratée (le texte suit le type choisi, le callback le remplace)
                note(_note_carte(len(TYPES)), id="qua-note-carte"),
                lecture("plus une province est foncée, plus elle compte de types de données estimés pour l'année et "
                        "le groupe d'élèves choisis."),
            ], className="carte-bloc bloc-carte", **{"aria-labelledby": "qua-t-carte"}),
            html.Section([
                entete_bloc("D'où viennent les valeurs estimées", id_titre="qua-t-synthese"),
                note("Toutes les années du tableau de bord, pour le type de donnée choisi. Un « cas » est une "
                     "province pour une année. Sur écran étroit, le tableau se fait glisser vers la gauche "
                     "pour en voir toutes les colonnes."),
                chargement(html.Div(id="qua-synthese")),
            ], className="carte-bloc", **{"aria-labelledby": "qua-t-synthese"}),
        ], className="qualite-haut"),
        html.Section([
            entete_bloc("Détail des valeurs estimées",
                        bouton("Exporter en CSV", id_="qua-export-btn", nom_icone="telecharger"),
                        id_titre="qua-t-detail"),
            note("Toutes les années du tableau de bord, pour le groupe d'élèves et le type de donnée choisis : "
                 "l'année choisie plus haut ne filtre que la carte. Triable, filtrable, exportable. Sur écran "
                 "étroit, le tableau se fait glisser vers la gauche pour en voir toutes les colonnes."),
            html.Div(chargement(dash_table.DataTable(
                id="qua-detail", sort_action="native", filter_action="native", page_size=15,
                # vue en liste : des filets horizontaux comme dans le top 10, jamais un quadrillage
                style_as_list_view=True, style_table={"overflowX": "auto"},
                # aucune couleur ni taille en clair ici : seulement des jetons, le reste vit
                # dans assets/page-qualite.css
                style_cell={"fontFamily": "var(--police)", "textAlign": "left", "whiteSpace": "normal",
                            "height": "auto"},
                filter_options={"case": "insensitive", "placeholder_text": "filtrer…"})),
                     className="zone-detail"),
            dcc.Download(id="qua-download"),
        ], className="carte-bloc", **{"aria-labelledby": "qua-t-detail"}),
        html.Div([
            html.Section([
                entete_bloc("Limites connues", id_titre="qua-t-limites"),
                note("À garder en tête avant de citer un chiffre de ce tableau de bord."),
                # « Limite connue » est le titre du bloc : répété en tête de chacune des six entrées, il
                # devient une litanie à l'oreille d'un lecteur d'écran. Il reste pour eux seuls, une fois
                # par entrée, sans occuper de place à l'écran.
                html.Dl([html.Div([html.Dt([html.Span("Limite connue : ",
                                                      className="limite-eti visuellement-cache"),
                                            html.Span(t, className="limite-nom")]),
                                   html.Dd(x)], className="limite") for t, x in LIMITES], className="limites"),
            ], className="carte-bloc", **{"aria-labelledby": "qua-t-limites"}),
            html.Section([
                entete_bloc("Fiabilité des contours", id_titre="qua-t-contours"),
                note("Un « contour » est le tracé d'une province sur les cartes. La plupart viennent tels quels du "
                     "jeu officiel COD-AB (les limites administratives publiées par OCHA et l'IGB) ; le tableau "
                     "liste celles dont le tracé n'est pas repris à l'identique, avec le degré de confiance associé."),
                chargement(html.Div(id="qua-contours")),
            ], className="carte-bloc", **{"aria-labelledby": "qua-t-contours"}),
        ], className="qualite-bas"),
    ], className="qualite-donnees")


def _long(P, sexe):
    """Détail des valeurs estimées, une ligne par province · année · type.

    Deux colonnes de source, et c'est voulu : `source` est la donnée, telle que le modèle la nomme
    (`meta.libelle_source`) — c'est elle, et elle seule, qui part dans l'export CSV, inchangée.
    `source_affichee` est sa mise en forme pour l'écran. L'affichage n'écrit jamais dans la donnée.
    """
    rows = []
    p = P[P["sexe"] == sexe]
    for k, (lib, f, so) in TYPES.items():
        q = p[p[f].fillna(0) > 0]
        for r in q.itertuples():
            brut = getattr(r, so)
            rows.append({"province": r.province, "pcode_province": r.pcode_province, "region": r.region,
                         "annee_debut": r.annee_debut, "annee_scolaire": r.annee_scolaire, "type": lib, "cle": k,
                         "source": libelle_source(brut) or "non précisée",
                         "source_affichee": libelle_source_lisible(brut) or "non précisée"})
    return pd.DataFrame(rows, columns=COLONNES_CSV + ["source_affichee"])


def _survol(nom, k, details):
    """Texte de survol en français courant : jamais « 1 type(s) », jamais un zéro muet."""
    if k == 0:
        t = f"<b>{nom}</b><br>Aucune valeur estimée pour cette sélection"
    elif k == 1:
        t = f"<b>{nom}</b><br>1 type de donnée estimé"
    else:
        t = f"<b>{nom}</b><br>{k} types de données estimés"
    for r in details.itertuples():
        t += f"<br>· {r.type} : {r.source_affichee[:90]}"
    return t


def register(app):
    @app.callback(Output("qua-carte", "figure"), Output("qua-synthese", "children"), Output("qua-detail", "data"),
                  Output("qua-detail", "columns"), Output("qua-contours", "children"),
                  Input("qua-annee", "value"), Input("qua-sexe", "value"), Input("qua-type", "value"))
    def maj(annee, sexe, typ):
        try:
            d = donnees()
            d.get()
        except Exception:
            e = erreur_donnees()
            return F.figure_vide("Données indisponibles"), e, [], [], e
        P = d.province()
        L = _long(P, sexe)
        if typ != "tous":
            L = L[L["cle"] == typ]
        la = L[L["annee_debut"] == annee]
        n = la.groupby("pcode_province").size()
        g = geoms_provinces(d, "ancien_45")
        noms = dict(P[["pcode_province", "province"]].drop_duplicates().values)
        vals = {}
        for c in g["code"]:
            k = int(n.get(c, 0))
            # la couleur porte un comptage, pas une valeur estimée : pas de hachure ici,
            # elle ne ferait que bruiter la carte (la hachure signale une valeur estimée, pas leur nombre)
            vals[c] = dict(valeur=k, impute=False, survol=_survol(nom_propre(noms.get(c, c)), k,
                                                                 la[la["pcode_province"] == c]))
        # bornes fixées par le nombre de types sélectionnés, pas par le maximum observé : l'échelle
        # garde le même sens d'une année à l'autre et la légende peut être dessinée en HTML
        fig = F.carte(g, vals, "nb_imputations", contours_regions=geoms_regions(d, "ancien_45"), hauteur=None,
                      palette=F.ECHELLE_NEUTRE, bornes=(0, _nb_types(typ)), legende=False, note_haut=False)
        # la synthèse est une lecture d'écran : elle groupe sur le libellé affiché
        s = (L.groupby(["type", "source_affichee"]).agg(n=("province", "size"),
                                               annees=("annee_debut", lambda x: ", ".join(
                                                   annee_scolaire(a) for a in sorted(set(x)))))
             .reset_index().sort_values(["type", "n"], ascending=[True, False]))
        if len(s):
            synth = _tableau([html.Th("Type"), html.Th("Source / méthode"),
                              html.Th("Cas", className="col-num"), html.Th("Années")],
                             [html.Tr([html.Td(r.type), html.Td(r.source_affichee), html.Td(fmt_nombre(r.n),
                                                                                   className="col-num"),
                                       html.Td(r.annees, className="col-annees")]) for r in s.itertuples()])
        else:
            synth = alerte("Aucune valeur estimée pour ce type de donnée.",
                           "Toutes les valeurs de ce type affichées dans le tableau de bord ont été relevées.",
                           variante="neutre")
        # colonnes montrées : la source y est celle qui se lit. La colonne `source` reste dans les
        # données de la table — invisible, mais c'est elle que l'export écrit, inchangée.
        cols = [{"name": n_, "id": i} for i, n_ in [("province", "Province"), ("region", "Région"),
                                                     ("annee_scolaire", "Année"), ("type", "Type"),
                                                     ("source_affichee", "Source / méthode")]]
        gg = d.get()["geo_province_geom"]
        gg = gg[~gg["fiabilite_contour"].str.startswith("exact")]
        cont = _tableau([html.Th("Découpage"), html.Th("Province"), html.Th("Fiabilité")],
                        [html.Tr([html.Td("2025" if r.decoupage == "2025_47" else "ancien"),
                                  html.Td(nom_propre(r.province_carte)),
                                  html.Td(r.fiabilite_contour, className="col-fiab")])
                         for r in gg.sort_values(["decoupage", "province_carte"]).itertuples()
                         if r.decoupage == "ancien_45" or r.valeur_heritee_province_mere == 1
                         or "confirmer" in r.fiabilite_contour])
        cont = html.Div([cont,
                         note("Source : OCHA COD-AB Burkina Faso v03 (IGB), valide au 01/08/2025. Ancien découpage "
                              "reconstitué par union des provinces 2025 (exact). Autres provinces : contour officiel "
                              "inchangé. Colonne « Fiabilité » : « exact » = contour repris tel quel du jeu "
                              "officiel ; « valide_equipe » = rattachement décidé par l'équipe, faute de mention "
                              "dans le décret ; une mention « à confirmer » signale un tracé encore à vérifier.")])
        return fig, synth, L.sort_values(["annee_debut", "province"]).to_dict("records"), cols, cont

    @app.callback(Output("qua-sous-titre", "children"), Output("qua-legende", "children"),
                  Output("qua-vide", "children"), Output("qua-note-carte", "children"),
                  Input("qua-annee", "value"), Input("qua-sexe", "value"), Input("qua-type", "value"))
    def cadre(annee, sexe, typ):
        """Habillage de la sélection : périmètre, légende discrète et bonne nouvelle quand rien n'est estimé.
        Aucun chiffre nouveau n'est calculé ici — c'est la même lecture que la carte."""
        nb = _nb_types(typ)
        legende = legende_carte(TITRE_ECHELLE, [fmt_nombre(i) for i in range(nb + 1)], cles=(), echelle="neutre")
        message = ""
        try:
            L = _long(donnees().province(), sexe)
            if typ != "tous":
                L = L[L["cle"] == typ]
            if not len(L[L["annee_debut"] == annee]):
                # un vide qui est une bonne nouvelle doit se lire comme telle
                message = alerte(f"Aucune valeur estimée en {annee_scolaire(annee)}.",
                                 "Toutes les valeurs de l'année et du groupe d'élèves choisis ont été relevées. "
                                 "Le détail plus bas liste les autres années.", variante="neutre")
        except Exception:
            message = ""
        return _sous_titre(annee, sexe), legende, message, _note_carte(nb)

    @app.callback(Output("qua-download", "data"), Input("qua-export-btn", "n_clicks"),
                  State("qua-detail", "derived_virtual_data"), State("qua-sexe", "value"), prevent_initial_call=True)
    def export(n, vues, sexe):
        """Le fichier exporté est la donnée, pas l'écran : les colonnes et les valeurs sont celles du
        modèle. La colonne d'affichage (`source_affichee`), elle, ne sort jamais du navigateur."""
        df = pd.DataFrame(vues or [])
        df = df[[c for c in COLONNES_CSV if c in df.columns]]
        return dcc.send_data_frame(df.to_csv, f"imputations_{sexe}.csv", index=False, sep=";", encoding="utf-8-sig")


def _nb_types(typ):
    """Borne haute de l'échelle : le nombre de types de données que la sélection peut faire compter."""
    return len(TYPES) if typ == "tous" else 1
