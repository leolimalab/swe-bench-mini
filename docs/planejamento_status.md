# Planejamento Status — Swe-Bench-Mini v2

## Fases

| Fase | Status |
|------|--------|
| 🔍 Pesquisa de referências (SWE-bench real) | ✅ Completo |
| 📝 Planejamento v2 (F2P/P2P) | ✅ Completo |
| 🛠️ Implementação v2 | ✅ Completo |
| 🧪 Testes e validação | ✅ Completo |
| 🔧 Melhorias (CLI, relatórios) | ✅ Completo |

## Tasks (44 total)

| Categoria | Arquivo | Quantidade |
|-----------|---------|------------|
| generation | `tasks/generation.json` | 5 |
| bug_fixing | `tasks/bug_fixing.json` | 15 |
| refactoring | `tasks/refactoring.json` | 5 |
| sql | `tasks/sql.json` | 14 |
| data_processing | `tasks/data_processing.json` | 5 |

## Decisões Tomadas

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Formato de avaliação | F2P (fail_to_pass) + P2P (pass_to_pass) | Baseado no SWE-bench real |
| Score | F2P_ratio × 60 + P2P_ratio × 40 | Peso maior na resolução do bug |
| Status de resolução | FULL / PARTIAL / NO / REGRESSION | Idêntico ao SWE-bench |
| Categorias de falha | syntax, runtime, unresolved, regression, timeout, no_code | Classificação granular |
| Formato tasks | JSON com arrays de asserts | Fácil editar, sem dep de framework |
| **Modo saída do modelo** | Código completo (não patch diff) | Mais simples, compatível com todos os modelos |
| **Hints** | Apenas em tasks difíceis | Inspirado no SWE-bench |
| **Runs por task** | 1 run (múltiplas runs futuramente) | Simplicidade na v2 |
| **evaluation_mode** | Campo opcional; fallback F2P==P2P | Controle explícito por task |
| **System prompt** | Por categoria com override opcional | SQL só em tasks SQL |
| **CLI** | checkpoint, resume, dry-run, consolidate, compare | Local-first (Termux) |

## Decisões Pendentes

Nenhuma crítica. Futuro (v3): `runs_per_task` estatístico, paralelismo multi-modelo.

## Marcos Concluídos

1. ✅ Pesquisa SWE-bench real
2. ✅ Definição do formato F2P/P2P
3. ✅ Tasks JSON (44 tasks, 5 categorias)
4. ✅ evaluator.py v2
5. ✅ bench.py com CLI completa
6. ✅ reporter.py (MD, HTML, CSV, compare)
