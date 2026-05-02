import importlib
import sys


def carregar_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "reservas_teste.db"))
    monkeypatch.setenv("DEMO_DATA_ENABLED", "0")
    monkeypatch.setenv("FLASK_DEBUG", "0")

    sys.modules.pop("app", None)
    sys.modules.pop("config", None)

    return importlib.import_module("app")


def test_bloqueia_reserva_na_mesma_sala_e_horario(tmp_path, monkeypatch):
    app = carregar_app(tmp_path, monkeypatch)
    conn = app.conectar()
    cursor = conn.cursor()

    primeira = app.registrar_reservas_projetor(
        cursor,
        "ABC",
        "11",
        "2026-05-04",
        "Fundamental",
        ["07:25"],
        "Nao",
    )
    segunda = app.registrar_reservas_projetor(
        cursor,
        "DEF",
        "11",
        "2026-05-04",
        "Fundamental",
        ["07:25"],
        "Nao",
    )

    conn.close()

    assert primeira["inseridas"] == 1
    assert segunda["inseridas"] == 0
    assert segunda["bloqueios_sala"] == 1


def test_bloqueia_quando_limite_de_projetores_e_atingido(tmp_path, monkeypatch):
    app = carregar_app(tmp_path, monkeypatch)
    conn = app.conectar()
    cursor = conn.cursor()

    for sala in ["11", "12", "13", "14"]:
        resultado = app.registrar_reservas_projetor(
            cursor,
            "ABC",
            sala,
            "2026-05-04",
            "Fundamental",
            ["07:25"],
            "Nao",
        )
        assert resultado["inseridas"] == 1

    bloqueada = app.registrar_reservas_projetor(
        cursor,
        "DEF",
        "17",
        "2026-05-04",
        "Fundamental",
        ["07:25"],
        "Nao",
    )

    conn.close()

    assert bloqueada["inseridas"] == 0
    assert bloqueada["bloqueios_limite"] == 1
