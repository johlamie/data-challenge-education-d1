"""Rendu headless de chaque page (Playwright/Chromium) : erreurs JS, requêtes externes, temps, captures.

Usage : python outils/captures.py URL_BASE DOSSIER_CAPTURES [--code-stdin]
Avec --code-stdin, le code d'accès est lu sur l'entrée standard (jamais écrit sur disque ni affiché).
Le résumé imprimé ne contient aucune valeur de données (comptes et durées uniquement).
"""
import json
import os
import sys
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

PAGES = [("accueil", "/"), ("classement", "/classement"), ("evolution", "/evolution"), ("fiche", "/fiche"),
         ("qualite", "/qualite"), ("methode", "/methode")]
TAILLES = {"bureau": {"width": 1440, "height": 900}, "mobile": {"width": 390, "height": 844}}


def attendre_rendu(page, timeout=30000):
    page.wait_for_load_state("networkidle", timeout=timeout)
    page.wait_for_function("""() => !document.querySelector('[data-dash-is-loading="true"]')
        && !document.querySelector('._dash-loading') && document.querySelector('#page') &&
        document.querySelector('#page').children.length > 0""", timeout=timeout)
    page.wait_for_timeout(600)


def main():
    base, dossier = sys.argv[1].rstrip("/"), sys.argv[2]
    code = sys.stdin.readline().strip() if "--code-stdin" in sys.argv else None
    os.umask(0o077)
    os.makedirs(dossier, mode=0o700, exist_ok=True)
    hote = urlparse(base).netloc
    res = {"pages": [], "requetes_externes": [], "erreurs_js": [], "console_erreurs": [], "echecs_requetes": []}
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=True, args=["--no-sandbox"], executable_path=os.environ.get("CHROME") or None)
        for taille, vp in TAILLES.items():
            ctx = nav.new_context(viewport=vp, locale="fr-FR", accept_downloads=True,
                                  device_scale_factor=2 if taille == "mobile" else 1)
            page = ctx.new_page()
            page.on("pageerror", lambda e: res["erreurs_js"].append(str(e)[:300]))
            page.on("console", lambda m: m.type == "error" and res["console_erreurs"].append(m.text[:300]))
            page.on("requestfailed", lambda r: res["echecs_requetes"].append(r.url.split("?")[0][-120:]))
            page.on("request", lambda r: urlparse(r.url).netloc not in (hote, "") and not r.url.startswith(("data:", "blob:"))
                    and res["requetes_externes"].append(r.url[:200]))
            if code:
                t0 = time.time()
                r = page.goto(base + "/")
                res.setdefault("sans_session_url", page.url.replace(base, ""))
                page.fill("#code", code)
                page.click("button[type=submit]")
                page.wait_for_load_state("networkidle")
            for nom, chemin in PAGES:
                t0 = time.time()
                r = page.goto(base + chemin)
                attendre_rendu(page)
                dt = round(time.time() - t0, 2)
                nb_graph = page.locator(".js-plotly-plot").count()
                chemin_png = os.path.join(dossier, f"{nom}_{taille}.png")
                page.screenshot(path=chemin_png, full_page=True)
                os.chmod(chemin_png, 0o600)
                res["pages"].append({"page": nom, "taille": taille, "http": r.status if r else None,
                                     "secondes": dt, "graphiques": nb_graph, "url_finale": page.url.replace(base, "")})
            if taille == "bureau":
                # interactions : découpage 2025, indicateur, région, export CSV, fiche
                page.goto(base + "/classement")
                attendre_rendu(page)
                t0 = time.time()
                page.click("#cla-decoupage")
                page.get_by_text("47 (2025)").last.click()
                attendre_rendu(page)
                n47 = page.locator("#cla-carte .scatterlayer .trace").count()
                page.click("#cla-mesure")
                page.get_by_text("Taux d'abandon").last.click()
                attendre_rendu(page)
                with page.expect_download() as dl:
                    page.click("#cla-export-btn")
                taille_csv = os.path.getsize(dl.value.path())
                lignes_csv = sum(1 for _ in open(dl.value.path(), encoding="utf-8-sig")) - 1
                dl.value.delete()
                p2 = os.path.join(dossier, "classement_2025_abandon_bureau.png")
                page.screenshot(path=p2, full_page=True)
                os.chmod(p2, 0o600)
                res["interaction_carte"] = {"traces_carte_2025": n47, "csv_lignes": lignes_csv,
                                            "csv_octets": taille_csv, "secondes": round(time.time() - t0, 2)}
                page.goto(base + "/fiche")
                attendre_rendu(page)
                page.click("#fic-province")
                page.keyboard.type("SOUM")
                page.keyboard.press("Enter")
                attendre_rendu(page)
                p3 = os.path.join(dossier, "fiche_soum_bureau.png")
                page.screenshot(path=p3, full_page=True)
                os.chmod(p3, 0o600)
                page.goto(base + "/evolution")
                attendre_rendu(page)
                page.click("label:has-text('Régions')")
                attendre_rendu(page)
                p4 = os.path.join(dossier, "evolution_regions_bureau.png")
                page.screenshot(path=p4, full_page=True)
                os.chmod(p4, 0o600)
                # survol d'une province sur la carte d'accueil
                page.goto(base + "/")
                attendre_rendu(page)
                bb = page.locator("#acc-carte .nsewdrag").first.bounding_box()
                res["survol_carte"] = 0
                for fx, fy in [(0.5, 0.5), (0.4, 0.4), (0.6, 0.6), (0.5, 0.3), (0.3, 0.6)]:
                    page.mouse.move(bb["x"] + bb["width"] * fx, bb["y"] + bb["height"] * fy)
                    page.wait_for_timeout(400)
                    if page.locator("#acc-carte .hovertext").count():
                        res["survol_carte"] = 1
                        break
                p5 = os.path.join(dossier, "accueil_survol_bureau.png")
                page.screenshot(path=p5)
                os.chmod(p5, 0o600)
            ctx.close()
        nav.close()
    res["nb_captures"] = len([f for f in os.listdir(dossier) if f.endswith(".png")])
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
