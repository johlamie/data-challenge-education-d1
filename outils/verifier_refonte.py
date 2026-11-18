"""Vérification headless de l'interface : pas de défilement sur la vue d'ensemble et le classement (1366×768 et
1920×1080), 0 erreur JS sur chaque page, carte verrouillée (pas de glisser), infobulles d'aide, captures PNG (600).

Usage : python outils/verifier_refonte.py URL_BASE DOSSIER [--code-stdin] [--toutes-pages]
Le résumé imprimé ne contient aucune valeur de données (dimensions, comptes, booléens).
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from captures import attendre_rendu  # noqa: E402

TAILLES = {"1366x768": (1366, 768), "1920x1080": (1920, 1080)}
PAGES = [("vue_ensemble", "/"), ("classement", "/classement"), ("fiche", "/fiche"), ("evolution", "/evolution"), ("methode", "/methode"),
         ("qualite", "/qualite")]


def main():
    base, dossier = sys.argv[1].rstrip("/"), sys.argv[2]
    code = sys.stdin.readline().strip() if "--code-stdin" in sys.argv else None
    os.umask(0o077)
    os.makedirs(dossier, mode=0o700, exist_ok=True)
    res = {"no_scroll": {}, "pages": [], "erreurs_js": [], "console_erreurs": [], "carte": {}}
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=True, args=["--no-sandbox"], executable_path=os.environ.get("CHROME") or None)
        for nom_t, (w, h) in TAILLES.items():
            ctx = nav.new_context(viewport={"width": w, "height": h}, locale="fr-FR", accept_downloads=True)
            page = ctx.new_page()
            page.on("pageerror", lambda e: res["erreurs_js"].append(str(e)[:200]))
            page.on("console", lambda m: m.type == "error" and res["console_erreurs"].append(m.text[:200]))
            if code:
                page.goto(base + "/")
                page.fill("#code", code)
                page.click("button[type=submit]")
                page.wait_for_load_state("networkidle")
            pages = PAGES if (nom_t == "1366x768" or "--toutes-pages" in sys.argv) else PAGES[:2]
            for nom, chemin in pages:
                page.goto(base + chemin)
                attendre_rendu(page)
                page.wait_for_timeout(800)
                m = page.evaluate("""() => ({sh: document.scrollingElement.scrollHeight, ih: window.innerHeight,
                    sw: document.scrollingElement.scrollWidth, iw: window.innerWidth})""")
                res["pages_aides"] = res.get("pages_aides", {})
                res["pages_aides"][f"{nom}_{nom_t}"] = page.locator(".aide").count()
                if chemin == "/classement":
                    res["no_scroll"][f"classement_{nom_t}"] = {**m, "ok": m["sh"] <= m["ih"] and m["sw"] <= m["iw"]}
                if chemin == "/":
                    res["no_scroll"][nom_t] = {**m, "ok": m["sh"] <= m["ih"] and m["sw"] <= m["iw"]}
                    ic = page.locator(".ligne-kpi .kpi-info").first
                    ic.hover()
                    page.wait_for_timeout(300)
                    res.setdefault("infobulle_survol", {})[nom_t] = page.locator("#bulle-aide.visible").count() == 1
                    page.mouse.move(2, 2)
                    page.wait_for_timeout(200)
                    # éléments tronqués : texte qui déborde de sa boîte dans les KPI et le top 10
                    res.setdefault("debordements", {})[nom_t] = page.evaluate("""() => [...document.querySelectorAll(
                        '.kpi-val, .kpi-lib, .kpi-var, .table-top10 td, .bloc-entete h2')].filter(e =>
                        e.scrollWidth > e.clientWidth + 1).length + [...document.querySelectorAll(
                        '.zone-top10, .zone-carte, .kpi')].filter(e => e.scrollHeight > e.clientHeight + 1
                        || e.scrollWidth > e.clientWidth + 1).length""")
                    # carte : tentative de glisser, la plage d'axes doit rester identique
                    avant = page.evaluate("() => JSON.stringify(document.querySelector('#acc-carte .js-plotly-plot')"
                                          "._fullLayout.xaxis.range)")
                    bb = page.locator("#acc-carte .nsewdrag").first.bounding_box()
                    page.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
                    page.mouse.down()
                    page.mouse.move(bb["x"] + bb["width"] * 0.95, bb["y"] + bb["height"] * 0.9, steps=8)
                    page.mouse.up()
                    page.mouse.wheel(0, -600)
                    page.wait_for_timeout(500)
                    apres = page.evaluate("() => JSON.stringify(document.querySelector('#acc-carte .js-plotly-plot')"
                                          "._fullLayout.xaxis.range)")
                    res["carte"][nom_t] = {"fixe_apres_glisser_et_molette": avant == apres}
                    res["carte"][nom_t]["survol_actif"] = False
                    for fx, fy in [(0.5, 0.45), (0.45, 0.4), (0.55, 0.5), (0.5, 0.3), (0.4, 0.55), (0.6, 0.35)]:
                        page.mouse.move(bb["x"] + bb["width"] * fx, bb["y"] + bb["height"] * fy)
                        page.wait_for_timeout(400)
                        if page.locator("#acc-carte .hovertext").count() > 0:
                            res["carte"][nom_t]["survol_actif"] = True
                            break
                    page.mouse.move(2, 2)
                    page.wait_for_timeout(300)
                suf = next((x.split("=", 1)[1] for x in sys.argv if x.startswith("--suffixe=")), "")
                png = os.path.join(dossier, f"{nom}_{nom_t}{suf}.png")
                page.screenshot(path=png, full_page=chemin != "/")
                os.chmod(png, 0o600)
                res["pages"].append({"page": nom, "taille": nom_t, "graphiques": page.locator(".js-plotly-plot").count()})
            ctx.close()
        nav.close()
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
