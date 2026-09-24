from __future__ import annotations

import argparse
import contextlib
import json
import os
import runpy
import sys
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from radar_store import SNAPSHOT_VERSION, write_snapshot

BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "valuation_engine.py"
DEFAULT_OUTPUT = BASE_DIR / "data" / "latest_snapshot.json.gz"
DEFAULT_LOG = BASE_DIR / "data" / "latest_run.log"
LOCK_PATH = BASE_DIR / "data" / ".update.lock"

TABLE_KEYS = [
    "UNIVERSE_SUMMARY",
    "METHOD_DISAGREEMENT_AUDIT",
    "QUALITY_SCORE_TABLE",
    "LONG_TERM_PORTFOLIO_RADAR",
    "EXECUTIVE_DECISION_PANEL",
    "EXECUTIVE_STRONG_WATCHLIST",
    "OBJECTIVE_SITUATION_TABLE",
    "FINAL_EXPLANATORY_ASSET_TABLE",
    "ASSET_DECISION_TABLE",
]

CONFIG_KEYS = [
    "HIST_YEARS",
    "AUX_NWC_YEAR",
    "CURRENT_ITR_YEAR",
    "PROJECTION_YEARS",
    "EQUITY_RISK_PREMIUM",
    "EQUITY_RISK_PREMIUM_ASOF",
    "BRAZIL_DEFAULT_SPREAD",
    "BRAZIL_DEFAULT_SPREAD_ASOF",
    "DEBT_SPREAD",
    "WACC_MARGINAL_TAX_RATE",
    "TERMINAL_GROWTH",
    "SCENARIOS",
    "METHOD_WEIGHTS",
    "EQUITY_METHOD_WEIGHTS",
]


def _acquire_lock() -> int:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    return os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)


def _release_lock(fd: int | None):
    if fd is not None:
        try:
            os.close(fd)
        except Exception:
            pass
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass


def _safe_table(ns, key):
    value = ns.get(key)
    return value if isinstance(value, pd.DataFrame) else pd.DataFrame()


def _build_snapshot(ns: dict) -> dict:
    assets = ns.get("ASSETS", {})
    results = ns.get("RESULTS", {})
    equity_results = ns.get("EQUITY_RESULTS", {})

    tables = {key: _safe_table(ns, key) for key in TABLE_KEYS}

    processed = set(results.keys()) | set(equity_results.keys())
    expected = list(assets.keys())
    missing = [s for s in expected if s not in processed]

    if missing:
        raise RuntimeError(
            "Motor terminou sem cobertura integral. Ativos ausentes: " + ", ".join(missing)
        )

    if len(processed) != len(expected):
        raise RuntimeError(
            f"Cobertura inesperada: {len(processed)}/{len(expected)} ativos processados."
        )

    asset_meta = {}
    for symbol, cfg in assets.items():
        asset_meta[symbol] = {
            "symbol": symbol,
            "name": cfg.get("name", symbol),
            "ticker": cfg.get("ticker"),
            "valuation_model": cfg.get("valuation_model"),
            "financial_profile": cfg.get("financial_profile"),
            "fcff_profile": cfg.get("fcff_profile"),
            "capex_profile": cfg.get("capex_profile"),
            "model_reason": cfg.get("model_reason"),
        }

    payload = {
        "snapshot_version": SNAPSHOT_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "engine_file": ENGINE_PATH.name,
        "engine_line_count": len(ENGINE_PATH.read_text(encoding="utf-8").splitlines()),
        "assets": asset_meta,
        "asset_order": expected,
        "config": {key: ns.get(key) for key in CONFIG_KEYS if key in ns},
        "rate_context": ns.get("RATE_CONTEXT", {}),
        "tables": tables,
        # Os resultados completos ficam no snapshot para o detalhamento do ativo.
        "results_fcff": results,
        "results_equity": equity_results,
        "execution": {
            "expected_assets": len(expected),
            "processed_fcff": len(results),
            "processed_equity": len(equity_results),
            "processed_total": len(processed),
            "failed_assets": ns.get("FAILED_ASSETS", []),
            "equity_failed_assets": ns.get("EQUITY_FAILED_ASSETS", []),
            "skipped_assets": ns.get("SKIPPED_ASSETS", []),
        },
    }
    return payload


def run_engine(output: Path, log_path: Path) -> dict:
    if not ENGINE_PATH.exists():
        raise FileNotFoundError(f"Motor não encontrado: {ENGINE_PATH}")

    os.environ.setdefault("MPLBACKEND", "Agg")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    started = datetime.now().astimezone()
    with log_path.open("w", encoding="utf-8") as log, \
         contextlib.redirect_stdout(log), \
         contextlib.redirect_stderr(log):
        print(f"[runner] início: {started.isoformat()}")
        print(f"[runner] engine: {ENGINE_PATH}")
        ns = runpy.run_path(str(ENGINE_PATH), run_name="__radar_w1_engine__")
        payload = _build_snapshot(ns)
        payload["run_started_at"] = started.isoformat()
        payload["run_finished_at"] = datetime.now().astimezone().isoformat()
        write_snapshot(output, payload)
        print(f"[runner] snapshot gravado: {output}")
        print(f"[runner] cobertura: {payload['execution']['processed_total']}/{payload['execution']['expected_assets']}")

    return {
        "ok": True,
        "snapshot": str(output),
        "log": str(log_path),
        "processed": payload["execution"]["processed_total"],
        "expected": payload["execution"]["expected_assets"],
        "finished_at": payload["run_finished_at"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o motor Radar W1 e exporta snapshot para o Streamlit.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    args = parser.parse_args()

    lock_fd = None
    try:
        try:
            lock_fd = _acquire_lock()
        except FileExistsError:
            print(json.dumps({"ok": False, "error": "Já existe uma atualização em andamento."}, ensure_ascii=False))
            return 3

        result = run_engine(Path(args.output), Path(args.log))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        # O snapshot anterior não é tocado porque write_snapshot só ocorre após o motor terminar.
        try:
            with Path(args.log).open("a", encoding="utf-8") as log:
                log.write("\n[runner] FALHA\n")
                traceback.print_exc(file=log)
        except Exception:
            pass
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1
    finally:
        _release_lock(lock_fd)


if __name__ == "__main__":
    raise SystemExit(main())
