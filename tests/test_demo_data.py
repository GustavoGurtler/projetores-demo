from datetime import date

from werkzeug.security import check_password_hash

from database import conectar, criar_tabelas
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
