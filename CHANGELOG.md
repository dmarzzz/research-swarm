# Changelog

## 0.1.1 — polish pass

- Welcome screen when `research-agent` is run without a question (replaces the argparse error wall).
- Friendly error when the LM isn't configured, with three copy-paste paths to a working setup.
- Live tool-call trace visible on stderr during a run. Every tool the agent picks, with args + latency + first line of the result. Suppress with `--quiet` or `RA_QUIET=1`.
- Banner at run start showing mode + question.
- Rewritten synthesis/sources/critique rendering: boxed synthesis, grounding score as filled circles, colored verdicts. Auto-disables ANSI when not a terminal or when `NO_COLOR` is set.
- `--version` flag.
- `examples/hello.py` and `examples/custom_tool.py` to shorten the path from clone to first demo.
- README rewritten around a 30-second tour and a clear "what actually happens" diagram.

## 0.1.0 — initial release

- DSPy ReAct agent with ~12 tools (local + web + arXiv + Semantic Scholar + GitHub + Nitter + deep-read primitives + citation verifier).
- Single and parallel (STORM) modes.
- Self-critique pass.
- trafilatura + Jina fetch pipeline, 7-day cache, write-through to `~/world_knowledge/`.
- SQLite FTS5 local index.
- DDG + optional SearXNG search providers; no API keys required.
- Temporal-marker auto-bypass for time-sensitive queries.
- Per-run JSON logs in `runs/`.
