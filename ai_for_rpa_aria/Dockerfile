# ─────────────────────────────────────────────────────────────────
# Dockerfile – ARIA Space RPA
# FIAP | Global Solution 2026 | AI for RPA
#
# ─────────────────────────────────────────────────────────────────

# ── Imagem base leve ──────────────────────────────────────────────
FROM python:3.12-slim

# Metadados
LABEL maintainer="FIAP Global Solution 2026"
LABEL description="ARIA – Automated Reconnaissance & Intelligence for Astronomy"
LABEL version="1.0.0"

# ── Variáveis de ambiente ─────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=5000

# ── Diretório de trabalho ─────────────────────────────────────────
WORKDIR /app

# ── Instala dependências do sistema ──────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Copia e instala dependências Python ──────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copia código-fonte ────────────────────────────────────────────
COPY src/ ./src/

# ── Cria diretórios de dados e relatórios ─────────────────────────
RUN mkdir -p data reports

# ── Healthcheck da API ────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# ── Expõe porta da API REST ───────────────────────────────────────
EXPOSE ${PORT}

# ── Ponto de entrada padrão: API Flask ───────────────────────────
# Para rodar apenas o pipeline: docker run aria python src/main.py
CMD ["python", "src/api.py"]
