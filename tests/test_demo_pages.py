import importlib
import sys


def carregar_app_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "demo_pages.db"))
    monkeypatch.setenv("DEMO_DATA_ENABLED", "1")
    monkeypatch.setenv("FLASK_DEBUG", "0")

    sys.modules.pop("app", None)
    sys.modules.pop("config", None)

    return importlib.import_module("app")


def test_professor_acessa_manual_e_minhas_reservas(tmp_path, monkeypatch):
    app = carregar_app_demo(tmp_path, monkeypatch)
    client = app.app.test_client()

    client.post("/login", data={"sigla": "ANA", "senha": "demo123"})

    assert client.get("/manual").status_code == 200
    assert client.get("/minhas-reservas").status_code == 200


def test_ti_acessa_monitor_relatorio_e_excel(tmp_path, monkeypatch):
    app = carregar_app_demo(tmp_path, monkeypatch)
    client = app.app.test_client()

    client.post("/login", data={"sigla": "TEC", "senha": "admin123"})

    assert client.get("/monitor-ti").status_code == 200
    assert client.get("/relatorio-ti").status_code == 200

    excel = client.get("/relatorio-ti/exportar-excel")
    assert excel.status_code == 200
    assert excel.content_type.startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_rota_antiga_de_relatorio_de_computadores_redireciona(tmp_path, monkeypatch):
    app = carregar_app_demo(tmp_path, monkeypatch)
    client = app.app.test_client()

    client.post("/login", data={"sigla": "TEC", "senha": "admin123"})
    resposta = client.get("/computadores/relatorio-ti")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith("/relatorio-ti")


def test_telas_antigas_redirecionam_para_fluxo_consolidado(tmp_path, monkeypatch):
    app = carregar_app_demo(tmp_path, monkeypatch)
    client = app.app.test_client()

    client.post("/login", data={"sigla": "TEC", "senha": "admin123"})

    computadores = client.get("/computadores?mensagem=teste")
    consulta = client.get("/computadores/consultar?data=2026-05-04")
    painel = client.get("/painel-ti?data=2026-05-04")

    assert computadores.status_code == 302
    assert computadores.headers["Location"].startswith("/?mensagem=teste")
    assert consulta.status_code == 302
    assert consulta.headers["Location"].startswith("/relatorio-ti")
    assert painel.status_code == 302
    assert painel.headers["Location"] == "/monitor-ti?data=2026-05-04"
