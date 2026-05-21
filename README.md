<div align="center">

```
      ·   ·
   ·  ◆    ·   ·       r e s e a r c h - s w a r m
 ·   ◆   ◆   ◆   ·     a local-first research harness that
   ◆   ◆   ◆    ·      thinks out loud, cites its sources,
      ·   ·            and remembers what you asked last time.
```

</div>

A small, scrappy [ReAct](https://arxiv.org/abs/2210.03629) research harness with DSPy and Codex app-server backends. Point it at a question. It picks tools, reads pages, and writes you back a grounded answer with real citations. Every page it reads lands in a local archive so the next time you ask something adjacent, it answers faster and from material it already trusts.

Backends:

- `dspy`: uses DSPy + litellm with Ollama, Anthropic, OpenAI, or any other supported provider.
- `codex`: uses `codex app-server` through [`codex-control`](https://github.com/cybernetic-physics/codex-control) and the user's existing Codex CLI/Desktop auth.
- `auto`: uses DSPy when `.env` or the shell provides an LM config; otherwise uses Codex when `codex app-server` is available.

---

## 30-second tour

```bash
$ research-agent "what is Loopix and how does it beat Tor?"

┌─ research-swarm ─────────────────────────────────────────────┐
│ mode     single · critic on                                  │
│ question what is Loopix and how does it beat Tor?            │
└──────────────────────────────────────────────────────────────┘

  ▸ arxiv_search("Loopix anonymous communication")     → 5 papers
  ▸ fetch_url("arxiv.org/abs/1703.00536")              → 3194 chars (trafilatura)
  ▸ fetch_url("arxiv.org/pdf/1703.00536")              → 73600 chars (jina)
  ▸ web_search("Loopix vs Tor latency tradeoff")       → 16 results
  ▸ fetch_url("planetary-mix.org/papers/loopix")       → cache hit
  ▸ finish                                             → 12.4s

╭─ synthesis ──────────────────────────────────────────────────╮
│ Loopix is a low-latency mix network by Piotrowska et al.     │
│ (Usenix Security 2017) [arXiv:1703.00536]. Unlike Tor's ...  │
╰──────────────────────────────────────────────────────────────╯

sources:
  · arXiv:1703.00536
  · https://planetary-mix.org/papers/loopix
  · https://en.wikipedia.org/wiki/Mix_network

critique:
  grounding: 4/5 · coverage gaps: none detected · likely errors: none
```

The next time you ask about mixnets, most of it's already in your archive.

---

## Install and run

```bash
# clone, install
git clone https://github.com/dmarzzz/research-swarm.git
cd research-swarm
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[codex]'     # DSPy and Codex backends
# or: pip install -e .        # DSPy-only install

cp .env.example .env
research-agent doctor

# .env defaults to RA_BACKEND=auto.
# For DSPy, add one of these:
# Option A — fully local, no key:
#   LM_MODEL=ollama/qwen3:35b         (needs Ollama running; see below)
# Option B — hosted:
#   ANTHROPIC_API_KEY=sk-ant-...
# Option C — anything litellm supports:
#   LM_MODEL=openai/gpt-4o and LM_API_KEY=sk-...
#
# For Codex, leave LM_MODEL/API keys unset or set:
#   RA_BACKEND=codex

# first query
research-agent "your question here"
```

**Ollama, for the no-key path:** `brew install ollama && ollama serve &` then `ollama pull qwen3:35b`.

---

## Two modes

### `research-agent "..."` — single

One ReAct loop. The selected backend picks from ~12 Python-owned tools turn by turn until it has enough to write a synthesis. This is the default. Usually what you want.

### `research-agent --parallel "..."` — STORM fan-out

Takes a broad question, decomposes it into 3–5 sub-questions, runs an independent ReAct loop per sub-question concurrently, then merges the sub-syntheses into one cohesive answer with all citations preserved. Use for surveys, comparative studies, or "tell me everything about X" queries.

```bash
research-agent --parallel "survey the design space of anonymous communication systems"
```

### `--no-critique` — skip the self-review

The default pipeline runs a self-critique pass after synthesis that flags fabricated citations, coverage gaps, and low-grounding claims. Skip it with `--no-critique` when you just want the answer fast.

### `--backend {auto,codex,dspy}` — choose the reasoning backend

`auto` is the default. It uses DSPy when `.env` or the shell provides `LM_MODEL`, `ANTHROPIC_API_KEY`, or an OpenAI-compatible local `LM_API_BASE`. If DSPy is not configured, it uses Codex when `codex app-server` is available. In both modes, Python executes the research tools.

Set `RA_BACKEND` in `.env` when you want a persistent default. A CLI flag always wins over `.env`, so `research-agent --backend codex "..."` overrides `RA_BACKEND=dspy`.

```bash
research-agent --backend codex "compare Loopix and Tor"
research-agent --backend dspy "compare Loopix and Tor"
research-agent --codex-model gpt-5.4 --codex-effort low "survey mixnets"
research-agent doctor
```

---

## What actually happens

```
  your question
       │
       ▼
  ┌─────────────┐         ┌─────────────────────────────────┐
  │ Codex or    │  picks  │  web_search · local_search      │
  │ DSPy ReAct  │──────►  │  arxiv_search · fetch_url       │
  │ controller  │  tool   │  github_search · extract_links  │
  └─────────────┘  by     │  verify_arxiv_citations · ...   │
       ▲           turn   └────────────┬────────────────────┘
       │                               │
       │      ┌────────────────────────┘
       │      ▼
       │   ┌──────────────────┐    writes through
       │   │  every fetched   │────────────────────┐
       │   │  page goes here  │                    ▼
       │   └──────────────────┘       ~/world_knowledge/web/
       │                              <domain>/<date>-<slug>.md
       │                              (YAML frontmatter, markdown body)
       │                                        │
       │                                        ▼
       │                              SQLite FTS5 index
       │                              (so local_search finds it forever)
       │
       └──────── next time you ask something adjacent,
                the agent sees the indexed content first.
```

The archive grows every query. After a week of use on the same topic, most of what the agent needs is already local. `web_search` has a query-hash cache that short-circuits repeat queries without hitting the network at all.

---

## Research traces

Every run writes a JSON trace to `runs/YYYYMMDD-HHMMSS-<slug>.json`: the question, backend, Python-owned tool calls, synthesis, sources, sub-results for parallel mode, backend metadata, and critique. The legacy top-level `question`, `synthesis`, `sources`, and `critique` fields are preserved so downstream tools keep working.

```bash
$ research-agent "what is Loopix and how does it beat Tor?"
...
$ ls runs/
20260423-140321-loopix-vs-tor.json
```

The traces are also the input format [`content-pipeline`](https://github.com/dmarzzz/content-pipeline) consumes to generate a blog post, tweet thread, or explainer video from a research run:

```bash
rotate content --trace research-swarm/runs/20260423-140321-loopix-vs-tor.json
```

Once you have ~20 traces you're happy with, they're also training data for `dspy.teleprompt.MIPROv2` to compile prompts tuned to your research style.

---

## The tool zoo

The agent picks from these each turn based on the tool's docstring:

| tool | when it fires | key needed |
|---|---|---|
| `local_search` | always first, reads your growing archive | — |
| `web_search` | general queries; DDG + optional SearXNG | — |
| `expanded_search` | when a query needs synonym coverage; LM expands → fan-out → LM rerank | just your LM |
| `arxiv_search` / `arxiv_fetch_paper` | peer-reviewed papers, full PDF read | — |
| `semantic_scholar_search` | broader than arXiv, citation counts | optional `SEMANTIC_SCHOLAR_API_KEY` |
| `github_search` | code, projects, activity signals | optional `GITHUB_TOKEN` (raises rate limit from 60 to 5000/hr) |
| `nitter_search` | Twitter/X via open-source Nitter frontend | — (public) or `NITTER_URL` |
| `fetch_url` / `fetch_urls_parallel` | read a URL in full; trafilatura → Jina fallback; 7-day cache | — |
| `extract_links` | one-hop follow-up from a promising page | — |
| `verify_arxiv_citations` | HEAD-check every arXiv ID in a text to catch fabrications | — |

---

## Use it from your own code

```python
from research_agent.agent import configure_lm, build_agent
from datetime import date

configure_lm()
agent = build_agent()
result = agent(
    current_date=date.today().isoformat(),
    question="what is Loopix and how does it beat Tor?",
)
print(result.synthesis)
for s in result.sources:
    print("·", s)
```

See `examples/` for more (hello-world, custom tool, parallel mode).

---

## Customize

### choose the backend / LM

`RA_BACKEND` sets the default backend:

```bash
RA_BACKEND=auto        # default: DSPy if configured, else Codex if available
RA_BACKEND=dspy        # make DSPy the persistent default
RA_BACKEND=codex       # make Codex the persistent default
CODEX_MODEL=gpt-5.4
CODEX_EFFORT=low
CODEX_TIMEOUT_SEC=600
```

Command-line flags override `.env`:

```bash
research-agent --backend dspy "use DSPy for this run"
research-agent --backend codex "use Codex for this run"
```

Anything [litellm](https://docs.litellm.ai/docs/providers) supports works in DSPy mode. Set `LM_MODEL` and the appropriate `LM_API_KEY` / `LM_API_BASE` in `.env` or the shell.

```bash
LM_MODEL=ollama/qwen3:35b                          # fully local
LM_MODEL=anthropic/claude-sonnet-4-6               # + ANTHROPIC_API_KEY
LM_MODEL=openai/gpt-4o                             # + LM_API_KEY
LM_MODEL=openai/my-local                           # + LM_API_BASE=http://localhost:8000/v1 for vLLM/llama.cpp
```

### add a tool

Any Python function with a docstring becomes a ReAct tool. The docstring is what the agent reads to decide when to call it, so write it for the agent.

```python
# mytools.py
def search_arxiv_by_author(author: str) -> str:
    """Look up papers by a specific arXiv author.

    Use this when the user mentions an author by name and wants
    their recent work, not a topic search.

    Args:
        author: Full name, e.g. "Claudia Diaz".

    Returns:
        Up to 5 papers with title, date, arXiv id, one-line abstract.
    """
    # ... your code ...
    return result_string

# then in agent.py build_agent():
from mytools import search_arxiv_by_author
return dspy.ReAct(ResearchTask, tools=[..., search_arxiv_by_author], max_iters=28)
```

### tune the cache

```bash
RA_CACHE_HIT_MIN=3                # min results to count as cache hit (default 3)
RA_CACHE_TTL_SEARCH=604800        # 7 days
RA_BYPASS_CACHE=1                 # force network for everything
RA_WORLD_KNOWLEDGE_DIR=/path      # override default ~/world_knowledge/
RA_WORLD_KNOWLEDGE=0              # disable write-through (for sandboxed runs)
```

Queries containing temporal markers (`"latest"`, `"today"`, current year) auto-bypass the cache so time-sensitive questions always hit the network.

---

## Under the hood

```
src/research_agent/
├── agent.py          legacy-compatible DSPy ResearchTask · build_agent · configure_lm
├── backends/         DSPy runner · Codex app-server runner · backend selection
├── tool_registry.py  Python-owned tool specs, validation, dispatch
├── types.py          backend-neutral ResearchResult / ToolCallRecord
├── parallel.py       backend-neutral decompose → fan-out → merge plus legacy DSPy path
├── critic.py         self-critique pass (flags fabrications, coverage gaps)
├── tools.py          every tool the agent can pick
├── log.py            per-run JSON logs in runs/
├── main.py           CLI
└── web/
    ├── providers.py  web_search (DDG + optional SearXNG), nitter_search
    ├── fetch.py      trafilatura → Jina fallback, cache, world_knowledge write
    ├── crawl.py      extract_links
    ├── knowledge.py  ~/world_knowledge/ write-through
    ├── index.py      SQLite FTS5 + local_search + reindex_knowledge
    └── canonical.py  URL normalization (RFC 3986 + tracking-param strip)
```

Every run lands in `runs/YYYYMMDD-HHMMSS-<slug>.json`. See [Research traces](#research-traces) above.

---

## FAQ

**Does this work offline?**
Partially. Your local archive and `local_search` work 100% offline. `web_search` falls back to DDG, which needs a network. An LM that's fully local (Ollama) means the only network traffic is the actual search/fetch.

**How is this different from `research-agent-exp001`?**
That repo was an experiment that evolved into [searxng-wth-frnds](https://github.com/dmarzzz/searxng-wth-frnds), which adds peer-to-peer slice replication and friend-to-friend search. This repo is the standalone agent, decoupled, zero P2P, one clear job.

**What LMs have you actually run it on?**
Codex app-server for the Codex backend; Claude Sonnet and Ollama running Qwen locally for the DSPy backend. Anything litellm supports should work in DSPy mode.

**It claims 12 tools. Why does the agent only call 3–4 per run?**
ReAct picks the minimum set. Most queries need `web_search` + `fetch_url` + `finish`. Complex research questions pull in `arxiv_search`, `verify_arxiv_citations`, `extract_links`. The tool pool matters more for breadth of coverage than per-query tool count.

**Fabricated arXiv IDs?**
The biggest single failure mode of research agents. The critic pass flags them. For extra belt-and-suspenders, call `verify_arxiv_citations(synthesis_text)` explicitly — it HEAD-checks every ID against arxiv.org.

---

## Stack

[`codex-control`](https://github.com/cybernetic-physics/codex-control) · [DSPy](https://github.com/stanfordnlp/dspy) · [trafilatura](https://trafilatura.readthedocs.io/) · [ddgs](https://pypi.org/project/ddgs/) · [arxiv.py](https://github.com/lukasschwab/arxiv.py) · [litellm](https://github.com/BerriAI/litellm) (via DSPy) · SQLite FTS5

## License

MIT. See [LICENSE](LICENSE).
