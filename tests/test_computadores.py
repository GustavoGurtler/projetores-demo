import importlib
import sys


def carregar_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "computadores_teste.db"))
    monkeypatch.setenv("DEMO_DATA_ENABLED", "0")
    monkeypatch.setenv("FLASK_DEBUG", "0")

    sys.modules.pop("app", None)
    sys.modules.pop("config", None)

    return importlib.import_module("app")


def test_bloqueia_requisicao_no_mesmo_local_e_horario(tmp_path, monkeypatch):
    app = carregar_app(tmp_path, monkeypatch)
    conn = app.conectar()
    cursor = conn.cursor()

    primeira = app.registrar_requisicoes_computador(
        cursor,
        "ABC",
        "notebook_samsung",
        5,
        "11",
        "2026-05-04",
        "Fundamental",
        ["07:25"],
    )
    segunda = app.registrar_requisicoes_computador(
        cursor,
        "DEF",
        "notebook_samsung",
        5,
        "11",
        "2026-05-04",
        "Fundamental",
        ["07:25"],
    )

    conn.close()

    assert primeira["inseridas"] == 1
    assert segunda["inseridas"] == 0
    assert segunda["bloqueios_local"] == 1


def test_bloqueia_quantidade_acima_da_disponibilidade(tmp_path, monkeypatch):
    app = carregar_app(tmp_path, monkeypatch)
    conn = app.conectar()
    cursor = conn.cursor()

    primeira = app.registrar_requisicoes_computador(
        cursor,
        "ABC",
        "notebook_samsung",
        10,
        "11",
        "2026-05-04",
        "Fundamental",
        ["07:25"],
    )
    segunda = app.registrar_requisicoes_computador(
        cursor,
        "DEF",
        "notebook_samsung",
        6,
        "12",
        "2026-05-04",
        "Fundamental",
        ["07:25"],
    )

    conn.close()

    assert primeira["inseridas"] == 1
    assert segunda["inseridas"] == 0
    assert segunda["bloqueios_limite"] == 1


def test_bloqueia_laboratorio_no_mesmo_horario(tmp_path, monkeypatch):
    app = carregar_app(tmp_path, monkeypatch)
    conn = app.conectar()
    cursor = conn.cursor()

    primeira = app.registrar_requisicoes_computador(
        cursor,
        "ABC",
        "laboratorio_sala15",
        1,
        app.LOCAL_LABORATORIO,
        "2026-05-04",
        "Medio",
        ["07:00"],
    )
    segunda = app.registrar_requisicoes_computador(
        cursor,
        "DEF",
        "laboratorio_sala15",
        1,
        app.LOCAL_LABORATORIO,
        "2026-05-04",
        "Medio",
        ["07:00"],
    )

    conn.close()

    assert primeira["inseridas"] == 1
    assert segunda["inseridas"] == 0
    assert segunda["bloqueios_local"] == 1
