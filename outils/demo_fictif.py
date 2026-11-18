"""Lance l'appli en mode démonstration (DC_EDU_DEMO=1) : données FICTIVES, bandeau « Données fictives »,
authentification désactivée, écoute sur 127.0.0.1 uniquement. Aucune connexion à une base.

python outils/demo_fictif.py [port]
"""
import os
import sys

os.environ["DC_EDU_DEMO"] = "1"
os.environ["DC_EDU_AUTH"] = "0"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dcdash.app import creer_app_production  # noqa: E402

if __name__ == "__main__":
    creer_app_production().run(host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8050, debug=False)
