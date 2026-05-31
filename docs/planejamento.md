# Swe-Bench-Mini — Plano de Evolução (F2P/P2P)

> **Visão:** Transformar o swe-bench-mini de um benchmark de algoritmos isolados em um benchmark que testa a capacidade do modelo de **resolver bugs reais** — inspirado na metodologia do SWE-bench (Princeton NLP).

---

## 1. Estado Atual vs Estado Desejado

| Aspecto | Atual (v1) | Futuro (v2) |
|---------|-----------|-------------|
| **Tarefas** | 15 tarefas de algoritmos clássicos | 20+ tarefas inspiradas em bugs reais |
| **Avaliação** | `test_code` único com asserts | `fail_to_pass` + `pass_to_pass` (F2P/P2P) |
| **Resolução** | Score numérico 0-100 | FULL / PARTIAL / NO |
| **Formato saída** | Código em ```python | Código OU patch diff |
| **Categorias** | generation, bug_fixing, refactoring | + edge_cases, type_handling, state_mutation |
| **Erro classificado** | Só "error" genérico | syntax / runtime / unresolved / regression / timeout |
| **Score** | Sintaxe 20 + Testes 50 + Tempo 15 + Qualidade 15 | F2P 60 + P2P 40 (com status de resolução) |

---

## 2. Novo Formato de Task (JSON)

```json
{
  "id": "fix-101",
  "name": "Trailing Newline Validation",
  "category": "bug_fixing",
  "difficulty": "easy",
  "description": "Regex $ permite trailing newline na validação de username",
  "instruction": "Corrija a função para que entradas com trailing newline sejam rejeitadas.",
  "code_context": "def validate_username(username):\n    import re\n    if not re.match(r'^[\\w.@+-]+$', username):\n        return False\n    return True",
  "fail_to_pass": [
    "assert validate_username('user\\n') == False",
    "assert validate_username('admin\\n') == False"
  ],
  "pass_to_pass": [
    "assert validate_username('user') == True",
    "assert validate_username('admin') == True",
    "assert validate_username('') == False",
    "assert validate_username('a b') == False"
  ],
  "timeout": 5,
  "hints": "O problema está na regex. O $ no Python regex permite corresponder a um \\n opcional antes do fim da string."
}
```

### Campos

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `id` | ✅ | Identificador único (ex: `fix-101`) |
| `name` | ✅ | Nome legível |
| `category` | ✅ | Categoria da tarefa |
| `difficulty` | ✅ | easy / medium / hard |
| `description` | ✅ | Descrição curta do bug |
| `instruction` | ✅ | Instrução para o modelo |
| `code_context` | ✅ (bug_fixing/refactoring) / ❌ (generation) | Código **bugado** que o modelo deve corrigir. `null` para generation (criação do zero) |
| `fail_to_pass` | ✅ | Lista de asserts que DEVEM passar no código corrigido |
| `pass_to_pass` | ✅ | Lista de asserts que NÃO DEVEM quebrar |
| `timeout` | ✅ | Timeout em segundos para execução |
| `hints` | ❌ | Dica opcional (inspirado no `hints_text` do SWE-bench) |

---

## 3. Arquitetura do Evaluator (v2)

### Fluxo de Avaliação

```
Resposta do modelo (código ou patch)
         │
         ▼
    Extrair código
         │
         ▼
    Syntax check (AST)
    ├── OK → continua
    └── FAIL → score=0, falha="syntax", retorna
         │
         ▼
    Detectar modo (task definition — arrays estáticos)
    ├── Se fail_to_pass == pass_to_pass → modo GERAÇÃO
    │   (sem conceito de regressão — P2P ignorado)
    └── Senão → modo BUG_FIXING normal
         │
         ▼
    Executar fail_to_pass (F2P) — wrapping try/except
    ├── count F2P_passed / F2P_total
    └── se algum FALHOU → "unresolved" (modo bug_fixing)
                        → "no" (modo geração)
         │
         ▼
    Executar pass_to_pass (P2P) — wrapping try/except
    ├── count P2P_passed / P2P_total
    ├── se algum FALHOU → "regression" (SÓ em modo bug_fixing)
    └── ignorado em modo geração
         │
         ▼
    Categoria de falha (ordem de precedência)
    no_code > syntax > timeout > runtime > regression > unresolved
         │
         ▼
    Score = (F2P_ratio × 60) + (P2P_ratio × 40)
    Resolução = FULL | PARTIAL | NO | REGRESSION
