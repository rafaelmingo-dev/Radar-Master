# Radar Mestre — Valuation + GARCH × GEX + Connors RSI

Projeto integrado para Streamlit. O objetivo é reunir, em um único aplicativo, os três painéis já existentes sem substituir nem misturar suas metodologias.

## Princípio de integração

- **Valuation** mantém `valuation_engine.py`, `radar_runner.py`, `radar_store.py` e `radar_ui.py`.
- **GARCH × GEX** mantém `garch_core.py`, `gex_core.py`, `confluence_core.py` e `panel_worker.py`.
- **Connors RSI** mantém a lógica 3/2/100, CRSI confirmado, snapshots 30D/90D/180D, Percentil CRSI 1A e eventos 20/80. O motor reutilizável está em `connors_core.py`; a página completa original está em `pages/03_Connors_RSI.py`.
- **Radar Mestre** apenas consolida as saídas por ticker usando `outer merge`. Não cria score combinado e não altera as fórmulas dos três motores.

## Estrutura obrigatória no GitHub

```text
radar-mestre/
├── app.py
├── master_core.py
├── valuation_adapter.py
├── garch_adapter.py
├── connors_core.py
├── valuation_engine.py
├── radar_runner.py
├── radar_store.py
├── radar_ui.py
├── garch_core.py
├── gex_core.py
├── confluence_core.py
├── panel_worker.py
├── AUDITORIA_PAINEL_V3.json
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
└── pages/
    ├── 01_Valuation.py
    ├── 02_GARCH_GEX.py
    └── 03_Connors_RSI.py
```

## Deploy no Streamlit Community Cloud

- Main file: `app.py`
- Python: **3.12**
- Branch: `main`

## Primeira execução

O Radar Mestre pode abrir com Valuation e/ou GARCH × GEX ainda sem base calculada. Isso é esperado.

- Use **Atualizar Valuation** para gerar `data/latest_snapshot.json.gz`.
- Use **Atualizar GARCH × GEX** para gerar `.panel_cache/painel_v3.pkl`.
- O Connors é calculado via `yfinance` e usa cache do próprio Streamlit.

Os diretórios `data/` e `.panel_cache/` são criados automaticamente em runtime e não precisam ser enviados ao GitHub.
