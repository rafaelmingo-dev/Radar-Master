# Auditoria de integração — Radar Mestre

Esta integração foi construída a partir dos três repositórios fornecidos pelo usuário em 24/09/2026.

## 1. Arquivos preservados sem alteração de conteúdo

### Valuation
- `valuation_engine.py`
- `radar_runner.py`
- `radar_store.py`
- `radar_ui.py`

### GARCH × GEX
- `garch_core.py`
- `gex_core.py`
- `confluence_core.py`
- `panel_worker.py`
- `AUDITORIA_PAINEL_V3.json`

## 2. Connors RSI

`connors_core.py` contém as mesmas constantes e as mesmas 34 funções do `app.py` do repositório Connors fornecido, extraídas sem alterar os corpos das funções. A interface completa permanece em `pages/03_Connors_RSI.py`, que é uma cópia do `app.py` original.

Parâmetros preservados:
- RSI preço = 3
- RSI streak = 2
- PercentRank = 100
- limites = 20 / 80
- confirmação diária = 18:15 America/Sao_Paulo
- snapshots = 30D / 90D / 180D do mesmo CRSI diário confirmado
- Percentil CRSI 1A = janela de 1 ano

## 3. Páginas originais

- `pages/01_Valuation.py`: conteúdo do `app.py` original do Valuation, com a única adaptação estrutural de `BASE_DIR` para apontar para a raiz do projeto integrado.
- `pages/02_GARCH_GEX.py`: conteúdo do `app.py` original do GARCH × GEX, com a única adaptação estrutural de `MODULE_DIR` para apontar para a raiz do projeto integrado.
- `pages/03_Connors_RSI.py`: cópia integral do `app.py` original do Connors.

Nenhuma dessas adaptações altera fórmulas, parâmetros, critérios ou resultados dos motores.

## 4. Radar Mestre

O Radar Mestre:
- normaliza somente o identificador do ticker para a união (`PETR4.SA` → `PETR4`);
- faz `outer merge`, portanto um ativo não desaparece por faltar em outro motor;
- mantém preços de cada motor em colunas separadas;
- não cria score composto;
- não cria classificação automática de compra/venda;
- não recalcula Valuation, GARCH, GEX ou Connors.

## 5. Dependências

O `requirements.txt` é a união das dependências dos três projetos. Foi incluído `mplfinance==0.12.10b0` porque `gex_core.py` possui importação lazy de `mplfinance` em uma função de gráfico preservada, embora essa dependência não constasse no `requirements.txt` original do GARCH × GEX.
