# Planejamento Status — Swe-Bench-Mini v2

## Fases

| Fase | Status |
|------|--------|
| 🔍 Pesquisa de referências (SWE-bench real) | ✅ Completo |
| 📝 Planejamento v2 (F2P/P2P) | ✅ Completo |
| 🛠️ Implementação | ⏸️ Aguardando aprovação |
| 🧪 Testes | ⏸️ Aguardando aprovação |

## Decisões Tomadas

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Formato de avaliação | F2P (fail_to_pass) + P2P (pass_to_pass) | Baseado no SWE-bench real |
| Score | F2P_ratio × 60 + P2P_ratio × 40 | Peso maior na resolução do bug |
| Status de resolução | FULL / PARTIAL / NO / REGRESSION | Idêntico ao SWE-bench |
| Categorias de falha | syntax, runtime, unresolved, regression, timeout, no_code | Classificação granular |
| Formato tasks | JSON com arrays de asserts | Fácil editar, sem dep de framework |
| Tasks de bug_fixing | 15 tasks em arquivo único `bug_fixing.json` | Simplicidade, agrupa por categoria principal |
| Tasks de refactoring | 5 tasks | Mesma quantidade, formato atualizado |
| Tasks de generation | 5 tasks, F2P/P2P unificado (arrays idênticos) | Consistência com o resto do benchmark |
| **Modo saída do modelo** | Código completo (não patch diff) | Mais simples, compatível com todos os modelos |
| **Hints** | Apenas em tasks difíceis (fix-107, fix-204, refac-103) | Inspirado no SWE-bench, sem poluir tasks fáceis |
| **Runs por task** | 1 run (múltiplas runs futuramente) | Simplicidade na v2 |
| **Compatibilidade retroativa** | Migrar tudo (sem suporte a test_code antigo) | Mais limpo, 25 tasks só |
| **Arquivos de tasks** | `bug_fixing.json` único (não separar por subtipo) | Simplicidade |
| **Contagem de asserts** | Wrapping try/except individual (não stderr parsing) | 100% preciso, suporta asserts duplicados |
| **Modo geração** | F2P=P2P detectado → sem conceito de regressão | Evita REGRESSION falsa em gen-101 a gen-105 |
| **Prompt do modelo** | Inclui fail_to_pass + pass_to_pass + hints (se houver) | Modelo sabe exatamente o que implementar |
| **Ordem de falhas** | no_code > syntax > timeout > runtime > regression > unresolved | Categoria não ambígua |
| **code_context** | Obrigatório para bug_fixing/refactoring; null para generation | Schema consistente |
| **Score vs Resolução** | Métricas complementares (ambas no relatório) | Visão completa |

## Decisões Pendentes

Nenhuma. Todas as 7 decisões foram resolvidas.

## Próximos Marcos

1. ✅ Pesquisa SWE-bench real
2. ✅ Definição do formato F2P/P2P
3. ⏸️ **Aprovação do usuário**
4. ⏸️ Criar tasks JSON (25 tasks)
5. ⏸️ Reformular evaluator.py
6. ⏸️ Adaptar bench.py
7. ⏸️ Adaptar reporter.py
8. ⏸️ Rodar benchmark completo
