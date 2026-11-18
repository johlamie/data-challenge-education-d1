import pytest
from werkzeug.security import generate_password_hash

from dcdash.app import creer_app
from dcdash.config import Config

CODE = "code-de-test-123"


@pytest.fixture()
def client(donnees):
    cfg = Config(auth_active=True, code_hash=generate_password_hash(CODE), secret_key="x" * 64, max_essais=3,
                 fenetre_essais_s=60)
    app = creer_app(cfg, donnees)
    app.server.testing = True
    return app.server.test_client()


def _jeton(client):
    r = client.get("/connexion")
    assert r.status_code == 200
    with client.session_transaction() as s:
        return s["jeton"]


def test_sans_session_redirige_ou_401(client):
    r = client.get("/")
    assert r.status_code == 302 and "/connexion" in r.headers["Location"]
    assert client.get("/_dash-layout").status_code == 401
    assert client.post("/_dash-update-component", json={}).status_code == 401
    assert client.get("/_dash-component-suites/dash/dash-renderer/build/dash_renderer.min.js").status_code == 401
    assert client.get("/sante").status_code == 200


def test_mauvais_code_puis_limite(client):
    j = _jeton(client)
    for _ in range(3):
        r = client.post("/connexion", data={"code": "faux", "jeton": j, "suite": "/"})
        assert r.status_code == 401
    r = client.post("/connexion", data={"code": CODE, "jeton": j, "suite": "/"})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0


def test_jeton_formulaire_obligatoire(client):
    _jeton(client)
    r = client.post("/connexion", data={"code": CODE, "jeton": "autre", "suite": "/"})
    assert r.status_code == 400


def test_bon_code_et_session(client):
    j = _jeton(client)
    r = client.post("/connexion", data={"code": CODE, "jeton": j, "suite": "//evil.example/x"})
    assert r.status_code == 302 and r.headers["Location"] == "/"
    cookie = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert client.get("/").status_code == 200
    assert client.get("/_dash-layout").status_code == 200
    r = client.get("/")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert client.get("/deconnexion").status_code == 302
    assert client.get("/").status_code == 302


def test_code_jamais_dans_les_reponses(client):
    j = _jeton(client)
    r = client.post("/connexion", data={"code": CODE, "jeton": j, "suite": "/"})
    assert CODE not in r.get_data(as_text=True)


def test_auth_desactivable(donnees):
    app = creer_app(Config(auth_active=False, code_hash="", secret_key=""), donnees)
    c = app.server.test_client()
    assert c.get("/").status_code == 200


def test_auth_active_sans_secret_refusee(donnees):
    with pytest.raises(RuntimeError):
        creer_app(Config(auth_active=True, code_hash="", secret_key="k" * 64), donnees)


CODE_JURY = "code-du-jury-456"
PROXY = "10.9.8.7"


@pytest.fixture()
def client_proxy(donnees):
    cfg = Config(auth_active=True, code_hash=generate_password_hash(CODE), secret_key="x" * 64, max_essais=3,
                 code_hash_jury=generate_password_hash(CODE_JURY), fenetre_essais_s=60, proxys_confiance=(PROXY,))
    app = creer_app(cfg, donnees)
    app.server.testing = True
    return app.server.test_client()


def test_code_jury_accepte(client_proxy):
    j = _jeton(client_proxy)
    r = client_proxy.post("/connexion", data={"code": CODE_JURY, "jeton": j, "suite": "/"})
    assert r.status_code == 302 and client_proxy.get("/").status_code == 200
    assert "Secure" not in r.headers["Set-Cookie"]


def test_limite_par_ip_reelle_derriere_proxy(client_proxy):
    j = _jeton(client_proxy)

    def essai(ip, code="faux"):
        return client_proxy.post("/connexion", data={"code": code, "jeton": j, "suite": "/"},
                                 environ_base={"REMOTE_ADDR": PROXY}, headers={"X-Forwarded-For": ip})
    for _ in range(3):
        assert essai("203.0.113.5").status_code == 401
    assert essai("203.0.113.5", CODE).status_code == 429
    # un autre client, par le même proxy, n'est pas bloqué
    assert essai("198.51.100.9", CODE).status_code == 302


def test_entete_ignore_hors_proxy_de_confiance(client_proxy):
    j = _jeton(client_proxy)
    for i in range(3):
        r = client_proxy.post("/connexion", data={"code": "faux", "jeton": j, "suite": "/"},
                              environ_base={"REMOTE_ADDR": "192.0.2.44"}, headers={"X-Forwarded-For": f"203.0.113.{i}"})
        assert r.status_code == 401
    r = client_proxy.post("/connexion", data={"code": CODE, "jeton": j, "suite": "/"},
                          environ_base={"REMOTE_ADDR": "192.0.2.44"}, headers={"X-Forwarded-For": "203.0.113.99"})
    assert r.status_code == 429


def test_cookie_secure_en_https_par_le_proxy(client_proxy):
    h = {"X-Forwarded-For": "203.0.113.5", "X-Forwarded-Proto": "https"}
    r = client_proxy.get("/connexion", environ_base={"REMOTE_ADDR": PROXY}, headers=h)
    assert "Secure" in r.headers["Set-Cookie"]
    r = client_proxy.get("/connexion", environ_base={"REMOTE_ADDR": "192.0.2.44"}, headers=h)
    assert "Secure" not in r.headers.get("Set-Cookie", "")