```

### Cálculo do Score

```
F2P_ratio = F2P_passed / F2P_total
P2P_ratio = P2P_passed / P2P_total

total_score = (F2P_ratio * 60) + (P2P_ratio * 40)
```

> **📌 Score vs Resolução:** Score (0-100) e resolução (FULL/PARTIAL/NO/REGRESSION) são **métricas complementares**, não equivalentes:
> - O **score** é um número contínuo que mede o **grau de acerto** (útil para rankings)
> - A **resolução** é um status qualitativo que indica **se o bug foi resolvido sem regressões**
> - Exemplo: F2P=0.5, P2P=1.0 → score = **70** (parece bom), mas resolução = **PARTIAL** (não resolveu completamente)
> - Ambos são mostrados lado a lado nos relatórios para dar visão completa

### Status de Resolução (inspirado no SWE-bench)

| F2P | P2P | Status | Significado |
|-----|-----|--------|-------------|
| 1.0 | 1.0 | **FULL** | ✅ Bug resolvido, sem regressões |
| 0 < x < 1 | 1.0 | **PARTIAL** | ⚠️ Bug parcialmente resolvido |
| 0 | 1.0 | **NO** | ❌ Bug não resolvido |
| qualquer | < 1.0 | **REGRESSION** | 🔴 Criou novo(s) bug(s) |

> **⚠️ Modo geração (F2P/P2P idênticos):** Quando os arrays `fail_to_pass` e `pass_to_pass` são **exatamente iguais** (como em gen-101 a gen-105), o evaluator detecta que é uma task de **geração pura** — não há código "anterior" para regredir. Nesse modo:
> - `F2P_ratio == 1.0` → **FULL** ✅
> - `F2P_ratio < 1.0` → **NO** ❌ (código simplesmente errado, não regressão)
> - A categoria `regression` **nunca** é atribuída nesse modo

### Categorias de Falha (ordem de precedência)

As categorias seguem **ordem de precedência decrescente** — quando múltiplas condições são verdadeiras, a de maior prioridade prevalece:

| Prioridade | Categoria | Quando ocorre |
|------------|-----------|---------------|
| 1 (maior) | `no_code` | Modelo não retornou código válido |
| 2 | `syntax` | Código não compila (AST parse falhou) |
| 3 | `timeout` | Execução excedeu o limite |
| 4 | `runtime` | Exceção em tempo de execução (não-AssertionError) |
| 5 | `regression` | Algum P2P falhou (criou regressão) |
| 6 | `unresolved` | Algum F2P falhou (bug não foi corrigido) |
| — | `None` | Tudo passou → FULL |

> **Exemplo:** Se o código tem erro de sintaxe E algum F2P falharia, a categoria é `syntax` (prioridade 2), não `unresolved` (prioridade 6).

---

## 4. Tasks Propostas

> **Nota:** Decisões de design já tomadas:
> - Modo saída: **código completo** (não patch diff)
> - Hints: **apenas em tasks difíceis** (fix-107, fix-204, refac-103)
> - Runs: **1 run por task** (múltiplas runs futuramente)
> - Compatibilidade: **migrar tudo** (sem suporte a test_code antigo)
> - Formato: **F2P/P2P unificado** inclusive para generation
> - Arquivos: **bug_fixing.json único** (não separar por subtipo)

### Bug Fixing — Todas as 15 tasks em `bug_fixing.json`

#### Edge Cases (7 tasks)

| ID | Nome | Dif. | Inspiração SWE-real | Hints |
|----|------|------|---------------------|-------|
| fix-101 | Trailing Newline Validation | easy | django-11099 ($ vs \\Z) | ❌ |
| fix-102 | Empty List Filter | easy | django-11163 (if fields vs is not None) | ❌ |
| fix-103 | Type Check Narrow | easy | django-11133 (memoryview) | ❌ |
| fix-104 | Decimal Small Notation | medium | django-11206 (Decimal '0.000') | ❌ |
| fix-105 | None Equality Safety | medium | astropy-7606 (Unit == None) | ❌ |
| fix-106 | Version String Parse | medium | astropy-7671 (minversion 'dev') | ❌ |
| fix-107 | Negative Duration Parse | hard | django-10999 (parse_duration negativo) | ✅ |

#### State Mutation (4 tasks)

| ID | Nome | Dif. | Inspiração | Hints |
|----|------|------|------------|-------|
| fix-201 | List Mutated In Place | medium | Bug comum de side-effect | ❌ |
| fix-202 | Dict Merge Mutates | medium | fix-005 melhorado com F2P/P2P | ❌ |
| fix-203 | Default Mutable Arg | medium | `def f(x=[])` clássico | ❌ |
| fix-204 | Shallow Copy Bug | hard | astropy-12907 (nested models) | ✅ |

#### Logic Errors (4 tasks)

| ID | Nome | Dif. | Inspiração | Hints |
|----|------|------|------------|-------|
| fix-301 | Off-by-One Range | easy | fix-001 (merge sort) melhorado | ❌ |
| fix-302 | Wrong Operator | medium | astropy-13033 (misleading exception) | ❌ |
| fix-303 | Missing Autoescape | medium | django-11119 (autoescape não propagado) | ❌ |
| fix-304 | FizzBuzz Off-by-One | easy | fix-002 melhorado com F2P/P2P | ❌ |

### Refactoring (5 tasks em `refactoring.json`)

| ID | Nome | Dif. | Inspiração | Hints |
|----|------|------|------------|-------|
| refac-101 | Regex to Compiled | easy | Melhoria de performance | ❌ |
| refac-102 | Nested If to Match | medium | refac-003 (match-case) | ❌ |
| refac-103 | Monolithic to Modular | hard | refac-004 (analyze_text) | ✅ |
| refac-104 | List Comprehension | easy | refac-001 melhorado | ❌ |
| refac-105 | Grade Calculator | medium | refac-002 melhorado | ❌ |

### Generation (5 tasks em `generation.json`) — formato F2P/P2P unificado

Para tasks de geração, `fail_to_pass` e `pass_to_pass` conterão os mesmos asserts (já que não há código bugado para corrigir), mantendo consistência com o resto do benchmark.

| ID | Nome | Dif. |
|----|------|------|
| gen-101 | Fibonacci | easy |
| gen-102 | Palindrome | easy |
| gen-103 | Binary Search | medium |
| gen-104 | Valid Parentheses | medium |
| gen-105 | CSV Parser | medium |

**Total: 25 tasks** (15 bug_fixing + 5 refactoring + 5 generation)

---

## 4.1 Formato Final das Tasks

### Bug Fixing (com hints opcional em difíceis)

```json
{
  "id": "fix-101",
  "name": "Trailing Newline Validation",
  "category": "bug_fixing",
  "difficulty": "easy",
  "description": "Regex $ permite trailing newline na validação de username",
  "instruction": "Corrija a função para que entradas com trailing newline sejam rejeitadas.",
  "code_context": "def validate_username(username):\n    import re\n    if not re.match(r'^[\\w.@+-]+$', username):\n        return False\n    return True",
  "fail_to_pass": [
    "assert validate_username('user\\n') == False",
    "assert validate_username('admin\\n') == False"
  ],
  "pass_to_pass": [
    "assert validate_username('user') == True",
    "assert validate_username('admin') == True",
    "assert validate_username('') == False",
    "assert validate_username('a b') == False"
  ],
  "timeout": 5
}
```

### Bug Fixing — Task Difícil (com hints)

```json
{
  "id": "fix-107",
  "name": "Negative Duration Parse",
  "category": "bug_fixing",
  "difficulty": "hard",
  "description": "Parse de duração negativa retorna timedelta errado",
  "instruction": "Corrija o parse de durações para que valores negativos como '-1:30' sejam interpretados corretamente.",
  "code_context": "def parse_duration(text):\n    import re\n    m = re.match(r'^(-?(\\d+):)?(\\d+)$', text)\n    if not m:\n        return None\n    hours = int(m.group(2) or 0)\n    minutes = int(m.group(3))\n    from datetime import timedelta\n    return timedelta(hours=hours, minutes=minutes)",
  "fail_to_pass": [
    "from datetime import timedelta; assert parse_duration('-1:30') == timedelta(hours=-1, minutes=-30)",
    "assert parse_duration('-00:01:01') == timedelta(minutes=-1, seconds=-1)"
  ],
  "pass_to_pass": [
    "assert parse_duration('1:30') == timedelta(hours=1, minutes=30)",
    "assert parse_duration('0:00') == timedelta(0)",
    "assert parse_duration('') == None"
  ],
  "timeout": 5,
  "hints": "O problema é que o sinal negativo só se aplica às horas, não aos minutos/segundos. Você precisa capturar o sinal separadamente e aplicá-lo a todos os componentes."
}
```

### Generation (F2P/P2P idênticos — sem código bugado)

```json
{
  "id": "gen-101",
  "name": "Fibonacci",
  "category": "generation",
  "difficulty": "easy",
  "description": "Write a function that returns the n-th Fibonacci number",
  "instruction": "Write a Python function fibonacci(n) that returns the n-th Fibonacci number.",
  "code_context": null,
  "fail_to_pass": [
    "assert fibonacci(0) == 0",
    "assert fibonacci(1) == 1",
    "assert fibonacci(10) == 55",
    "assert fibonacci(20) == 6765"
  ],
  "pass_to_pass": [
    "assert fibonacci(0) == 0",
    "assert fibonacci(1) == 1",
    "assert fibonacci(10) == 55",
    "assert fibonacci(20) == 6765"
  ],
  "timeout": 5
}
```

---

## 5. Mudanças por Arquivo

### `core/evaluator.py` — REFORMULAR COMPLETAMENTE

O evaluator atual tem 200 linhas e usa um único `test_code`. O novo evaluator:

- **Remove:** `W_SYNTAX`, `W_TESTS`, `W_TIME`, `W_QUALITY`, `_quality_score()`, `_run_tests()` (antigo)
- **Mantém:** `_extract_code()`, `_check_syntax()`
- **Adiciona:**
  - `evaluate()` — novo pipeline principal (substitui o antigo)
  - `_run_test_list(asserts, code, timeout)` — executa lista de asserts via wrapping try/except, conta sucessos individualmente

> **Implementação do `_run_test_list`:** Cada assert é executado num único subprocess com **wrapping try/except individual**, garantindo que todos os asserts rodem mesmo se alguns falharem:
> ```python
> def _run_test_list(self, asserts, code, timeout):
>     """Run a list of assert statements, return (passed, total, exec_time, error)."""
>     # Build wrapper: import + code + try/except for each assert
>     wrapper_lines = [code]
>     wrapper_lines.append("")
>     wrapper_lines.append("_results = {}")
>     for i, assert_code in enumerate(asserts):
>         wrapper_lines.append(f"""
> try:
>     {assert_code}
>     _results[{i}] = 'PASS'
> except AssertionError:
>     _results[{i}] = 'FAIL'
> except Exception as e:
>     _results[{i}] = 'ERR:' + str(e)
> """)
>     wrapper_lines.append("")
>     wrapper_lines.append("import json")
>     wrapper_lines.append("print('__RESULTS__')")
>     wrapper_lines.append("print(json.dumps(_results))")
>     full_code = "\n".join(wrapper_lines)
>
>     # Write to temp file and execute
>     t0 = time.time()
>     try:
>         result = subprocess.run([sys.executable, tmp_path],
>             capture_output=True, text=True, timeout=timeout)
>         exec_time = time.time() - t0
>         # Parse JSON results from stdout
>         for line in result.stdout.splitlines():
>             if line.strip() == '__RESULTS__':
>                 # Next line is JSON
>                 ...
>     except subprocess.TimeoutExpired:
>         ...
> ```
> **Vantagens:** 100% preciso com asserts duplicados, captura runtime errors como `ERR:`, não mascara falhas, execução em subprocess único.
  - `_get_resolution_status(f2p_ratio, p2p_ratio)` → FULL/PARTIAL/NO/REGRESSION
  - `_classify_failure(f2p_passed, f2p_total, p2p_passed, p2p_total, syntax_ok)` → categoria
  - `compute_score(f2p_ratio, p2p_ratio)` → `(f2p_ratio * 60) + (p2p_ratio * 40)`
- **Hints:** Campo `hints` na task é passado adiante no resultado (não usado na avaliação, apenas para referência/display)

**Interface de saída** (cada resultado):
```python
{
    "code": "...",
    "syntax_ok": True,
    "syntax_error": None,
    "f2p_passed": 2,
    "f2p_total": 2,
    "p2p_passed": 4,
    "p2p_total": 4,
    "f2p_ratio": 1.0,
    "p2p_ratio": 1.0,
    "total_score": 100,
    "resolution": "FULL",        # FULL | PARTIAL | NO | REGRESSION
    "failure_category": None,    # syntax | runtime | unresolved | regression | timeout | no_code
    "exec_time": 0.05,
    "error": None,
}
```

### `bench.py` — ADAPTAR

- Mudar `task["test_code"]` → `task["fail_to_pass"]` + `task["pass_to_pass"]`
- Mostrar status de resolução no output:
  - `FULL ✅` (score ≥ 100)
  - `PARTIAL ⚠️` (F2P parcial, P2P ok)
  - `NO ❌` (F2P = 0)
  - `REGRESSION 🔴` (P2P quebrou)
- Mostrar categoria de falha quando relevante
- Exibir `hints` se presente (no verbose mode)
- Tasks antigas (formato `test_code`) NÃO são mais suportadas

### `core/runner.py` — ADAPTAR PROMPT

O prompt enviado ao modelo deve incluir tanto `fail_to_pass` quanto `pass_to_pass`, para que o modelo saiba exatamente o que seu código precisa atender:

```python
def _build_prompt(self, task):
    parts = [task["instruction"]]

    if task.get("code_context"):
        parts.append(f"\nCódigo atual (contém bugs):\n```\n{task['code_context']}\n```")

    if task.get("fail_to_pass"):
        parts.append("\nSeu código deve passar nestes testes (resolver o bug):\n```\n" +
                      "\n".join(task["fail_to_pass"]) + "\n```")

    if task.get("pass_to_pass"):
        parts.append("\nE não deve quebrar estes testes (sem regressão):\n```\n" +
                      "\n".join(task["pass_to_pass"]) + "\n```")

    if task.get("hints"):
        parts.append(f"\nDica: {task['hints']}")

    if task.get("constraints"):
        parts.append(f"\nRestrições: {task['constraints']}")

    return "\n".join(parts)
