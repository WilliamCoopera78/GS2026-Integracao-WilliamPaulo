"""
monitor.py – Monitoramento de Sistema com psutil

Responsabilidades:
  • Capturar métricas de CPU, RAM e disco
  • Detectar picos de uso durante o pipeline
  • Registrar o processo do robô para análise de performance
  • Exportar snapshots para os relatórios finais
"""

import os
import time
import logging
from datetime import datetime, timezone

import psutil

log = logging.getLogger("ARIA.Monitor")


class SystemMonitor:
    """Monitor de recursos do sistema usando psuti"""

    def __init__(self):
        self.process  = psutil.Process(os.getpid())
        self._history: list[dict] = []
        log.debug("SystemMonitor inicializado para PID %d", os.getpid())

    # ── Snapshot instantâneo ──────────────────────────────────────────────
    def snapshot(self) -> dict:
        """
        Captura métricas de sistema em um instante.
        Retorna dict com CPU, RAM, disco e processo atual.
        """
        try:
            # Métricas globais
            cpu_pct  = psutil.cpu_percent(interval=0.5)
            ram      = psutil.virtual_memory()
            disk     = psutil.disk_usage("/")
            net      = psutil.net_io_counters()

            # Métricas do processo ARIA
            proc_mem = self.process.memory_info()
            proc_cpu = self.process.cpu_percent(interval=0.1)

            snap = {
                "timestamp":        datetime.now(timezone.utc).isoformat(),

                # Sistema
                "cpu_percent":      cpu_pct,
                "cpu_count":        psutil.cpu_count(logical=True),
                "ram_total_gb":     round(ram.total / 1_073_741_824, 2),
                "ram_used_gb":      round(ram.used  / 1_073_741_824, 2),
                "ram_percent":      ram.percent,
                "disk_total_gb":    round(disk.total / 1_073_741_824, 2),
                "disk_used_gb":     round(disk.used  / 1_073_741_824, 2),
                "disk_percent":     disk.percent,
                "net_bytes_sent_mb":round(net.bytes_sent / 1_048_576, 2),
                "net_bytes_recv_mb":round(net.bytes_recv / 1_048_576, 2),

                # Processo ARIA
                "proc_pid":         os.getpid(),
                "proc_cpu_percent": proc_cpu,
                "proc_ram_mb":      round(proc_mem.rss / 1_048_576, 2),
                "proc_threads":     self.process.num_threads(),
            }

            self._history.append(snap)
            return snap

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            log.warning("Erro ao coletar métricas: %s", e)
            return {"error": str(e)}

    # ── Monitoramento contínuo em background ──────────────────────────────
    def watch(self, interval_sec: float = 5.0, max_samples: int = 60) -> None:
        """
        Coleta snapshots em loop até atingir max_samples.
        Pode ser executado em thread separada.
        """
        log.info("Monitoramento contínuo iniciado (intervalo=%.1fs).", interval_sec)
        for _ in range(max_samples):
            self.snapshot()
            time.sleep(interval_sec)
        log.info("Monitoramento finalizado. %d amostras coletadas.", len(self._history))

    # ── Relatório de performance ──────────────────────────────────────────
    def performance_report(self) -> dict:
        """Calcula estatísticas agregadas do histórico de monitoramento."""
        if not self._history:
            return {"error": "Nenhuma amostra coletada."}

        cpu_vals  = [s["cpu_percent"]  for s in self._history if "cpu_percent"  in s]
        ram_vals  = [s["ram_percent"]  for s in self._history if "ram_percent"  in s]
        proc_vals = [s["proc_ram_mb"]  for s in self._history if "proc_ram_mb"  in s]

        def _stats(values: list[float]) -> dict:
            if not values:
                return {}
            return {
                "min":  round(min(values), 2),
                "max":  round(max(values), 2),
                "avg":  round(sum(values) / len(values), 2),
            }

        return {
            "samples_collected": len(self._history),
            "duration_seconds":  len(self._history),   # ~1 snapshot/coleta de pipeline
            "cpu_percent":       _stats(cpu_vals),
            "ram_percent":       _stats(ram_vals),
            "proc_ram_mb":       _stats(proc_vals),
            "latest":            self._history[-1] if self._history else {},
        }

    # ── Informações de boot e uptime ──────────────────────────────────────
    @staticmethod
    def system_info() -> dict:
        """Retorna informações estáticas do sistema operacional."""
        boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
        uptime_sec = (datetime.now(timezone.utc) - boot_time).total_seconds()

        return {
            "boot_time":    boot_time.isoformat(),
            "uptime_hours": round(uptime_sec / 3600, 2),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_count_logical":  psutil.cpu_count(logical=True),
            "python_pid":         os.getpid(),
        }
