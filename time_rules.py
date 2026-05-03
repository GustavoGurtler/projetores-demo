from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - fallback for older Python versions
    ZoneInfo = None

    class ZoneInfoNotFoundError(Exception):
        pass


DEFAULT_TIMEZONE = "America/Sao_Paulo"


def obter_fuso_horario(nome_fuso):
    if not nome_fuso or ZoneInfo is None:
        return None

    try:
        return ZoneInfo(nome_fuso)
    except ZoneInfoNotFoundError:
        return None


def agora_no_fuso(nome_fuso=DEFAULT_TIMEZONE):
    fuso = obter_fuso_horario(nome_fuso)
    if fuso is None:
        return datetime.now()

    return datetime.now(fuso)


def montar_data_hora(data_iso, horario, nome_fuso=DEFAULT_TIMEZONE):
    data_referencia = date.fromisoformat(data_iso)
    horario_referencia = datetime.strptime(horario, "%H:%M").time()
    data_hora = datetime.combine(data_referencia, horario_referencia)
    fuso = obter_fuso_horario(nome_fuso)

    if fuso is None:
        return data_hora

    return data_hora.replace(tzinfo=fuso)


def horario_ja_passou(data_iso, horario, *, agora=None, fuso_horario=DEFAULT_TIMEZONE):
    inicio = montar_data_hora(data_iso, horario, fuso_horario)
    agora = agora or agora_no_fuso(fuso_horario)

    if inicio.tzinfo and not agora.tzinfo:
        agora = agora.replace(tzinfo=inicio.tzinfo)
    elif agora.tzinfo and not inicio.tzinfo:
        inicio = inicio.replace(tzinfo=agora.tzinfo)

    return inicio <= agora


def filtrar_horarios_futuros(
    data_iso,
    horarios,
    *,
    agora=None,
    fuso_horario=DEFAULT_TIMEZONE,
):
    try:
        referencia = agora or agora_no_fuso(fuso_horario)
        passados = [
            horario
            for horario in horarios
            if horario_ja_passou(
                data_iso,
                horario,
                agora=referencia,
                fuso_horario=fuso_horario,
            )
        ]
    except (TypeError, ValueError):
        return list(horarios), []

    futuros = [horario for horario in horarios if horario not in passados]
    return futuros, passados
