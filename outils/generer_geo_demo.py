"""Génère des contours SCHÉMATIQUES du Burkina Faso (45 provinces, 13 régions) pour la démonstration fictive.

Hors ligne et déterministe : aucune requête réseau, aucune dépendance hors numpy.

- Le contour national est saisi à la main (connaissance géographique générale : bosse sahélienne au nord,
  pointe de la Léraba au sud-ouest, pointe de la Tapoa au sud-est, frontières sud presque rectilignes),
  puis densifié et légèrement ondulé pour ne pas ressembler à un croquis à facettes.
- Les 45 provinces sont les cellules de Voronoï de points-graines placés à l'emplacement approximatif des
  chefs-lieux des anciennes provinces, découpées sur le contour (pavage exact : ni trou ni recouvrement).
  Les arêtes intérieures sont ondulées de façon identique pour les deux voisines, donc le pavage reste exact.
- Les 13 régions sont l'union EXACTE de leurs provinces (annulation des arêtes partagées, puis rechaînage).

Le fichier produit ne contient AUCUN attribut réel : seulement « geometry » et l'indice entier de région.
Ce ne sont PAS les limites administratives officielles ; pour une carte officielle, fournir un fichier de
contours via DC_EDU_DEMO_GEO (même format).

python outils/generer_geo_demo.py [fichier_sortie]
"""
import hashlib
import json
import math
import os
import sys

import numpy as np

K = math.cos(math.radians(12.3))  # 1 degré de longitude vaut K degré de latitude à la latitude moyenne du pays
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "dcdash", "geo_demo.json")
NOTE = ("Contours schematiques APPROXIMATIFS generes hors ligne pour la demonstration fictive : ce ne sont pas "
        "les limites administratives officielles du Burkina Faso. Aucun nom ni code reel. Pour une carte "
        "officielle, fournir un fichier de contours equivalent via DC_EDU_DEMO_GEO.")

# Contour national de contrôle, sens horaire, en (longitude, latitude) : extrêmes ≈ lon -5,52…2,41 / lat 9,40…15,08.
CONTOUR = [
    # nord : pointe de l'Oudalan puis tripoint Mali–Niger
    (-0.46, 15.08), (0.23, 14.93),
    # frontière du Niger, vers le sud-est jusqu'à la pointe orientale de la Tapoa
    (0.52, 14.50), (0.72, 14.08), (1.10, 13.65), (1.42, 13.30), (1.72, 12.97), (2.05, 12.55), (2.28, 12.28),
    (2.41, 12.02),
    # frontière du Bénin (Pendjari), vers le sud-ouest
    (2.22, 11.78), (1.95, 11.62), (1.66, 11.47), (1.38, 11.36), (1.10, 11.22), (0.90, 11.08),
    # frontière du Togo, presque rectiligne vers l'ouest
    (0.58, 11.02), (0.30, 10.98), (0.15, 11.10),
    # frontière du Ghana : d'abord vers l'ouest, puis plein sud le long de la Volta noire
    (-0.18, 11.11), (-0.55, 11.06), (-0.92, 11.01), (-1.30, 10.98), (-1.68, 11.00), (-2.05, 10.97), (-2.40, 10.93),
    (-2.55, 10.72), (-2.68, 10.42), (-2.80, 10.10), (-2.89, 9.78), (-2.80, 9.42),
    # frontière de la Côte d'Ivoire, vers le nord-ouest jusqu'au coin de la Léraba
    (-3.02, 9.56), (-3.28, 9.74), (-3.62, 9.89), (-4.00, 9.96), (-4.38, 10.04), (-4.72, 10.14), (-5.08, 10.22),
    (-5.42, 10.33), (-5.52, 10.55),
    # frontière du Mali : remontée de l'ouest, boucle du Mouhoun, puis bosse sahélienne vers le nord-est
    (-5.44, 10.88), (-5.30, 11.22), (-5.20, 11.55), (-5.00, 11.88), (-4.78, 12.12), (-4.56, 12.38), (-4.47, 12.72),
    (-4.22, 13.00), (-3.92, 13.22), (-3.58, 13.34), (-3.32, 13.52), (-3.08, 13.68), (-2.78, 13.82), (-2.42, 13.92),
    (-2.08, 14.04), (-1.82, 14.22), (-1.55, 14.38), (-1.26, 14.58), (-1.00, 14.76), (-0.72, 14.96),
]

