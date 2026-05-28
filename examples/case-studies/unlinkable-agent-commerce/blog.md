---
title: "The privacy fight for agent commerce is not where the papers are looking"
date: 2026-05-14
source: source.md
aesthetic: _pipeline-snapshot/aesthetic/default.yaml
generated_by: content-pipeline/formats/blog
---

ERC-8004 Trustless Agents hit Ethereum mainnet on January 29. By the end of the first three days, 22,900 agents had registered. In a different corner of the same stack, x402 is now doing roughly $600M annualized in transaction volume across Base and Solana, and a single facilitator, Coinbase, sits on more than half of that graph. None of these systems existed in their current form six months ago. All of them assume, by default, that the agent on the other side of a paid API call has a stable on-chain identity.

That assumption is the load-bearing one. The default that crystallizes by end of 2026 is the default for the next decade of agent commerce, and right now the default is hardening in the direction of attribution-by-construction. The cryptographic primitives to do better all exist. They do not yet talk to each other, and most of the conversation about wiring them together is happening at the wrong layer.

<details>
<summary>source</summary>

<source-citation>
"~22,900 registrations in first three days; Base / L2 expansion followed." On x402: ">119M transactions on Base, ~35M on Solana, ~$600M annualized volume... Coinbase facilitates >50% of volume."
Source: <a href="https://eips.ethereum.org/EIPS/eip-8004">EIP-8004: Trustless Agents</a> and <a href="https://x402.org">x402.org</a>, accessed 2026-05-13
</source-citation>

<source-reasoning>
Both numbers anchor the framing claim that the agent-commerce stack is consolidating around identity-by-default protocols at production volume, not at experimental scale.
</source-reasoning>
</details>

The rest of this post argues three things. First, that the privacy discourse is concentrated at the wrong layers of a four-layer stack. Second, that composition is doing more de-anonymization work than any single protocol, which is why protocol-by-protocol audits keep coming up clean while the resulting transaction graph remains a surveillance dataset. Third, that a ten-dimensional workload taxonomy lets a designer score an API spec for anonymity amenability before picking a payment substrate. The taxonomy is the piece I have not seen elsewhere, and it changes which problems are worth working on.

## Four layers, and the discourse is on the wrong two

Treat agent commerce as a stack:

- Layer 1, network. DC-nets, mixnets, anonymous broadcast.
- Layer 2, credential. ACT, ZK API Credits, Boomerang, Coconut, batched Privacy Pass, ARC.
- Layer 3, protocol and identity. x402, MPP, ERC-8004, MCP, A2A, AP2.
- Layer 4, workload. The API itself: what is being paid for, and how its content, sessions, and identity coupling leak.

