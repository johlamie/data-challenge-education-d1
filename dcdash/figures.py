"""Figures Plotly entièrement hors ligne.

Les cartes sont dessinées comme des polygones remplis sur des axes cartésiens (projection équirectangulaire
corrigée de la latitude) : aucune tuile, aucun topojson ni fichier distant n'est chargé par le navigateur.
"""
import math

import numpy as np
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from .meta import INDICATEURS, fmt_valeur

# ---------------------------------------------------------------------------
# Jetons de couleur : copie fidèle de assets/tokens.css (Plotly ne lit pas le CSS).
# Toute modification ici doit être reportée dans assets/tokens.css, et inversement.
# ---------------------------------------------------------------------------
INK = "#15201D"
INK_2 = "#49544F"
INK_3 = "#5E6965"
SURFACE_1 = "#FFFFFF"
LINE_STRONG = "#C2CAC7"
ACCENT = "#0F6A5A"
GRILLE = "#EEF0F2"
AXE_ZERO = "#9AA5A1"

# échelle du risque : une seule teinte séquentielle (ColorBrewer Reds), sûre pour toutes les formes de
# daltonisme — elle varie en clarté, le canal que chacune conserve. Elle remplace l'arc-en-ciel YlOrRd.
ECHELLE_RISQUE = ["#FFF0E8", "#FEE0D2", "#FCBBA1", "#FC9272", "#FB6A4A", "#EF3B2C", "#CB181D", "#A50F15", "#67000D"]
# échelle neutre (compte d'imputations) : les bleus de la carte de localisation, jamais le rouge du risque
ECHELLE_NEUTRE = ["#F2F7FC", "#E1ECF7", "#CBDDF0", "#A8C8E8", "#86B0DC", "#6798CE", "#4A7CB8", "#2F609C", "#1D3F6E"]
# Okabe-Ito, ses deux membres inutilisables remplacés
OKABE_ITO = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9", "#E69F00", "#882255", "#2B2B2B"]
SERIE_NATIONALE = "#8A948F"
SERIE_ACLED = "#D55E00"
SERIE_PDI = "#0072B2"
CONTRIB_PLUS = "#CB181D"
CONTRIB_MOINS = "#0072B2"
GRIS_ND = "#D9D9D9"
HACHURE = "rgba(20,20,20,0.6)"
# cartes : un filet gris entre provinces (avec une rampe monochrome, un filet blanc laisserait une
# province à faible risque sans contour visible) ; blanc au contraire sur la carte de localisation.
CARTE_TRAIT = "#DCE1DF"
CARTE_TRAIT_LOCALI = "#FFFFFF"
# (plus de contour « top 10 » : ce code visuel a été retiré des cartes)
CARTE_CONTOUR_REGION = "#7B8794"
CARTE_CHOISIE = "#1d3f6e"
CARTE_REGION = "#A8C8E8"
CARTE_REGION_TRAIT = "#1D4F91"
CARTE_AUTRE = "#E8EAEC"

POLICE = dict(family="system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
              size=12, color=INK_2)
CONFIG = {"displaylogo": False, "responsive": True, "scrollZoom": False, "showLink": False, "showSendToCloud": False,
          "showEditInChartStudio": False,
          "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines",
                                     "hoverClosestCartesian", "hoverCompareCartesian", "sendDataToCloud"],
          "toImageButtonOptions": {"format": "png", "scale": 2}, "locale": "fr"}
# cartes : ni déplacement ni zoom (le pays reste cadré) ; double-clic = recadrage ; survol actif
CONFIG_CARTE = {**CONFIG, "scrollZoom": False, "doubleClick": "reset", "displayModeBar": False}
COS_LAT = math.cos(math.radians(12.3))  # latitude moyenne du Burkina Faso


def _anneaux(geom):
    """Liste des x, y (séparés par None) d'une géométrie Polygon ou MultiPolygon GeoJSON."""
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    xs, ys = [], []
    for poly in polys:
        for ring in poly:
            xs.extend(p[0] for p in ring)
            ys.extend(p[1] for p in ring)
            xs.append(None)
            ys.append(None)
    return xs, ys


