from datetime import date
from functools import wraps
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from computadores_service import montar_mensagens_requisicao_computador as montar_mensagens_computador_service
from computadores_service import registrar_requisicoes_computador as registrar_requisicoes_computador_service
from computadores_service import verificar_conflitos_requisicao_computador as verificar_conflitos_computador_service
from config import Config
from consultas import buscar_disponibilidade_computadores_geral as buscar_disp_comp_db
from consultas import buscar_disponibilidade_geral as buscar_disp_reservas_db
from consultas import buscar_requisicao_computador_por_id as buscar_requisicao_comp_db
from consultas import buscar_requisicoes_computadores_por_data as buscar_req_comp_data_db
from consultas import buscar_requisicoes_computadores_relatorio as buscar_req_comp_relatorio_db
from consultas import buscar_reserva_por_id as buscar_reserva_db
from consultas import buscar_reservas_por_data as buscar_reservas_data_db
from consultas import buscar_reservas_relatorio as buscar_reservas_relatorio_db
from database import conectar as abrir_conexao
from database import criar_tabelas
from demo_data import DEMO_CREDENTIALS, popular_dados_demo
from domain import HORARIOS, HORARIOS_POR_INICIO
from domain import LIMITE_COMPUTADORES_POR_RESERVA, LOCAL_LABORATORIO
from domain import NIVEL_LABELS, RECURSOS_COMPUTADORES
from domain import SALAS, TIPOS_USUARIO, TOTAL_PROJETORES
from painel_service import gerar_planejamento_ti, montar_painel_disponibilidade
from painel_service import montar_painel_disponibilidade_computadores
from painel_service import montar_tarefas_do_dia
from permissions import usuario_eh_ti as verificar_usuario_eh_ti
from permissions import usuario_pode_gerenciar_por_sigla as verificar_permissao_sigla
from permissions import usuario_pode_gerenciar_reserva as verificar_permissao_reserva
from reservas_service import montar_mensagens_reserva_projetor as montar_mensagens_reserva_service
from reservas_service import registrar_reservas_projetor as registrar_reservas_service
from reservas_service import verificar_conflitos_reserva as verificar_conflitos_reserva_service
from relatorios_service import montar_relatorio_computadores_ti, montar_relatorio_ti
from serializers import marcar_permissoes_requisicao_computador as marcar_perm_req_comp
from serializers import marcar_permissoes_requisicoes_computadores as marcar_perm_req_comps
from serializers import marcar_permissoes_reserva as marcar_perm_reserva
from serializers import marcar_permissoes_reservas as marcar_perm_reservas
from serializers import rotulo_local_computador as rotulo_local_computador_serializer
from serializers import serializar_requisicao_computador as serializar_req_comp
from serializers import serializar_reserva as serializar_reserva_db
from usuarios import buscar_usuario_por_sigla as buscar_usuario_por_sigla_db
from usuarios import criar_usuario as criar_usuario_db
from usuarios import existe_usuario_ti as existe_usuario_ti_db
from usuarios import listar_usuarios as listar_usuarios_db
from validators import normalizar_sigla_professor, normalizar_som
from validators import validar_requisicao_computador, validar_reserva

app = Flask(__name__)
app.config.from_object(Config)


def conectar():
    return abrir_conexao(app.config["DATABASE_PATH"])


criar_tabelas(app.config["DATABASE_PATH"])

if app.config["DEMO_DATA_ENABLED"]:
    popular_dados_demo(app.config["DATABASE_PATH"])


def usuario_eh_ti(tipo_usuario=None):
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")
    return verificar_usuario_eh_ti(tipo_usuario)


def usuario_pode_gerenciar_por_sigla(
    sigla_registro,
    sigla_usuario=None,
    tipo_usuario=None,
):
    sigla_usuario = sigla_usuario or session.get("usuario_sigla")
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")
    return verificar_permissao_sigla(sigla_registro, sigla_usuario, tipo_usuario)


def usuario_pode_gerenciar_reserva(
    reserva,
    sigla_usuario=None,
    tipo_usuario=None,
):
    sigla_usuario = sigla_usuario or session.get("usuario_sigla")
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")
    return verificar_permissao_reserva(reserva, sigla_usuario, tipo_usuario)


def buscar_usuario_por_sigla(sigla):
    return buscar_usuario_por_sigla_db(conectar, sigla, TIPOS_USUARIO)


def listar_usuarios():
    return listar_usuarios_db(conectar, TIPOS_USUARIO)


def existe_usuario_ti():
    return existe_usuario_ti_db(conectar)


def criar_usuario(sigla, senha, tipo):
    criar_usuario_db(conectar, sigla, senha, tipo)


def adicionar_parametros_url(url, **params):
    partes = urlsplit(url)
    query = dict(parse_qsl(partes.query, keep_blank_values=True))

    for chave, valor in params.items():
        if valor is None:
            query.pop(chave, None)
            continue

        query[chave] = valor

    return urlunsplit(
        (
            partes.scheme,
            partes.netloc,
            partes.path,
            urlencode(query),
            partes.fragment,
        )
    )


