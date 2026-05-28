# Unlinkable Agent Commerce in 2026

### Stack, Workloads, Open Problems

*dmarz · 2026-05 · research artifact on unlinkable agent commerce*

> Research traces: `dmarzzz/research-swarm` parallel + single runs, included under `./swarm-traces/`. Graphics: hand-rolled Remotion compositions (in the canonical version of this artifact; not included in this example).

## Companion formats

This artifact has three derivative formats produced by the `content-pipeline` pass on 2026-05-14. They share the canonical source and are intended for different reading modes.

| Format | Path | For |
|---|---|---|
| Blog post (2,100 words, dual-layer with source-citation `<details>` blocks) | [`blog.md`](./blog.md) | The skimmable distillation with provenance reachable inline |
| Explainer video (8 scrollytelling panels, self-contained HTML, 37 KB) | [`explainer-video.html`](./explainer-video.html) | 60 to 180 seconds of read time; the visual summary |
| Tweet thread (11 tweets, video-paired) | [`tweet-thread.md`](./tweet-thread.md) | Distribution; tweet 1 stands alone |

This artifact is the canonical reference. The blog is the writing the artifact compresses to. The video is the structure the artifact walks. The thread is the share-shaped surface.

## At a glance

The video's eight panels map this artifact's structure end to end. Use as a navigation aid:

1. **Crystallization year** (§1). Three production-volume signals: x402 at ~$600M annualized; ERC-8004 with ~22,900 agents in its first three days; AP2 to FIDO in April.
2. **Four-layer stack** (§2). Network, credential, protocol, workload. Independent layers; composite privacy is the conjunction.
3. **Discourse vs. threat** (§§3-6). Research attention concentrated at L2; industry conversation concentrated at L3; the deepest threats are at L1 and L4.
4. **Workload taxonomy** (§6). Ten dimensions, three clusters: native / recoverable / identity-dominated.
5. **Agentic search as canonical native workload** (§7). Why it scores anonymity-friendly on every dimension.
6. **Open problems** (§8). Eight, with the ERC-8004 `proofOfPayment` field and ACT-of-N threshold issuance as highest-leverage open.
7. **Reference design** (§9). One credible wiring: ACT-on-BBS over Flashnet plus Nym SURB.
8. **Takeaway**. 2026 is the crystallization year; the cryptographic and transport primitives all exist; nobody has wired them.

## Abstract

AI agent commerce is consolidating in 2026 on protocols and registries that default to persistent on-chain identity. Stripe and Tempo's Machine Payments Protocol shipped in March. Coinbase and Cloudflare's x402 moved to the Linux Foundation in April. Google and Mastercard's AP2 went to FIDO the same month. ERC-8004 Trustless Agents has been on Ethereum mainnet since January with twenty-plus thousand registered agents. Most of these protocols are excellent at what they do; few of them treat unlinkability as a first-class property.

This artifact does three things. First, it surveys the four-layer stack of agent commerce as it exists today, with attention to where each layer leaks identity and where it admits anonymity. Second, it introduces a ten-dimensional taxonomy of API workload profiles that classifies which workloads can be served against query-atomic anonymous payment, which can be served with care, and which are identity-dominated by construction. Third, it identifies eight open problems whose solution would meaningfully change the privacy posture of agent commerce by end of 2026.

The artifact is intentionally not a protocol proposal. It is reference material for the Flashbots research workstream on DC-nets, agentic search, and AI inference, and for the conversations between Privacy Pass, Ethereum Foundation, Flashbots, and the agent-commerce ecosystem that have not yet happened.

## 1. Framing: the crystallization year

Three observations.

**The default is hardening.** Five months ago none of MPP, the Linux Foundation x402, mainnet ERC-8004, FIDO AP2, or shipped ACT prototypes existed in their current form. They do now. The transaction graph that emerges from their composition is *additively de-anonymizing*: x402 inside MPP inside an ERC-8004 reputation entry inside an AP2 mandate produces a permanent, queryable record of every agent action with the buyer address attached. Each layer is reasonable on its own. The composition is the surveillance dataset of the late 2020s.

**The primitives to prevent that exist.** Anonymous Credit Tokens (ACT) is being prototyped by Cloudflare and Google. The Crapis-Buterin ZK API Usage Credits proposal landed on ethresear.ch in February. Coconut credentials are in production inside NymVPN since March 2025. Flashbots' Network-Anonymized Mempools writeup shipped in February with ZIPNet-derived anonymous broadcast targeting low latency. None of these is yet wired to the others.

**The window is now.** The integrations that crystallize in the next two quarters are the ones that get embedded into agent SDKs, merchant integrations, and reputation registries. After that the cost of changing the default rises by an order of magnitude per quarter.

The contribution of this artifact is not a new protocol. It is a map of where the pieces are and what fits with what, plus a workload-side taxonomy that lets a designer score an API spec for anonymity amenability before integrating any payment substrate.

## 2. The four-layer model

For the rest of this artifact I treat agent commerce as a four-layer stack. The layers are independent: a deployment can be private at one layer and leaky at another. The composite privacy property is the conjunction.

```
   +-----------------------------------------------+
   |  Layer 4 | Workload                           |   the API itself: what is being paid for,
   |  (taxonomy in §6)                             |   how content/sessions/identity leak
   +-----------------------------------------------+
   |  Layer 3 | Protocol and identity              |   x402 / MPP / ERC-8004 / MCP / A2A / AP2
   |  (§5)                                         |
   +-----------------------------------------------+
   |  Layer 2 | Credential                         |   ACT, ZK API Credits, Boomerang, Coconut,
   |  (§4)                                         |   ARC, batched Privacy Pass
   +-----------------------------------------------+
   |  Layer 1 | Network                            |   DC-nets, mixnets, anonymous broadcast,
   |  (§3)                                         |   incentivized cover traffic
   +-----------------------------------------------+
```

The reader's tempo prediction matters: every existing piece of literature on anonymous payments focuses on Layer 2. Almost all of the agent-commerce industry conversation is at Layer 3. The deepest threats in 2026 are at Layer 1 (network metadata) and Layer 4 (workload structure and content). The shape of this artifact is therefore upside-down relative to the existing discourse: more weight on 1 and 4, less on 3, treating 2 as well-trodden ground that the new work has to bridge.

## 3. Layer 1: Network-layer anonymity

Two design families and one production system.

### 3.1 DC-net lineage

Chaum's 1988 Dining Cryptographers protocol sets the security ceiling: information-theoretic sender anonymity against an adversary that watches every wire. Every modern revival trades some of that ceiling for tractability.