def echelle(cle):
    sens = INDICATEURS.get(cle, {}).get("sens", 1)
    if sens == 0:
        return ECHELLE_NEUTRE
    if sens < 0:
        return ECHELLE_RISQUE[::-1]
    return ECHELLE_RISQUE


def _bornes(vals, cle):
    v = np.asarray([x for x in vals if x is not None and x == x], dtype=float)
    if cle == "proba_risque_t1":
        return 0.0, 1.0
    if not len(v):
        return 0.0, 1.0
    lo, hi = float(v.min()), float(v.max())
    if lo == hi:
        hi = lo + 1
    return lo, hi


def bornes(vals, cle):
    """Bornes de l'échelle de couleur d'une carte (utilisées aussi par la légende discrète en HTML)."""
    return _bornes(vals, cle)


def emprise(geoms, marge=0.02):
    """Emprise [xmin, xmax], [ymin, ymax] des géométries (cadrage sur le pays), avec une petite marge."""
    xs, ys = [], []
    for geom in geoms:
        a, b = _anneaux(geom)
        xs += [x for x in a if x is not None]
        ys += [y for y in b if y is not None]
    if not xs:
        return None, None
    dx, dy = (max(xs) - min(xs)) * marge or 0.1, (max(ys) - min(ys)) * marge or 0.1
    return [min(xs) - dx, max(xs) + dx], [min(ys) - dy, max(ys) + dy]


def verrouiller(fig, geoms):
    """Carte fixe : cadrée sur l'emprise du pays, sans glisser ni zoomer (fixedrange), survol conservé."""
    rx, ry = emprise(geoms)
    fig.update_layout(dragmode=False)
    fig.update_xaxes(fixedrange=True, range=rx, autorange=False if rx else True)
    fig.update_yaxes(fixedrange=True, range=ry, autorange=False if ry else True)
    return fig


def figure_vide(message, hauteur=420):
    """Un vide dit pourquoi : la phrase nomme la raison, jamais « aucune donnée », jamais un zéro."""
    f = go.Figure()
    f.add_annotation(text=message, showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper",
                     font=dict(size=14, color=INK_2))
    f.update_layout(height=hauteur, autosize=hauteur is None, xaxis_visible=False, yaxis_visible=False,
                    plot_bgcolor=SURFACE_1, paper_bgcolor=SURFACE_1, font=POLICE,
                    margin=dict(l=8, r=8, t=8, b=8))
    return f