The privacy literature lives almost entirely at Layer 2. The industry conversation lives almost entirely at Layer 3. Layer 1 has one production-deployed incentivized mixnet (HOPR) that nobody in the agent-commerce orbit talks about, plus a research-grade construction (ZIPNet, and Flashbots' Flashnet derivation of it) that is not yet framed as a payment-transport layer. Layer 4 has no integrated taxonomy at all; the dimensions that matter for it (content fingerprintability, reputation accumulation, cross-request correlatability) are absent from every existing workload framework I can find.

The deepest threats to anonymous agent commerce in 2026 are not where the papers are looking. They are at Layer 1, where metadata leaks even when payment crypto is perfect, and at Layer 4, where the request itself proves who you are regardless of how the payment was authenticated.

<details>
<summary>source</summary>

<source-citation>
"every existing piece of literature on anonymous payments focuses on Layer 2. Almost all of the agent-commerce industry conversation is at Layer 3. The deepest threats in 2026 are at Layer 1 (network metadata) and Layer 4 (workload structure and content)."
Source: <a href="./unlinkable-agent-commerce.md">Unlinkable Agent Commerce in 2026, accessed 2026-05-13</a>
</source-citation>

<source-reasoning>
This is the central inversion the artifact argues for, and the reason the rest of the post weights Layer 1 and Layer 4 more heavily than the existing discourse does.
</source-reasoning>
</details>

## Composition is the surveillance dataset

Trace a single agent action through the 2026 stack. The agent pays via x402, so its on-chain address is visible to the merchant and the facilitator. The call is wrapped in an AP2 mandate, signed end-to-end as a verifiable credential, because the user wants a "tamper-proof log of user-authorized agent actions." The agent's identity is in the ERC-8004 Identity Registry, and the call may emit a reputation entry whose optional `proofOfPayment` field ties the on-chain receipt directly into the reputation graph. The call moves over A2A or MCP, both of which publish discoverable agent metadata at well-known endpoints.

Every layer here is reasonable on its own. x402 is excellent at its job. MPP's draft spec is unusually privacy-forward: "Servers MUST NOT require user accounts for payment. Payment methods SHOULD support pseudonymous options where possible." ERC-8004 is the right shape for a trust-minimizing identity registry. AP2 buys exactly the audit guarantees a regulated payments rail needs. The composition, x402 inside MPP inside an ERC-8004 reputation entry inside an AP2 mandate, is what produces a permanent, queryable record of every agent action with the buyer address attached. No one layer is to blame, which is also why no one layer is going to fix it.

<details>
<summary>source</summary>

<source-citation>
"x402 inside MPP inside an ERC-8004 reputation entry inside an AP2 mandate produces a permanent, queryable record of every agent action with the buyer address attached. Each layer is reasonable on its own. The composition is the surveillance dataset of the late 2020s."
Source: <a href="./unlinkable-agent-commerce.md">Unlinkable Agent Commerce in 2026, accessed 2026-05-13</a>
</source-citation>

<source-reasoning>
This is the artifact's framing of the structural problem: composition, not protocol, is the threat. I lean on it because it explains why protocol-level privacy audits keep clearing the same systems whose composed transaction graph is the surveillance vector.
</source-reasoning>
</details>

A sharper version of the point lands on AP2 specifically. AP2 just moved to the FIDO Alliance with 60+ orgs in tow, and its mandate model, "Verifiable Intent through Mandates," is identity-by-construction. There is no anonymizable variant of an AP2 mandate that preserves its audit guarantees. If AP2 becomes the dominant authorization layer, the privacy work has to happen *under* it, in the payment method or the rail itself, not at the mandate layer. That is a substantial constraint on what the privacy work is even allowed to look like.

<details>
<summary>source</summary>

<source-citation>
"AP2 is fundamentally incompatible with unlinkable credentials. There is no anonymizable variant of an AP2 mandate that preserves its audit guarantees."
Source: <a href="https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol">Google AP2 announcement, accessed 2026-05-13</a>; analysis from <a href="./unlinkable-agent-commerce.md">source.md</a>
</source-citation>

<source-reasoning>
AP2's mandate model is structurally inconsistent with unlinkability. This constrains where in the stack any privacy work can land and is the reason "fix AP2" is not a viable plan.
</source-reasoning>
</details>

## The ten dimensions that decide whether anonymity is possible at all

This is the part I think is the actual contribution. Every Layer 2 paper asks whether the payment credential is unlinkable. Almost nobody asks whether the workload it pays for is unlinkable. They are different questions, and the second one is the binding constraint in production. Ten dimensions, each separately measurable, each separately remediable.

1. **Session shape.** Atomic, cursor-bound, session-bound, account-bound. Atomic and cursor-bound are anonymous-payment-native. Account-bound is where anonymity collapses.
2. **Idempotency class.** Safe, idempotent, non-idempotent. Non-idempotent calls force idempotency keys, which are correlation bait.
3. **Cross-request correlatability.** Uncorrelatable, weakly correlatable, deterministically linked. A streaming chat that holds an SSE channel open is deterministically linked over the channel's lifetime no matter how the bytes are paid for.
4. **Side-effect locus.** Pure-read, merchant-internal-write, externally-side-effecting. Anonymity does not wash through a downstream KYCed system.
5. **Temporal profile.** Sub-second, seconds, minutes, detached-batch. Detached-batch is great for unlinkability if the job handle is bearer-only.
6. **Payload size.** KB, MB, GB+. Payload size is a fingerprinting channel under TLS.
7. **Pricing-unit granularity.** Per-request, per-resource-consumed, per-time, per-outcome. Per-request maps cleanly onto one anonymous token per call. Per-time and per-outcome are hard to do anonymously without losing the property.
8. **Identity coupling.** Identity-free, pseudonym-tolerant, stable-pseudonym-required, verified-identity-required. Pfitzmann-Hansen's pseudonymity ladder, restated for APIs.
9. **Reputation-accumulation dependence.** None, soft, hard. The dimension every cryptographer working on payment unlinkability underweights. Reputation systems are the anti-anonymity force in production APIs.
10. **Content-fingerprintability.** Low, medium, high. If the *content* proves two requests came from the same agent, payment unlinkability is theater.

<details>
<summary>source</summary>

<source-citation>
"It claims that ten dimensions are sufficient to predict, from an API spec, whether a workload is a clean fit for query-atomic anonymous payment, a recoverable fit with specific protocol additions, or identity-dominated... Cryptographically unlinkable payment is necessary but not sufficient: if the content proves two requests came from the same agent, payment unlinkability is theater."
Source: <a href="./unlinkable-agent-commerce.md">Unlinkable Agent Commerce in 2026, accessed 2026-05-13</a>
</source-citation>

<source-reasoning>
The taxonomy is the artifact's load-bearing original contribution. I am summarizing the ten axes here at the level a designer can apply them with, and pulling forward D9 and D10 as the dimensions the existing discourse most underweights.
</source-reasoning>
</details>

Score any API on those ten and three clusters emerge. Agentic web search, public-corpus RAG, read-only MCP tool calls: every dimension lands in the anonymity-friendly value. These are the workloads the agentic web should default to identity-free for. Single-turn LLM completions, file uploads with bearer handles, generic batch inference: the payment layer can be anonymous, but a second mechanism (bearer handles, prepay-with-refund tokens, content padding) has to do real work. A DEX trade, or an MCP tool call that sends an email, is identity-dominated by construction. Anonymous payment at the API edge there is cosmetic. The downstream system already knows who you are.

The clean read of this is that **D9 (reputation) and D10 (content fingerprintability) are the dimensions the cryptography literature is least equipped to address.** No amount of credential design fixes a hard reputation gate. No payment unlinkability survives a multi-turn chat that reveals a personal corpus across turns. Those are the breakers, and they live in the workload, not in the wire.

## The canonical workload is already in production

Score agentic web search against the taxonomy: D1 atomic, D2 safe, D3 uncorrelatable, D4 pure-read, D5 sub-second per leaf, D6 KB, D7 per-request, D8 identity-free, D9 none, D10 medium. Every dimension lands in the anonymity-friendly value.

This is not a hypothetical. A single Perplexity Deep Research query takes two to five minutes and visits 100+ web pages, at fractions of a cent per leaf, touching Exa, Perplexity, OpenAI, Anthropic, and dozens of source websites in one cross-merchant traversal. The micropayment volume is real and growing fast. The cryptographic primitives to make it private exist (ACT is in a Cloudflare prototype as of October 2025; batched Privacy Pass is in IETF WG Last Call; ZK API Usage Credits has a testnet implementation in 4Mica). The transport primitives exist (Nym is in production GA, Flashnet is the credible sub-second path). The standards conversation has not yet wired them together.

If any class of paid API traffic in 2026 should be private by default, it is agentic search. It is also the workload whose default is about to be set by the SDKs being written this quarter.

<details>
<summary>source</summary>

<source-citation>
"A Deep Research query takes 2–5 minutes and visits 100+ web pages... Perplexity web search $0.005/call, URL fetch $0.0005/call. Micropayment-native. Cross-merchant by design."
Source: <a href="https://docs.perplexity.ai/docs/agent-api/quickstart">Perplexity Agent API docs, accessed 2026-05-13</a>
</source-citation>

<source-reasoning>
Anchors the claim that agentic search is the canonical native workload at production volume, not a thought experiment. The cross-merchant traversal is precisely the shape that benefits from anonymous payment.
</source-reasoning>
</details>

## What I think is actually worth working on

A few claims with varying confidence.

The most consequential industry signal in the open right now is Cloudflare shipping ACT on MCP before the IETF Privacy Pass process completes. If Anthropic, Cloudflare, and Google converge on MCP-with-anonymous-credentials, the credential layer consolidates before the payment layer settles, and the integration target for any serious anonymous-credential work becomes MCP, not x402 or MPP. That is a different bet than most of the agent-commerce ecosystem is making.

<details>
<summary>source</summary>

<source-citation>
"The Cloudflare ACT demo runs on MCP. This is more important than it reads. Cloudflare is treating MCP as the de facto substrate for AI-agent rate-limited access... and shipping anonymous credentials on top before the IETF Privacy Pass process completes."
Source: <a href="https://blog.cloudflare.com/private-rate-limiting/">Cloudflare, "Anonymous credentials: rate-limiting bots and agents," accessed 2026-05-13</a>
</source-citation>

<source-reasoning>
Cloudflare's choice of MCP as the demo substrate is the strongest current signal that the credential layer is consolidating around MCP rather than around the payment-protocol families. This drives the recommendation about integration target.
</source-reasoning>
</details>

The cleanest research direction nobody is working on in the open is bringing ACT's credit-bearing semantics into Coconut-shaped *t-of-n* threshold issuance. ACT today is single-issuer-and-origin, which is the right shape for a Cloudflare deployment and the wrong shape for an open agent-commerce rail. Threshold-issued ACT removes the single-issuer compulsion gap (a court order against one issuer cannot reconstruct the spend history) and the revenue concentration that makes single-issuer ACT a centralized rail by default.

I am less certain about the path for network-layer transport. Generalizing Flashnet from transaction broadcast to per-query API payments is plausibly small technical work (the round-based DC-net abstraction is payload-agnostic) and the latency budget for agent payments is slightly looser than for block-building. The hard part is cover-traffic economics: who pays for it, in what currency, with what incentive compatibility. HOPR has working answers and the Loopix lineage mostly does not. I am not yet confident the economics close, and the right move is to take HOPR's probabilistic-payment ticket design seriously as prior art rather than reinventing it inside a Flashbots writeup.

The threat I am most worried about, and least confident anyone will solve in the next twelve months, is stylometric de-anonymization of inference prompts. Every Layer 2 paper is about payment unlinkability. Every Layer 3 protocol is about identity at the wire level. For AI inference, the prompt content is sufficient for re-identification regardless of payment scheme, and there is no production-ready story for prompt-stylometry-resistant inference. Anonymous payment for inference is a partial answer at best until that gap closes.

<details>
<summary>source</summary>

<source-citation>
"The single most underweighted threat in the entire stack. Every paper in Layer 2 is about payment unlinkability. Every protocol in Layer 3 is about identity at the wire level. For AI inference workloads specifically, the content of the prompt is sufficient for re-identification regardless of payment scheme."
Source: <a href="./unlinkable-agent-commerce.md">Unlinkable Agent Commerce in 2026, accessed 2026-05-13</a>
</source-citation>

<source-reasoning>
This is the open problem I am most confident is real and least confident has a clean solution path. It is also the dimension D10 collapses onto for the most economically important workload (LLM inference), which is why it deserves to be flagged separately.
</source-reasoning>
</details>

## Caveats and where my confidence runs out

The ten dimensions are not fully orthogonal. D1 and D8 are correlated in practice; D6 and D10 are correlated for content-rich workloads. I claim they are separately measurable and separately remediable, which is what matters for design. I do not claim they form a basis.

The Crapis-Buterin v2 ZK API Usage Credits construction has an unstated re-randomization requirement that surfaces only in the ethresear.ch comment thread. Without per-submission re-randomization, the server can chain commitments across requests and re-link them. Re-randomization in turn requires the server's signature to survive re-blinding, which pushes the construction back to BBS+. The original post does not state this; the design is load-bearing only with the comment-thread amendment. A clean v3 spec is the right deliverable, and I do not yet see one.

Flashnet is not yet a payment-transport layer. The February 2026 writeup targets transaction broadcast for the Flashbots block-building pipeline. The reuse-for-machine-payments framing is exactly the open question, not a settled answer.

I am not addressing how regulators interact with any of this. A meaningful fraction of the workloads I have called identity-dominated are that way because of KYC and AML constraints downstream, and the design space for anonymous payment at the API edge ends abruptly when it hits a regulated rail. That is the binding constraint on how much of agent commerce can be made unlinkable at all, and this post does not address it.

## Where this leaves the next two quarters

The integrations that crystallize in the next two quarters are the ones that get embedded into agent SDKs, merchant defaults, and reputation registries. After that, the cost of changing the default rises sharply. The cryptographic and transport primitives to make the default privacy-respecting all exist; they do not yet talk to each other; the wiring is mostly mechanical, mostly unclaimed, and almost entirely in the open. The most consequential implementation choice an SDK author is going to make this quarter is whether their library rotates source identifiers per request or caches them per session. The MPP spec is silent on persistence. SDKs cache by default. That single line of code, in the agent SDKs being written right now, will determine the cross-merchant linkability of the agentic web for years. The workloads where it matters most are already in production. The choice of default is the work.