def destino_seguro(proximo, endpoint_padrao, **valores_padrao):
    if proximo and proximo.startswith("/"):
        return proximo
    return url_for(endpoint_padrao, **valores_padrao)


def redirecionar_com_mensagem(proximo, endpoint_padrao, mensagem, tipo, **valores_padrao):
    destino = destino_seguro(proximo, endpoint_padrao, **valores_padrao)
    return redirect(adicionar_parametros_url(destino, mensagem=mensagem, tipo=tipo))


def destino_atual():
    query = request.query_string.decode().strip()
    if query:
        return f"{request.path}?{query}"
    return request.path


def login_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("usuario_sigla"):
            return redirect(
                url_for(
                    "login",
                    next=destino_atual(),
                    mensagem="Fa\u00e7a login para continuar.",
                    tipo="warning",
                )
            )
        return view(*args, **kwargs)

    return wrapper


def ti_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("usuario_sigla"):
            return redirect(
                url_for(
                    "login",
                    next=destino_atual(),
                    mensagem="Fa\u00e7a login da equipe de TI para continuar.",
                    tipo="warning",
                )
            )

        if session.get("usuario_tipo") != "ti":
            return redirect(
                url_for(
                    "home",
                    mensagem="Esta \u00e1rea interna est\u00e1 dispon\u00edvel apenas para a equipe de TI.",
                    tipo="warning",
                )
            )

        return view(*args, **kwargs)

    return wrapper


def serializar_reserva(linha):
    return serializar_reserva_db(linha)


def marcar_permissoes_reserva(
    reserva,
    sigla_usuario=None,
    tipo_usuario=None,
):
    if not reserva:
        return None

    sigla_usuario = sigla_usuario or session.get("usuario_sigla")
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")
    return marcar_perm_reserva(
        reserva,
        sigla_usuario=sigla_usuario,
        tipo_usuario=tipo_usuario,
    )


def marcar_permissoes_reservas(
    reservas,
    sigla_usuario=None,
    tipo_usuario=None,
):
    sigla_usuario = sigla_usuario or session.get("usuario_sigla")
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")
    return marcar_perm_reservas(
        reservas,
        sigla_usuario=sigla_usuario,
        tipo_usuario=tipo_usuario,
    )


def serializar_requisicao_computador(linha):
    return serializar_req_comp(linha)


def marcar_permissoes_requisicao_computador(
    requisicao,
    sigla_usuario=None,
    tipo_usuario=None,
):
    if not requisicao:
        return None

    sigla_usuario = sigla_usuario or session.get("usuario_sigla")
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")
    return marcar_perm_req_comp(
        requisicao,
        sigla_usuario=sigla_usuario,
        tipo_usuario=tipo_usuario,
    )


def marcar_permissoes_requisicoes_computadores(
    requisicoes,
    sigla_usuario=None,
    tipo_usuario=None,
):
    sigla_usuario = sigla_usuario or session.get("usuario_sigla")
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")
    return marcar_perm_req_comps(
        requisicoes,
        sigla_usuario=sigla_usuario,
        tipo_usuario=tipo_usuario,
    )


def rotulo_local_computador(nivel, recurso, local):
    return rotulo_local_computador_serializer(nivel, recurso, local)


def validar_dados_requisicao_computador(
    nivel,
    recurso,
    local,
    data_requisicao,
    quantidade,
    horario=None,
):
    return validar_requisicao_computador(
        nivel,
        recurso,
        local,
        data_requisicao,
        quantidade,
        salas=SALAS,
        recursos_computadores=RECURSOS_COMPUTADORES,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        limite_computadores_por_reserva=LIMITE_COMPUTADORES_POR_RESERVA,
        horario=horario,
    )


def buscar_disponibilidade_computadores_geral():
    return buscar_disp_comp_db(conectar)


def buscar_requisicoes_computadores_por_data(data_filtro):
    return buscar_req_comp_data_db(
        conectar,
        serializar_requisicao_computador,
        data_filtro,
    )


def buscar_requisicao_computador_por_id(requisicao_id):
    return buscar_requisicao_comp_db(
        conectar,
        serializar_requisicao_computador,
        requisicao_id,
    )


def buscar_disponibilidade_geral():
    return buscar_disp_reservas_db(conectar)


def buscar_reservas_por_data(data_filtro):
    return buscar_reservas_data_db(conectar, serializar_reserva, data_filtro)


def buscar_reserva_por_id(reserva_id):
    return buscar_reserva_db(conectar, serializar_reserva, reserva_id)


def validar_dados_reserva(nivel, sala, data_reserva, horario=None):
    return validar_reserva(
        nivel,
        sala,
        data_reserva,
        salas=SALAS,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        horario=horario,
    )


