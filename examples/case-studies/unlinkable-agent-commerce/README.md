# Case study: unlinkable agent commerce in 2026

An end-to-end example of using `research-swarm` for a real research workstream:
two swarm queries, downstream `content-pipeline` fanout to three formats,
all five outputs preserved as published.

This is a heavier example than the snippets in `examples/`. The
single-file Python examples there show *how* to call the swarm. This case
study shows *what one workstream looks like* when you actually use the
swarm to drive a multi-format research artifact.

## The workstream

The author was preparing a foundational reference on the privacy posture
of AI-agent commerce in 2026: anonymous credentials, network-layer
anonymity, agent payment protocols, and the API-workload taxonomy that
sits underneath all of them. Two distinct research questions, one survey-
shaped, one taxonomy-shaped.

### Step 1: Swarm queries

Both runs used the OpenAI `gpt-4.1` model via the field-kit `rotate`
launcher.

```bash
# Big survey, parallel STORM decomposition into 4 sub-questions
rotate research --parallel "For a 2026 research artifact on unlinkable
agent commerce and machine payments, produce a deep survey covering four
areas: (1) network-layer anonymity systems (DC-nets, mixnets, HOPR),
(2) anonymous credential schemes that carry spendable state (ACT, ZK API
Credits, Boomerang, batched Privacy Pass, Coconut), (3) agent commerce
protocols and identity defaults (x402, MPP, ERC-8004, MCP, A2A, AP2),
(4) agentic search and AI inference as workloads. Today is May 14 2026."

# Focused single-mode taxonomy query
rotate research "Is there a formal framework or taxonomy for describing
API workload profiles, particularly in the context of which workloads
are amenable to unlinkable or anonymous payment vs which require
persistent identity? ..."
```

Resulting traces under `./swarm-traces/`:

- `survey-parallel.json` (~18 KB): the four-area decomposition with 17
  sources and a critique pass
- `taxonomy-single.json` (~10 KB): the taxonomy framework question with
  3 sources and a critique pass

### Step 2: Synthesis

Trace synthesis was used as one input among several. The author also ran
parallel Claude subagents for deeper-context research where the swarm's
single-model budget wasn't enough. Both informed the canonical artifact
at `./unlinkable-agent-commerce.md` (~6,700 words).

This is worth saying: the traces are real, complete, illustrative of
what the swarm produces, and useful inputs to the synthesis. They are
not the only inputs. A research artifact at this length and depth
typically combines several research substrates.

### Step 3: Content-pipeline fanout

The artifact was then passed through `content-pipeline` to produce three
derivative formats:

```bash
rotate content --markdown unlinkable-agent-commerce.md \
  --slug unlinkable-agent-commerce \
  --formats all
```

The pipeline's `NEXT.md` instruction file told format-specific agents to
execute three prompts (blog, explainer-video, tweet-thread), each
reading the artifact and the aesthetic. Outputs:

- `./blog.md`: 2,100-word dual-layer blog post with collapsible
  `<details>` source-citation blocks
- `./explainer-video.html`: 37 KB self-contained scrollytelling HTML,
  eight panels, CSS animations, no external dependencies
- `./tweet-thread.md`: 11 tweets, video-paired, distribution-shaped

## What this case study shows

For people reading this in the `research-swarm` repo:

1. **Trace structure in the wild.** Open
   `./swarm-traces/survey-parallel.json` to see what a complete parallel
   STORM run looks like, including the sub-question decomposition, per-
   sub-question synthesis, critique pass, and source list.

2. **Trace as content-pipeline input.** The trace JSON schema is also
   the input format `content-pipeline` consumes. See the pipeline's
   `adapters/from_research_trace.py` for the schema.

3. **The author's voice and aesthetic.** The blog and video both honor
   the same content-pipeline aesthetic (default: conversational-
   analytical voice, paper-toned visual palette, single accent color
   reserved for load-bearing markings). Use this as a reference for
   what content-pipeline output looks like end-to-end.

## Files

```
./
├── README.md                          # this file
├── unlinkable-agent-commerce.md       # the canonical research artifact
├── blog.md                            # 2,100-word blog distillation
├── explainer-video.html               # 8-panel scrollytelling, 37 KB
├── tweet-thread.md                    # 11 tweets
└── swarm-traces/
    ├── survey-parallel.json           # STORM-decomposed survey trace
    └── taxonomy-single.json           # single-mode taxonomy trace
```

## How to reproduce

Reproducing exactly requires the same model weights and the same web
state on the day of the run. The model identifiers and prompt text
are preserved verbatim in each trace JSON under
`question` and the various sub-question fields. Sources are pinned with
URLs and access dates.

To run the swarm against the same questions yourself:

```bash
git clone https://github.com/dmarzzz/research-swarm.git
cd research-swarm
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env
# add LM_MODEL=openai/gpt-4.1 and LM_API_KEY=sk-... (or any litellm provider)

# survey
research-agent --parallel "$(cat <<'EOF'
For a 2026 research artifact on unlinkable agent commerce and machine
payments, produce a deep survey covering four areas: ... [see traces/]
EOF
)"
```

You will get different sources, slightly different sub-question
decomposition, and a different synthesis. The trace shape will be
identical to what's checked in here.
