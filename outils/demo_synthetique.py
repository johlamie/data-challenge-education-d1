"""Lance l'appli sur le jeu SYNTHÉTIQUE des tests (aucune donnée réelle), pour le développement.

Ce jeu-là sert aux tests unitaires : valeurs aléatoires, bandeau « confidentiel », contours en CARRÉS.
Pour travailler l'interface, utiliser plutôt `outils/demo_fictif.py` (mode démo : valeurs fictives cohérentes,
carte réaliste du Burkina Faso, bandeau « Données fictives »).

python outils/demo_synthetique.py [port]   (auth désactivée, écoute sur 127.0.0.1)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from dcdash.demo import SourceSynthetique  # noqa: E402
from dcdash import db  # noqa: E402
from dcdash.app import creer_app  # noqa: E402
from dcdash.config import Config  # noqa: E402

if __name__ == "__main__":
    d = db.Donnees(SourceSynthetique(), ttl_s=10 ** 9)
    app = creer_app(Config(auth_active=False, code_hash="", secret_key=""), d)
    app.run(host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8050, debug=False)
