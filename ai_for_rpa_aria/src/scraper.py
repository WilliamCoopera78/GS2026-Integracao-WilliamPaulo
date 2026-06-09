"""
scraper.py – Módulo de Web Crawling e Consumo de APIs Externas

APIs utilizadas (todas públicas, sem autenticação obrigatória):
  • Spaceflight News API  – notícias espaciais
  • NASA Open API         – NEOs (Near-Earth Objects) com DEMO_KEY
  • Open Notify API       – posição ao vivo da ISS
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("ARIA.Scraper")

# ─── Configurações ───────────────────────────────────────────────────────────
SPACEFLIGHT_API = "https://api.spaceflightnewsapi.net/v4/articles/"
NASA_NEO_API    = "https://api.nasa.gov/neo/rest/v1/feed"
ISS_POSITION    = "http://api.open-notify.org/iss-now.json"
NASA_DEMO_KEY   = "DEMO_KEY"  
TIMEOUT         = 15          
RETRY_ATTEMPTS  = 3


class SpaceScraper:
    """Robô de coleta de dados espaciais via web crawling e APIs REST."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARIA-RPA-Bot/1.0 ",
            "Accept": "application/json",
        })

    # ── Método auxiliar com retry e error handling ────────────────────────
    def _get(self, url: str, params: dict | None = None) -> dict | list:
        """GET com retry automático e tratamento de exceções."""
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                resp = self.session.get(url, params=params, timeout=TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                log.warning("HTTP %s em %s (tentativa %d/%d)",
                            e.response.status_code, url, attempt, RETRY_ATTEMPTS)
            except requests.exceptions.ConnectionError:
                log.warning("Falha de conexão em %s (tentativa %d/%d)",
                            url, attempt, RETRY_ATTEMPTS)
            except requests.exceptions.Timeout:
                log.warning("Timeout em %s (tentativa %d/%d)",
                            url, attempt, RETRY_ATTEMPTS)
            except Exception as e:
                log.error("Erro inesperado: %s", e)
                break
            time.sleep(2 ** attempt)   # backoff exponencial

        log.error("❌ Falha definitiva ao acessar %s", url)
        return {}

    # ── 1. Spaceflight News – REST API + BeautifulSoup ────────────────────
    def fetch_spaceflight_news(self, limit: int = 10) -> list[dict]:
        """
        Coleta artigos da Spaceflight News API.
        Demonstra: consumo de REST API + parsing com BeautifulSoup.
        """
        log.info("Buscando %d artigos em Spaceflight News API…", limit)
        data = self._get(SPACEFLIGHT_API, params={"limit": limit, "ordering": "-published_at"})

        articles = []
        for item in data.get("results", []):
            # BeautifulSoup para limpar HTML residual em summaries
            soup = BeautifulSoup(item.get("summary", ""), "html.parser")
            clean_summary = soup.get_text(separator=" ", strip=True)

            articles.append({
                "source_id":    item.get("id"),
                "title":        item.get("title", "N/A"),
                "summary":      clean_summary[:500],
                "url":          item.get("url", ""),
                "image_url":    item.get("image_url", ""),
                "news_site":    item.get("news_site", ""),
                "published_at": item.get("published_at", ""),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })

        log.info("✔ %d artigos coletados.", len(articles))
        return articles

    # ── 2. NASA NEO Feed – REST API ───────────────────────────────────────
    def fetch_nasa_neos(self) -> list[dict]:
        """
        Coleta dados de Objetos Próximos da Terra (NEOs) da NASA.
        Demonstra: consumo de REST API com parâmetros e parsing de JSON aninhado.
        """
        from datetime import date, timedelta
        today = date.today().isoformat()
        end   = (date.today() + timedelta(days=2)).isoformat()

        log.info("Buscando NEOs entre %s e %s…", today, end)
        data = self._get(NASA_NEO_API, params={
            "start_date": today,
            "end_date":   end,
            "api_key":    NASA_DEMO_KEY,
        })

        neos = []
        for date_key, objects in data.get("near_earth_objects", {}).items():
            for neo in objects:
                diameter = neo.get("estimated_diameter", {})
                km_min = diameter.get("kilometers", {}).get("estimated_diameter_min", 0)
                km_max = diameter.get("kilometers", {}).get("estimated_diameter_max", 0)

                close_approach = neo.get("close_approach_data", [{}])[0]
                velocity_kph   = close_approach.get("relative_velocity", {}).get("kilometers_per_hour", "0")
                miss_km        = close_approach.get("miss_distance", {}).get("kilometers", "0")

                neos.append({
                    "neo_id":           neo.get("id"),
                    "name":             neo.get("name"),
                    "is_hazardous":     neo.get("is_potentially_hazardous_asteroid", False),
                    "diameter_km_min":  round(km_min, 4),
                    "diameter_km_max":  round(km_max, 4),
                    "velocity_kph":     round(float(velocity_kph), 2),
                    "miss_distance_km": round(float(miss_km), 2),
                    "approach_date":    date_key,
                    "nasa_url":         neo.get("nasa_jpl_url", ""),
                    "collected_at":     datetime.now(timezone.utc).isoformat(),
                })

        neos.sort(key=lambda x: x["miss_distance_km"])
        log.info("✔ %d NEOs coletados.", len(neos))
        return neos

    # ── 3. ISS Position – REST API ────────────────────────────────────────
    def fetch_iss_position(self) -> dict:
        """
        Obtém posição atual da Estação Espacial Internacional (ISS).
        Demonstra: REST API em tempo real.
        """
        log.info("Obtendo posição atual da ISS…")
        data = self._get(ISS_POSITION)

        if not data:
            return {"latitude": 0.0, "longitude": 0.0, "timestamp": 0, "collected_at": ""}

        pos = data.get("iss_position", {})
        return {
            "latitude":     float(pos.get("latitude", 0)),
            "longitude":    float(pos.get("longitude", 0)),
            "timestamp":    data.get("timestamp", 0),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── 4. Web scraping com BeautifulSoup (página HTML) ───────────────────
    def scrape_nasa_news_page(self) -> list[dict]:
        """
        Scraping direto da página de notícias da NASA.
        Demonstra: parsing HTML com BeautifulSoup4.
        """
        url = "https://www.nasa.gov/news/"
        log.info("Scraping HTML de %s…", url)

        try:
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            log.warning("Não foi possível acessar NASA news: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        headlines = []

        # Seleciona títulos de notícias (adaptar seletores conforme layout atual)
        for tag in soup.select("h2.hds-content-item-heading, h3.entry-title")[:10]:
            text = tag.get_text(strip=True)
            if text:
                headlines.append({"headline": text, "source": "NASA.gov",
                                  "collected_at": datetime.now(timezone.utc).isoformat()})

        log.info("✔ %d headlines da NASA coletadas.", len(headlines))
        return headlines
