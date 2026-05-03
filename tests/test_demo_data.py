from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from werkzeug.security import check_password_hash

from database import conectar, criar_tabelas
from demo_data import manter_dados_demo
from demo_data import popular_dados_demo


def test_popula_usuarios_e_registros_de_demo(tmp_path):
    caminho_banco = str(tmp_path / "demo.db")
    criar_tabelas(caminho_banco)

    popular_dados_demo(caminho_banco, hoje=date(2026, 5, 4))

    conn = conectar(caminho_banco)
    cursor = conn.cursor()

    cursor.execute("SELECT sigla, senha_hash, tipo FROM usuarios WHERE sigla = 'ANA'")
    sigla, senha_hash, tipo = cursor.fetchone()
    assert sigla == "ANA"
    assert tipo == "professor"
    assert check_password_hash(senha_hash, "demo123")

    cursor.execute("SELECT COUNT(*) FROM reservas")
    assert cursor.fetchone()[0] == 4

    cursor.execute("SELECT COUNT(*) FROM requisicoes_computadores")
    assert cursor.fetchone()[0] == 3

    conn.close()


def test_seed_de_demo_nao_duplica_registros(tmp_path):
    caminho_banco = str(tmp_path / "demo.db")
    criar_tabelas(caminho_banco)

    popular_dados_demo(caminho_banco, hoje=date(2026, 5, 4))
    popular_dados_demo(caminho_banco, hoje=date(2026, 5, 4))

    conn = conectar(caminho_banco)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    assert cursor.fetchone()[0] == 7

    cursor.execute("SELECT COUNT(*) FROM reservas")
    assert cursor.fetchone()[0] == 4

    cursor.execute("SELECT COUNT(*) FROM requisicoes_computadores")
    assert cursor.fetchone()[0] == 3

    conn.close()


def test_seed_de_demo_remove_usuarios_fora_da_demo(tmp_path):
    caminho_banco = str(tmp_path / "demo.db")
    criar_tabelas(caminho_banco)

    conn = conectar(caminho_banco)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO usuarios (sigla, senha_hash, tipo)
        VALUES ('ZZZ', 'hash', 'ti')
        """
    )
    conn.commit()
    conn.close()

    popular_dados_demo(caminho_banco, hoje=date(2026, 5, 4))

    conn = conectar(caminho_banco)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE sigla = 'ZZZ'")
    assert cursor.fetchone()[0] == 0
    conn.close()


def test_mantem_demo_reseta_quando_passa_do_limite(tmp_path):
    caminho_banco = str(tmp_path / "demo.db")
    criar_tabelas(caminho_banco)
    popular_dados_demo(caminho_banco, hoje=date(2026, 5, 4))

    conn = conectar(caminho_banco)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reservas (sigla, sala, data, horario, nivel, som)
        VALUES ('ANA', '13', '2026-05-06', '09:25', 'Fundamental', 'Nao')
        """
    )
    conn.commit()
    conn.close()

    manter_dados_demo(
        caminho_banco,
        intervalo_horas=6,
        limite_registros=4,
        hoje=date(2026, 5, 4),
    )

    conn = conectar(caminho_banco)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reservas")
    assert cursor.fetchone()[0] == 4
    conn.close()


def test_mantem_demo_reseta_quando_intervalo_expira(tmp_path):
    caminho_banco = str(tmp_path / "demo.db")
    criar_tabelas(caminho_banco)

    agora = datetime(2026, 5, 4, 12, tzinfo=timezone.utc)
    futuro = agora + timedelta(hours=7)
    popular_dados_demo(caminho_banco, hoje=date(2026, 5, 4), agora=agora)

    manter_dados_demo(
        caminho_banco,
        intervalo_horas=6,
        limite_registros=80,
        hoje=date(2026, 5, 4),
        agora=futuro,
    )

    conn = conectar(caminho_banco)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reservas")
    assert cursor.fetchone()[0] == 4
    conn.close()
