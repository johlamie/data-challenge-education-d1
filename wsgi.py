"""Point d'entrée WSGI (gunicorn wsgi:server)."""
from dcdash.app import creer_app_production

app = creer_app_production()
server = app.server