def verificar_conflitos_reserva(
    cursor,
    data_reserva,
    horario,
    nivel,
    sala,
    reserva_id_ignorada=None,
):
    return verificar_conflitos_reserva_service(
        cursor,
        data_reserva,
        horario,
        nivel,
        sala,
        TOTAL_PROJETORES,
        reserva_id_ignorada=reserva_id_ignorada,
    )


def verificar_conflitos_requisicao_computador(
    cursor,
    data_requisicao,
    horario,
    nivel,
    recurso,
    local,
    quantidade,
    requisicao_id_ignorada=None,
):
    return verificar_conflitos_computador_service(
        cursor,
        data_requisicao,
        horario,
        nivel,
        recurso,
        local,
        quantidade,
        RECURSOS_COMPUTADORES,
        requisicao_id_ignorada=requisicao_id_ignorada,
    )


def registrar_reservas_projetor(
    cursor,
    sigla,
    sala,
    data_reserva,
    nivel,
    aulas,
    som,
):
    return registrar_reservas_service(
        cursor,
        sigla,
        sala,
        data_reserva,
        nivel,
        aulas,
        som,
        salas=SALAS,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        total_projetores=TOTAL_PROJETORES,
    )


def montar_mensagens_reserva_projetor(resultado):
    return montar_mensagens_reserva_service(resultado)


def registrar_requisicoes_computador(
    cursor,
    sigla,
    recurso,
    quantidade_int,
    local_normalizado,
    data_requisicao,
    nivel,
    aulas,
):
    return registrar_requisicoes_computador_service(
        cursor,
        sigla,
        recurso,
        quantidade_int,
        local_normalizado,
        data_requisicao,
        nivel,
        aulas,
        recursos_computadores=RECURSOS_COMPUTADORES,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        rotulo_local=rotulo_local_computador,
    )


def montar_mensagens_requisicao_computador(resultado):
    return montar_mensagens_computador_service(resultado)


def buscar_reservas_relatorio(data_inicial, data_final, nivel="", sigla=""):
    return buscar_reservas_relatorio_db(
        conectar,
        serializar_reserva,
        data_inicial,
        data_final,
        nivel=nivel,
        sigla=sigla,
    )


def buscar_requisicoes_computadores_relatorio(
    data_inicial,
    data_final,
    nivel="",
    sigla="",
    recurso="",
):
    return buscar_req_comp_relatorio_db(
        conectar,
        serializar_requisicao_computador,
        data_inicial,
        data_final,
        nivel=nivel,
        sigla=sigla,
        recurso=recurso,
    )


@app.context_processor
def injetar_usuario():
    tipo = session.get("usuario_tipo")
    return {
        "usuario_sigla": session.get("usuario_sigla"),
        "usuario_tipo": tipo,
        "usuario_tipo_label": TIPOS_USUARIO.get(tipo),
        "usuario_eh_ti": tipo == "ti",
        "demo_data_enabled": app.config["DEMO_DATA_ENABLED"],
        "demo_credentials": DEMO_CREDENTIALS,
    }


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        sigla = normalizar_sigla_professor(request.form.get("sigla", ""))
        senha = request.form.get("senha", "")
        proximo = request.form.get("next", "")
        usuario = buscar_usuario_por_sigla(sigla)

        if not usuario or not check_password_hash(usuario["senha_hash"], senha):
            return render_template(
                "login.html",
                mensagem="Sigla ou senha inv\u00e1lida.",
                tipo_mensagem="warning",
                proximo=proximo,
                primeiro_acesso_disponivel=not existe_usuario_ti(),
            )

        session["usuario_sigla"] = usuario["sigla"]
        session["usuario_tipo"] = usuario["tipo"]

        if proximo and proximo.startswith("/"):
            return redirect(proximo)

        if usuario["tipo"] == "ti":
            return redirect(url_for("painel_ti"))

        return redirect(url_for("home"))

    if session.get("usuario_sigla"):
        if session.get("usuario_tipo") == "ti":
            return redirect(url_for("painel_ti"))
        return redirect(url_for("home"))

    return render_template(
        "login.html",
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "warning"),
        proximo=request.args.get("next", ""),
        primeiro_acesso_disponivel=not existe_usuario_ti(),
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        url_for(
            "login",
            mensagem="Sess\u00e3o encerrada com sucesso.",
            tipo="success",
        )
    )


