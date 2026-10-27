"""Serve a pasta docs/ e liga o controle remoto aos slides.

Uso: python3 docs/apresentacao/servidor.py [porta]
  slides:   /apresentacao/
  controle: /apresentacao/controle.html

POST /remoto      publica uma mensagem JSON para todos os conectados.
GET  /remoto?desde=N  devolve as mensagens depois de N, esperando até 20 s
                      (long-polling: o túnel do Cloudflare segura fluxos SSE).
"""
import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

DOCS = Path(__file__).resolve().parent.parent
seq = 0  # número da última mensagem publicada
mensagens: list[tuple[int, dict]] = []  # só as 200 mais recentes
estado = None  # último estado dos slides, para o controle recém-aberto
novidade = threading.Condition()


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        global estado, seq
        if self.path != "/remoto":
            return self.send_error(404)
        try:
            msg = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 65536)))
        except ValueError:
            return self.send_error(400)
        with novidade:
            if "estado" in msg:
                estado = msg
            seq += 1
            mensagens.append((seq, msg))
            del mensagens[:-200]
            novidade.notify_all()
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path != "/remoto":
            return super().do_GET()
        with novidade:
            desde = int(parse_qs(url.query).get("desde", ["-1"])[0])
            if desde < 0:  # primeira chamada: o ponto de partida e o estado atual
                resposta = {"seq": seq, "msgs": [estado] if estado else []}
            else:
                novidade.wait_for(lambda: seq > desde, timeout=20)
                resposta = {"seq": seq, "msgs": [m for n, m in mensagens if n > desde]}
        corpo = json.dumps(resposta).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(("127.0.0.1", porta), partial(Handler, directory=str(DOCS))).serve_forever()
