# Análise do SWE-bench Real — Melhorias para swe-bench-mini

## Dados Coletados

- **SWE-bench Full**: 2.294 instâncias (princeton-nlp/SWE-bench no HuggingFace)
- **SWE-bench Verified**: 500 instâncias verificadas por humanos
- **Repos**: astropy, django, flask, sympy, scikit-learn, pytest, matplotlib, sphinx, requests, etc.

## 1. Estrutura Real de uma Task SWE-bench

```python
{
    "instance_id": "django__django-11099",
    "repo": "django/django",
    "base_commit": "abc123...",
    "patch": "diff --git a/django/contrib/auth/validators.py\n...",   # Diff da correção
    "test_patch": "diff --git a/tests/auth_tests/test_validators.py\n...", # Diff dos testes
    "problem_statement": "UsernameValidator allows trailing newline...",
    "hints_text": "Comments do issue antes do primeiro commit do PR",
    "FAIL_TO_PASS": ["test_ascii_validator ...", "test_unicode_validator ..."],
    "PASS_TO_PASS": ["test_defaults ...", "test_international ...", ...],
    "version": "2.1",
    "created_at": "2019-01-15T10:00:00Z",
    "environment_setup_commit": "def456..."
}
```

## 2. O Sistema F2P/P2P (Coração do SWE-bench)

| Conceito | Descrição | Exemplo real |
|----------|-----------|--------------|
| **FAIL_TO_PASS** | Testes que **quebram** no código bugado e **passam** no corrigido | `test_ascii_validator` com trailing newline |
| **PASS_TO_PASS** | Testes que **passam** em ambos (garantem que nada quebrou) | 1.432 testes do Django que não foram afetados |

### Status de Resolução:
| F2P | P2P | Resultado |
|-----|-----|-----------|
| 1.0 | 1.0 | **RESOLVED_FULL** (resolvido) |
| 0 < x < 1 | 1.0 | **RESOLVED_PARTIAL** (parcial) |
| qualquer outro | | **RESOLVED_NO** (não resolvido) |

## 3. Patches Reais (os bugs são PEQUENOS mas REAIS)

### Exemplo 1: Django — Regex $ vs \Z (2 linhas)
```diff
-    regex = r'^[\w.@+-]+$'
+    regex = r'^[\w.@+-]+\Z'
```
**Bug**: `$` no Python regex permite trailing newline. `\Z` não.

### Exemplo 2: Django — autoescape não propagado (1 linha)
```diff
-    return t.render(Context(context))
+    return t.render(Context(context, autoescape=self.autoescape))
```
**Bug**: Engine com autoescape=False ignorava o atributo em render_to_string().

### Exemplo 3: Django — memoryview não suportado (1 linha)
```diff
-    if isinstance(value, bytes):
+    if isinstance(value, (bytes, memoryview)):
```
**Bug**: HttpResponse não aceitava memoryview do PostgreSQL.

### Exemplo 4: Django — if fields vs is not None (1 caractere)
```diff
-    if fields and f.name not in fields:
+    if fields is not None and f.name not in fields:
```
**Bug**: `fields=[]` (lista vazia) é falsy, então retornava todos os campos.

### Exemplo 5: Django — Decimal pequeno vira notação científica
```python
cutoff = Decimal('0.' + '1'.rjust(decimal_pos, '0'))
if abs(number) < cutoff:
    number = Decimal('0')
```

### Exemplo 6: Astropy — Unit == None (TypeError)
```python
# Antes: raise TypeError
# Depois: return NotImplemented (deixa Python tratar como False)
```

### Exemplo 7: Astropy — minversion com 'dev'
```python
# Regex PEP440 para extrair só números da versão
expr = r'^([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*'
```

## 4. Padrões de Bug no SWE-bench Real

| Categoria | % Aprox | Exemplos |
|-----------|---------|----------|
| **Edge case** (caso de borda) | ~35% | valor vazio, None, zero, negativo |
| **Type handling** (tipo errado) | ~20% | bytes vs str, memoryview, None |
| **Logic error** (lógica errada) | ~25% | condicional invertida, operador errado |
| **State mutation** (efeito colateral) | ~10% | modifica input sem copiar |
| **Regressão** (versão quebrou) | ~10% | mudança em lib quebra compatibilidade |

## 5. Proposta de Novas Tasks para swe-bench-mini

### Categoria: Edge Cases (bug_fixing)

#### fix-101: Django-style "trailing newline" (fácil)
```python
# code_context: valida username mas permite \n no final
def validate_username(username):
    import re
    if not re.match(r'^[\w.@+-]+$', username):
        return False
    return True

# F2P: validate_username("user\n") → False
# P2P: validate_username("user") → True, validate_username("") → False
```

#### fix-102: "if list" vs "if list is not None" (fácil)
```python
# code_context: fields=[] retorna todos os campos (bug)
def filter_fields(data, fields=None):
    result = {}
    for key, value in data.items():
        if fields and key not in fields:
            continue
        result[key] = value
    return result

# F2P: filter_fields({"a":1,"b":2}, []) → {}
# P2P: filter_fields({"a":1,"b":2}) → {"a":1,"b":2}
```

