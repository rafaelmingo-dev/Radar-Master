from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from radar_store import read_snapshot
from radar_ui import main_table
from valuation_adapter import build_clear_decision_table
from garch_adapter import CACHE_FILE as GARCH_CACHE_FILE, carregar_cache
import confluence_core as confluence
import connors_core

ROOT_DIR = Path(__file__).resolve().parent
VALUATION_SNAPSHOT = ROOT_DIR / "data" / "latest_snapshot.json.gz"
VALUATION_LOG = ROOT_DIR / "data" / "latest_run.log"
VALUATION_RUNNER = ROOT_DIR / "radar_runner.py"
GARCH_WORKER = ROOT_DIR / "panel_worker.py"

def normalizar_ticker(valor) -> str:
    return str(valor or "").strip().upper().replace(".SA", "")

def carregar_valuation_master():
    if not VALUATION_SNAPSHOT.exists():
        return pd.DataFrame(), None, "SNAPSHOT_AUSENTE"
    try:
        snapshot = read_snapshot(VALUATION_SNAPSHOT)
        radar = main_table(snapshot)
        tabela = build_clear_decision_table(snapshot, radar)
        if not tabela.empty:
            tabela = tabela.copy()
            tabela["Ativo"] = tabela["Ativo"].map(normalizar_ticker)
        return tabela, snapshot, None
    except Exception as exc:
        return pd.DataFrame(), None, f"{type(exc).__name__}: {exc}"

def _garch_dentro_da_zona(resultados: dict) -> pd.DataFrame:
    rows=[]
    mapa=[("30D", "Mensal × 30D"),("90D", "Semestral × 90D"),("180D", "Semestral × 180D")]
    for ativo, res in resultados.items():
        row={"Ativo": normalizar_ticker(ativo)}
        for curto, nome in mapa:
            bloco=(res.get("blocos") or {}).get(nome, {})
            principal=bloco.get("principal") if isinstance(bloco, dict) else None
            row[f"{curto} · Dentro da zona"] = (
                bool(principal.get("Preço atual dentro da zona")) if isinstance(principal, dict)
                and principal.get("Preço atual dentro da zona") is not None else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)

def carregar_garch_master():
    payload, erro = carregar_cache()
    if payload is None:
        return pd.DataFrame(), None, erro
    try:
        resultados = payload["resultados"]
        df = confluence.dataframe_radar(resultados).copy()
        if df.empty:
            return df, payload, "CACHE_SEM_TABELA"
        df["Ativo"] = df["Ativo"].map(normalizar_ticker)
        dentro = _garch_dentro_da_zona(resultados)
        if not dentro.empty:
            df = df.merge(dentro, on="Ativo", how="left")
        return df, payload, None
    except Exception as exc:
        return pd.DataFrame(), payload, f"{type(exc).__name__}: {exc}"

def carregar_connors_master():
    try:
        resultado, auditoria_tf, erros_df, historicos, calculado_em = connors_core.carregar_painel()
        if not resultado.empty:
            resultado = resultado.copy()
            resultado["Ativo"] = resultado["Ativo"].map(normalizar_ticker)
        return resultado, {
            "auditoria_tf": auditoria_tf,
            "erros_df": erros_df,
            "historicos": historicos,
            "calculado_em": calculado_em,
        }, None
    except Exception as exc:
        return pd.DataFrame(), None, f"{type(exc).__name__}: {exc}"