@app.route("/primeiro-acesso", methods=["GET", "POST"])
def primeiro_acesso():
    if existe_usuario_ti():
        return redirect(
            url_for(
                "login",
                mensagem="O primeiro acesso j\u00e1 foi configurado. Fa\u00e7a login.",
                tipo="warning",
            )
        )

    if request.method == "POST":
        sigla = normalizar_sigla_professor(request.form.get("sigla", ""))
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if len(sigla) != 3:
            return render_template(
                "primeiro_acesso.html",
                mensagem="Informe uma sigla com exatamente 3 letras.",
                tipo_mensagem="warning",
            )

        if buscar_usuario_por_sigla(sigla):
            return render_template(
                "primeiro_acesso.html",
                mensagem="Essa sigla j\u00e1 possui um acesso cadastrado.",
                tipo_mensagem="warning",
            )

        if len(senha) < 4:
            return render_template(
                "primeiro_acesso.html",
                mensagem="A senha precisa ter pelo menos 4 caracteres.",
                tipo_mensagem="warning",
            )

        if senha != confirmar_senha:
            return render_template(
                "primeiro_acesso.html",
                mensagem="A confirma\u00e7\u00e3o da senha n\u00e3o confere.",
                tipo_mensagem="warning",
            )

        criar_usuario(sigla, senha, "ti")
        return redirect(
            url_for(
                "login",
                mensagem="Primeiro acesso da TI criado. Agora fa\u00e7a login.",
                tipo="success",
            )
        )

    return render_template(
        "primeiro_acesso.html",
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "warning"),
    )


@app.route("/usuarios", methods=["GET", "POST"])
@ti_obrigatorio
def gerenciar_usuarios():
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "success")

    if request.method == "POST":
        sigla = normalizar_sigla_professor(request.form.get("sigla", ""))
        senha = request.form.get("senha", "")
        tipo = request.form.get("tipo", "professor")

        if len(sigla) != 3:
            mensagem = "Informe uma sigla com exatamente 3 letras."
            tipo_mensagem = "warning"
        elif len(senha) < 4:
            mensagem = "A senha precisa ter pelo menos 4 caracteres."
            tipo_mensagem = "warning"
        elif tipo not in TIPOS_USUARIO:
            mensagem = "Selecione um tipo de acesso v\u00e1lido."
            tipo_mensagem = "warning"
        elif buscar_usuario_por_sigla(sigla):
            mensagem = "Essa sigla j\u00e1 possui um acesso cadastrado."
            tipo_mensagem = "warning"
        else:
            criar_usuario(sigla, senha, tipo)
            return redirect(
                url_for(
                    "gerenciar_usuarios",
                    mensagem=f"Acesso {TIPOS_USUARIO[tipo].lower()} criado para {sigla}.",
                    tipo="success",
                )
            )

    return render_template(
        "usuarios.html",
        usuarios=listar_usuarios(),
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
        tipos_usuario=TIPOS_USUARIO,
    )


@app.route("/")
@login_obrigatorio
def home():
    disponibilidade, salas_ocupadas = buscar_disponibilidade_geral()
    dados_computadores, locais_computadores_ocupados = (
        buscar_disponibilidade_computadores_geral()
    )
    return render_template(
        "home.html",
        dados=disponibilidade,
        salas_ocupadas=salas_ocupadas,
        dados_computadores=dados_computadores,
        locais_computadores_ocupados=locais_computadores_ocupados,
        recursos_computadores=RECURSOS_COMPUTADORES,
        salas=SALAS,
        horarios=HORARIOS,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "warning"),
    )


@app.route("/computadores")
@login_obrigatorio
def home_computadores():
    disponibilidade, locais_ocupados = buscar_disponibilidade_computadores_geral()
    return render_template(
        "computadores.html",
        dados=disponibilidade,
        locais_ocupados=locais_ocupados,
        recursos_computadores=RECURSOS_COMPUTADORES,
        salas=SALAS,
        horarios=HORARIOS,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "warning"),
    )


@app.route("/computadores/solicitar", methods=["POST"])
@login_obrigatorio
def solicitar_computadores():
    sigla = session.get("usuario_sigla")
    recurso = request.form.get("recurso", "")
    nivel = request.form.get("nivel", "")
    local = request.form.get("local", "")
    data_requisicao = request.form.get("data", "")
    quantidade = request.form.get("quantidade", "")
    aulas = request.form.getlist("aulas")

    erro_validacao, quantidade_int, local_normalizado = validar_dados_requisicao_computador(
        nivel,
        recurso,
        local,
        data_requisicao,
        quantidade,
    )
    if erro_validacao:
        return redirect(
            url_for(
                "home_computadores",
                mensagem=erro_validacao,
                tipo="warning",
            )
        )

    if not aulas:
        return redirect(
            url_for(
                "home_computadores",
                mensagem="Selecione pelo menos uma aula para solicitar os computadores.",
                tipo="warning",
            )
        )

    conn = conectar()
    c = conn.cursor()
    resultado = registrar_requisicoes_computador(
        c,
        sigla,
        recurso,
        quantidade_int,
        local_normalizado,
        data_requisicao,
        nivel,
        aulas,
    )
    conn.commit()
    conn.close()

    mensagens, tipo = montar_mensagens_requisicao_computador(resultado)

    if not mensagens:
        tipo = "warning"
        mensagens.append("Nenhum hor\u00e1rio foi solicitado.")

    return redirect(
        url_for(
            "ver_requisicoes_computadores",
            data=data_requisicao,
            mensagem=" ".join(mensagens),
            tipo=tipo,
        )
    )


