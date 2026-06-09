"""
Responsabilidades:
  • Criação e migração de tabelas (DDL)
  • Inserção com upsert (INSERT OR REPLACE)
  • Consultas tipadas para a API REST
  • Context manager para conexões seguras
"""

import sqlite3
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any

log = logging.getLogger("ARIA.Database")

DB_SCHEMA = """
-- Artigos de notícias espaciais
CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id    TEXT    UNIQUE,
    title        TEXT    NOT NULL,
    summary      TEXT,
    url          TEXT,
    image_url    TEXT,
    news_site    TEXT,
    published_at TEXT,
    collected_at TEXT
);

-- NEOs (Near-Earth Objects) da NASA
CREATE TABLE IF NOT EXISTS neos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    neo_id           TEXT    UNIQUE,
    name             TEXT,
    is_hazardous     INTEGER DEFAULT 0,
    diameter_km_min  REAL,
    diameter_km_max  REAL,
    velocity_kph     REAL,
    miss_distance_km REAL,
    approach_date    TEXT,
    nasa_url         TEXT,
    collected_at     TEXT
);

-- Posições históricas da ISS
CREATE TABLE IF NOT EXISTS iss_positions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude     REAL,
    longitude    REAL,
    timestamp    INTEGER,
    collected_at TEXT
);

-- Resultados de análise de IA
CREATE TABLE IF NOT EXISTS ai_analyses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    summary      TEXT,
    hazard_alert TEXT,
    insights     TEXT,
    raw_response TEXT,
    created_at   TEXT
);
"""


class MissionDatabase:
    """Gerenciador de banco de dados SQLite para o projet"""

    def __init__(self, db_path: str = "data/aria.db"):
        self.db_path = db_path
        log.info("Banco de dados configurado em: %s", db_path)

    # ── Context manager para conexões ─────────────────────────────────────
    @contextmanager
    def _connect(self):
        """Abre e fecha a conexão com tratamento de exceções."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row   # retorna dicts-like rows
        conn.execute("PRAGMA journal_mode=WAL")  # escrita simultânea
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            log.error("Erro no banco de dados: %s", e)
            raise
        finally:
            conn.close()

    # ── Setup / Migrations ────────────────────────────────────────────────
    def setup(self):
        """Cria todas as tabelas se não existirem."""
        with self._connect() as conn:
            conn.executescript(DB_SCHEMA)
        log.info("✔ Schema do banco de dados verificado/criado.")

    # ── Inserções ─────────────────────────────────────────────────────────
    def insert_articles(self, articles: list[dict]) -> int:
        """Insere ou atualiza artigos de notícias (upsert por source_id)."""
        if not articles:
            return 0
        sql = """
            INSERT OR REPLACE INTO articles
              (source_id, title, summary, url, image_url, news_site, published_at, collected_at)
            VALUES
              (:source_id, :title, :summary, :url, :image_url, :news_site, :published_at, :collected_at)
        """
        with self._connect() as conn:
            conn.executemany(sql, articles)
        log.debug("Inseridos %d artigos.", len(articles))
        return len(articles)

    def insert_neos(self, neos: list[dict]) -> int:
        """Insere ou atualiza NEOs."""
        if not neos:
            return 0
        sql = """
            INSERT OR REPLACE INTO neos
              (neo_id, name, is_hazardous, diameter_km_min, diameter_km_max,
               velocity_kph, miss_distance_km, approach_date, nasa_url, collected_at)
            VALUES
              (:neo_id, :name, :is_hazardous, :diameter_km_min, :diameter_km_max,
               :velocity_kph, :miss_distance_km, :approach_date, :nasa_url, :collected_at)
        """
        with self._connect() as conn:
            conn.executemany(sql, neos)
        log.debug("Inseridos %d NEOs.", len(neos))
        return len(neos)

    def insert_iss_position(self, pos: dict) -> None:
        """Insere posição atual da IS"""
        sql = """
            INSERT INTO iss_positions (latitude, longitude, timestamp, collected_at)
            VALUES (:latitude, :longitude, :timestamp, :collected_at)
        """
        with self._connect() as conn:
            conn.execute(sql, pos)

    def insert_analysis(self, analysis: dict) -> None:
        """Persiste resultado da análise de IA no banco"""
        sql = """
            INSERT INTO ai_analyses (summary, hazard_alert, insights, raw_response, created_at)
            VALUES (:summary, :hazard_alert, :insights, :raw_response, :created_at)
        """
        with self._connect() as conn:
            conn.execute(sql, analysis)

    # ── Consultas (usadas pela API REST) ──────────────────────────────────
    def get_articles(self, limit: int = 20) -> list[dict]:
        sql = "SELECT * FROM articles ORDER BY published_at DESC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_neos(self, only_hazardous: bool = False) -> list[dict]:
        sql = "SELECT * FROM neos"
        params: tuple = ()
        if only_hazardous:
            sql += " WHERE is_hazardous = 1"
        sql += " ORDER BY miss_distance_km ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_latest_iss(self) -> dict | None:
        sql = "SELECT * FROM iss_positions ORDER BY id DESC LIMIT 1"
        with self._connect() as conn:
            row = conn.execute(sql).fetchone()
        return dict(row) if row else None

    def get_latest_analysis(self) -> dict | None:
        sql = "SELECT * FROM ai_analyses ORDER BY id DESC LIMIT 1"
        with self._connect() as conn:
            row = conn.execute(sql).fetchone()
        return dict(row) if row else None

    def get_stats(self) -> dict:
        """Retorna estatísticas gerais do banco"""
        with self._connect() as conn:
            return {
                "total_articles": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
                "total_neos":     conn.execute("SELECT COUNT(*) FROM neos").fetchone()[0],
                "hazardous_neos": conn.execute("SELECT COUNT(*) FROM neos WHERE is_hazardous=1").fetchone()[0],
                "iss_snapshots":  conn.execute("SELECT COUNT(*) FROM iss_positions").fetchone()[0],
                "ai_analyses":    conn.execute("SELECT COUNT(*) FROM ai_analyses").fetchone()[0],
                "db_path":        self.db_path,
            }