```

- `fail_to_pass` e `pass_to_pass` são mostrados separadamente para dar contexto ao modelo
- `hints` é incluído quando presente (apenas em tasks difíceis)
- `constraints` mantido do formato antigo

### `core/reporter.py` — ADICIONAR CAMPOS

- Colunas na tabela: Score, Resolução, F2P, P2P, Falha, Tempo
- Cores no HTML:
  - FULL → verde
  - PARTIAL → laranja
  - NO → vermelho
  - REGRESSION → vermelho escuro com borda
- No Markdown: emojis e bold para destacar status

### Tasks JSON — SUBSTITUIR CONTEÚDO

- `tasks/bug_fixing.json` — 15 novas tasks (fix-101 a fix-304)
- `tasks/refactoring.json` — 5 tasks (refac-101 a refac-105)
- `tasks/generation.json` — 5 tasks (gen-101 a gen-105, mantidas)

---

## 6. Compatibilidade Retroativa

**Decisão: Migrar tudo.** Não haverá suporte a tasks no formato antigo (`test_code`).

Todas as 25 tasks serão convertidas para o novo formato. As tasks antigas de algoritmos (Fibonacci, etc.) serão mantidas como `gen-101` a `gen-105` no formato F2P/P2P unificado (fail_to_pass e pass_to_pass com os mesmos asserts).

As 10 tasks antigas de bug_fixing e refactoring serão substituídas pelas 20 novas tasks inspiradas no SWE-bench real.

---

## 7. Dependências

Nenhuma nova dependência. Tudo com stdlib Python:
- `ast` (já usado)
- `subprocess` (já usado)
- `tempfile` (já usado)
- `json` (já usado)

---

## 8. Ordem de Implementação Sugerida

| Fase | O quê | Arquivos | Descrição |
|------|-------|----------|-----------|
| **1** | Tasks JSON (25 tasks) | `tasks/bug_fixing.json`, `tasks/refactoring.json`, `tasks/generation.json` | Criar os 3 arquivos JSON com o novo formato F2P/P2P. Incluir campo `hints` apenas em fix-107, fix-204, refac-103. |
| **2** | Evaluator v2 | `core/evaluator.py` | Reescrever o evaluator com pipeline F2P/P2P, detecção de modo (geração vs bug_fixing), `_run_test_list()` (wrapping try/except), `_get_resolution_status()`, `_classify_failure()` (ordem de precedência), `compute_score()`. |
| **3** | CLI | `bench.py` | Adaptar para ler `fail_to_pass`/`pass_to_pass`, exibir status de resolução e categoria de falha, exibir hints em verbose mode. |
| **4** | Reporter | `core/reporter.py` | Adicionar colunas de resolução, F2P, P2P, Falha. Cores condicionais no HTML (verde/laranja/vermelho). |
| **5** | Teste completo | — | Rodar `python bench.py` com um modelo (ex: Flash), verificar output, relatório HTML e MD. |