@app.route("/computadores/consultar")
@login_obrigatorio
def ver_requisicoes_computadores():
    data_filtro = request.args.get("data") or date.today().isoformat()
    requisicoes, disponibilidade = buscar_requisicoes_computadores_por_data(data_filtro)
    requisicoes = marcar_permissoes_requisicoes_computadores(requisicoes)
    painel = montar_painel_disponibilidade_computadores(disponibilidade)

    return render_template(
        "computadores_consulta.html",
        requisicoes=requisicoes,
        painel=painel,
        data_selecionada=data_filtro,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "success"),
    )


@app.route("/reservar", methods=["POST"])
@login_obrigatorio
def reservar():
    sigla = session.get("usuario_sigla")
    data_reserva = request.form.get("data", "")
    nivel = request.form.get("nivel", "")
    aulas = request.form.getlist("aulas")
    incluir_projetor = request.form.get("incluir_projetor") == "on"
    incluir_computador = request.form.get("incluir_computador") == "on"

    if not incluir_projetor and not incluir_computador:
        return redirect(
            url_for(
                "home",
                mensagem="Selecione pelo menos um recurso: projetor, computador ou ambos.",
                tipo="warning",
            )
        )

    if not aulas:
        return redirect(
            url_for(
                "home",
                mensagem="Selecione pelo menos uma aula para concluir a solicita\u00e7\u00e3o.",
                tipo="warning",
            )
        )

    mensagens = []
    tipo = "success"

    conn = conectar()
    c = conn.cursor()

    if incluir_projetor:
        sala = request.form.get("sala", "")
        erro_validacao = validar_dados_reserva(nivel, sala, data_reserva)
        if erro_validacao:
            conn.close()
            return redirect(
                url_for(
                    "home",
                    mensagem=erro_validacao,
                    tipo="warning",
                )
            )

        som = request.form.get("som", "N\u00e3o") if nivel == "Fundamental" else "N\u00e3o"
        resultado_projetor = registrar_reservas_projetor(
            c,
            sigla,
            sala,
            data_reserva,
            nivel,
            aulas,
            som,
        )
        mensagens_projetor, tipo_projetor = montar_mensagens_reserva_projetor(
            resultado_projetor
        )
        mensagens.extend(mensagens_projetor)
        if tipo_projetor == "warning":
            tipo = "warning"

    if incluir_computador:
        recurso = request.form.get("recurso_computador", "")
        local_computador = request.form.get("local_computador", "")
        quantidade_computador = request.form.get("quantidade_computador", "")
        erro_validacao, quantidade_int, local_normalizado = (
            validar_dados_requisicao_computador(
                nivel,
                recurso,
                local_computador,
                data_reserva,
                quantidade_computador,
            )
        )
        if erro_validacao:
            conn.close()
            return redirect(
                url_for(
                    "home",
                    mensagem=erro_validacao,
                    tipo="warning",
                )
            )

        resultado_computador = registrar_requisicoes_computador(
            c,
            sigla,
            recurso,
            quantidade_int,
            local_normalizado,
            data_reserva,
            nivel,
            aulas,
        )
        mensagens_computador, tipo_computador = montar_mensagens_requisicao_computador(
            resultado_computador
        )
        mensagens.extend(mensagens_computador)
        if tipo_computador == "warning":
            tipo = "warning"

    conn.commit()
    conn.close()

    if not mensagens:
        tipo = "warning"
        mensagens.append("Nenhum hor\u00e1rio foi reservado.")

    return redirect(
        url_for(
            "ver_reservas",
            data=data_reserva,
            mensagem=" ".join(mensagens),
            tipo=tipo,
        )
    )


@app.route("/reservas")
@login_obrigatorio
def ver_reservas():
    data_filtro = request.args.get("data") or date.today().isoformat()
    reservas, disponibilidade = buscar_reservas_por_data(data_filtro)
    reservas = marcar_permissoes_reservas(reservas)
    painel = montar_painel_disponibilidade(disponibilidade)

    return render_template(
        "reservas.html",
        reservas=reservas,
        painel=painel,
        data_selecionada=data_filtro,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "success"),
    )


