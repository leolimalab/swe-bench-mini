# Referências — Swe-Bench-Mini

> Projetos similares analisados durante o planejamento.
> Data da análise: 30/05/2026

---

## 1. tabupl/AdamBench

- **GitHub:** https://github.com/tabupl/AdamBench
- **⭐:** 27 | **🍴:** 2
- **Linguagem:** TypeScript
- **Conexão:** Ollama
- **Atualização:** 07/05/2026

### Como funciona
Benchmark de modelos locais para tarefas de "agentic coding". Cada modelo recebe uma tarefa de projeto (criar um app do zero) e é avaliado por:
- Qualidade do projeto final (LLM-as-judge)
- Número de iterações necessárias
- Tempo total

### Métrica
"AdamBench score" — combina qualidade + iterações + tempo.

### Destaques
- Métrica composta interessante
- Benchmark prático (projetos reais, não snippets)
- Hardware específico (RTX 5080, 64GB RAM)

### Limitações
- Subjetivo (LLM julga outro LLM)
- TypeScript (não Python)
- Projetos grandes (leva horas)
- Só Ollama

### Lições para nós
- ✅ Métrica composta é melhor que passa/não passa
- ✅ Múltiplas runs por tarefa
- ❌ Avaliação subjetiva é cara e não reproduzível
- ❌ Projetos grandes são lentos demais para "benchmark rápido"

---

## 2. ArturasDedinas123/local-llm-benchmark

- **GitHub:** https://github.com/ArturasDedinas123/local-llm-benchmark
- **⭐:** 2 | **🍴:** 0
- **Linguagem:** Python + Jupyter
- **Conexão:** Ollama
- **Atualização:** 27/05/2026

### Como funciona
Benchmark automatizado de modelos locais (Qwen 3.6, Gemma 4) em 6 tarefas práticas de código. Cada tarefa tem um prompt em `.txt` com instrução + código de referência.

### Tarefas
| ID | Tarefa | Categoria |
|----|--------|-----------|
| 01_fifo_trades | Implementar FIFO financeiro | Geração |
| 02_debug | Corrigir merge sort bugado | Correção |
| 03_refactor | Refatorar código procedural | Refatoração |
| 04_extend | Adicionar métodos a LRUCache | Geração |
| 05_decorator | Estender decorator com TTL | Misto |
| 06_pandas | Análise de outliers | Geração |