def carte(geoms, valeurs, cle, contours_regions=None, gras=(), hauteur=540, titre_echelle=None, legende=True,
          palette=None, bornes=None, note_haut=True):
    """Carte choroplèthe.

    geoms : DataFrame [code, nom, geometrie] ; valeurs : dict code -> dict(valeur, impute, survol).
    contours_regions : DataFrame [geometrie] (traits épais).

    `gras` n'est plus dessiné : le contour noir des dix provinces les plus à risque a été retiré
    (code visuel non compris et peu lisible à cette épaisseur ;
    le top 10 se lit dans le classement, à côté de la carte). Le paramètre reste accepté pour ne
    casser aucun appel existant, et il n'a plus d'effet, pas même dans la note.
    """
    m = INDICATEURS.get(cle, {})
    sc = palette or echelle(cle)
    vals = [valeurs.get(c, {}).get("valeur") for c in geoms["code"]]
    lo, hi = bornes or _bornes(vals, cle)
    fig = go.Figure()
    meta = []
    nb_imp = 0
    for code, nom, geom in zip(geoms["code"], geoms["nom"], geoms["geometrie"]):
        info = valeurs.get(code, {})
        v = info.get("valeur")
        imp = bool(info.get("impute"))
        nb_imp += imp
        if v is None or v != v:
            couleur = GRIS_ND
        else:
            couleur = sample_colorscale(sc, [min(max((float(v) - lo) / (hi - lo), 0), 1)])[0]
        xs, ys = _anneaux(geom)
        texte = info.get("survol") or f"<b>{nom}</b><br>{m.get('label', cle)} : {fmt_valeur(v, cle)}"
        trace = dict(x=xs, y=ys, mode="lines", fill="toself", fillcolor=couleur, name=nom,
                     line=dict(color=CARTE_TRAIT, width=0.6),
                     hoveron="fills", hoverinfo="text", text=texte, showlegend=False)
        if imp:
            # une valeur estimée ne se distingue jamais par la couleur seule : hachure à 45°
            trace["fillpattern"] = dict(shape="/", fgcolor=HACHURE, bgcolor=couleur, size=7, solidity=0.25)
        fig.add_trace(go.Scatter(**trace))
        meta.append(code)
    if contours_regions is not None:
        xs, ys = [], []
        for geom in contours_regions["geometrie"]:
            a, b = _anneaux(geom)
            xs += a
            ys += b
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=CARTE_CONTOUR_REGION, width=1.6),
                                 hoverinfo="skip", showlegend=False))
        meta.append(None)
    if legende:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", hoverinfo="skip", showlegend=False,
            marker=dict(colorscale=sc, cmin=lo, cmax=hi, color=[lo], showscale=True,
                        colorbar=dict(orientation="h", y=-0.02, yanchor="top", x=0.5, xanchor="center", len=0.85,
                                      thickness=12, outlinewidth=0, tickfont=dict(size=12, color=INK_3),
                                      title=dict(text=titre_echelle or m.get("label", cle), side="top",
                                                 font=dict(size=12, color=INK_2)),
                                      tickformat=m.get("fmt", ".0f").replace(",", "")))))
        meta.append(None)
    note = "Gris : non disponible"
    if nb_imp:
        note = "Hachures : valeur imputée · " + note
    if note_haut:
        fig.add_annotation(text=note, showarrow=False, x=0, y=1.0, xref="paper", yref="paper", xanchor="left",
                           yanchor="bottom", font=dict(size=12, color=INK_3))
    # la légende et la note vivent hors du tracé (HTML) quand la page les dessine elle-même :
    # on ne réserve alors plus la bande du bas, et le pays occupe toute la hauteur du panneau.
    # La boîte est déjà au format du pays (règle commune) : aucune marge à lui reprendre.
    externe = not legende and not note_haut
    fig.update_layout(height=hauteur, autosize=hauteur is None,
                      margin=dict(l=0 if externe else 4, r=0 if externe else 4,
                                  t=24 if note_haut else (0 if externe else 4),
                                  b=64 if legende else (0 if externe else 4)),
                      plot_bgcolor=SURFACE_1, paper_bgcolor=SURFACE_1, font=POLICE, meta=meta, separators=", ",
                      hoverlabel=dict(bgcolor=SURFACE_1, bordercolor=LINE_STRONG, font_size=12,
                                      font_color=INK, namelength=-1, align="left"),
                      xaxis=dict(visible=False, scaleanchor="y", scaleratio=COS_LAT, constrain="domain"),
                      yaxis=dict(visible=False))
    return verrouiller(fig, geoms["geometrie"])


