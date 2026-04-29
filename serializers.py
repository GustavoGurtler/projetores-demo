from domain import HORARIOS_POR_INICIO, LIMITE_COMPUTADORES_POR_RESERVA
from domain import NIVEL_LABELS, RECURSOS_COMPUTADORES, SALAS
from permissions import usuario_pode_gerenciar_por_sigla
from permissions import usuario_pode_gerenciar_reserva
from validators import normalizar_som


def rotulo_local_computador(nivel, recurso, local):
    configuracao = RECURSOS_COMPUTADORES.get(recurso, {})

    if local == configuracao.get("local_fixo"):
        return configuracao.get("local_label", local)

    return SALAS.get(nivel, {}).get(local, local or "Local n\u00e3o informado")


def serializar_reserva(linha):
    reserva = {
        "id": linha[0],
        "sigla": linha[1],
        "sala": linha[2],
        "data": linha[3],
        "horario": linha[4],
        "nivel": linha[5],
        "som": normalizar_som(linha[6]),
    }

    faixa = HORARIOS_POR_INICIO.get(reserva["nivel"], {}).get(reserva["horario"])
    reserva["nivel_label"] = NIVEL_LABELS.get(reserva["nivel"], reserva["nivel"])
    reserva["sala_label"] = SALAS.get(reserva["nivel"], {}).get(
        reserva["sala"],
        f"Sala {reserva['sala']}",
    )
    reserva["aula_label"] = faixa["label"] if faixa else reserva["horario"]
    reserva["horario_fim"] = faixa["fim"] if faixa else ""
    reserva["pode_gerenciar"] = False
    return reserva


def marcar_permissoes_reserva(
    reserva,
    sigla_usuario=None,
    tipo_usuario=None,
):
    if not reserva:
        return None

    reserva["pode_gerenciar"] = usuario_pode_gerenciar_reserva(
        reserva,
        sigla_usuario,
        tipo_usuario,
    )
    return reserva


def marcar_permissoes_reservas(
    reservas,
    sigla_usuario=None,
    tipo_usuario=None,
):
    return [
        marcar_permissoes_reserva(
            reserva,
            sigla_usuario=sigla_usuario,
            tipo_usuario=tipo_usuario,
        )
        for reserva in reservas
    ]


def serializar_requisicao_computador(linha):
    requisicao = {
        "id": linha[0],
        "sigla": linha[1],
        "recurso": linha[2],
        "quantidade": linha[3],
        "local": linha[4],
        "data": linha[5],
        "horario": linha[6],
        "nivel": linha[7],
    }

    faixa = HORARIOS_POR_INICIO.get(requisicao["nivel"], {}).get(requisicao["horario"])
    recurso = RECURSOS_COMPUTADORES.get(requisicao["recurso"], {})
    requisicao["nivel_label"] = NIVEL_LABELS.get(
        requisicao["nivel"],
        requisicao["nivel"],
    )
    requisicao["recurso_label"] = recurso.get("label", requisicao["recurso"])
    requisicao["recurso_total"] = recurso.get("total", 0)
    requisicao["max_por_reserva"] = recurso.get(
        "max_por_reserva",
        min(requisicao["recurso_total"], LIMITE_COMPUTADORES_POR_RESERVA),
    )
    requisicao["usa_sala"] = recurso.get("usa_sala", True)
    requisicao["usa_quantidade"] = recurso.get("usa_quantidade", True)
    requisicao["capacidade_label"] = recurso.get(
        "capacidade_label",
        f"{requisicao['recurso_total']} unidades",
    )
    requisicao["local_label"] = rotulo_local_computador(
        requisicao["nivel"],
        requisicao["recurso"],
        requisicao["local"],
    )
    requisicao["quantidade_label"] = (
        str(requisicao["quantidade"])
        if requisicao["usa_quantidade"]
        else "Sala completa"
    )
    requisicao["aula_label"] = faixa["label"] if faixa else requisicao["horario"]
    requisicao["horario_fim"] = faixa["fim"] if faixa else ""
    requisicao["pode_gerenciar"] = False
    return requisicao


def marcar_permissoes_requisicao_computador(
    requisicao,
    sigla_usuario=None,
    tipo_usuario=None,
):
    if not requisicao:
        return None

    requisicao["pode_gerenciar"] = usuario_pode_gerenciar_por_sigla(
        requisicao["sigla"],
        sigla_usuario,
        tipo_usuario,
    )
    return requisicao


def marcar_permissoes_requisicoes_computadores(
    requisicoes,
    sigla_usuario=None,
    tipo_usuario=None,
):
    return [
        marcar_permissoes_requisicao_computador(
            requisicao,
            sigla_usuario=sigla_usuario,
            tipo_usuario=tipo_usuario,
        )
        for requisicao in requisicoes
    ]