### Avaliação
1. Extrai código da resposta (regex ```python)
2. Salva em tempfile
3. Executa com subprocess
4. Testa com asserts embutidos
5. Gera CSV com pass/fail

### Destaques
- Mais alinhado com nossa ideia
- Código Python simples e direto
- Execução real de código (não subjetivo)
- 3 runs por tarefa (mediana)
- Stock vs Tuned (compara configurações de sampling)

### Limitações
- Só Ollama (não llama.cpp)
- Sem relatório HTML (só CSV + notebook)
- Tarefas fixas em .txt (não modulares)
- Sem classificação de falhas

### Lições para nós
- ✅ Extrair código com regex
- ✅ Executar em tempfile com subprocess
- ✅ Múltiplas runs (mediana)
- ✅ Prompts em arquivos separados
- ❌ Formato .txt é menos estruturado que JSON
- ✅ Usar pyproject.toml para dependências mínimas

---

## 3. abhaymundhara/llm-benchmark-suite

- **GitHub:** https://github.com/abhaymundhara/llm-benchmark-suite
- **⭐:** 3 | **🍴:** 0
- **Linguagem:** Python
- **Conexão:** Ollama, OpenAI, Anthropic, Gemini
- **Atualização:** 23/04/2026

### Como funciona
Suite completa de benchmarks (HumanEval, MBPP, BigCodeBench, SWE-bench) com adaptadores para múltiplos provedores de modelo.

### Arquitetura
```
benchmarks/
  base.py          # Classe abstrata Benchmark + BenchmarkTask + TaskResult
  humaneval.py     # HumanEval via datasets HuggingFace
  mbpp.py          # MBPP via datasets
  bigcodebench.py  # BigCodeBench
  swe_bench.py     # SWE-bench demo (similarity scoring)
models/
  base.py          # Adapter abstrato
  ollama_adapter.py
  openai_adapter.py
  claude_adapter.py
  gemini_adapter.py
```

### Avaliação
- Extrai código da resposta
- Executa em ambiente controlado
- **Classifica falhas em categorias:** syntax, runtime, logic, timeout
- Gera relatório JSON + Streamlit UI

### Destaques
- Arquitetura modular e extensível (adapters)
- Classificação de falhas (não só pass/fail)
- Suporte a múltiplos benchmarks conhecidos
- Suite de testes pytest
- Streamlit UI interativa

### Limitações
- Depende de datasets HuggingFace (HumanEval, MBPP)
- Complexo para nosso objetivo (queremos algo leve)
- Sem suporte a llama.cpp
- Sem relatório HTML standalone

### Lições para nós
- ✅ Arquitetura de adapters (abstrair conexão)
- ✅ Classificar falhas (syntax ≠ runtime ≠ logic)
- ✅ Usar timeout para evitar loops infinitos
- ✅ BenchmarkTask como dataclass
- ❌ Depender de datasets externos é pesado

---

## 4. perminder-klair/locca

- **GitHub:** https://github.com/perminder-klair/locca
- **⭐:** 13 | **🍴:** 0
- **Linguagem:** TypeScript
- **Conexão:** llama.cpp (nativo)
- **Atualização:** 24/05/2026

### Como funciona
TUI (terminal UI) ao redor do llama.cpp para gerenciar modelos GGUF, rodar servidores, executar benchmark e lançar o agente `pi` (coding agent).

### Funcionalidades
- Download de modelos via catálogo
- Gerenciamento de servidores llama.cpp (múltiplas portas)
- Benchmark de modelos
- Integração com agente pi
- Detecção automática de hardware (VRAM, RAM)

### Destaques
- **Único com suporte nativo a llama.cpp**
- Gerencia ciclo de vida completo (download → servidor → benchmark)
- Detecta hardware e sugere modelos compatíveis
- Catálogo de modelos com hints de tamanho

### Limitações
- TypeScript (não Python)
- Foco mais em gerenciamento do que avaliação
- TUI complexa
- Benchmark é secundário (feature, não core)

### Lições para nós
- ✅ Suporte nativo a llama.cpp é viável
- ✅ Múltiplos modelos em portas diferentes
- ✅ Gerenciar servidores é útil mas não essencial
- ❌ Não precisamos de TUI complexa

---

## 5. Outros Projetos Mencionados

### bigcode-project/bigcode-inference-benchmark ⭐ 19
- https://github.com/bigcode-project/bigcode-inference-benchmark
- Benchmark de inferência (velocidade, não qualidade)
- Focado em throughput, não em correção de código

### bastosmichael/coder-benchmark ⭐ 5
- https://github.com/bastosmichael/coder-benchmark
- Node.js, Ollama, TypeScript scenarios
- Similar mas em JavaScript

### nik-kl/local-llm-tech-bench ⭐ 1
- https://github.com/nik-kl/local-llm-tech-bench
- Compara GPT-OSS, Llama 3, Qwen, DeepSeek
- 4 níveis, 36 pontos de teste
- Inclui coding, network, security

---

## Comparação Final

| Aspecto | AdamBench | local-llm-benchmark | llm-benchmark-suite | locca | **Nosso Projeto** |
|---------|-----------|---------------------|--------------------|-------|-------------------|
| **Linguagem** | TS | Python | Python | TS | **Python** |
| **Conexão** | Ollama | Ollama | Multi | **llama.cpp** | **llama.cpp** |
| **Avaliação** | Subjetiva | Execução real | Execução real | N/A | **Execução real** |
| **Tarefas** | Projetos | 6 prompts | HumanEval+ | N/A | **JSON modular** |
| **Relatório** | Subjetivo | CSV | JSON+Streamlit | N/A | **HTML+MD** |
| **Sandbox** | Não | tempfile | Sim | N/A | **tempfile** |
| **Dependências** | Muitas | requests+pandas | requests+datasets | Muitas | **requests** |
| **Complexidade** | Alta | Baixa | Média | Alta | **Baixa** |
