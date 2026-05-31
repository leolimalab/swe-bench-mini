# AGENTS.md — Swe-Bench-Mini

## Instruções para Agentes Futuros

Este documento descreve o projeto **swe-bench-mini** e as decisões já tomadas para que qualquer agente (IA ou humano) possa continuar o trabalho sem perder contexto.

## Origem do Projeto

Idealizado por **Leo Lima**, um desenvolvedor que:
- Usa modelos LLM locais via **llama.cpp** (Qwen 3.5, Qwen 3.6, Gemma 4)
- Quer um benchmark rápido para comparar modelos de código
- Prefere soluções em **Python**, mínimas em dependências
- Usa Hermes Agent (BytePlus ModelArk) como assistente principal

## Estado Atual

- ✅ **Pesquisa de referências:** Concluída (SWE-bench real analisado)
- ✅ **Planejamento v2 (F2P/P2P):** Concluído (ver `planejamento.md`)
- ⏸️ **Implementação:** Aguardando aprovação do usuário
- ⏸️ **Testes:** Aguardando aprovação do usuário

## Regras Importantes

1. **Só implementar após aprovação explícita** do usuário
2. **Sempre criar todo list** (ferramenta `todo`) para tarefas complexas
3. **Manter dependências mínimas** — priorizar stdlib Python
4. **Foco em llama.cpp** (não Ollama) — conexão via API OpenAI-compatível
5. **Tarefas em JSON** (não TXT) — mais estruturado para avaliação automática

## Decisões de Design (Tomadas)

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Linguagem | Python | Preferência do usuário, mais projetos similares |
| Conexão | llama.cpp (OpenAI-compat) | É o que o usuário usa |
| Tarefas | Arquivos `.json` separados | Fácil editar sem mexer em código |
| Avaliação | F2P (fail_to_pass) + P2P (pass_to_pass) | Baseado no SWE-bench real |
| Score | F2P_ratio × 60 + P2P_ratio × 40 | Peso maior na resolução do bug |
| Resolução | FULL / PARTIAL / NO / REGRESSION | Idêntico ao SWE-bench |
| Relatório | HTML + Markdown | HTML para visualização, MD para docs |
| Sandbox | tempfile + subprocess | Seguro, isolado, sem dependências |
| **Modo saída do modelo** | Código completo (não patch diff) | Compatível com todos os modelos |
| **Hints** | Só em tasks difíceis | Inspirado no SWE-bench |
| **Runs por task** | 1 run | Simplicidade |
| **Compatibilidade** | Migrar tudo (sem legado) | Mais limpo |
| **Arquivos** | `bug_fixing.json` único | Simplicidade |
| **Contagem de asserts** | Wrapping try/except individual (não stderr) | 100% preciso |
| **Modo geração** | F2P=P2P → sem regressão | Evita falso REGRESSION |
| **Prompt** | Inclui F2P + P2P + hints | Modelo sabe o que implementar |
| **Ordem falhas** | no_code > syntax > timeout > runtime > regression > unresolved | Sem ambiguidade |
| **code_context** | Obrigatório para bugs, null para geração | Schema limpo |
| **Score vs Resolução** | Complementares (ambos no relatório) | Visão completa |

## Decisões de Design (Pendentes)

Ver `planejamento_status.md` para a lista completa de decisões pendentes.

## Projetos Similares (Referências)

| Projeto | Destaque |
|---------|----------|
| ArturasDedinas123/local-llm-benchmark | Python, execução real de código, prompts .txt |
| abhaymundhara/llm-benchmark-suite | Arquitetura modular, classificação de falhas, múltiplos provedores |
| perminder-klair/locca | Único com suporte nativo a llama.cpp |
| tabupl/AdamBench | LLM-as-judge (subjetivo), métrica composta |

Ver `referencias.md` para análise detalhada.

## Fluxo de Trabalho

1. Usuário configura modelos em `config.yaml`
2. Usuário executa: `python bench.py --model "Qwen 3.5"`
3. Para cada tarefa:
   - Runner → llama.cpp API → resposta do modelo
   - Evaluator extrai código → executa testes → calcula score
4. Reporter gera HTML + Markdown em `results/`

## Perfil do Usuário

- **Nome:** Leo Lima
- **Idioma:** Português (Brasil)
- **Modelo preferido (análise profunda):** Kimi-K2.5 (via BytePlus)
- **Modelo preferido (tarefas rápidas):** DeepSeek-V4-Flash
- **Plataforma:** Android via Termux
- **Hermes profiles:** `fast` (Flash), `deep` (Kimi-K2.5)

## Contato

Usuário acessível via Telegram (DM). Responder sempre em português.
