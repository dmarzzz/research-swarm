---
source_blog: blog.md
video: explainer-video.html
aesthetic: _pipeline-snapshot/aesthetic/default.yaml
generated_by: content-pipeline/formats/tweet-thread
tweet_count: 11
---

## tweet 1
ERC-8004 hit Ethereum mainnet in January. 22,900 agents registered in three days. x402 is doing ~$600M annualized across Base and Solana, with Coinbase facilitating over half. All of it assumes the agent on the other side of a paid call has a stable on-chain identity.

## tweet 2
Agent commerce is a four-layer stack. L1 network (mixnets, DC-nets). L2 credential (ACT, Privacy Pass, Coconut). L3 protocol/identity (x402, MPP, ERC-8004, MCP, AP2). L4 the workload itself. The privacy literature lives at L2. The industry conversation lives at L3.

## tweet 3
The deepest threats in 2026 sit at the other two layers. L1, where network metadata leaks even when payment crypto is perfect. L4, where the request itself proves who you are no matter how the payment was authenticated. The papers and protocol drafts are looking elsewhere.

## tweet 4
Each layer is reasonable alone. x402 inside MPP inside an ERC-8004 reputation entry inside an AP2 mandate produces a permanent, queryable record of every agent action with the buyer address attached. No single layer is to blame, which is why no single layer fixes it.

## tweet 5
The actual contribution: a 10-dimension workload taxonomy that scores an API spec for anonymity amenability before you pick a payment substrate. Session shape, idempotency, correlatability, side-effects, temporal profile, payload, pricing, identity, reputation, content.

## tweet 6
D9 (reputation) and D10 (content fingerprintability) are the ones cryptographers underweight. No credential design fixes a hard reputation gate. No payment unlinkability survives a multi-turn chat that leaks a personal corpus. The breakers live in the workload, not in the wire.

## tweet 7
Agentic web search scores anonymity-friendly on every dimension. One Perplexity Deep Research query visits 100+ pages across Exa, Perplexity, OpenAI, Anthropic, dozens of sites. Sub-cent per leaf, already production. If any 2026 workload should be private by default, this is it.

## tweet 8
Two open problems. ERC-8004's optional `proofOfPayment` field welds x402 receipts into the reputation graph; it should not be the default. ACT under t-of-n threshold issuance (Coconut-shaped) removes the single-issuer compulsion gap that makes today's ACT a centralized rail.

## tweet 9
The threat I'm most worried about, least confident anyone solves in twelve months: stylometric de-anonymization of inference prompts. For LLM inference the prompt is sufficient for re-identification regardless of payment scheme. Anonymous payment is partial until that closes.

## tweet 10
I made a short animated explainer of the four layers and the taxonomy: <EXPLAINER_VIDEO_URL>

## tweet 11
The default that crystallizes in the next two quarters is the default for the next decade. The wiring is mostly mechanical, mostly unclaimed, mostly in the open. Whether agent SDKs rotate source identifiers per request or cache per session is the work. Full post: <BLOG_URL>
