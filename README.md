# research-swarm

A DSPy-based research agent. Takes a question, researches it across web / arXiv / GitHub / Semantic Scholar / Wikipedia, and produces a grounded synthesis with inline citations.

Two modes:

- **Single**: one ReAct loop iterates with tools until it has the answer.
- **Parallel** (`--parallel`): STORM-inspired. Decompose into sub-questions, run a ReAct loop per sub-question concurrently, merge the syntheses.

Every fetched page is extracted with `trafilatura` (local, no intermediary), cached for 7 days, and written through to `~/world_knowledge/`. Repeat queries short-circuit to the local cache without hitting the network.

Self-sovereign by default: no API keys required. DuckDuckGo is the free fallback; optionally point at a self-hosted SearXNG via `SEARXNG_URL` if you want more engines.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure an LM (any litellm provider)
cp .env.example .env
# Fully-local:  LM_MODEL=ollama/qwen3:35b
# Remote:       LM_MODEL=anthropic/claude-sonnet-4-6 + LM_API_KEY=sk-ant-...
```

## Usage

```bash
# single ReAct loop
research-agent "What is Loopix and how does it compare to Tor?"

# parallel fan-out (decompose → research sub-questions → merge)
research-agent --parallel "Survey the design space of anonymous communication systems"

# skip the self-critique pass
research-agent --no-critique "your question"
```

Every run is saved to `runs/YYYYMMDD-HHMMSS-<slug>.json` with the question, synthesis, sources, and self-critique. Review + curate these, and once you have ~20 accepted examples you can compile the agent with `dspy.teleprompt.MIPROv2` for better-tuned prompts (out of scope for this repo; see DSPy docs).

## Tools the agent can call

| tool | what it does | keys required |
|---|---|---|
| `local_search` | SQLite FTS5 over the content you've already fetched | none |
| `web_search` | DDG + optional SearXNG, with local cache short-circuit | none |
| `expanded_search` | LM expands the question → queries → fan-out → LM rerank | just your LM |
| `arxiv_search` / `arxiv_fetch_paper` | arXiv API + full-paper fetch | none |
| `semantic_scholar_search` | broader than arXiv, with citation counts | optional `SEMANTIC_SCHOLAR_API_KEY` |
| `github_search` | GitHub repo search | optional `GITHUB_TOKEN` (raises rate limit) |
| `nitter_search` | Twitter/X via open-source Nitter | none (public) or `NITTER_URL` |
| `fetch_url` / `fetch_urls_parallel` | trafilatura → Jina fallback, paginated + cached + archived | none |
| `extract_links` | link map from a page for one-hop follow-up | none |
| `verify_arxiv_citations` | HEAD-check every arXiv ID in a text to catch fabrications | none |

## Layout

```
src/research_agent/
├── __init__.py            # load_dotenv
├── __main__.py            # `python -m research_agent "..."` entry
├── main.py                # CLI
├── agent.py               # ResearchTask signature + build_agent (ReAct)
├── parallel.py            # decompose-fan-out-merge (STORM)
├── critic.py              # self-critique pass
├── tools.py               # DSPy tool adapters
├── log.py                 # JSON run logs
└── web/
    ├── providers.py       # web_search (DDG + optional SearXNG), nitter_search
    ├── fetch.py           # trafilatura → Jina fallback, cache, world_knowledge
    ├── crawl.py           # extract_links
    ├── knowledge.py       # world_knowledge/ write-through
    ├── index.py           # SQLite FTS5 + local_search + reindex_knowledge
    └── canonical.py       # URL canonicalization

examples/
└── seed_questions.py      # test questions covering different research shapes

tests/
└── test_canonical.py      # URL canonicalization tests
```

## How it works, at a glance

The DSPy `ReAct` module picks a tool per turn based on the tool's docstring. On each iteration it can search, fetch, verify, or finish. The loop caps at `MAX_ITERS` (default 28). Every `fetch_url` call:

1. Opens the on-disk cache (7-day TTL)
2. Cache miss: raw HTML → trafilatura local extraction
3. If trafilatura returns empty (PDFs, SPAs, paywalls), fall through to Jina Reader
4. Write the clean markdown to `~/world_knowledge/web/<domain>/<YYYY-MM-DD>-<slug>.md` with YAML frontmatter
5. Index into SQLite FTS5 so `local_search` finds it forever

Every `web_search` call:

1. If the query has temporal markers ("latest", "today", year), bypass cache, hit network
2. Otherwise check the query-hash cache (7 days, ≥3 rows to count as a hit)
3. Cache miss: fan out to DDG + SearXNG (if configured), merge + dedup by canonical URL, cache for next time

Grounding rules live in `ResearchTask`'s signature docstring and are strict about citations. The critic pass scores the synthesis 1–5 and flags fabricated arXiv IDs; `verify_arxiv_citations` HEAD-checks every ID against arxiv.org.

## Stack

- **[DSPy](https://github.com/stanfordnlp/dspy)** — ReAct + signatures
- **[trafilatura](https://trafilatura.readthedocs.io/)** — local HTML → markdown extraction
- **[ddgs](https://pypi.org/project/ddgs/)** — DuckDuckGo (zero-key fallback)
- **[arxiv.py](https://github.com/lukasschwab/arxiv.py)** — arXiv client
- **[litellm](https://github.com/BerriAI/litellm)** (via DSPy) — LM provider abstraction
- **SQLite FTS5** (stdlib) — the local index

## Tests

```bash
pip install -e '.[dev]'
pytest -q
```