@app.route("/reservas/<int:reserva_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_reserva(reserva_id):
    proximo = request.values.get("next", "")
    reserva = buscar_reserva_por_id(reserva_id)

    if not reserva:
        return redirecionar_com_mensagem(
            proximo,
            "ver_reservas",
            "Reserva n\u00e3o encontrada.",
            "warning",
            data=date.today().isoformat(),
        )

    if not usuario_pode_gerenciar_reserva(reserva):
        return redirecionar_com_mensagem(
            proximo,
            "ver_reservas",
            "Voc\u00ea n\u00e3o tem permiss\u00e3o para editar esta reserva.",
            "warning",
            data=reserva["data"],
        )

    reserva = marcar_permissoes_reserva(reserva)
    dados_formulario = {
        "sigla": reserva["sigla"],
        "nivel": reserva["nivel"],
        "sala": reserva["sala"],
        "data": reserva["data"],
        "horario": reserva["horario"],
        "som": reserva["som"],
    }
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "warning")

    if request.method == "POST":
        dados_formulario = {
            "sigla": reserva["sigla"],
            "nivel": request.form.get("nivel", ""),
            "sala": request.form.get("sala", ""),
            "data": request.form.get("data", ""),
            "horario": request.form.get("horario", ""),
            "som": request.form.get("som", "N\u00e3o"),
        }

        if dados_formulario["nivel"] != "Fundamental":
            dados_formulario["som"] = "N\u00e3o"

        erro_validacao = validar_dados_reserva(
            dados_formulario["nivel"],
            dados_formulario["sala"],
            dados_formulario["data"],
            dados_formulario["horario"],
        )

        if erro_validacao:
            mensagem = erro_validacao
            tipo_mensagem = "warning"
        else:
            conn = conectar()
            c = conn.cursor()
            conflito_sala, limite_atingido = verificar_conflitos_reserva(
                c,
                dados_formulario["data"],
                dados_formulario["horario"],
                dados_formulario["nivel"],
                dados_formulario["sala"],
                reserva_id_ignorada=reserva_id,
            )

            if conflito_sala:
                mensagem = (
                    "J\u00e1 existe um projetor reservado para essa sala nesse hor\u00e1rio."
                )
                tipo_mensagem = "warning"
            elif limite_atingido:
                mensagem = (
                    "N\u00e3o foi poss\u00edvel atualizar: os 4 projetores desse n\u00edvel "
                    "j\u00e1 est\u00e3o em uso no hor\u00e1rio escolhido."
                )
                tipo_mensagem = "warning"
            else:
                c.execute(
                    """
                    UPDATE reservas
                    SET sala = ?, data = ?, horario = ?, nivel = ?, som = ?
                    WHERE id = ?
                    """,
                    (
                        dados_formulario["sala"],
                        dados_formulario["data"],
                        dados_formulario["horario"],
                        dados_formulario["nivel"],
                        normalizar_som(dados_formulario["som"]),
                        reserva_id,
                    ),
                )
                conn.commit()
                conn.close()

                return redirecionar_com_mensagem(
                    proximo,
                    "ver_reservas",
                    "Reserva atualizada com sucesso.",
                    "success",
                    data=dados_formulario["data"],
                )

            conn.close()

    return render_template(
        "editar_reserva.html",
        reserva=reserva,
        reserva_form=dados_formulario,
        niveis=NIVEL_LABELS,
        salas=SALAS,
        horarios=HORARIOS,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
        proximo=destino_seguro(proximo, "ver_reservas", data=reserva["data"]),
    )