def carte_localisation(geoms, code_sel, contours_regions=None, hauteur=200, survols=None, region_sel=None):
    """Carte de localisation : la province choisie en bleu foncé, toutes les provinces de sa région en
    bleu clair, le reste du pays en gris neutre, et le contour extérieur de la région en bleu, 2 px.

    Les deux remplissages bleus ne sont séparés que de 1,44:1 : c'est ce trait de 2 px, pas la teinte,
    qui porte la région sur un petit écran. La région est lue dans `pcode_region_carte`, déjà renvoyé
    par vues.geoms_provinces() — aucune requête ni aucun calcul nouveau.

    survols : dict code -> texte ; s'il est donné, le nom s'affiche au survol et la carte émet des clics (fiche)."""
    regions = geoms["pcode_region_carte"] if "pcode_region_carte" in geoms else None
    if region_sel is None and regions is not None:
        sel = [r for c, r in zip(geoms["code"], regions) if c == code_sel]
        region_sel = sel[0] if sel else None
    fig = go.Figure()
    for i, (code, geom) in enumerate(zip(geoms["code"], geoms["geometrie"])):
        xs, ys = _anneaux(geom)
        survol = dict(hoverinfo="text", hoveron="fills", text=survols.get(code, "")) if survols else dict(hoverinfo="skip")
        if code == code_sel:
            couleur = CARTE_CHOISIE
        elif region_sel is not None and regions is not None and regions.iloc[i] == region_sel:
            couleur = CARTE_REGION
        else:
            couleur = CARTE_AUTRE
        # filet blanc un peu plus épais sous la province choisie : sur un panneau de 300 px de haut,
        # c'est lui qui la détache de ses voisines bleu clair, sans ajouter de couleur
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", showlegend=False, fillcolor=couleur,
                                 line=dict(color=CARTE_TRAIT_LOCALI, width=1.2 if code == code_sel else 0.5),
                                 **survol))
    if contours_regions is not None and region_sel is not None and "pcode_region" in contours_regions:
        c = contours_regions[contours_regions["pcode_region"] == region_sel]
        xs, ys = [], []
        for geom in c["geometrie"]:
            a, b = _anneaux(geom)
            xs += a
            ys += b
        if xs:
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=CARTE_REGION_TRAIT, width=2),
                                     hoverinfo="skip", showlegend=False))
    fig.update_layout(height=hauteur, autosize=hauteur is None, margin=dict(l=0, r=0, t=0, b=0),
                      plot_bgcolor=SURFACE_1, paper_bgcolor=SURFACE_1, font=POLICE,
                      hoverlabel=dict(bgcolor=SURFACE_1, bordercolor=LINE_STRONG, font_size=12,
                                      font_color=INK, namelength=-1, align="left"),
                      xaxis=dict(visible=False, scaleanchor="y", scaleratio=COS_LAT, constrain="domain"),
                      yaxis=dict(visible=False))
    return verrouiller(fig, geoms["geometrie"])


MAX_ETIQUETTES_FIN = 5  # au-delà, les noms de bout de tracé se marchent dessus : la légende reprend la main
HAUTEUR_LIGNE_ETIQUETTE = 18  # hauteur d'une ligne de texte de 12 px, interligne compris


