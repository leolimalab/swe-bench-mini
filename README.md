# swe-bench-mini

Benchmark leve inspirado no [SWE-bench](https://www.swebench.com/) para avaliar LLMs locais (llama.cpp) e APIs compatíveis com OpenAI em tarefas de código Python.

Usa metodologia **F2P/P2P** (fail-to-pass / pass-to-pass) com status de resolução **FULL / PARTIAL / NO / REGRESSION**.

## Setup

```bash
pip install -r requirements.txt
cp config.template.yaml config.yaml
# Edite config.yaml com seus endpoints e API keys
```

Validar tasks antes de rodar:

```bash
python validate_tasks.py
```

## Uso

```bash
python bench.py --list-models          # Listar modelos configurados
python bench.py --list-tasks           # Listar 44 tasks em 5 categorias
python bench.py --model "Qwen 3.5"     # Rodar um modelo específico
python bench.py --task bug_fixing      # Rodar uma categoria
python bench.py --task-id fix-101      # Rodar uma task específica
python bench.py --checkpoint results/run.json   # Salvar após cada task
python bench.py --resume results/run.json       # Retomar run interrompido
python bench.py --dry-run results/bench.json    # Reavaliar sem chamar LLM
python bench.py --consolidate a.json b.json     # Merge de runs parciais
python bench.py --compare a.json b.json         # Comparar dois runs
python bench.py -v                     # Saída detalhada (erros de API, código)
```

## Categorias de tasks (44 total)

| Categoria | Arquivo | Tasks |
|-----------|---------|-------|
| Geração | `tasks/generation.json` | 5 |
| Correção de bugs | `tasks/bug_fixing.json` | 15 |
| Refatoração | `tasks/refactoring.json` | 5 |
| SQL (BigQuery) | `tasks/sql.json` | 14 |
| Data Processing | `tasks/data_processing.json` | 5 |

## Estrutura do projeto

```
bench.py              # CLI principal
core/
  runner.py           # Chamada à API OpenAI-compat
  evaluator.py        # Avaliação F2P/P2P (subprocess + asserts)
  reporter.py         # Relatórios JSON / MD / HTML / CSV
tasks/*.json          # Definição das tasks
results/              # Saída gerada (gitignored)
docs/AGENTS.md        # Contexto para agentes IA
```

## Avaliação

- **F2P**: testes que devem passar após a correção/implementação
- **P2P**: testes que não podem quebrar (regressão)
- **Score**: `F2P_ratio × 60 + P2P_ratio × 40`
- **Resolução**: FULL (100%), PARTIAL, NO, REGRESSION

Tasks de geração (`generation`) usam F2P=P2P e não aplicam detecção de regressão. Tasks `sql` e `data_processing` usam `evaluation_mode: "generation"` com P2P como edge cases adicionais.

## Segurança

- Nunca commite `config.yaml` (contém API keys) — use `config.template.yaml`
- Use a variável de ambiente `MODEL_API_KEY` como alternativa à chave no config

## Documentação

- [docs/AGENTS.md](docs/AGENTS.md) — decisões de design e contexto
- [docs/planejamento.md](docs/planejamento.md) — especificação F2P/P2P v2
- [REAL_SWE_ANALYSIS.md](REAL_SWE_ANALYSIS.md) — análise do SWE-bench real