@app.route("/reservas/<int:reserva_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_reserva(reserva_id):
    proximo = request.form.get("next", "")
    reserva = buscar_reserva_por_id(reserva_id)

    if not reserva:
        return redirecionar_com_mensagem(
            proximo,
            "ver_reservas",
            "Reserva n\u00e3o encontrada.",
            "warning",
            data=date.today().isoformat(),
        )

    if not usuario_pode_gerenciar_reserva(reserva):
        return redirecionar_com_mensagem(
            proximo,
            "ver_reservas",
            "Voc\u00ea n\u00e3o tem permiss\u00e3o para excluir esta reserva.",
            "warning",
            data=reserva["data"],
        )

    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        DELETE FROM reservas
        WHERE id = ?
        """,
        (reserva_id,),
    )
    conn.commit()
    conn.close()

    return redirecionar_com_mensagem(
        proximo,
        "ver_reservas",
        (
            f"Reserva de {reserva['sigla']} em {reserva['sala_label']} "
            f"({reserva['aula_label']}) exclu\u00edda com sucesso."
        ),
        "success",
        data=reserva["data"],
    )


@app.route("/painel-ti")
@ti_obrigatorio
def painel_ti():
    data_filtro = request.args.get("data") or date.today().isoformat()
    reservas, disponibilidade = buscar_reservas_por_data(data_filtro)
    reservas = marcar_permissoes_reservas(reservas)
    painel = montar_painel_disponibilidade(disponibilidade)
    planejamento = gerar_planejamento_ti(reservas)
    tarefas_do_dia = montar_tarefas_do_dia(planejamento)

    return render_template(
        "painel_ti.html",
        reservas=reservas,
        painel=painel,
        planejamento=planejamento,
        tarefas_do_dia=tarefas_do_dia,
        data_selecionada=data_filtro,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "success"),
    )


@app.route("/relatorio-ti")
@ti_obrigatorio
def relatorio_ti():
    data_hoje = date.today().isoformat()
    data_inicial = request.args.get("data_inicial") or data_hoje
    data_final = request.args.get("data_final") or data_inicial
    sigla = normalizar_sigla_professor(request.args.get("sigla", ""))
    nivel = request.args.get("nivel", "")
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "success")

    try:
        date.fromisoformat(data_inicial)
        date.fromisoformat(data_final)
    except ValueError:
        data_inicial = data_hoje
        data_final = data_hoje
        mensagem = "Per\u00edodo inv\u00e1lido. O relat\u00f3rio foi ajustado para a data de hoje."
        tipo_mensagem = "warning"

    if data_inicial > data_final:
        data_inicial, data_final = data_final, data_inicial
        mensagem = (
            "A data inicial era maior que a final. O per\u00edodo foi ajustado automaticamente."
        )
        tipo_mensagem = "warning"

    if nivel and nivel not in SALAS:
        nivel = ""
        mensagem = "Filtro de n\u00edvel inv\u00e1lido. Exibindo todos os n\u00edveis."
        tipo_mensagem = "warning"

    reservas = buscar_reservas_relatorio(data_inicial, data_final, nivel=nivel, sigla=sigla)
    reservas = marcar_permissoes_reservas(reservas)
    relatorio = montar_relatorio_ti(reservas)

    return render_template(
        "relatorio_ti.html",
        reservas=reservas,
        relatorio=relatorio,
        data_inicial=data_inicial,
        data_final=data_final,
        sigla=sigla,
        nivel=nivel,
        niveis=NIVEL_LABELS,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
    )


@app.route("/computadores/<int:requisicao_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_requisicao_computador(requisicao_id):
    proximo = request.values.get("next", "")
    requisicao = buscar_requisicao_computador_por_id(requisicao_id)

    if not requisicao:
        return redirecionar_com_mensagem(
            proximo,
            "ver_requisicoes_computadores",
            "Requisi\u00e7\u00e3o de computadores n\u00e3o encontrada.",
            "warning",
            data=date.today().isoformat(),
        )

    if not usuario_pode_gerenciar_por_sigla(requisicao["sigla"]):
        return redirecionar_com_mensagem(
            proximo,
            "ver_requisicoes_computadores",
            "Voc\u00ea n\u00e3o tem permiss\u00e3o para editar esta requisi\u00e7\u00e3o.",
            "warning",
            data=requisicao["data"],
        )

    requisicao = marcar_permissoes_requisicao_computador(requisicao)
    dados_formulario = {
        "sigla": requisicao["sigla"],
        "recurso": requisicao["recurso"],
        "quantidade": requisicao["quantidade"],
        "local": requisicao["local"],
        "data": requisicao["data"],
        "horario": requisicao["horario"],
        "nivel": requisicao["nivel"],
    }
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "warning")

    if request.method == "POST":
        dados_formulario = {
            "sigla": requisicao["sigla"],
            "recurso": request.form.get("recurso", ""),
            "quantidade": request.form.get("quantidade", ""),
            "local": request.form.get("local", ""),
            "data": request.form.get("data", ""),
            "horario": request.form.get("horario", ""),
            "nivel": request.form.get("nivel", ""),
        }

        erro_validacao, quantidade_int, local_normalizado = validar_dados_requisicao_computador(
            dados_formulario["nivel"],
            dados_formulario["recurso"],
            dados_formulario["local"],
            dados_formulario["data"],
            dados_formulario["quantidade"],
            dados_formulario["horario"],
        )

        if erro_validacao:
            mensagem = erro_validacao
            tipo_mensagem = "warning"
        else:
            conn = conectar()
            c = conn.cursor()
            conflito_local, limite_excedido, disponibilidade_restante = (
                verificar_conflitos_requisicao_computador(
                    c,
                    dados_formulario["data"],
                    dados_formulario["horario"],
                    dados_formulario["nivel"],
                    dados_formulario["recurso"],
                    local_normalizado,
                    quantidade_int,
                    requisicao_id_ignorada=requisicao_id,
                )
            )

            if conflito_local:
                mensagem = (
                    "J\u00e1 existe uma requisi\u00e7\u00e3o desse recurso para esse local "
                    "no hor\u00e1rio escolhido."
                )
                tipo_mensagem = "warning"
            elif limite_excedido:
                mensagem = (
                    "N\u00e3o foi poss\u00edvel atualizar: a quantidade solicitada ultrapassa "
                    f"a disponibilidade restante de {disponibilidade_restante} unidade(s)."
                )
                tipo_mensagem = "warning"
            else:
                c.execute(
                    """
                    UPDATE requisicoes_computadores
                    SET recurso = ?, quantidade = ?, local = ?, data = ?, horario = ?, nivel = ?
                    WHERE id = ?
                    """,
                    (
                        dados_formulario["recurso"],
                        quantidade_int,
                        local_normalizado,
                        dados_formulario["data"],
                        dados_formulario["horario"],
                        dados_formulario["nivel"],
                        requisicao_id,
                    ),
                )
                conn.commit()
                conn.close()

                return redirecionar_com_mensagem(
                    proximo,
                    "ver_requisicoes_computadores",
                    "Requisi\u00e7\u00e3o de computadores atualizada com sucesso.",
                    "success",
                    data=dados_formulario["data"],
                )

            conn.close()

            dados_formulario["quantidade"] = quantidade_int
            dados_formulario["local"] = local_normalizado

    return render_template(
        "editar_computador.html",
        requisicao=requisicao,
        requisicao_form=dados_formulario,
        niveis=NIVEL_LABELS,
        salas=SALAS,
        horarios=HORARIOS,
        recursos_computadores=RECURSOS_COMPUTADORES,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
        proximo=destino_seguro(
            proximo,
            "ver_requisicoes_computadores",
            data=requisicao["data"],
        ),
    )


@app.route("/computadores/<int:requisicao_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_requisicao_computador(requisicao_id):
    proximo = request.form.get("next", "")
    requisicao = buscar_requisicao_computador_por_id(requisicao_id)

    if not requisicao:
        return redirecionar_com_mensagem(
            proximo,
            "ver_requisicoes_computadores",
            "Requisi\u00e7\u00e3o de computadores n\u00e3o encontrada.",
            "warning",
            data=date.today().isoformat(),
        )

    if not usuario_pode_gerenciar_por_sigla(requisicao["sigla"]):
        return redirecionar_com_mensagem(
            proximo,
            "ver_requisicoes_computadores",
            "Voc\u00ea n\u00e3o tem permiss\u00e3o para excluir esta requisi\u00e7\u00e3o.",
            "warning",
            data=requisicao["data"],
        )

    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        DELETE FROM requisicoes_computadores
        WHERE id = ?
        """,
        (requisicao_id,),
    )
    conn.commit()
    conn.close()

    return redirecionar_com_mensagem(
        proximo,
        "ver_requisicoes_computadores",
        (
            (
                f"Requisi\u00e7\u00e3o de {requisicao['quantidade']} unidade(s) de "
                f"{requisicao['recurso_label']} para {requisicao['local_label']} exclu\u00edda com sucesso."
            )
            if requisicao["usa_quantidade"]
            else f"Reserva de {requisicao['recurso_label']} exclu\u00edda com sucesso."
        ),
        "success",
        data=requisicao["data"],
    )