def evolution(series, titre_y, hauteur=440, fmt=".1f", etiquettes_fin=False):
    """series : liste de dict(nom, x, y, couleur, tiret, imputes(list bool), sources(list str)).

    Deux drapeaux facultatifs par série : `etiquette` (nommer la courbe au bout de son tracé) et
    `legende` (apparaître dans la légende Plotly) — une courbe de contrôle reste ainsi silencieuse
    des deux côtés, sans disparaître du graphique.

    etiquettes_fin : chaque courbe est nommée au bout de son tracé et la légende Plotly s'efface.
    L'identité d'une série ne repose jamais sur la couleur seule : sous 1024 px la page masque ces
    étiquettes (elles ne tiennent pas) et affiche des pastilles nommées à la place."""
    fig = go.Figure()
    for s in series:
        imp = s.get("imputes") or [False] * len(s["x"])
        src = s.get("sources") or [""] * len(s["x"])
        hov = [f"{s['nom']}<br>{x}-{x + 1} : {('n.d.' if y is None or y != y else format(y, fmt).replace('.', ','))}"
               + (f"<br><i>* imputé : {so}</i>" if i else "") for x, y, i, so in zip(s["x"], s["y"], imp, src)]
        fig.add_trace(go.Scatter(
            x=s["x"], y=s["y"], name=s["nom"], mode="lines+markers", legendgroup=s.get("groupe", s["nom"]),
            showlegend=s.get("legende", True),
            line=dict(color=s["couleur"], dash=s.get("tiret", "solid"), width=s.get("epaisseur", 2.4)),
            marker=dict(symbol=["circle-open" if i else "circle" for i in imp], size=[11 if i else 6 for i in imp],
                        line=dict(width=2, color=s["couleur"]), color=s["couleur"]),
            text=hov, hovertemplate="%{text}<extra></extra>"))
    # les noms de bout de tracé ne sont tenables qu'en petit nombre : au-delà, ils se chevauchent entre
    # eux et sur les courbes. La légende Plotly reprend alors l'identité des séries, sans rien perdre.
    fins = []
    if etiquettes_fin:
        for s in series:
            pts = [(x, float(y)) for x, y in zip(s["x"], s["y"]) if y is not None and y == y]
            if pts and s.get("etiquette", True):
                fins.append([pts[-1][0], pts[-1][1], s["nom"], s["couleur"]])
    nommer_au_bout = etiquettes_fin and 0 < len(fins) <= MAX_ETIQUETTES_FIN
    annees = list(range(2017, 2025))
    # une année sur deux porte son étiquette, la dernière toujours : huit libellés « 2017-18 »
    # ne tiennent pas côte à côte sur un écran de 390 px, et la grille garde toutes les années.
    etiq_x = [f"{a}-{str(a + 1)[2:]}" if (2024 - a) % 2 == 0 else "" for a in annees]
    fig.update_layout(height=hauteur, autosize=hauteur is None,
                      margin=dict(l=48, r=128 if nommer_au_bout else 12, t=8, b=40), plot_bgcolor=SURFACE_1,
                      paper_bgcolor=SURFACE_1, font=POLICE, separators=", ", hovermode="closest",
                      showlegend=not nommer_au_bout,
                      hoverlabel=dict(bgcolor=SURFACE_1, bordercolor=LINE_STRONG, font_size=12, font_color=INK,
                                      namelength=-1, align="left"),
                      legend=dict(orientation="h", y=-0.15, yanchor="top", x=0, font=dict(size=12, color=INK_2)),
                      xaxis=dict(tickmode="array", tickvals=annees, ticktext=etiq_x, gridcolor=GRILLE,
                                 linecolor=GRILLE, tickfont=dict(size=12, color=INK_3)),
                      # automargin : la marge de gauche s'élargit d'elle-même si le titre d'axe et ses
                      # graduations ne tiennent pas dans les 48 px — un titre rogné n'est pas lisible
                      yaxis=dict(title=dict(text=titre_y, font=dict(size=12, color=INK_2)), gridcolor=GRILLE,
                                 zerolinecolor=AXE_ZERO, tickfont=dict(size=12, color=INK_3), automargin=True))
    if nommer_au_bout:
        def plier(nom, n=19):
            """Un nom plus long que la marge passe à la ligne : une étiquette de courbe se plie, elle ne
            se coupe pas — une étiquette coupée ferait lire un faux nom de province."""
            if len(nom) <= n:
                return nom
            lignes, ligne = [], ""
            for mot in nom.split(" "):
                essai = (ligne + " " + mot).strip()
                if ligne and len(essai) > n:
                    lignes.append(ligne)
                    ligne = mot
                else:
                    ligne = essai
            return "<br>".join(lignes + [ligne])

        toutes = [float(y) for s in series for y in s["y"] if y is not None and y == y]
        # Deux courbes qui finissent au même niveau auraient deux étiquettes superposées : on les
        # écarte d'une ligne de texte, puis on étire l'axe pour qu'aucune ne sorte du cadre.
        # L'écart se mesure en pixels, pas en unités de l'axe : étirer l'axe écrase l'écart déjà
        # calculé, donc on reprend le calcul jusqu'à ce que l'étendue ne bouge plus (le point fixe
        # existe tant que les étiquettes tiennent dans la hauteur, ce que MAX_ETIQUETTES_FIN garantit).
        hauteur_tracee = max((hauteur or 440) - 48, 120)
        fins.sort(key=lambda f: -f[1])
        depart = [f[1] for f in fins]
        bas, haut = min(toutes), max(toutes)
        ys = list(depart)
        for _ in range(8):
            etendue = (haut - bas) or abs(haut) or 1.0
            pas = etendue * HAUTEUR_LIGNE_ETIQUETTE / hauteur_tracee
            ys = list(depart)
            for i in range(1, len(ys)):
                ys[i] = min(ys[i], ys[i - 1] - pas)
            marge = 0.06 * ((max(max(toutes), ys[0]) - min(min(toutes), ys[-1])) or 1)
            n_bas, n_haut = min(min(toutes), ys[-1]) - marge, max(max(toutes), ys[0]) + marge
            if abs(n_bas - bas) < 1e-12 and abs(n_haut - haut) < 1e-12:
                break
            bas, haut = n_bas, n_haut
        fig.update_yaxes(range=[bas, haut])
        for (x, _, nom, couleur), y in zip(fins, ys):
            fig.add_annotation(x=x, y=y, text=plier(nom), showarrow=False, xanchor="left", yanchor="middle",
                               xshift=8, align="left", font=dict(size=12, color=couleur))
    return fig