# Points-graines des 45 anciennes provinces, dans l'ordre des indices utilisés par la démo (province i ↔ graine i),
# avec l'indice de leur région (0…12). Positions approximatives des chefs-lieux, quelques-unes décalées vers le
# centre de la province pour que les cellules gardent des tailles plausibles. Les noms restent en commentaire :
# rien de tout cela n'est écrit dans le fichier produit.
GRAINES = [
    # 0 Boucle du Mouhoun (6)
    (-2.93, 11.75, 0),   # Balé / Boromo
    (-4.08, 12.18, 0),   # Banwa / Solenzo
    (-3.86, 12.73, 0),   # Kossi / Nouna
    (-3.47, 12.46, 0),   # Mouhoun / Dédougou
    (-2.88, 12.77, 0),   # Nayala / Toma
    (-3.07, 13.07, 0),   # Sourou / Tougan
    # 1 Cascades (2)
    (-4.77, 10.63, 1),   # Comoé / Banfora
    (-5.17, 10.66, 1),   # Léraba / Sindou
    # 2 Centre (1)
    (-1.52, 12.37, 2),   # Kadiogo / Ouagadougou
    # 3 Centre-Est (3)
    (-0.37, 11.78, 3),   # Boulgou / Tenkodogo
    (0.06, 11.50, 3),    # Koulpélogo / Ouargaye
    (-0.35, 12.18, 3),   # Kouritenga / Koupéla
    # 4 Centre-Nord (3)
    (-1.53, 13.32, 4),   # Bam / Kongoussi
    (-0.57, 12.66, 4),   # Namentenga / Boulsa
    (-1.08, 13.09, 4),   # Sanmatenga / Kaya
    # 5 Centre-Ouest (4)
    (-2.30, 12.14, 5),   # Boulkiemdé / Koudougou (décalé)
    (-2.62, 12.42, 5),   # Sanguié / Réo (décalé)
    (-2.10, 11.10, 5),   # Sissili / Léo
    (-1.77, 11.55, 5),   # Ziro / Sapouy
    # 6 Centre-Sud (3)
    (-1.33, 12.07, 6),   # Bazèga / Kombissiri
    (-1.15, 11.17, 6),   # Nahouri / Pô
    (-1.07, 11.66, 6),   # Zoundwéogo / Manga
    # 7 Est (5)
    (-0.14, 12.97, 7),   # Gnagna / Bogandé
    (0.36, 12.06, 7),    # Gourma / Fada N'Gourma
    (0.49, 12.65, 7),    # Komandjoari / Gayéri
    (0.70, 11.25, 7),    # Kompienga / Pama
    (1.79, 12.07, 7),    # Tapoa / Diapaga
    # 8 Hauts-Bassins (3)
    (-4.30, 11.18, 8),   # Houet / Bobo-Dioulasso
    (-4.93, 10.98, 8),   # Kénédougou / Orodara
    (-3.52, 11.50, 8),   # Tuy / Houndé
    # 9 Nord (4)
    (-2.07, 13.77, 9),   # Loroum / Titao
    (-2.26, 12.96, 9),   # Passoré / Yako
    (-2.42, 13.58, 9),   # Yatenga / Ouahigouya
    (-2.36, 13.21, 9),   # Zondoma / Gourcy
    # 10 Plateau-Central (3)
    (-0.62, 12.25, 10),  # Ganzourgou / Zorgho
    (-1.89, 12.66, 10),  # Kourwéogo / Boussé
    (-1.30, 12.58, 10),  # Oubritenga / Ziniaré
    # 11 Sahel (4)
    (-0.23, 14.44, 11),  # Oudalan / Gorom-Gorom
    (-0.03, 14.03, 11),  # Séno / Dori
    (-1.63, 14.10, 11),  # Soum / Djibo
    (0.53, 13.44, 11),   # Yagha / Sebba
    # 12 Sud-Ouest (4)
    (-3.35, 10.85, 12),  # Bougouriba / Diébougou (décalé)
    (-2.95, 11.25, 12),  # Ioba / Dano (décalé)
    (-2.92, 9.88, 12),   # Noumbiel / Batié
    (-3.18, 10.33, 12),  # Poni / Gaoua
]
NB_REGIONS = 13