@app.route("/computadores/relatorio-ti")
@ti_obrigatorio
def relatorio_computadores_ti():
    data_hoje = date.today().isoformat()
    data_inicial = request.args.get("data_inicial") or data_hoje
    data_final = request.args.get("data_final") or data_inicial
    sigla = normalizar_sigla_professor(request.args.get("sigla", ""))
    nivel = request.args.get("nivel", "")
    recurso = request.args.get("recurso", "")
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "success")

    try:
        date.fromisoformat(data_inicial)
        date.fromisoformat(data_final)
    except ValueError:
        data_inicial = data_hoje
        data_final = data_hoje
        mensagem = "Per\u00edodo inv\u00e1lido. O relat\u00f3rio foi ajustado para a data de hoje."
        tipo_mensagem = "warning"

    if data_inicial > data_final:
        data_inicial, data_final = data_final, data_inicial
        mensagem = (
            "A data inicial era maior que a final. O per\u00edodo foi ajustado automaticamente."
        )
        tipo_mensagem = "warning"

    if nivel and nivel not in SALAS:
        nivel = ""
        mensagem = "Filtro de n\u00edvel inv\u00e1lido. Exibindo todos os n\u00edveis."
        tipo_mensagem = "warning"

    if recurso and recurso not in RECURSOS_COMPUTADORES:
        recurso = ""
        mensagem = "Filtro de recurso inv\u00e1lido. Exibindo todos os recursos."
        tipo_mensagem = "warning"

    requisicoes = buscar_requisicoes_computadores_relatorio(
        data_inicial,
        data_final,
        nivel=nivel,
        sigla=sigla,
        recurso=recurso,
    )
    requisicoes = marcar_permissoes_requisicoes_computadores(requisicoes)
    relatorio = montar_relatorio_computadores_ti(requisicoes)

    return render_template(
        "relatorio_computadores_ti.html",
        requisicoes=requisicoes,
        relatorio=relatorio,
        data_inicial=data_inicial,
        data_final=data_final,
        sigla=sigla,
        nivel=nivel,
        recurso=recurso,
        niveis=NIVEL_LABELS,
        recursos_computadores=RECURSOS_COMPUTADORES,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
    )


if __name__ == "__main__":
    app.run(
        debug=app.config["FLASK_DEBUG"],
        host=app.config["HOST"],
        port=app.config["PORT"],
    )