#### fix-103: isinstance type check (fácil)
```python
# code_context: só aceita bytes, não memoryview ou bytearray
def to_bytes(value):
    if isinstance(value, bytes):
        return value
    return str(value).encode()

# F2P: to_bytes(memoryview(b"hello")) → b"hello"
# P2P: to_bytes(b"hello") → b"hello"
```

#### fix-104: Decimal muito pequeno vira notação científica (médio)
```python
# code_context: Decimal('1e-199') renderiza como '1e-199' em vez de '0.00'
def format_decimal(value, decimal_places=2):
    return f"{value:.{decimal_places}f}"

# F2P: format_decimal(Decimal('1e-199'), 2) → '0.00'
# P2P: format_decimal(Decimal('3.14'), 2) → '3.14'
```

#### fix-105: None propagation / == None (médio)
```python
# code_context: comparação com None levanta exceção
def safe_equals(a, b):
    return a == b  # Bug: a == None pode dar TypeError em tipos custom

# F2P: safe_equals(SomeCustomType("x"), None) → False
# P2P: safe_equals(1, 1) → True
```

### Categoria: State Mutation / Side Effects

#### fix-201: Lista mutada (médio)
```python
# code_context: função modifica a lista original
def deduplicate(items):
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    items.clear()
    items.extend(result)
    return result

# F2P: original = [1,2,2,3]; deduplicate(original); original == [1,2,2,3]
# P2P: deduplicate([1,2,2,3]) → [1,2,3]
```

#### fix-202: Dicionário mutado (médio)
```python
# code_context: merge modifica o primeiro dict
def merge_dicts(dict1, dict2):
    for key, value in dict2.items():
        dict1[key] = value
    return dict1

# F2P: a = {"x":1}; merge_dicts(a, {"y":2}); a == {"x":1}
# P2P: merge_dicts({"x":1}, {"y":2}) → {"x":1, "y":2}
```

### Categoria: Refactoring (inspirado em bugs reais)

#### refac-101: Regex vulnerability (médio)
```python
# code_context: regex permite trailing newline
def validate_email(email):
    import re
    return bool(re.match(r'^[\w.@+-]+@[\w.]+\.\w+$', email))

# F2P: validate_email("user@example.com\n") → False
# P2P: validate_email("user@example.com") → True
```

#### refac-102: Parse de duração negativa (hard)
```python
# code_context: parse de "-1:30" retorna timedelta errado
def parse_duration(text):
    import re
    m = re.match(r'^(-?(\d+):)?(\d+)$', text)
    if not m:
        return None
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3))
    from datetime import timedelta
    return timedelta(hours=hours, minutes=minutes)

# F2P: parse_duration("-1:30") == timedelta(hours=-1, minutes=-30)
# P2P: parse_duration("1:30") == timedelta(hours=1, minutes=30)
```

## 6. Mudanças Necessárias no swe-bench-mini

> **Decisões já tomadas:**
> - Modo saída: **código completo** (não patch diff)
> - Hints: **apenas em tasks difíceis** (fix-107, fix-204, refac-103)
> - Runs: **1 run por task** (múltiplas runs futuramente)
> - Compatibilidade: **migrar tudo** (sem suporte a test_code antigo)
> - Formato: **F2P/P2P unificado** inclusive para generation
> - Arquivos: **bug_fixing.json único** (não separar por subtipo)

### 6.1 Novo Formato de Task (inspirado no SWE-bench real)

```python
{
    "id": "fix-101",
    "name": "Trailing Newline Validation",
    "category": "bug_fixing",
    "difficulty": "easy",
    "description": "Regex $ permite trailing newline na validação de username",
    "instruction": "Corrija a regex para que usernames com trailing newline sejam rejeitados.",
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

### 6.2 Mudanças no Evaluator

1. **F2P/P2P em vez de test_code único**
   - `fail_to_pass`: testes que DEVEM passar no código corrigido (verifica resolução)
   - `pass_to_pass`: testes que NÃO DEVEM quebrar (verifica regressão)
   - **Contagem:** wrapping try/except individual (não parsing de stderr)
   - Score: F2P_ratio × 60 + P2P_ratio × 40
   - Score e Resolução são complementares (ambos no relatório)

2. **Status de Resolução**
   - FULL: F2P=1.0 e P2P=1.0
   - PARTIAL: 0<F2P<1 e P2P=1.0
   - NO: F2P=0
   - REGRESSION: P2P<1.0
   - **Modo geração** (F2P==P2P): FULL ou NO (sem regressão)

3. **Ordem de Precedência das Falhas**
   `no_code > syntax > timeout > runtime > regression > unresolved`

4. **Prompt do modelo**
   - `fail_to_pass` e `pass_to_pass` são incluídos separadamente
   - `hints` incluído quando presente (apenas tasks difíceis)

### 6.3 Novas Categorias de Task

| Categoria | Descrição | Exemplo real |
|-----------|-----------|--------------|
| **edge_cases** | Bugs de caso de borda (None, vazio, negativo) | django-10999, django-11206 |
| **type_handling** | Bugs de tipo (bytes vs str, memoryview) | django-11133, astropy-8707 |
| **state_mutation** | Bugs de efeito colateral (muta input) | astropy-12907 (nested models) |
| **logic_error** | Bugs de lógica (condicional errada) | django-11163, django-11119 |
| **regression** | Bugs introduzidos por mudanças | astropy-7671 |