# --------------------------------------------------------------------------------------------------- géométrie de base

def aire(anneau):
    """Aire signée (formule du lacet) d'un anneau non fermé."""
    s = 0.0
    for i in range(len(anneau)):
        x1, y1 = anneau[i]
        x2, y2 = anneau[(i + 1) % len(anneau)]
        s += x1 * y2 - x2 * y1
    return s / 2


def dedans(point, anneau):
    """Point dans l'anneau (lancer de rayon)."""
    x, y = point
    r = False
    for i in range(len(anneau)):
        x1, y1 = anneau[i]
        x2, y2 = anneau[(i + 1) % len(anneau)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            r = not r
    return r


def _croise(a, b, c, d):
    """Les segments ouverts [a,b] et [c,d] se croisent-ils franchement (sommets partagés exclus) ?"""
    def o(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return (v > 1e-12) - (v < -1e-12)
    if a in (c, d) or b in (c, d):
        return False
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def simple(anneau):
    """Anneau sans auto-intersection (contrôle en force brute, anneaux courts)."""
    n = len(anneau)
    seg = [(anneau[i], anneau[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 2, n if i else n - 1):
            if _croise(*seg[i], *seg[j]):
                return False
    return True


def _courbe(a, b, nb=3, part=0.11, maxi=0.028):
    """Points intermédiaires ondulés entre a et b (déplacement perpendiculaire déterministe, dérivé des extrémités).

    Les deux voisines d'une arête appellent cette fonction sur la même paire ordonnée : l'ondulation est identique
    des deux côtés, donc le pavage reste exact.
    """
    dx, dy = b[0] - a[0], b[1] - a[1]
    long = math.hypot(dx, dy)
    if long < 0.09:
        return []
    cle = "|".join(f"{v:.6f}" for v in (*a, *b))
    rng = np.random.default_rng(int.from_bytes(hashlib.blake2b(cle.encode(), digest_size=8).digest(), "big"))
    c1, c2 = float(rng.uniform(-1, 1)), float(rng.uniform(-0.45, 0.45))
    amp = min(part * long, maxi)
    ux, uy = -dy / long, dx / long
    pts = []
    for i in range(1, nb + 1):
        f = i / (nb + 1)
        d = amp * (c1 * math.sin(math.pi * f) + c2 * math.sin(2 * math.pi * f))
        pts.append((a[0] + dx * f + ux * d, a[1] + dy * f + uy * d))
    return pts


def contour(pas=0.28):
    """Contour national en repère local (x = longitude × K, y = latitude), sens anti-horaire, densifié et ondulé."""
    brut = [(lon * K, lat) for lon, lat in CONTOUR]
    pts = []
    for i, a in enumerate(brut):
        b = brut[(i + 1) % len(brut)]
        pts.append(a)
        nb = int(math.hypot(b[0] - a[0], b[1] - a[1]) / pas)
        pts.extend(_courbe(a, b, nb=nb, part=0.085, maxi=0.035) if nb else [])
    if aire(pts) < 0:
        pts.reverse()
    return pts


# ------------------------------------------------------------------------------------------- découpage par demi-plans

def _couper_anneau(anneau, n, c, eps=1e-12):
    """Découpe un anneau anti-horaire par le demi-plan n·p ≤ c. Retourne 0, 1 ou plusieurs anneaux."""
    v = [n[0] * p[0] + n[1] * p[1] - c for p in anneau]
    if max(v) <= eps:
        return [anneau]
    if min(v) >= -eps:
        return []
    m = len(anneau)
    aug = []  # (point, 0 = sommet intérieur, 1 = entrée, -1 = sortie)
    for i in range(m):
        p, q, vp, vq = anneau[i], anneau[(i + 1) % m], v[i], v[(i + 1) % m]
        if vp <= eps:
            aug.append((p, 0))
        if (vp > eps) != (vq > eps):
            t = vp / (vp - vq)
            aug.append(((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])), -1 if vp <= eps else 1))
    k = len(aug)
    chaines = {}
    for i in (j for j in range(k) if aug[j][1] == 1):
        pts, j = [aug[i][0]], (i + 1) % k
        while aug[j][1] == 0:
            pts.append(aug[j][0])
            j = (j + 1) % k
        if aug[j][1] != -1:
            raise RuntimeError("découpage : chaîne intérieure mal formée")
        chaines[i] = (pts + [aug[j][0]], j)
    # le long de la droite de coupe, orientée d = n tourné de +90°, le côté conservé est à gauche :
    # après une sortie, la frontière suit d jusqu'à l'entrée suivante.
    pos = {i: aug[i][0][0] * -n[1] + aug[i][0][1] * n[0] for i in range(k) if aug[i][1]}
    ordre = sorted(pos, key=lambda i: pos[i])
    suivant = {}
    for a, b in zip(ordre, ordre[1:]):
        if aug[a][1] == -1:
            if aug[b][1] != 1:
                raise RuntimeError("découpage : intersections non alternées")
            suivant[a] = b
    anneaux, vus = [], set()
    for i in chaines:
        if i in vus:
            continue
        ring, j = [], i
        while j not in vus:
            vus.add(j)
            pts, sortie = chaines[j]
            ring.extend(pts)
            j = suivant[sortie]
        ring = _nettoyer(ring)
        if len(ring) >= 3:
            anneaux.append(ring)
    return anneaux


def _nettoyer(anneau, eps=1e-10):
    """Retire les points consécutifs confondus (et la fermeture éventuelle)."""
    out = []
    for p in anneau:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    while len(out) > 1 and abs(out[0][0] - out[-1][0]) <= eps and abs(out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


def cellules(anneau, graines):
    """Cellules de Voronoï des graines découpées sur le contour : liste (par graine) de listes d'anneaux."""
    out = []
    for i, (xi, yi) in enumerate(graines):
        anneaux = [anneau]
        for j, (xj, yj) in enumerate(graines):
            if i == j:
                continue
            n = (2 * (xj - xi), 2 * (yj - yi))
            c = xj * xj + yj * yj - xi * xi - yi * yi
            anneaux = [r for a in anneaux for r in _couper_anneau(a, n, c)]
            if not anneaux:
                break
        if not anneaux:
            raise RuntimeError(f"cellule {i} vide : graine hors contour ou graines confondues")
        out.append(anneaux)
    return out


# ---------------------------------------------------------------------------------- recollement exact des frontières

class Points:
    """Registre de points avec accrochage : deux calculs du même sommet de Voronoï reçoivent le même identifiant."""

    def __init__(self, tol=1e-7):
        self.liste, self.index, self.tol = [], {}, tol

    def id(self, x, y):
        cx, cy = round(x / self.tol), round(y / self.tol)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in self.index.get((cx + dx, cy + dy), ()):
                    if abs(self.liste[i][0] - x) <= self.tol and abs(self.liste[i][1] - y) <= self.tol:
                        return i
        self.index.setdefault((cx, cy), []).append(len(self.liste))
        self.liste.append((x, y))
        return len(self.liste) - 1


def _unir(anneaux):
    """Union exacte d'anneaux adjacents donnés en identifiants de points : annule les arêtes partagées, rechaîne."""
    arcs = {}
    for ring in anneaux:
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            if arcs.get((b, a)):
                arcs[(b, a)] -= 1
                if not arcs[(b, a)]:
                    del arcs[(b, a)]
            else:
                arcs[(a, b)] = arcs.get((a, b), 0) + 1
    suiv = {}
    for (a, b), n in arcs.items():
        if n != 1:
            raise RuntimeError("union : arête répétée")
        suiv.setdefault(a, []).append(b)
    out = []
    while suiv:
        depart = next(iter(suiv))
        ring, a = [depart], depart
        while True:
            b = suiv[a].pop()
            if not suiv[a]:
                del suiv[a]
            if b == depart:
                break
            ring.append(b)
            a = b
            if a not in suiv:
                raise RuntimeError("union : chaîne ouverte")
        out.append(ring)
    return out


def pavage():
    """Construit le pavage : (anneaux de provinces, anneaux de régions, contour), en identifiants de points."""
    pays = contour()
    graines = [(lon * K, lat) for lon, lat, _ in GRAINES]
    for i, g in enumerate(graines):
        if not dedans(g, pays):
            raise RuntimeError(f"graine {i} hors du contour national")
    pts = Points()
    brutes = [[[pts.id(*p) for p in _nettoyer(r)] for r in c] for c in cellules(pays, graines)]
    # arêtes intérieures (présentes dans deux cellules) : une ondulation commune, insérée dans les deux sens
    occur = {}
    for ci, anneaux in enumerate(brutes):
        for ri, ring in enumerate(anneaux):
            for i in range(len(ring)):
                a, b = ring[i], ring[(i + 1) % len(ring)]
                occur.setdefault((min(a, b), max(a, b)), []).append(ci)
    ondul = {}
    for (a, b), cs in occur.items():
        if len(cs) == 2 and cs[0] != cs[1]:
            ondul[(a, b)] = [pts.id(*p) for p in _courbe(pts.liste[a], pts.liste[b])]
    provinces = []
    for anneaux in brutes:
        rings = []
        for ring in anneaux:
            out = []
            for i in range(len(ring)):
                a, b = ring[i], ring[(i + 1) % len(ring)]
                out.append(a)
                sup = ondul.get((min(a, b), max(a, b)))
                if sup:
                    out.extend(sup if a < b else sup[::-1])
            rings.append(out)
        provinces.append(rings)
    regions = [_unir([r for i, c in enumerate(provinces) if GRAINES[i][2] == k for r in c])
               for k in range(NB_REGIONS)]
    return provinces, regions, pays, pts


# ----------------------------------------------------------------------------------------------------------- sortie

def _geometrie(anneaux, pts, nd=4):
    """MultiPolygon GeoJSON en degrés (longitude, latitude), coordonnées arrondies."""
    polys = []
    for ring in anneaux:
        r = _nettoyer([(round(pts.liste[i][0] / K, nd), round(pts.liste[i][1], nd)) for i in ring], eps=1e-9)
        if len(r) >= 3 and abs(aire(r)) > 1e-7:
            polys.append([[list(p) for p in r] + [list(r[0])]])
    if not polys:
        raise RuntimeError("géométrie vide après arrondi")
    return {"type": "MultiPolygon", "coordinates": polys}


def construire():
    """Dictionnaire prêt à écrire : 45 provinces (geometry + indice de région) et 13 régions."""
    provinces, regions, pays, pts = pavage()
    for i, anneaux in enumerate(provinces):
        for ring in anneaux:
            if not simple([pts.liste[j] for j in ring]):
                raise RuntimeError(f"province {i} : anneau auto-intersecté (réduire l'ondulation)")
    ap = sum(abs(aire([pts.liste[j] for j in r])) for c in provinces for r in c)
    ar = sum(abs(aire([pts.liste[j] for j in r])) for c in regions for r in c)
    api = abs(aire(pays))
    if abs(ap - api) / api > 1e-6 or abs(ar - api) / api > 1e-6:
        raise RuntimeError(f"pavage non exact : provinces {ap:.6f}, régions {ar:.6f}, pays {api:.6f}")
    return {"note": NOTE,
            "provinces": [{"geometry": _geometrie(c, pts), "region": GRAINES[i][2]}
                          for i, c in enumerate(provinces)],
            "regions": [{"geometry": _geometrie(c, pts)} for c in regions]}, (provinces, regions, pays, pts)


def main():
    sortie = sys.argv[1] if len(sys.argv) > 1 else SORTIE
    os.umask(0o077)
    data, (provinces, regions, pays, _) = construire()
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        f.write("\n")
    km2 = 111.32 * 110.57  # 1 unité du repère local ≈ 1 degré de latitude dans les deux directions
    lons = [c[0] for p in data["provinces"] for poly in p["geometry"]["coordinates"] for c in poly[0]]
    lats = [c[1] for p in data["provinces"] for poly in p["geometry"]["coordinates"] for c in poly[0]]
    print(f"{sortie} : {len(data['provinces'])} provinces, {len(data['regions'])} régions, "
          f"contour {len(pays)} sommets")
    print(f"emprise lon {min(lons):.2f}…{max(lons):.2f} · lat {min(lats):.2f}…{max(lats):.2f} · "
          f"superficie ≈ {abs(aire(pays)) * km2:,.0f} km2".replace(",", " "))
    print("anneaux par région : " + " ".join(str(len(r)) for r in regions)
          + " · sommets par province : " + f"min {min(sum(len(r) for r in c) for c in provinces)}, "
          f"max {max(sum(len(r) for r in c) for c in provinces)}")


if __name__ == "__main__":
    main()
