"""
ARIA - Automated Reconnaissance & Intelligence for Astronomy
Projeto de automação RPA para coleta, análise e geração de relatórios sobre missões espaciais.
"""

import time
import json
import logging
from datetime import datetime
from pathlib import Path

# ─── Cria pastas necessárias ANTES de qualquer outra coisa ──────────────────
Path("data").mkdir(exist_ok=True)
Path("reports").mkdir(exist_ok=True)

from scraper import SpaceScraper
from database import MissionDatabase
from ai_analyzer import AIAnalyzer
from report_generator import ReportGenerator
from monitor import SystemMonitor

# ─── Configuração de logging ────────────────────────────────────────────────
import sys
import io

# Fix para encoding UTF-8 no Windows 
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("data/aria.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ARIA.Main")


def banner():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║   █████╗ ██████╗ ██╗ █████╗                                      ║
║  ██╔══██╗██╔══██╗██║██╔══██╗                                     ║
║  ███████║██████╔╝██║███████║                                     ║
║  ██╔══██║██╔══██╗██║██╔══██║                                     ║
║  ██║  ██║██║  ██║██║██║  ██║                                     ║
║  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝                                     ║
║  Automated Reconnaissance & Intelligence for Astronomy           ║
║  FIAP | Global Solution 2026 | AI for RPA                    :P  ║
╚══════════════════════════════════════════════════════════════════╝
    """)


def run_pipeline():
    """Pipeline principal de automação RPA."""
    banner()
    start_time = datetime.now()
    log.info("🚀 Pipeline ARIA iniciado em %s", start_time.isoformat())

    # ── 1. Monitoramento de sistema (psutil) ────────────────────────────────
    monitor = SystemMonitor()
    sys_snapshot = monitor.snapshot()
    log.info("📊 Sistema: CPU=%.1f%% | RAM=%.1f%% | Disco=%.1f%%",
             sys_snapshot["cpu_percent"],
             sys_snapshot["ram_percent"],
             sys_snapshot["disk_percent"])

    # ── 2. Inicializa banco de dados (SQLite) ───────────────────────────────
    db = MissionDatabase("data/aria.db")
    db.setup()
    log.info("🗄️  Banco de dados inicializado.")

    # ── 3. Web Scraping / consumo de APIs (BeautifulSoup4 + requests) ───────
    scraper = SpaceScraper()

    log.info("🌐 Coletando artigos de notícias espaciais…")
    articles = scraper.fetch_spaceflight_news(limit=15)
    db.insert_articles(articles)
    log.info("   ✔ %d artigos salvos.", len(articles))

    log.info("☄️  Coletando dados de NEOs (Near-Earth Objects) da NASA…")
    neos = scraper.fetch_nasa_neos()
    db.insert_neos(neos)
    log.info("   ✔ %d NEOs salvos.", len(neos))

    log.info("🛸 Coletando missões ISS (posição atual)…")
    iss = scraper.fetch_iss_position()
    db.insert_iss_position(iss)
    log.info("   ✔ Posição ISS salva: lat=%.4f, lon=%.4f",
             iss["latitude"], iss["longitude"])

    # ── 4. Análise com IA  ──────────────────────────
    log.info("🤖 Enviando dados para análise de IA…")
    analyzer = AIAnalyzer()
    analysis = analyzer.analyze_mission_data(articles[:5], neos[:10], iss)
    db.insert_analysis(analysis)
    log.info("   ✔ Análise de IA concluída.")

    # ── 5. Geração de artefatos / outputs técnicos ──────────────────────────
    log.info("📄 Gerando relatórios e artefatos…")
    reporter = ReportGenerator(db)
    reporter.export_articles_csv("reports/articles.csv")
    reporter.export_neos_csv("reports/neos.csv")
    reporter.export_full_json("reports/mission_data.json")
    reporter.export_summary_txt("reports/summary.txt", analysis, sys_snapshot)
    log.info("   ✔ Relatórios exportados em /reports/")

    # ── 6. Snapshot final de sistema ────────────────────────────────────────
    end_snapshot = monitor.snapshot()
    elapsed = (datetime.now() - start_time).total_seconds()

    log.info("✅ Pipeline concluído em %.2fs | CPU final=%.1f%% | RAM=%.1f%%",
             elapsed, end_snapshot["cpu_percent"], end_snapshot["ram_percent"])

    print("\n" + "="*65)
    print("  ARIA Pipeline finalizado com sucesso!")
    print(f"  Duração: {elapsed:.2f}s")
    print("  Artefatos gerados em ./reports/")
    print("  API REST disponível em http://localhost:5000")
    print("="*65 + "\n")

    return {"status": "ok", "elapsed_seconds": elapsed, "analysis": analysis}


if __name__ == "__main__":
    run_pipeline()
