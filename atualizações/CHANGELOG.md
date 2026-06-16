# Changelog — swe-bench-mini

Registro consolidado das atualizações realizadas no projeto.  
**Repositório:** https://github.com/leolimalab/swe-bench-mini  
**Última atualização:** 2026-06-15

---

## Visão geral

O **swe-bench-mini** evoluiu de um benchmark v1 (algoritmos clássicos, score único) para uma **v2 completa** inspirada no [SWE-bench](https://www.swebench.com/), com metodologia **F2P/P2P** (fail-to-pass / pass-to-pass), **44 tasks** em 5 categorias, CLI unificada e suporte a modelos locais via **llama.cpp** (incluindo modelos com **thinking**).

---

## Histórico de commits

| Commit | Descrição |
|--------|-----------|
| `ab39d40` | Planejamento v2 — F2P/P2P inspirado no SWE-bench real |
| `4d7fd7f` | Remove cache, results e config do versionamento |
| `c0aa848` | Adiciona `config.template.yaml` (secrets fora do git) |
| `d04f4cc` | Implementação v2 — F2P/P2P, 25 tasks iniciais |
| `d2994db` | Consolida v2 — CLI unificada, thinking, tasks SQL/data |

---

## Fase 1 — Essencial: segurança, docs e prompts

### Segurança
- Removida API key hardcoded de `run_kimi.py` (script posteriormente excluído)
- Credenciais lidas de `config.yaml` (gitignored) ou variável `MODEL_API_KEY`
- `config.yaml` nunca versionado; apenas `config.template.yaml` no repositório

### System prompt por categoria (`core/runner.py`)
| Categoria | Prompt |
|-----------|--------|
| `generation`, `bug_fixing`, `refactoring` | Engenheiro Python genérico |
| `sql` | Especialista SQL/BigQuery |
| `data_processing` | Engenheiro Python + processamento de dados |

- Método `_system_prompt(task)` com override opcional via campo `system_prompt` na task JSON

### Documentação
- **`README.md`** criado na raiz (setup, comandos, estrutura)
- **`docs/AGENTS.md`** — status atualizado para v2 concluída (44 tasks, 5 categorias)
- **`docs/planejamento_status.md`** — fases e marcos marcados como concluídos
- **`config.template.yaml`** — inclui `sql` e `data_processing` em `benchmark.tasks`

### Limpeza
- Removido `requests` de `requirements.txt` (código usa apenas `urllib` da stdlib)
- Removido `TEMPLATES_DIR` não utilizado em `core/reporter.py`
- Dependência final: apenas `pyyaml>=6.0`

---

## Fase 2 — Confiabilidade: testes e validação

### Testes unitários (`tests/test_evaluator.py`)
11 casos cobrindo:
- Resposta sem code block → `no_code`
- Syntax error → `syntax`
- Generation FULL / parcial
- Bug fixing REGRESSION / PARTIAL
- Extração de múltiplos blocos ` ```python `
- Timeout
- `evaluation_mode` explícito (SQL sem falso REGRESSION)
- Tags `` — usa último bloco de código

```bash
python3 -m unittest discover tests -v
```

### Validador de tasks (`validate_tasks.py`)
- IDs únicos globalmente entre `tasks/*.json`
- Campos obrigatórios por schema F2P/P2P
- `code_context` obrigatório em `bug_fixing`/`refactoring`
- Asserts parseáveis via `ast.parse`
- Avisos para F2P==P2P fora de `generation`

```bash
python3 validate_tasks.py   # 44 tasks validadas
```

### Campo `evaluation_mode`
- Opcional nas tasks: `"generation"` | `"bug_fixing"`
- Fallback automático: F2P==P2P → generation
- Aplicado em **`tasks/sql.json`** (14 tasks) e **`tasks/data_processing.json`** (5 tasks)
- P2P usado como edge cases sem rótulo REGRESSION enganoso

### Correções no evaluator (`core/evaluator.py`)
- Modo de avaliação explícito via `evaluation_mode`
- Temp files em `.eval_tmp/` (projeto) em vez de `~/` — funciona em sandbox/Termux
- Fix: `'t0' in dir()` → `'t0' in locals()`
- Extração de código com suporte a tags `` (último bloco quando há thinking)

---

## Fase 3 — CLI unificada (local-first)

### Novas flags em `bench.py`

| Flag | Função |
|------|--------|
| `--checkpoint FILE` | Salva JSON após cada task |
| `--resume FILE` | Retoma run interrompido (pula `model` + `task_id` já feitos) |
| `--task-id ID` | Executa uma task específica (ex: `fix-101`) |
| `--dry-run FILE` | Reavalia respostas salvas sem chamar LLM |
| `--consolidate FILE...` | Merge de runs parciais + relatório |
| `--compare BASE CURRENT` | Compara dois runs (delta de score/resolução) |
| `-v` / `--verbose` | Erros de API, código gerado, thinking |

### Erros visíveis
- `core/runner.py` retorna `{"error": "..."}` em falhas de API
- `bench.py` exibe detalhe com `--verbose`

### Scripts removidos (substituídos pela CLI)
- `run_kimi.py`
- `run_bugfix.py`
- `consolidate.py`

---

## Fase 4 — Relatórios e comparação

### Exportações (`core/reporter.py`)
- **JSON** — resultados brutos (`bench_<timestamp>.json`)
- **Markdown** — relatório detalhado por modelo/task
- **HTML** — dashboard com summary, detalhes, breakdown
- **CSV** — `report_<timestamp>.csv` para planilhas

### Melhorias no HTML
- Seção **By Difficulty** (easy / medium / hard) com gráfico SVG
- Seção **Failure Categories** (syntax, runtime, regression, etc.)
- Coluna de dificuldade na tabela de detalhes

### Comparador de runs
- `Reporter.compare(baseline, current)` → `compare_<timestamp>.md`
- Tabela delta por task/modelo
- Resumo: improved / regressed / unchanged / médias / FULL count

---

## Suporte a modelos thinking

Novo módulo **`core/thinking.py`**:

- `merge_model_response()` — combina `content` e `reasoning_content` da API OpenAI-compat
- `strip_think_tags()` — remove blocos `` embutidos no content
- Prioridade: `content` com code block → `reasoning_content` com code block → fallback
- Sufixo extra no system prompt para modelos com `thinking: true` no config

### Configuração exemplo (Qwen 3.6 35B local)

```yaml
- name: "Qwen 3.6 (35B Local)"
  endpoint: "http://192.168.7.13:8000/v1"
  thinking: true
  max_tokens: 8192
  timeout: 600
```

- `max_tokens` e `timeout` podem ser sobrescritos por modelo
- Resultados incluem `reasoning_content` quando diferente do texto avaliado
- `--verbose` exibe trecho do raciocínio

---

## Novas tasks (19 adicionadas → 44 total)

| Categoria | Arquivo | Tasks | Descrição |
|-----------|---------|-------|-----------|
| Geração | `tasks/generation.json` | 5 | Algoritmos clássicos (F2P=P2P) |
| Correção | `tasks/bug_fixing.json` | 15 | Bugs inspirados no SWE-bench real |
| Refatoração | `tasks/refactoring.json` | 5 | Melhorias de código |
| **SQL** | `tasks/sql.json` | **14** | BigQuery-style com sqlite3 (window functions, GROUP BY, etc.) |
| **Data Processing** | `tasks/data_processing.json` | **5** | JSON flatten, log parser, ETL |

---

## Arquivos criados

| Arquivo | Descrição |
|---------|-----------|
| `README.md` | Documentação principal |
| `core/thinking.py` | Helpers para modelos thinking |
| `validate_tasks.py` | Validador de schema das tasks |
| `tests/test_evaluator.py` | Testes unitários do evaluator |
| `tasks/sql.json` | 14 tasks SQL |
| `tasks/data_processing.json` | 5 tasks de processamento de dados |
| `atualizacoes/CHANGELOG.md` | Este arquivo |

## Arquivos removidos

| Arquivo | Motivo |
|---------|--------|
| `consolidate.py` | Substituído por `bench.py --consolidate` |
| `run_bugfix.py` | Substituído por `bench.py --task bug_fixing` |
| `run_kimi.py` | Substituído por `bench.py --model` + `--checkpoint` |

## Arquivos modificados (principais)

| Arquivo | Mudanças |
|---------|----------|
| `bench.py` | CLI completa, checkpoint, resume, dry-run, compare |
| `core/runner.py` | Prompts por categoria, thinking, erros, overrides por modelo |
| `core/evaluator.py` | `evaluation_mode`, `.eval_tmp/`, thinking tags |
| `core/reporter.py` | CSV, compare, HTML com breakdown |
| `.gitignore` | `.eval_tmp/` |
| `docs/AGENTS.md` | Status v2 concluída |
| `docs/planejamento_status.md` | Marcos atualizados |

---

## Publicação no GitHub

- Repositório criado: **https://github.com/leolimalab/swe-bench-mini**
- Branch: `master`
- Visibilidade: pública
- Commit publicado: `d2994db`

---

## Comandos de referência rápida

```bash
# Setup
cp config.template.yaml config.yaml
pip install -r requirements.txt
python validate_tasks.py

# Benchmark
python bench.py --list-models
python bench.py --list-tasks
python bench.py --model "Qwen 3.6" --task sql
python bench.py --model "35B" --task sql --checkpoint results/run.json -v
python bench.py --resume results/run.json

# Análise
python bench.py --dry-run results/bench.json
python bench.py --compare results/run_a.json results/run_b.json
python bench.py --consolidate results/partial1.json results/partial2.json

# Testes
python3 -m unittest discover tests -v
```

---

## Fora de escopo (deliberado na v2)

- Patch diff como formato de saída (mantido: código completo)
- Docker sandbox por instância (mantido: subprocess + tempfile)
- Repos reais Django/Astropy (tasks sintéticas inspiradas em `REAL_SWE_ANALYSIS.md`)
- Múltiplas runs estatísticas (`runs_per_task` → v3)
- Paralelismo multi-modelo (risco de OOM em llama.cpp local)

---

## Próximos passos sugeridos (v3)

- `runs_per_task` com média e desvio padrão
- Benchmark SQL no Qwen 3.6 35B com thinking (LAN `192.168.7.13:8000`)
- Rotacionar API keys expostas historicamente no git
- CI com `validate_tasks.py` + `unittest` no GitHub Actions
