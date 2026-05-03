from collections import defaultdict, deque
from time import time


class RateLimitExceeded(Exception):
    pass


class DemoRateLimiter:
    def __init__(self, limite, janela_segundos):
        self.limite = limite
        self.janela_segundos = janela_segundos
        self._acessos = defaultdict(deque)

    def verificar(self, chave):
        agora = time()
        acessos = self._acessos[chave]

        while acessos and agora - acessos[0] > self.janela_segundos:
            acessos.popleft()

        if len(acessos) >= self.limite:
            raise RateLimitExceeded

        acessos.append(agora)


def identificar_cliente(request):
    encaminhado = request.headers.get("X-Forwarded-For", "")
    if encaminhado:
        return encaminhado.split(",", 1)[0].strip()[:80]

    return (request.remote_addr or "local")[:80]