def barres_contributions(noms, valeurs, total, hauteur=320):
    """Une contribution qui fait monter le score prend le rouge haut de l'échelle du risque : une barre
    positive est de la même teinte qu'une province très à risque sur la carte.

    Anatomie des barres de contribution : une colonne de libellés alignés à
    droite, une piste grise de 18 px par composante, le zéro au quart de la largeur (le quart de gauche
    est la place des contributions négatives), la valeur signée dans la barre — juste à côté quand la
    barre est trop courte pour la contenir. **Aucun axe gradué** : ce sont six contributions à comparer
    entre elles, pas une échelle à lire.

    `total` reste dans la signature : la somme est désormais écrite en toutes lettres par la page, au-dessus
    du graphique (une note de bloc se lit mieux qu'un titre de tracé et ne rogne pas la hauteur utile).
    `hauteur=None` : la figure se dimensionne sur ses lignes (18 px de piste, 16 px d'écart)."""
    piste, ecart = 18, 16  # hauteur d'une piste et écart entre deux pistes
    n = len(noms)
    if hauteur is None:
        hauteur = n * (piste + ecart) + 16
    finies = [v for v in valeurs if v == v]
    plus, moins = max(finies + [0.0]), -min(finies + [0.0])
    # zéro au quart de la largeur : x0 est le bord gauche, x1 = -3 × x0 place donc le zéro à 25 %
    x0 = -max(moins * 1.08, plus * 1.08 / 3, 1e-6)
    x1 = -3 * x0
    couleurs = [CONTRIB_PLUS if v >= 0 else CONTRIB_MOINS for v in valeurs]
    fig = go.Figure()
    # la piste : le fond sur lequel la barre se lit, exactement à la hauteur de la barre
    fig.add_trace(go.Bar(x=[x1 - x0] * n, base=[x0] * n, y=noms, orientation="h", hoverinfo="skip",
                         showlegend=False, marker=dict(color=GRILLE, cornerradius=4)))
    fig.add_trace(go.Bar(
        x=valeurs, y=noms, orientation="h", showlegend=False,
        marker=dict(color=couleurs, cornerradius=4),
        text=[f"<b>{format(v, '+.2f')}</b>".replace(".", ",").replace("-", "−") for v in valeurs],
        textposition="auto", insidetextanchor="end", constraintext="none",
        insidetextfont=dict(size=11, color=SURFACE_1), outsidetextfont=dict(size=11, color=INK),
        hovertemplate="%{y} : %{x:+.3f}<extra></extra>", cliponaxis=False))
    fig.add_vline(x=0, line_color=AXE_ZERO, line_width=1)
    fig.update_layout(height=hauteur, barmode="overlay", bargap=ecart / (piste + ecart),
                      margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor=SURFACE_1, paper_bgcolor=SURFACE_1,
                      font=POLICE, separators=", ",
                      hoverlabel=dict(bgcolor=SURFACE_1, bordercolor=LINE_STRONG, font_size=12, font_color=INK,
                                      namelength=-1, align="left"),
                      xaxis=dict(visible=False, fixedrange=True, range=[x0, x1]),
                      yaxis=dict(autorange="reversed", automargin=True, fixedrange=True, showgrid=False,
                                 zeroline=False, showline=False, tickfont=dict(size=12, color=INK_2)))
    return fig
