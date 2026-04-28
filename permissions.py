def usuario_eh_ti(tipo_usuario):
    return tipo_usuario == "ti"


def usuario_pode_gerenciar_por_sigla(sigla_registro, sigla_usuario, tipo_usuario):
    if not sigla_usuario or not sigla_registro:
        return False

    return usuario_eh_ti(tipo_usuario) or sigla_usuario == sigla_registro


def usuario_pode_gerenciar_reserva(reserva, sigla_usuario, tipo_usuario):
    if not reserva:
        return False

    return usuario_pode_gerenciar_por_sigla(
        reserva["sigla"],
        sigla_usuario,
        tipo_usuario,
    )
