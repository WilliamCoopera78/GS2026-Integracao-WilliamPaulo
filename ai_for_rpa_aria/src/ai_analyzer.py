""" Análise com o Ollama (Local)
Tecnologia: Ollama – servidor de IA local (http://localhost:11434)
Modelo padrão: llama3.2 (3B) – roda em 16GB RAM no Windows

"""

import json
import logging
import requests
from datetime import datetime, timezone

log = logging.getLogger("ARIA.AIAnalyzer")

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_API_URL  = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
DEFAULT_MODEL   = "llama3.2"
TIMEOUT         = 120  


class AIAnalyzer:
    """
    Motor de inteligência artificial local do ARIA.
    Usa o Ollama para rodar modelos de linguagem diretamente na máquina.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self._check_ollama()

    def _check_ollama(self) -> None:
        """Verifica se o Ollama está rodando e se o modelo está disponível."""
        try:
            resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
            resp.raise_for_status()
            models_available = [m["name"] for m in resp.json().get("models", [])]
            log.info("✔ Ollama online. Modelos disponíveis: %s", models_available)

            # Verifica se o modelo escolhido está baixado
            model_found = any(self.model in m for m in models_available)
            if not model_found:
                log.warning(
                    "⚠️  Modelo '%s' não encontrado. Execute: ollama pull %s",
                    self.model, self.model
                )
            else:
                log.info("✔ Modelo '%s' pronto para uso.", self.model)

        except requests.exceptions.ConnectionError:
            log.error(
                "❌ Ollama não está rodando! "
                "Abra o app Ollama ou execute 'ollama serve' no terminal."
            )
        except Exception as e:
            log.warning("Aviso ao verificar Ollama: %s", e)

    def _call_ollama(self, prompt: str) -> str:
        """
        Envia prompt para o Ollama e retorna o texto de resposta.
        Usa a API REST local – mesma lógica de um serviço remoto.
        """
        body = {
            "model":  self.model,
            "prompt": prompt,
            "stream": False,   # retorna resposta completa de uma vez
            "options": {
                "temperature": 0.3,   # mais determinístico para análise técnica
                "num_predict": 800,   # limite de tokens na resposta
            },
            "system": (
                "Você é ARIA, um sistema de inteligência artificial especializado em "
                "análise de dados de exploração espacial. Responda sempre em português, "
                "de forma técnica e objetiva. Use marcadores (•) para listas."
            ),
        }

        try:
            log.info("Enviando prompt ao Ollama (modelo: %s)…", self.model)
            resp = requests.post(OLLAMA_API_URL, json=body, timeout=TIMEOUT)
            resp.raise_for_status()
            result = resp.json()
            response_text = result.get("response", "").strip()
            log.info("✔ Resposta recebida do Ollama (%d chars).", len(response_text))
            return response_text

        except requests.exceptions.ConnectionError:
            msg = "❌ Ollama offline. Inicie com: ollama serve"
            log.error(msg)
            return msg
        except requests.exceptions.Timeout:
            msg = "⏱️ Timeout: o modelo demorou demais. Tente um modelo menor."
            log.error(msg)
            return msg
        except requests.exceptions.HTTPError as e:
            msg = f"Erro HTTP do Ollama: {e.response.status_code}"
            log.error(msg)
            return msg
        except Exception as e:
            log.error("Erro inesperado: %s", e)
            return f"Erro: {e}"

    # ── Análise principal ─────────────────────────────────────────────────
    def analyze_mission_data(
        self,
        articles: list[dict],
        neos:     list[dict],
        iss:      dict,
    ) -> dict:
        """
        Análise completa dos dados da missão.
        Retorna dicionário com summary, hazard_alert e insights.
        """
        log.info("Iniciando análise de IA com %d artigos e %d NEOs…",
                 len(articles), len(neos))

        # Monta contexto estruturado
        articles_text = "\n".join(
            f"- [{a.get('news_site', '')}] {a.get('title', '')}: "
            f"{a.get('summary', '')[:120]}"
            for a in articles
        ) or "Nenhum artigo disponível."

        hazardous_neos = [n for n in neos if n.get("is_hazardous")]
        neos_text = "\n".join(
            f"- {n.get('name')} | Distância: {n.get('miss_distance_km', 0):,.0f} km | "
            f"Velocidade: {n.get('velocity_kph', 0):,.0f} km/h | "
            f"Perigoso: {'SIM ⚠️' if n.get('is_hazardous') else 'NÃO'}"
            for n in neos[:8]
        ) or "Nenhum NEO disponível."

        prompt = f"""Analise os dados espaciais abaixo e gere um relatório técnico em português.

NOTÍCIAS ESPACIAIS RECENTES:
{articles_text}

NEOs (Objetos Próximos da Terra) – próximas 48h:
{neos_text}

POSIÇÃO ATUAL DA ISS:
Latitude: {iss.get('latitude', 0):.4f}° | Longitude: {iss.get('longitude', 0):.4f}°

Gere um relatório com EXATAMENTE estas 3 seções:

RESUMO EXECUTIVO:
(3 frases sobre o panorama atual da exploração espacial com base nas notícias)

ALERTA DE AMEACAS:
(avalie os NEOs: quantos são perigosos, qual o mais próximo e qual o risco real)

INSIGHTS ESTRATEGICOS:
• (insight 1)
• (insight 2)
• (insight 3)

Seja direto e técnico."""

        raw_response = self._call_ollama(prompt)

        # Extrai seções da resposta
        summary      = self._extract_section(raw_response, "RESUMO EXECUTIVO")
        hazard_alert = self._extract_section(raw_response, "ALERTA DE AMEACAS")
        insights     = self._extract_section(raw_response, "INSIGHTS ESTRATEGICOS")

        # Fallback se a extração falhar
        if not summary:
            summary = raw_response[:400]
        if not hazard_alert:
            hazard_alert = (
                f"{len(hazardous_neos)} NEO(s) potencialmente perigoso(s) detectado(s) "
                f"nas próximas 48h."
            )

        return {
            "summary":      summary,
            "hazard_alert": hazard_alert,
            "insights":     insights,
            "raw_response": raw_response,
            "model_used":   self.model,
            "created_at":   datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _extract_section(text: str, section_name: str) -> str:
        """Extrai o conteúdo de uma seção específica do texto."""
        import re
        # Busca a seção e captura até a próxima seção ou fim do texto
        pattern = (
            rf"{re.escape(section_name)}[:\s]*\n(.*?)"
            rf"(?=(?:RESUMO EXECUTIVO|ALERTA DE AMEAC|INSIGHTS ESTRATEG|$))"
        )
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    # ── Utilitário: listar modelos disponíveis ────────────────────────────
    @staticmethod
    def list_available_models() -> list[str]:
        """Retorna os modelos instalados no Ollama."""
        try:
            resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []
