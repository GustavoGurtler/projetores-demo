import importlib
import sys

import pytest

from demo_protection import DemoRateLimiter, RateLimitExceeded


def carregar_app_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "demo_app.db"))
    monkeypatch.setenv("DEMO_DATA_ENABLED", "1")
    monkeypatch.setenv("DEMO_MAX_RECORDS", "80")
    monkeypatch.setenv("DEMO_RATE_LIMIT_REQUESTS", "40")
    monkeypatch.setenv("DEMO_RATE_LIMIT_WINDOW_SECONDS", "600")
    monkeypatch.setenv("DEMO_RESET_INTERVAL_HOURS", "6")
    monkeypatch.setenv("FLASK_DEBUG", "0")

    sys.modules.pop("app", None)
    sys.modules.pop("config", None)

    return importlib.import_module("app")


def test_rate_limit_bloqueia_excesso_de_acoes():
    limitador = DemoRateLimiter(limite=2, janela_segundos=60)

    limitador.verificar("127.0.0.1:/login")
    limitador.verificar("127.0.0.1:/login")

    with pytest.raises(RateLimitExceeded):
        limitador.verificar("127.0.0.1:/login")


def test_demo_bloqueia_criacao_de_usuario(tmp_path, monkeypatch):
    app = carregar_app_demo(tmp_path, monkeypatch)
    client = app.app.test_client()

    login = client.post("/login", data={"sigla": "TEC", "senha": "admin123"})
    assert login.status_code == 302

    resposta = client.post(
        "/usuarios",
        data={"sigla": "NOV", "senha": "1234", "tipo": "professor"},
    )
    assert resposta.status_code == 200

    conn = app.conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE sigla = 'NOV'")
    assert cursor.fetchone()[0] == 0
    conn.close()
