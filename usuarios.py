from werkzeug.security import generate_password_hash


def buscar_usuario_por_sigla(conectar, sigla, tipos_usuario):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, sigla, senha_hash, tipo
        FROM usuarios
        WHERE sigla = ?
        """,
        (sigla,),
    )
    linha = c.fetchone()
    conn.close()

    if not linha:
        return None

    return {
        "id": linha[0],
        "sigla": linha[1],
        "senha_hash": linha[2],
        "tipo": linha[3],
        "tipo_label": tipos_usuario.get(linha[3], linha[3]),
    }


def listar_usuarios(conectar, tipos_usuario):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        SELECT sigla, tipo
        FROM usuarios
        ORDER BY tipo, sigla
        """
    )
    usuarios = [
        {
            "sigla": linha[0],
            "tipo": linha[1],
            "tipo_label": tipos_usuario.get(linha[1], linha[1]),
        }
        for linha in c.fetchall()
    ]
    conn.close()
    return usuarios


def existe_usuario_ti(conectar):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        SELECT COUNT(*)
        FROM usuarios
        WHERE tipo = 'ti'
        """
    )
    total = c.fetchone()[0]
    conn.close()
    return total > 0


def criar_usuario(conectar, sigla, senha, tipo):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO usuarios (sigla, senha_hash, tipo)
        VALUES (?, ?, ?)
        """,
        (sigla, generate_password_hash(senha), tipo),
    )
    conn.commit()
    conn.close()
