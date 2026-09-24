from __future__ import annotations

import hashlib
import pickle
from pathlib import Path

CACHE_SCHEMA = 4
ROOT_DIR = Path(__file__).resolve().parent
CACHE_DIR = ROOT_DIR / ".panel_cache"
CACHE_FILE = CACHE_DIR / "painel_v3.pkl"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def current_core_hashes() -> dict[str, str]:
    return {
        nome: sha256_file(ROOT_DIR / nome)
        for nome in ("gex_core.py", "garch_core.py", "confluence_core.py", "panel_worker.py")
    }

def carregar_cache():
    if not CACHE_FILE.exists():
        return None, "CACHE_AUSENTE"
    try:
        with CACHE_FILE.open("rb") as f:
            payload = pickle.load(f)
    except Exception as exc:
        return None, f"CACHE_ILEGÍVEL: {type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, "CACHE_INVÁLIDO"
    if payload.get("cache_schema") != CACHE_SCHEMA:
        return None, "CACHE_INCOMPATÍVEL_COM_ESTA_VERSÃO"
    try:
        hashes_atuais = current_core_hashes()
    except Exception as exc:
        return None, f"ERRO_AO_VALIDAR_CORES: {type(exc).__name__}: {exc}"
    if payload.get("core_hashes") != hashes_atuais:
        return None, "CACHE_DE_OUTRA_VERSÃO_DOS_MOTORES"
    resultados = payload.get("resultados")
    if not isinstance(resultados, dict) or not resultados:
        return None, "CACHE_SEM_RESULTADOS"
    return payload, None
