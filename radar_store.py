from __future__ import annotations

import gzip
import json
import math
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SNAPSHOT_VERSION = 1


def _finite_float(value: Any):
    try:
        x = float(value)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def to_jsonable(value: Any) -> Any:
    """Converte os objetos produzidos pelo motor em JSON sem alterar seus valores econômicos."""
    if value is None:
        return None

    if value is pd.NA:
        return None

    if isinstance(value, (np.bool_, bool)):
        return bool(value)

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        return _finite_float(value)

    if isinstance(value, int):
        return int(value)

    if isinstance(value, str):
        return value

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, pd.DataFrame):
        frame = value.copy()
        index_name = frame.index.name or "index"
        # Preserva o índice porque várias tabelas usam Ativo/Ano como chave econômica.
        frame = frame.reset_index()
        return {
            "__type__": "dataframe",
            "index_name": index_name,
            "columns": [str(c) for c in frame.columns],
            "records": [
                {str(k): to_jsonable(v) for k, v in row.items()}
                for row in frame.to_dict(orient="records")
            ],
        }

    if isinstance(value, pd.Series):
        return {
            "__type__": "series",
            "name": None if value.name is None else str(value.name),
            "index_name": value.index.name or "index",
            "records": [
                {"index": to_jsonable(idx), "value": to_jsonable(val)}
                for idx, val in value.items()
            ],
        }

    if isinstance(value, np.ndarray):
        return [to_jsonable(x) for x in value.tolist()]

    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]

    # Fallback apenas para metadados diagnósticos incomuns; nunca é usado para recalcular valuation.
    return str(value)


def from_jsonable(value: Any) -> Any:
    if isinstance(value, list):
        return [from_jsonable(v) for v in value]

    if not isinstance(value, dict):
        return value

    marker = value.get("__type__")
    if marker == "dataframe":
        df = pd.DataFrame(value.get("records", []))
        index_name = value.get("index_name") or "index"
        if index_name in df.columns:
            df = df.set_index(index_name)
        return df

    if marker == "series":
        records = value.get("records", [])
        s = pd.Series(
            [from_jsonable(r.get("value")) for r in records],
            index=[from_jsonable(r.get("index")) for r in records],
            name=value.get("name"),
        )
        s.index.name = value.get("index_name") or None
        return s

    return {k: from_jsonable(v) for k, v in value.items()}


def write_snapshot(path: str | Path, payload: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    encoded = to_jsonable(payload)

    if path.suffix == ".gz":
        with gzip.open(temp, "wt", encoding="utf-8") as fh:
            json.dump(encoded, fh, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    else:
        with temp.open("w", encoding="utf-8") as fh:
            json.dump(encoded, fh, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

    os.replace(temp, path)
    return path


def read_snapshot(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
    else:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    decoded = from_jsonable(raw)
    if not isinstance(decoded, dict):
        raise ValueError("Snapshot inválido: raiz não é um dicionário.")
    return decoded


def frame(snapshot: dict[str, Any], key: str) -> pd.DataFrame:
    value = snapshot.get("tables", {}).get(key)
    return value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame()