| System | Family | Threat model | Latency | Anonymity set | TEE? | Deployment |
|---|---|---|---|---|---|---|
| Dissent (Wolinsky et al., OSDI 2012) | DC-net + verifiable shuffle | active disruptor | seconds | round-bounded | no | research |
| Verdict (Corrigan-Gibbs et al., USENIX 2013) | DC-net + NIZK | identifies disruptors | seconds | round-bounded | no | research |
| Riposte (Corrigan-Gibbs et al., S&P 2015) | DC-net (PIR-style) | 1-of-3 honest server | ~hours batch | up to ~2.9M users | no | research |
| Riffle (Kwon et al., PETS 2016) | hybrid DC-net + mix | anytrust | seconds-to-minutes | round-bounded | no | research |
| Atom (Kwon et al., SOSP 2017) | DC-net + mixnet | anytrust + active | ~28 min / 1M msgs at 1024 servers | system-wide | no | research |
| Stadium (Tyagi et al., SOSP 2017) | parallel verifiable mix | anytrust | minutes | large | no | research |
| ZIPNet ([ePrint 2024/1227](https://eprint.iacr.org/2024/1227), PoPETs 2025) | DC-net with TEE liveness | anytrust + active | sub-second target | "hundreds of anytrust servers" scaling | yes (liveness only) | research → Flashbots adoption |
| Flashnet ([writings.flashbots.net, Feb 2026](https://writings.flashbots.net/network-anonymized-mempools)) | ZIPNet-derived | anytrust + global passive | "low" (unspecified) | per-round client set | yes (liveness, client + server) | planned, Flashbots Phase 2 |

The architectural move that makes ZIPNet relevant to machine payments is the TEE/cryptography split, stated by the Flashbots writeup verbatim: *"adopt ZIPNet's approach of using TEEs to ensure liveness, but rely on classical cryptographic means to ensure anonymity, such that should a TEE be broken, the system may become unresponsive but anonymity does not rely on the security of TEEs."* This separation is what allows a payment-transport substrate to make minimal trust claims to the merchants and clients it serves.

The honest caveat: **Flashnet does not yet describe itself as a payment-transport layer.** The Feb 2026 writeup targets transaction broadcast for the Flashbots block-building pipeline. The reuse-for-machine-payments framing is the open question this workstream targets.

### 3.2 Mixnets

The Loopix-family alternative.

- [Loopix (Piotrowska et al., USENIX Security 2017)](https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/piotrowska). Poisson-mix design with Sphinx packet format and stratified topology. Mix nodes handle 300+ messages/second with ~1.5 ms processing overhead on top of the protocol-mandated Poisson delay. End-to-end latency in seconds.
- [Nym](https://nym.com/nym-whitepaper.pdf). Loopix descendant, incentivized via NYM token. NymVPN moved to general availability March 2025: the first production-deployed incentivized Loopix-style mixnet. Composes mixnet packets with [Coconut](https://www.ndss-symposium.org/ndss-paper/coconut-threshold-issuance-selective-disclosure-credentials-with-applications-to-distributed-ledgers/) threshold credentials (zk-nyms) for unlinkable access tickets.
- Sphinx / Mixminion / Mixmaster lineage. Older but Sphinx is still the dominant packet format because of its bit-identical headers across hops.

### 3.3 HOPR: the underweighted production system

[HOPR](https://hoprnet.org/) is the only meaningfully deployed *incentivized* mixnet. Probabilistic-payment tickets compensate relay nodes for both real traffic and cover traffic; cover-traffic generation rolls into staking rewards. HOPR has weaker anonymity properties than Loopix-style Poisson mixing but solves an economic problem the rest of the field hasn't begun to address: **who pays for cover traffic, in what currency, with what incentive compatibility.**

For agent payments where merchants are the entities being de-anonymized, the question of who funds the cover traffic is non-trivial. HOPR's mechanism design (probabilistic-payment tickets per relay, cover-traffic-as-staking-reward) is the prior art that most directly addresses the Flashnet bandwidth-cost problem. It deserves more attention than it gets in Flashbots-orbit discourse.

### 3.4 What this layer needs

For *payment-transport at agent scale* (sub-second round trip, kilobyte responses, cross-merchant) the deployed options today are Nym (production but seconds of latency) and HOPR (lower latency, weaker properties). Everything that approaches a machine-payment-grade latency budget while keeping strong anonymity is still in research, with ZIPNet/Flashnet being the closest credible path. The open question for Layer 1: **can Flashnet's anytrust DC-net generalize from transaction broadcast to per-query API payment transport, on a sub-second budget, with HOPR-style cover-traffic economics?**

## 4. Layer 2: Anonymous credentials carrying spendable state

Every Privacy Pass variant is unlinkable. The axis that matters for machine payments is whether the credential carries credit and how partial-spend and refund work.

### 4.1 Anonymous Credit Tokens (ACT)

[`draft-schlesinger-privacypass-act-01`](https://datatracker.ietf.org/doc/draft-schlesinger-privacypass-act/) (Sam Schlesinger, Frédéric Meunier; underlying crypto in `draft-schlesinger-cfrg-act-00`). BBS-style credential over Ristretto255 with Pedersen commitments. A credential carries a credit counter; each redemption re-issues a new credential with updated nullifier and counter values. Spec text: *"When a client spends a certain number of credits from a credential, that credential is invalidated and the client receives a new credential with the remaining balance."*

Properties: origin-client, issuer-client, and redemption-context unlinkability. Trust model is **single-issuer, jointly-operated with origin**: *"ACT is only compatible with deployment models where the Issuer and Origin are operated by the same entity, as tokens produced from a credential are not publicly verifiable."*

Concurrency: spent sequentially. From the spec: *"a single live session is enforced per initial credential. This provides concurrency control."* Clients cannot pipeline two redemptions in flight against a single credential.

Production status: [Cloudflare's October 2025 post](https://blog.cloudflare.com/private-rate-limiting/) explicitly frames ACT for agent rate-limiting and uses MCP as the transport. Benchmarks: VOPRF issuance of 1000 tokens takes 99 ms versus 1.35 ms for one ARC credential allowing 1000 presentations (about 70× faster on issuance, but ARC is cheaper on redemption).

### 4.2 ZK API Usage Credits (Crapis & Buterin, Feb 11 2026)

[ethresear.ch post](https://ethresear.ch/t/zk-api-usage-credits-llms-and-beyond/24104). Construction:

1. User deposits *D* into an L1 contract; the contract inserts the user's identity commitment into a Merkle tree.
2. Each request carries a ZK-STARK proof *π_req* of (a) Merkle membership, (b) refund summation *R = Σv_j* with server-signed refund tickets, (c) solvency constraint *(i + 1) · C_max ≤ D + R*, (d) Rate-Limit-Nullifier components.
3. RLN binds anonymity to financial stake: *"honest users who stay within protocol limits remain unlinkable, while users who double-spend cryptographically reveal their secret key,"* enabling slashing.
4. After the request, the server signs a refund ticket for unused capacity. Users accumulate refunds locally.

The v2 homomorphic refund extension addresses a circuit-cost objection raised in the comment thread: instead of per-ticket signatures, the server homomorphically adds to a commitment, *E(R_new) = E(R) ⊕ E(r)*. **This v2 path has an unstated re-randomization requirement.** Commenter omarespejel surfaced it on page 2: without per-submission re-randomization, the server can chain commitments across requests and re-link them. Re-randomization in turn requires the server's signature to survive re-blinding, pushing the construction back to BBS+. The original post does not state this; the design is load-bearing only with the comment-thread amendment.

Production status: [4Mica](https://4mica.dev) is live on testnet with SDKs in Rust, Python, and TypeScript. Zeko rollup demo. No mainnet production.

### 4.3 Boomerang

[arXiv 2401.01353](https://arxiv.org/abs/2401.01353) (Ankele, Celi, Giles, Haddadi; v2 Oct 2024; [Brave research blog](https://brave.com/blog/boomerang-protocol/), [repo](https://github.com/brave-experiments/Boomerang)). Bulletproof range proofs plus a Black-Box Accumulator (BBA / BBA+) plus an L1 smart contract. The BBA+ accumulates tokens without associating them to the user, prevents double-spending, and **supports negative point collection**.

The negative-point property is underappreciated. Of all the credential schemes in this section, Boomerang's BBA+ is the only one that natively supports refunds and clawbacks at the cryptographic primitive level, without piling homomorphic encryption on top. If a payment credential ever needs to support spend, refund, and partial-claw-back in a single scheme, BBA+ is the only off-the-shelf design that gives it.

Throughput: ~23.6M users/day on a single backend; ~15.5M users/day on Solana at ~$0.00011/user.

### 4.4 Batched Privacy Pass (the degenerate but shippable fallback)

[`draft-ietf-privacypass-batched-tokens-08`](https://datatracker.ietf.org/doc/draft-ietf-privacypass-batched-tokens/) is in IETF WG Last Call. Batches VOPRF issuance at approximately half the cost of *N* individual issuances. Not credit-bearing: each token is one-shot at fixed denomination. The pragmatic version: fake credit-bearing semantics by batched-issuing *N* tokens at once, accepting the loss of partial-spend and refresh affordances. The only Privacy Pass variant about to leave the IETF; the lowest-cost path to "anonymous credit" if you need to ship this quarter.

### 4.5 ARC (Anonymous Rate-limited Credentials)

[`draft-ietf-privacypass-arc-protocol`](https://datatracker.ietf.org/doc/draft-ietf-privacypass-arc-protocol/) (Cathie Yun, Christopher A. Wood). Uses the MAC_GGM algebraic MAC: pairings-free, smaller credentials than MAC_DDH. Fixed-N: a credential carries a presentation limit set at issuance with all presentations unlinkable from each other and from issuance. ACT borrowed its context-threading approach from ARC. ARC trades flexibility for parallelism: ACT is sequential and credit-bearing, ARC is parallel and fixed-N.

### 4.6 Coconut / zk-nyms (the threshold issuance story)

[Coconut (Sonnino et al., NDSS 2019)](https://sonnino.com/papers/coconut.pdf). The only credential primitive on this list with threshold issuance: *t-of-n* authorities, unforgeable while fewer than *t* collude, blind and unlinkable no matter how many collude. Verification ~10 ms.

In production today as zk-nyms inside NymVPN: the only deployed threshold-issued anonymous credential system at consumer scale. For a payment rail, threshold issuance is the structural answer to the "single-Issuer compulsion" problem (a court order against one issuer cannot reconstruct the spend history). The cleanest research direction in 2026 is bringing ACT's credit-bearing semantics into Coconut-shaped threshold issuance.

### 4.7 Comparison

| Scheme | Crypto basis | Credit semantics | Issuer trust | Refund | Production |
|---|---|---|---|---|---|
| ACT | BBS / Ristretto255 + Pedersen | stateful, partial-spend, sequential | single issuer = origin | re-issued credential | Cloudflare prototype Oct 2025 |
| ZK API Credits | RLN + ZK-STARK + (v2) HE/BBS+ | deposit-funded, parallel via RLN index | on-chain contract | server-signed tickets / HE accumulator | 4Mica testnet, Zeko demo |
| Boomerang | Bulletproofs + BBA+ + L1 | accumulator; supports negative points | L1 verifier | native (negative points) | Brave PoC |
| Batched Privacy Pass | VOPRF batched | fixed denomination, one-shot | single issuer | none | IETF WG Last Call |
| ARC | MAC_GGM | fixed-N presentations | single issuer | none | drafted |
| Coconut / zk-nyms | BLS pairing-based, threshold | attribute / e-cash variants | *t-of-n* threshold | scheme-dependent | NymVPN production |

The honest read as a payment primitive: **ACT is the most-shippable single-issuer credit token. ZK API Credits is the most-trustless deposit-to-credit. Coconut is the most-decentralized issuance. Batched Privacy Pass is what ships this quarter. Boomerang is the most cryptographically expressive on refunds.**

For Flashbots research: **the integration target is ACT for issuance-side simplicity, with a Coconut-shaped threshold-ACT as the v2 mainline that nobody is working on in the open and which the program could claim.**

## 5. Layer 3: Agent commerce protocols and identity defaults

### 5.1 x402

[x402.org](https://www.x402.org/), Coinbase + Cloudflare. HTTP-402 wrapper: server returns 402 with payment requirements; client retries with payment headers; a **facilitator** verifies and settles on-chain. As of March 2026: >119M transactions on Base, ~35M on Solana, ~$600M annualized volume, zero protocol fees. The [x402 Foundation launched under the Linux Foundation](https://www.linuxfoundation.org/press/linux-foundation-is-launching-the-x402-foundation-and-welcoming-the-contribution-of-the-x402-protocol) on April 2, 2026, with Adyen, AWS, Amex, Circle, Cloudflare, Coinbase, Google, Mastercard, Microsoft, Polygon, Stripe, Visa, and others. [x402 v2](https://www.x402.org/writing/x402-v2-launch) (Dec 11 2025) introduced plugin-driven facilitator architecture and CAIP-122 Sign-In-With-X session bindings.

**Identity exposure**: buyer on-chain address visible to merchant *and* facilitator. Coinbase facilitates >50% of volume. **A single entity sees a majority of the cross-merchant payment graph.** This is the correlation problem at this layer.

### 5.2 Machine Payments Protocol (MPP)

[`draft-ryan-httpauth-payment-00/01`](https://datatracker.ietf.org/doc/draft-ryan-httpauth-payment/) (Brendan Ryan, Jake Moxey, Tom Meagher, Tempo Labs; Jeff Weinstein, Steve Kaliski, Stripe; March 18 2026). Defines the HTTP `Payment` authentication scheme. Methods registered in an "HTTP Payment Methods" IANA registry. The identity-exposure stance is unusually privacy-forward in the spec text:

> Servers MUST NOT require user accounts for payment. Payment methods SHOULD support pseudonymous options where possible.

The `source` field is optional; when populated, the recommendation is W3C DIDs. MPP also defines a "sessions" primitive for streaming micropayments under a pre-authorized spending limit, sidestepping per-call on-chain transactions.

MPP earns its keep as **the standardized multi-rail wire format**, particularly at the issuance step where an agent needs to pay an Issuer in fiat, Lightning, stablecoin, or card via a uniform HTTP authentication scheme. It is not the right wrapper at the spend step where Privacy Pass's `Authorization: PrivateToken` is the native carrier for ACT.

### 5.3 ERC-8004 Trustless Agents

[EIP-8004](https://eips.ethereum.org/EIPS/eip-8004) (Marco De Rossi @ MetaMask, Davide Crapis @ EF, Jordan Ellis @ Google, Erik Reppel @ Coinbase). Mainnet January 29 2026. ~22,900 registrations in first three days; Base / L2 expansion followed. Three registries:

1. **Identity Registry**. ERC-721 + URIStorage, global identifier *{namespace}:{chainId}:{identityRegistry}* plus *agentId*.
2. **Reputation Registry**: signed feedback signals; clients don't need to be registered.
3. **Validation Registry**: generic hooks for stakers, zkML verifiers, TEE oracles.

The feedback file mandates *agentRegistry, agentId, clientAddress, createdAt, value, valueDecimals*. **Optional includes a `proofOfPayment` schema** ({fromAddress, toAddress, chainId, txHash}) which the spec notes *"can be used for x402 proof of payment."* The composition is the quiet de-anonymization vector: once reputation systems expect proof-of-payment, every reputation-bearing call carries an on-chain receipt traceable to the buyer's address.

Anonymizability: the buyer side can be pseudonymous, the seller agent side cannot. The seller-agent side is identity-by-construction.

### 5.4 MCP and the Cloudflare ACT-on-MCP signal

[MCP spec 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18) (Anthropic, with broad ecosystem adoption). JSON-RPC 2.0; host/client/server roles. No native payment construct. Spec is explicit on least disclosure: *"The protocol intentionally limits server visibility into prompts."* Payment is bolted on via extensions: [Vercel's x402-mcp](https://vercel.com/blog/introducing-x402-mcp-open-protocol-payments-for-mcp-tools) wires x402 directly into MCP tool calls.

**The Cloudflare ACT demo runs on MCP.** This is more important than it reads. Cloudflare is treating MCP as the de facto substrate for AI-agent rate-limited access (not just for tool-calling) and shipping anonymous credentials on top before the IETF Privacy Pass process completes. If Anthropic, Cloudflare, and Google converge on MCP-with-anonymous-credentials, the credential layer might consolidate before the payment layer does.

### 5.5 A2A and AP2

[A2A (Agent2Agent)](https://a2a-protocol.org/latest/), Apache 2.0, donated to Linux Foundation June 2025. AgentCards published at `/.well-known/agent.json` describe agent capabilities, authentication, skills. 150+ orgs as of April 2026.

[AP2 (Agent Payments Protocol)](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol) (Google + Mastercard, Sep 16 2025; [donated to FIDO Alliance Apr 28 2026](https://blog.google/products-and-platforms/platforms/google-pay/agent-payments-protocol-fido-alliance/)). Implements *Verifiable Intent through Mandates*: user-signed verifiable credentials at every step (Intent, Cart, Payment mandate). The architectural premise is *"tamper-proof log of user-authorized agent actions to ensure accountability."* AP2 explicitly composes with A2A and MCP.

**AP2 is fundamentally incompatible with unlinkable credentials.** There is no anonymizable variant of an AP2 mandate that preserves its audit guarantees. If AP2 becomes the dominant authorization layer for agent commerce, the privacy work has to happen *under* AP2 (in the payment-method layer of MPP, or in the rail itself), not at the mandate layer.

### 5.6 Comparison and pattern

| Protocol | Layer | Default identity exposure | Anonymizable? | Status |
|---|---|---|---|---|
| x402 | HTTP 402 wrapper | buyer address + facilitator | weakly, via shielded pools / ZK extensions | LF Foundation Apr 2026; ~$600M annualized |
| MPP | HTTP auth scheme | optional DID `source` | yes by spec | IETF draft Mar 2026; live via Stripe/Tempo |
| ERC-8004 | on-chain registries | agent identity mandatory; client pseudonymous | clients yes, agents no | mainnet Jan 2026; ~22.9k registered |
| MCP | tool RPC | host-controlled; no payment-native | yes via Privacy Pass / ACT wrapper | spec 2025-06-18; broad adoption |
| A2A | agent discovery | AgentCard public, selective disclosure | partial | LF June 2025; 150+ orgs |
| AP2 | mandate layer | user-signed VCs at every step | no | FIDO Apr 2026 |

**The pattern**: payment-layer protocols (x402, MPP) leave room for anonymity by default. Identity-and-orchestration-layer protocols (ERC-8004, A2A, AP2) close that room. The cross-protocol composition (x402 inside ERC-8004 inside AP2 inside A2A) is additively de-anonymizing. Each layer adds another permanent identifier; the resulting transaction graph is the union.

## 6. Layer 4: An API workload taxonomy for anonymity amenability

This is the load-bearing contribution of the artifact. No existing engineering taxonomy classifies API workloads by their amenability to query-atomic anonymous payment. The dimensions exist piecewise across other frameworks; none of them are integrated, and the privacy-relevant ones (content fingerprintability, reputation accumulation, cross-request correlatability) are absent from the dominant ones.

### 6.1 What exists, briefly

- **REST and HTTP semantics**: [Fielding's dissertation](https://ics.uci.edu/~fielding/pubs/dissertation/fielding_dissertation.pdf) (statelessness as architectural constraint); [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) (safe / idempotent / cacheable). Method-level only; says nothing about identity coupling or correlatability.
- **Database workloads**: OLTP vs OLAP vs HTAP. [YCSB workloads A-F](https://courses.cs.duke.edu/fall13/compsci590.4/838-CloudPapers/ycsb.pdf) (read/write ratio, recency bias). The closest existing thing to a request-shape taxonomy. Silent on identity.
- **Inference workloads**: [MLPerf scenarios](https://arxiv.org/pdf/1911.02549) (Single-Stream / Multi-Stream / Server / Offline); LLM serving prefill/decode characterization. Arrival pattern and latency, no privacy.
- **Agent benchmarks**: [GAIA](https://arxiv.org/abs/2311.12983), [AgentBench](https://agentic-design.ai/patterns/evaluation-monitoring/agentbench), [τ-bench](https://arxiv.org/abs/2406.12045). Task-complexity oriented; merchant-side privacy is not in scope.
- **MCP Resources vs Tools**: the cleanest existing semantic split at the agent-API boundary, but binary and merchant-side only.
- **Privacy terminology**: [Pfitzmann & Hansen](https://dud.inf.tu-dresden.de/literatur/Anon_Terminology_v0.34.pdf) (anonymity, unlinkability, pseudonymity gradient). Gives us the target properties; says nothing about which workloads can deliver them.
- **Payment workloads**: ISO 18245 MCC codes (industry verticals); Stripe Payment Intents (one-shot / setup / metered). All silently assume identity throughout.

The gap is a workload-side taxonomy whose dimensions are the dimensions along which an anonymous-payment substrate either holds or breaks. The dimensions below are *separately measurable* and *separately remediable*, which is what matters for design.

### 6.2 The ten dimensions

**D1. Session shape.** *How much server-side state must persist across this client's requests to make the workload work?*
Values: `atomic` (each request fully self-contained), `cursor-bound` (server remembers a handle but no client identity), `session-bound` (per-client session for a logical task), `account-bound` (state across logical tasks, indexed by stable identity).

Why it matters: anonymous-payment-native workloads live on the atomic and cursor-bound rungs. Session-bound is recoverable with bearer-capability handles. Account-bound is where anonymity collapses.

**D2. Idempotency class.** RFC 9110, restated. Values: `safe`, `idempotent`, `non-idempotent`. Safe and idempotent requests retry cleanly after a payment-layer hiccup; non-idempotent requests force idempotency-keys (correlation bait) or anonymity-preserving dedup.

**D3. Cross-request correlatability (server-observable).** *Given two paid requests from a client population, the merchant's a-priori probability they came from the same agent.*
Values: `uncorrelatable` (no content, timing, or routing signal above the anonymity-set baseline), `weakly-correlatable` (overlap leaks a few bits), `deterministically-linked` (protocol forces a shared identifier).

This is Pfitzmann-Hansen unlinkability projected onto workload structure. A streaming chat that holds an SSE channel open is deterministically-linked over the channel's lifetime even if every byte is paid with fresh anonymous tokens.

**D4. Side-effect locus.** *Where do the effects manifest?*
Values: `pure-read`, `merchant-internal-write`, `externally-side-effecting`.

Pure-read is the natural home of anonymous payment. Externally-side-effecting requests inherit the destination system's identity requirements (KYC at a bank, sender domain in email). Anonymity at the API layer cannot wash through.

**D5. Temporal profile.** Values: `sub-second`, `seconds`, `minutes`, `detached-batch`. Detached-batch decouples submission from retrieval, which is good for unlinkability (anonymous submit, anonymous retrieval) only if the job handle is bearer-only.

**D6. Payload size.** Values: `KB`, `MB`, `GB+`. Payload size is a fingerprinting channel under TLS (cf. website-fingerprinting literature). Constant-size response classes are more anonymity-friendly than variable.

**D7. Pricing-unit granularity.** *What primitive is metered?*
Values: `per-request`, `per-resource-consumed` (tokens, CPU-seconds, bytes), `per-time` (subscription/quota), `per-outcome`.

Per-request maps cleanly onto one anonymous token per call. Per-resource requires prepayment-with-refund (ACT-shaped) or post-pay reconciliation (handle). Per-time and per-outcome are hard to do anonymously without losing the property.

**D8. Identity coupling (protocol-mandated).** *Does the protocol itself, independent of business policy, require a stable identifier?*
Values: `identity-free`, `pseudonym-tolerant` (per-request pseudonym suffices), `stable-pseudonym-required` (per-session), `verified-identity-required` (KYC).

Distinct from D1: a session can be cookie-only (pseudonym-tolerant) or login-only (stable). Loosely follows Pfitzmann-Hansen's transaction → relationship → role → person pseudonymity ladder.

**D9. Reputation-accumulation dependence.** *Does workload quality, price, or availability depend on prior behavior of this client at this merchant?*
Values: `none`, `soft` (rate limits, fraud scoring), `hard` (whitelists, KYC tiers, reputation gates).

The dimension underweighted by every cryptographer working on payment unlinkability. Reputation systems are *the* anti-anonymity force in production APIs. A workload with hard reputation dependence is fundamentally incompatible with full unlinkability regardless of payment-layer crypto.

**D10. Content-fingerprintability.** *Independent of payment metadata, does the request or response content identify the requester above the anonymity-set baseline?*
Values: `low` (generic search, popular cached resources), `medium` (queries reveal interest profile, no single query is uniquely identifying), `high` (queries embed user-specific corpus: RAG over private docs, multi-turn chat continuing a personal thread).

This is the dimension most engineers underestimate. Cryptographically unlinkable payment is necessary but not sufficient: if the *content* proves two requests came from the same agent, payment unlinkability is theater.

### 6.3 Worked examples

| Workload | D1 Session | D2 Idem | D3 Correlate | D4 Side-eff | D5 Time | D6 Size | D7 Price | D8 Identity | D9 Reputation | D10 Content fingerprint | Amenable? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Agentic web search (single call) | atomic | safe | uncorrelatable | pure-read | sub-sec | KB | per-request | identity-free | none | medium | **Yes** |
| LLM completion, single-turn | atomic | safe | weakly | pure-read | seconds | KB | per-resource | identity-free | none | medium | **Yes, with prepay-refund** |
| LLM chat, multi-turn streaming | session-bound | safe | deterministic (within stream) | pure-read | sec–min | KB–MB | per-resource | pseudonym-tolerant | none | high (multi-turn reveals user corpus) | **Partial; D10 is the breaker** |
| RAG lookup, public corpus | atomic | safe | weakly | pure-read | sub-sec | KB–MB | per-request or per-token | identity-free | none | medium | **Yes** |
| DEX trade | atomic at API; account-bound on-chain | non-idem | deterministic (wallet on-chain) | externally-side-effecting | seconds | KB | per-outcome | verified-identity (KYC tier) | hard | high | **No; anonymity is theater** |
| File storage upload | cursor-bound | idempotent | deterministic (handle) | merchant-internal-write | seconds | MB–GB | per-request + per-byte-time | pseudonym-tolerant | soft | high (file fingerprint) | **Partial; bearer handle is the right pattern** |
| Cron batch inference | detached-batch | idempotent | weakly | merchant-write then pure-read | min–hr | MB–GB | per-resource | pseudonym-tolerant | none | varies | **Yes (generic) / Partial (personal)** |
| MCP tool call, read-only resource | atomic | safe | uncorrelatable | pure-read | sub-sec | KB | per-request | identity-free | none | low–medium | **Yes** |
| MCP tool call, side-effecting (send_email) | account-bound (downstream) | non-idem | deterministic (downstream system) | externally-side-effecting | sub-sec–sec | KB | per-request | verified-identity downstream | hard | high (side effect identifies) | **No; anonymity ends at boundary** |

Three clusters emerge.

- **Native** (rows 1, 4, 7-generic, 8): atomic or detached-batch, safe, identity-free, low-to-medium content fingerprint. These are the workloads the agentic web should default to identity-free for.
- **Recoverable with care** (rows 2, 3, 6, 7-personal): the payment layer can be anonymous, but a second mechanism (bearer handles, prepay-with-refund tokens, content padding, session-scoped pseudonyms) has to do real work.
- **Identity-dominated** (rows 5, 9): the side-effecting downstream system or the regulated settlement dominates. Anonymous payment at the API edge is cosmetic.

### 6.4 What this taxonomy claims, and what it doesn't

It claims that ten dimensions are sufficient to predict, from an API spec, whether a workload is a clean fit for query-atomic anonymous payment, a recoverable fit with specific protocol additions, or identity-dominated.

It does not claim the dimensions are fully orthogonal. D1 and D8 are correlated in practice; D6 and D10 are correlated for content-rich workloads. They are *separately measurable* and *separately remediable*, which is what matters for design guidance.

It does not claim novelty for the underlying privacy properties (Pfitzmann-Hansen, Chaum, Privacy Pass did that work). The contribution is the workload-side mapping: a designer holding an OpenAPI spec can score on these ten axes in an hour and know what the anonymity ceiling is before integrating any payment substrate.

It is intentionally agnostic to the payment substrate. Applies equally to x402-over-USDC, L402-over-Lightning, Chaumian ecash, ACT, ZK API Credits, batched Privacy Pass. Substrate determines whether the payment artifact is unlinkable; the taxonomy determines whether the *workload* is.

## 7. Agentic search as the canonical native workload

The taxonomy makes agentic search the cleanest fit in the entire stack. This deserves its own section because it is also the workload this research workstream targets.

### 7.1 What "agentic search" is

A search loop where an autonomous agent decomposes a question, queries multiple data sources, reflects on gaps, queries again, synthesizes. The architecture-survey literature ([Agentic RAG Survey, arXiv 2501.09136](https://arxiv.org/abs/2501.09136); [Deep Research Survey, arXiv 2508.12752](https://arxiv.org/abs/2508.12752)) converges on a taxonomy along agent cardinality, control structure, autonomy, and knowledge representation. Multi-step decomposition fits the case where subtasks are not predefined.

### 7.2 Production landscape (mid-2026)

- **Perplexity Agent API and Deep Research** (Claude Opus 4.5/4.6 for Pro/Max). A Deep Research query takes 2–5 minutes and visits 100+ web pages.
- **OpenAI Deep Research**. Specialized o3 variant.
- **Anthropic** research mode. Multi-agent: lead agent plus sub-agents.
- **Exa.ai**. The dominant *search backend* for agents; the most-used search server in 2026 via its MCP server.
- **Brave** agentic search. Low-latency raw results (median 669 ms vs ~11 s for Perplexity with synthesis).

### 7.3 Workload profile

- **Query rate**: dozens to hundreds of API calls per high-level user question.
- **Latency budget**: sub-second per leaf; total 2–5 minutes for deep-research.
- **Cost per leaf**: cents to fractions of a cent (Perplexity web search $0.005/call, URL fetch $0.0005/call). Micropayment-native.
- **Cross-merchant by design**: a single Deep Research run touches Exa, Perplexity, OpenAI, Anthropic, plus dozens of source websites. This is exactly the cross-merchant correlation graph that a unified facilitator (Coinbase, Stripe) sees today.
- **Response shape**: kilobyte-scale text.

### 7.4 Why this is the canonical fit

Scored against the taxonomy: D1 atomic, D2 safe, D3 uncorrelatable, D4 pure-read, D5 sub-second, D6 KB, D7 per-request, D8 identity-free, D9 none, D10 medium. **Every dimension lands in the anonymity-friendly value.** The only D10 caveat (medium content fingerprint) is mitigated by the high entropy of generic search queries across a large user population.

The point: if any class of paid API traffic in 2026 should be private by default, it is agentic search. The volume is real and growing. The cryptographic primitives exist (Layer 2). The transport primitives exist (Layer 1). The standards conversation has not yet wired them together.

## 8. Open problems

Eight, in roughly the order of how much they would change the privacy posture of agent commerce if solved by end of 2026.

**1. The proof-of-payment field in ERC-8004.** Optional in the v1 schema but expected to populate as reputation systems mature. Every reputation-bearing call carrying an on-chain receipt is the quietest, most production-ready de-anonymization in the entire stack. A ZK-validator extension to ERC-8004 that proves "this agent is in good standing" without revealing the underlying payment receipt would bridge ERC-8004's reputation primitive into Lethe-style unlinkable presentations. Substantive cryptographic work; the right place to claim a research milestone.

**2. ACT-of-N: Coconut-threshold ACT.** ACT is single-issuer-and-origin; the cleanest research direction is bringing its credit-bearing semantics into Coconut-shaped *t-of-n* threshold issuance. Removes the single-issuer compulsion gap. Removes the Issuer revenue concentration that makes single-issuer ACT a centralized rail. Nobody is working on this in the open. PhD-thesis-shaped piece of work.

**3. The Crapis-Buterin E(R) re-randomization gap.** The v2 ZK API Usage Credits homomorphic-refund construction requires per-submission re-randomization, which requires the server's signature to survive re-blinding, which pushes the construction back to BBS+. The original ethresear.ch post does not state this; the comment thread does. A clean v3 spec is the right deliverable. Also: a write-up that disentangles the v1 vs v2 vs (proposed) v3 trust assumptions and surfaces the BBS+ requirement explicitly.

**4. Flashnet as payment-transport.** The Feb 2026 Flashbots writeup targets transaction broadcast. The reuse for per-query API payments is the central open question. The technical answer is plausibly yes: anonymity-set requirements are similar; the latency budget for agent payments is slightly looser. The open question is the cover-traffic economics. Who pays for it, in what currency, with what incentive compatibility? HOPR's probabilistic-payment-ticket design is the prior art that most directly addresses this.

**5. Boomerang BBA+ as a Privacy Pass primitive.** The BBA+ accumulator with negative-point support gives spend + refund + clawback at the cryptographic primitive level, without piling homomorphic encryption on top. None of the IETF Privacy Pass drafts have this affordance. Bringing BBA+ into the Privacy Pass standards-track conversation is a relatively short-horizon contribution that produces an outsized increase in the design space of credit-bearing credentials.

**6. AP2's incompatibility with unlinkable credentials.** AP2 is gaining adoption fast (60+ orgs, FIDO Alliance home). Its mandate model is identity-by-construction. If AP2 becomes the dominant authorization layer, the privacy work has to happen under AP2 in the payment method or rail layer, not at the mandate layer. The contribution is to articulate clearly what *cannot* be anonymized about AP2 and where the residual anonymity surface is.

**7. The Cloudflare-ACT-on-MCP consolidation path.** Cloudflare is shipping ACT on MCP before the IETF Privacy Pass process completes. If Anthropic, Cloudflare, and Google converge on MCP-with-anonymous-credentials, the credential layer consolidates before the payment layer settles. The implication for any Flashbots research in this space: MCP is the natural integration target for any Flashbots anonymous-credential work, *not* x402 or MPP. This may be the most consequential industry-direction signal currently in the open.

**8. Stylometric de-anonymization of inference prompts.** The single most underweighted threat in the entire stack. Every paper in Layer 2 is about payment unlinkability. Every protocol in Layer 3 is about identity at the wire level. For AI inference workloads specifically, the content of the prompt is sufficient for re-identification regardless of payment scheme. There is no production-ready story for prompt-stylometry-resistant inference. A research program can claim this gap: anonymous-payment for inference is a partial answer at best until stylometric resistance is solved.

## 9. An integrated reference design

For completeness, a brief sketch of how the four layers compose for the canonical agentic-search use case.

```
   Layer 4 | Workload:    agentic web search (D1 atomic, D8 identity-free, D10 medium)
   Layer 3 | Protocol:    Authorization: PrivateToken (RFC 9577); ACT presentation
                          MPP only at issuance, for multi-rail payment to PSP
   Layer 2 | Credential:  ACT in publicly-verifiable BBS instantiation
                          v2: Coconut-threshold ACT-of-N
   Layer 1 | Network:     Flashnet for forward path (anytrust DC-net)
                          Nym mixnet SURB for response path (asymmetric anonymity, honest)
```

Issuance: agent pays PSP via MPP (any rail, Stripe/Lightning/card avoids on-chain footprint). PSP runs RFC 9578 Privacy Pass issuance protocol, mints ACT credential.

Spend: agent encodes HTTPS request to merchant inside Flashnet payload; `Authorization: PrivateToken` carries ACT presentation. Exit gateway forwards plaintext to merchant. Merchant verifies BBS-style proof against published Issuer keys, checks nullifier locally, encrypts response under client-provided key, sends back via Nym SURB.

This sketch is *not* a proposal; it is an existence proof. The Lethe-proposal draft that preceded this artifact ([backed up as `unlinkable-machine-payments-lethe-proposal-v1.md`](file:///Users/halcyon/unlinkable-machine-payments-lethe-proposal-v1.md)) develops the design in more detail; it is one wiring, not the only one.

## 10. What this asks of the research community

**For Flashbots research.** Position Flashnet not as a transaction-broadcast layer but as a payment-transport layer. The technical generalization is small (the round-based DC-net abstraction is payload-agnostic). The brand opportunity is large: Flashbots becomes the team making agent commerce private by default, not the team that ships another transport. Open problem #4 (cover-traffic economics) and #1 (ZK-validator extension to ERC-8004) are the highest-leverage research milestones for the program's first quarter.

**For the IETF Privacy Pass WG.** Open problem #2 (Coconut-threshold ACT) is the v2 mainline that nobody is working on in the open. Bringing Sonnino's group and Schlesinger's collaborating is the right convening move. Open problem #5 (Boomerang BBA+) is a shorter-horizon contribution to the same conversation.

**For Ethereum Foundation AI.** Open problem #3 (E(R) re-randomization) is a clean v3 spec milestone. Open problem #1 (ZK-validator on ERC-8004) is the architectural defense against the proof-of-payment de-anonymization that EIP-8004's own validation registry is positioned to host.

**For agent commerce protocol authors.** Open problem #6 (AP2 incompatibility) deserves to be stated clearly in the FIDO Alliance work plan: AP2 sits above the privacy layer; privacy work belongs in the payment method or rail layer. Open problem #7 (MCP consolidation) is the integration target nobody has named.

**For agent SDK authors.** Default credential rotation policy on `did:key` source identifiers should be per-request, not per-session. The MPP spec is silent on persistence; SDKs cache by default. The single most consequential implementation choice for cross-merchant linkability is whether the SDK rotates by default. Don't cache.

**For stylometry researchers.** Open problem #8 is the largest unaddressed threat in the stack. Anonymous payment for inference is a partial answer until prompt-stylometric resistance ships.

## 11. Conclusion

The four layers of agent commerce in 2026 are crystallizing. The payment-layer and credential-layer primitives are arriving at integration shape. The orchestration and identity layers are arriving at attribution-by-default shape. The network layer is arriving at production at the Loopix-Nym frontier and at research at the ZIPNet-Flashnet frontier. The workload layer is arriving at the foreground for the first time as agent traffic shifts from human-operated batch jobs to autonomous cross-merchant streams.

The default that crystallizes by end of 2026 is the default for the next decade of agent commerce. The cryptographic and transport primitives to make that default privacy-respecting all exist. They do not yet talk to each other. The first contribution this workstream can make is the wiring.

---

## Acknowledgments and review

This artifact was reviewed by cognitive variants of Tina Z and Quintus Kilbourn from the Flashbots psychocognition lab. Tina's review pushed the framing from "research proposal" to "research artifact serving a forcing function." Quintus's review surfaced the response-path anonymity-asymmetry claim, the cloud-TEE substrate as a realistic adversary, and the Issuer-compulsion-vs-cryptographic-anonymity distinction. Research support from `dmarzzz/research-swarm` (run offline due to environment).

## References

### Network anonymity
- Chaum, ["The Dining Cryptographers Problem,"](https://link.springer.com/article/10.1007/BF00206326) J. Cryptology 1988
- Wolinsky et al., ["Dissent in Numbers,"](https://www.usenix.org/conference/osdi12/technical-sessions/presentation/wolinsky) OSDI 2012
- Corrigan-Gibbs et al., ["Proactively Accountable Anonymous Messaging in Verdict,"](https://www.usenix.org/conference/usenixsecurity13/technical-sessions/papers/corrigan-gibbs) USENIX Security 2013
- Corrigan-Gibbs et al., ["Riposte,"](https://crypto.stanford.edu/~henrycg/pubs/riposte/) IEEE S&P 2015
- Kwon et al., ["Riffle,"](https://www.degruyter.com/document/doi/10.1515/popets-2016-0008/html) PETS 2016
- Kwon et al., ["Atom,"](https://people.csail.mit.edu/devadas/pubs/atom.pdf) SOSP 2017
- Tyagi et al., "Stadium," SOSP 2017
- Rosenberg, Shih, Zhao, Wang, Miers, Zhang, ["ZIPNet,"](https://eprint.iacr.org/2024/1227) IACR ePrint 2024/1227; [PoPETs 2025](https://petsymposium.org/popets/2025/popets-2025-0058.php)
- Flashbots, ["Network-Anonymized Mempools,"](https://writings.flashbots.net/network-anonymized-mempools) Feb 17 2026
- Piotrowska et al., ["Loopix,"](https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/piotrowska) USENIX Security 2017
- [Nym whitepaper](https://nym.com/nym-whitepaper.pdf); NymVPN GA March 2025
- [HOPR docs / cover traffic](https://docs.hoprnet.org/core/cover-traffic)

### Anonymous credentials
- Chaum, ["Blind Signatures for Untraceable Payments,"](https://sceweb.sce.uhcl.edu/yang/teaching/csci5234WebSecurityFall2011/Chaum-blind-signatures.PDF) CRYPTO 1982
- Sonnino et al., ["Coconut,"](https://www.ndss-symposium.org/ndss-paper/coconut-threshold-issuance-selective-disclosure-credentials-with-applications-to-distributed-ledgers/) NDSS 2019
- IRTF [`draft-irtf-cfrg-bbs-signatures-10`](https://datatracker.ietf.org/doc/draft-irtf-cfrg-bbs-signatures/)
- IETF [`draft-schlesinger-cfrg-act-00`](https://samuelschlesinger.github.io/draft-act/draft-schlesinger-cfrg-act.html), [`draft-schlesinger-privacypass-act-01`](https://datatracker.ietf.org/doc/draft-schlesinger-privacypass-act/)
- IETF [`draft-ietf-privacypass-arc-crypto-01`](https://datatracker.ietf.org/doc/draft-ietf-privacypass-arc-crypto/), [`draft-ietf-privacypass-arc-protocol-01`](https://datatracker.ietf.org/doc/draft-ietf-privacypass-arc-protocol/)
- IETF [`draft-ietf-privacypass-batched-tokens`](https://datatracker.ietf.org/doc/draft-ietf-privacypass-batched-tokens/)
- IETF [`draft-meunier-privacypass-reverse-flow-03`](https://datatracker.ietf.org/doc/draft-meunier-privacypass-reverse-flow/)
- [RFC 9576](https://datatracker.ietf.org/doc/rfc9576/), [9577](https://datatracker.ietf.org/doc/rfc9577/), [9578](https://datatracker.ietf.org/doc/rfc9578/) (Privacy Pass)
- Crapis & Buterin, ["ZK API Usage Credits: LLMs and Beyond,"](https://ethresear.ch/t/zk-api-usage-credits-llms-and-beyond/24104) ethresear.ch Feb 11 2026
- Ankele, Celi, Giles, Haddadi, ["Boomerang,"](https://arxiv.org/abs/2401.01353) arXiv 2401.01353
- Cloudflare, ["Anonymous credentials: rate-limiting bots and agents,"](https://blog.cloudflare.com/private-rate-limiting/) Oct 30 2025

### Agent commerce
- [`tempoxyz/mpp-specs`](https://github.com/tempoxyz/mpp-specs); [Stripe MPP blog](https://stripe.com/blog/machine-payments-protocol)
- IETF [`draft-ryan-httpauth-payment`](https://datatracker.ietf.org/doc/draft-ryan-httpauth-payment/)
- [`coinbase/x402`](https://github.com/coinbase/x402); [x402.org](https://x402.org); [x402 v2 launch](https://www.x402.org/writing/x402-v2-launch); [x402 Foundation at LF](https://www.linuxfoundation.org/press/linux-foundation-is-launching-the-x402-foundation-and-welcoming-the-contribution-of-the-x402-protocol)
- [EIP-8004: Trustless Agents](https://eips.ethereum.org/EIPS/eip-8004); [erc-8004/erc-8004-contracts](https://github.com/erc-8004/erc-8004-contracts)
- [MCP Specification 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18); [Vercel x402-mcp](https://vercel.com/blog/introducing-x402-mcp-open-protocol-payments-for-mcp-tools)
- [A2A Protocol](https://a2a-protocol.org/latest/); [Google AP2 announcement](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol); [AP2 → FIDO](https://blog.google/products-and-platforms/platforms/google-pay/agent-payments-protocol-fido-alliance/)

### Workload taxonomy prior art
- Fielding, ["Architectural Styles and the Design of Network-based Software Architectures,"](https://ics.uci.edu/~fielding/pubs/dissertation/fielding_dissertation.pdf) 2000
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- Cooper et al., ["Benchmarking Cloud Serving Systems with YCSB,"](https://courses.cs.duke.edu/fall13/compsci590.4/838-CloudPapers/ycsb.pdf) SoCC 2010
- Reddi et al., ["MLPerf Inference Benchmark,"](https://arxiv.org/pdf/1911.02549) 2019/2020
- Mialon et al., ["GAIA,"](https://arxiv.org/abs/2311.12983) 2023; [τ-bench](https://arxiv.org/abs/2406.12045); [τ²-Bench](https://arxiv.org/abs/2506.07982)
- Pfitzmann & Hansen, ["A terminology for talking about privacy by data minimization, v0.34,"](https://dud.inf.tu-dresden.de/literatur/Anon_Terminology_v0.34.pdf) 2010
- Mehnaz & Bertino, ["Side-Channel Attacks on Query-Based Data Anonymization,"](https://dl.acm.org/doi/10.1145/3460120.3484751) CCS 2021
- [Stripe Payment Intents](https://docs.stripe.com/payments/payment-intents); [Stripe usage-based billing](https://docs.stripe.com/billing/subscriptions/usage-based/pricing-plans)

### Agentic search
- ["Agentic RAG: A Survey,"](https://arxiv.org/abs/2501.09136) arXiv 2501.09136
- ["Deep Research: A Survey of Autonomous Research Agents,"](https://arxiv.org/abs/2508.12752) arXiv 2508.12752
- [Perplexity Agent API docs](https://docs.perplexity.ai/docs/agent-api/quickstart)
- [Exa.ai](https://exa.ai)
