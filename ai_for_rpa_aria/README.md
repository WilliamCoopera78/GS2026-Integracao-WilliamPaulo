# ARIA – Automated Reconnaissance & Intelligence for Astronomy

Pipeline de automação para coleta e análise de dados espaciais em tempo real.
Global Solution 2026 da FIAP — AI for RPA.

Membros:

Paulo Gabriel - RM 566446

William Stahl - RM 562800

---

## O que faz

O ARIA roda um pipeline que:

1. Coleta notícias espaciais recentes via Spaceflight News API
2. Busca dados de NEOs (objetos próximos da Terra) na API da NASA
3. Registra a posição atual da ISS
4. Manda tudo para um modelo de linguagem local (Ollama + llama3.2) que gera um relatório de análise
5. Persiste os dados em SQLite e exporta relatórios em CSV, JSON e TXT
6. Sobe uma API REST Flask para consulta dos dados

Tudo roda localmente, sem custo e sem precisar de chave de API externa.

---

## Pré-requisitos

- Python 3.12+
- [Ollama](https://ollama.com/download) instalado e com o modelo baixado:

```
ollama pull llama3.2
```

---

## Instalação

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / Mac
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Uso

**Rodar o pipeline completo:**

```bash
# Terminal 1 — garante que o Ollama está ativo
ollama serve

# Terminal 2 — executa a automação
python src/main.py
```

Os relatórios são gerados na pasta `reports/`.

**Subir só a API REST:**

```bash
python src/api.py
# disponível em http://localhost:5000
```

**Via Docker:**

```bash
docker-compose up --build
```

---

## Estrutura

```
src/
├── main.py              — orquestrador do pipeline
├── scraper.py           — coleta dados via HTTP e BeautifulSoup4
├── database.py          — operações SQLite (DDL, upsert, queries)
├── ai_analyzer.py       — integração com Ollama para análise de texto
├── api.py               — API REST com Flask
├── report_generator.py  — exporta CSV, JSON, TXT e XLSX
└── monitor.py           — monitoramento de sistema com psutil
```

---

## Endpoints da API

| Método | Rota | O que retorna |
|--------|------|---------------|
| GET | `/` | status + métricas de sistema |
| GET | `/articles` | notícias coletadas (param: `?limit=N`) |
| GET | `/neos` | NEOs (param: `?hazardous=true`) |
| GET | `/iss` | última posição registrada da ISS |
| GET | `/analysis` | último relatório gerado pela IA |
| GET | `/stats` | contagens do banco + uso de CPU/RAM |
| POST | `/run-pipeline` | dispara o pipeline em background |

---

## Fontes de dados

- **Spaceflight News API** — `api.spaceflightnewsapi.net/v4`
- **NASA NEO Feed** — `api.nasa.gov/neo/rest/v1/feed` (DEMO_KEY)
- **Open Notify** — `api.open-notify.org/iss-now.json`

Todas públicas e sem autenticação obrigatória.

---