def construir_radar_mestre(valuation: pd.DataFrame, garch: pd.DataFrame, connors: pd.DataFrame) -> pd.DataFrame:
    # O Radar Mestre NÃO cria score nem recalcula nenhum motor. Só seleciona/renomeia
    # saídas existentes e faz outer merge por ticker.
    frames=[]
    if valuation is not None and not valuation.empty:
        cols=[
            "Ativo", "Qualidade para carteira", "Preço atual", "Alvo validado 12m",
            "Upside/Downside", "Alvo validado 24m", "Potencial preço 24m",
            "CAGR preço 24m", "Valuation final", "Confiança", "Auditoria dos métodos",
            "Conclusão para carteira",
        ]
        v=valuation[[c for c in cols if c in valuation.columns]].copy()
        if "Preço atual" in v.columns:
            v=v.rename(columns={"Preço atual":"Preço Valuation"})
        frames.append(v)
    if garch is not None and not garch.empty:
        cols=[
            "Ativo", "Preço atual",
            "30D · Principal", "30D · Confluência %", "30D · Dist Preço→Zona %", "30D · Dentro da zona",
            "90D · Principal", "90D · Confluência %", "90D · Dist Preço→Zona %", "90D · Dentro da zona",
            "180D · Principal", "180D · Confluência %", "180D · Dist Preço→Zona %", "180D · Dentro da zona",
            "Anual · Banda", "Anual · Dist %", "Anual · Status",
        ]
        g=garch[[c for c in cols if c in garch.columns]].copy()
        if "Preço atual" in g.columns:
            g=g.rename(columns={"Preço atual":"Preço GARCH/GEX"})
        frames.append(g)
    if connors is not None and not connors.empty:
        cols=[
            "Ativo", "Preço atual", "CRSI confirmado", "CRSI 30D", "CRSI 90D", "CRSI 180D",
            "Percentil CRSI 1A", "Evento confirmado", "Zona confirmada",
            "Distância confirmada 20/80", "Pregões extremo confirmado", "Auditoria CRSI",
        ]
        c=connors[[c for c in cols if c in connors.columns]].copy()
        if "Preço atual" in c.columns:
            c=c.rename(columns={"Preço atual":"Preço Connors"})
        frames.append(c)
    if not frames:
        return pd.DataFrame()
    out=frames[0]
    for df in frames[1:]:
        out=out.merge(df,on="Ativo",how="outer")
    return out.sort_values("Ativo").reset_index(drop=True)

def executar_valuation() -> tuple[bool,str]:
    cmd=[sys.executable,str(VALUATION_RUNNER),"--output",str(VALUATION_SNAPSHOT),"--log",str(VALUATION_LOG)]
    try:
        proc=subprocess.run(cmd,cwd=str(ROOT_DIR),text=True,capture_output=True,timeout=1800)
    except subprocess.TimeoutExpired:
        return False,"A atualização do Valuation ultrapassou 30 minutos; o snapshot anterior foi preservado."
    if proc.returncode==0:
        return True,"Valuation atualizado."
    return False,(proc.stderr or proc.stdout or "Falha desconhecida no Valuation")[-1800:]

def executar_garch(force_gex: bool | None = None) -> tuple[bool,str]:
    if force_gex is None:
        force_gex = GARCH_CACHE_FILE.exists()
    GARCH_CACHE_FILE.parent.mkdir(parents=True,exist_ok=True)
    cmd=[sys.executable,str(GARCH_WORKER),"--output",str(GARCH_CACHE_FILE)]
    if force_gex:
        cmd.append("--force-gex")
    env=os.environ.copy()
    env.update({
        "PYTHONUNBUFFERED":"1","MPLBACKEND":"Agg","OMP_NUM_THREADS":"1",
        "OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1",
        "MALLOC_ARENA_MAX":"2",
    })
    try:
        proc=subprocess.run(cmd,cwd=str(ROOT_DIR),text=True,capture_output=True,timeout=1800,env=env)
    except subprocess.TimeoutExpired:
        return False,"A atualização GARCH × GEX ultrapassou 30 minutos; o cache anterior foi preservado."
    if proc.returncode==0:
        return True,"GARCH × GEX atualizado."
    return False,(proc.stderr or proc.stdout or "Falha desconhecida no GARCH × GEX")[-1800:]

def limpar_cache_connors():
    try:
        connors_core.carregar_painel.clear()
    except Exception:
        pass
