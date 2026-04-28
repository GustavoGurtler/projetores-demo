from werkzeug.security import check_password_hash

from database import conectar, criar_tabelas
from usuarios import buscar_usuario_por_sigla
from usuarios import criar_usuario
from usuarios import existe_usuario_ti
from usuarios import listar_usuarios


TIPOS_USUARIO = {
    "professor": "Professor",
    "ti": "Equipe de TI",
}


def criar_conexao_teste(tmp_path):
    caminho_banco = str(tmp_path / "usuarios_teste.db")
    criar_tabelas(caminho_banco)
    return lambda: conectar(caminho_banco)


def test_cria_e_busca_usuario_por_sigla(tmp_path):
    conexao = criar_conexao_teste(tmp_path)

    criar_usuario(conexao, "ABC", "1234", "professor")
    usuario = buscar_usuario_por_sigla(conexao, "ABC", TIPOS_USUARIO)

    assert usuario["sigla"] == "ABC"
    assert usuario["tipo"] == "professor"
    assert usuario["tipo_label"] == "Professor"
    assert check_password_hash(usuario["senha_hash"], "1234")


def test_lista_usuarios_ordenados_por_tipo_e_sigla(tmp_path):
    conexao = criar_conexao_teste(tmp_path)

    criar_usuario(conexao, "XYZ", "1234", "professor")
    criar_usuario(conexao, "ABC", "1234", "professor")
    criar_usuario(conexao, "TIU", "1234", "ti")

    usuarios = listar_usuarios(conexao, TIPOS_USUARIO)

    assert [usuario["sigla"] for usuario in usuarios] == ["ABC", "XYZ", "TIU"]


def test_identifica_quando_existe_usuario_ti(tmp_path):
    conexao = criar_conexao_teste(tmp_path)

    assert not existe_usuario_ti(conexao)

    criar_usuario(conexao, "TIU", "1234", "ti")

    assert existe_usuario_ti(conexao)
