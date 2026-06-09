"""
API REST do sistema 

Endpoints disponíveis:
  GET  /               – Health check e status do sistema
  GET  /articles       – Lista de artigos coletados
  GET  /neos           – Lista de NEOs (query param: ?hazardous=true)
  GET  /iss            – Última posição registrada da ISS
  GET  /analysis       – Última análise de IA gerada
  GET  /stats          – Estatísticas gerais do banco de dados
  POST /run-pipeline   – Dispara o pipeline de automação manualmente
"""

import logging
import threading
from datetime import datetime
from flask import Flask, jsonify, request, abort

from database import MissionDatabase
from monitor import SystemMonitor

log = logging.getLogger("ARIA.API")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

db      = MissionDatabase("data/aria.db")
monitor = SystemMonitor()


# ── Utilitários ──────────────────────────────────────────────────────────────
def _ok(data: dict | list, status: int = 200):
    return jsonify({"status": "ok", "data": data, "timestamp": datetime.utcnow().isoformat()}), status


def _err(message: str, status: int = 400):
    return jsonify({"status": "error", "message": message}), status


# ── Middleware simples de log ─────────────────────────────────────────────────
@app.after_request
def log_request(response):
    log.info("%s %s → %d", request.method, request.path, response.status_code)
    return response


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    """Health check + snapshot de sistema."""
    snap = monitor.snapshot()
    return _ok({
        "service":     "ARIA – Automated Reconnaissance & Intelligence for Astronomy",
        "version":     "1.0.0",
        "description": "FIAP Global Solution 2026 | AI for RPA",
        "system":      snap,
    })


@app.get("/articles")
def get_articles():
    """
    Retorna artigos de notícias espaciais coletados.
    Query params:
      - limit (int, default=20)
    """
    try:
        limit = int(request.args.get("limit", 20))
        if limit < 1 or limit > 100:
            return _err("limit deve estar entre 1 e 100.", 400)
    except ValueError:
        return _err("limit deve ser um inteiro.", 400)

    articles = db.get_articles(limit=limit)
    return _ok({"count": len(articles), "articles": articles})


@app.get("/neos")
def get_neos():
    """
    Retorna NEOs coletados.
    Query params:
      - hazardous=true  (filtra apenas potencialmente perigosos)
    """
    only_hazardous = request.args.get("hazardous", "").lower() == "true"
    neos = db.get_neos(only_hazardous=only_hazardous)
    return _ok({
        "count":    len(neos),
        "filtered": only_hazardous,
        "neos":     neos,
    })


@app.get("/iss")
def get_iss():
    """Retorna a última posição registrada da ISS."""
    pos = db.get_latest_iss()
    if not pos:
        return _err("Nenhuma posição da ISS disponível. Execute o pipeline primeiro.", 404)
    return _ok(pos)


@app.get("/analysis")
def get_analysis():
    """Retorna o último relatório de análise gerado pela IA."""
    analysis = db.get_latest_analysis()
    if not analysis:
        return _err("Nenhuma análise disponível. Execute o pipeline primeiro.", 404)
    return _ok(analysis)


@app.get("/stats")
def get_stats():
    """Retorna estatísticas gerais: contagens do banco + monitoramento do sistema."""
    db_stats  = db.get_stats()
    sys_stats = monitor.snapshot()
    return _ok({"database": db_stats, "system": sys_stats})


@app.post("/run-pipeline")
def run_pipeline_endpoint():
    """
    Dispara o pipeline de automação em background.
    Não bloqueia a resposta HTTP.
    """
    def _run():
        from main import run_pipeline
        try:
            run_pipeline()
        except Exception as e:
            log.error("Erro no pipeline: %s", e)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return _ok({"message": "Pipeline iniciado em background. Consulte /stats para progresso."}), 202


# ── Tratamento de erros HTTP ──────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return _err(f"Endpoint não encontrado: {request.path}", 404)


@app.errorhandler(405)
def method_not_allowed(e):
    return _err(f"Método {request.method} não permitido neste endpoint.", 405)


@app.errorhandler(500)
def internal_error(e):
    log.exception("Erro interno: %s", e)
    return _err("Erro interno do servidor.", 500)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from pathlib import Path
    Path("data").mkdir(exist_ok=True)
    db.setup()
    port = int(os.getenv("PORT", 5000))
    log.info("🚀 ARIA API iniciada na porta %d", port)
    app.run(host="0.0.0.0", port=port, debug=False)
