# UAT Earned-Authority Swarm — Invention Dossier and Market Architecture

Status: **design plus a tested vertical slice. Validate, not Commit.** This document grants no authority. Everything it describes runs in simulation. No agent, grant, payment or contact exists because of it.

Inputs:
- Alfonso's *UAT Group-Chat Operating System* and *Grok Bot Builder Answers* (2026-10-22). They are held outside this public repository.
- [`MASTER_PLAN_EFFECT_COMPILATION.md`](MASTER_PLAN_EFFECT_COMPILATION.md).
- The working code: `uat_governor.py`, `uat_missions.py` and `uat_swarm.py`.

Method: Mechanism Recombination Foundry (§1–7), then Spider-Web Hegemony (§8–15).

---

## 1. Invention field

**Transformation.** "My network becomes my wealth-building machine." The machine is a team of people and bots that keeps finding, selling and delivering income streams. It gets better with every accepted outcome while founder attention falls.

**Constraint.** The two documents design a fixed institution:
- 13 bots in 5 rooms;
- roles assigned by name;
- one review after 14 days;
- rules that, in the documents' own words, chat cannot enforce.

That design cannot scale into a swarm. Adding bots adds coordination cost and review load. Trust is also assumed from the role a bot holds, not earned from its work.

**Minimum impressive result.** A swarm can add an agent, or a human member with their own agent. That newcomer starts on full review, earns autonomy only from independently accepted work, and is credited for collected cash. None of this adds founder minutes.

**Strongest feasible result.** The same ledger becomes the trust, routing and payout layer for any team of mixed humans and agents doing paid work.

**Unacceptable harms:**
- an agent acting outside a human grant;
- bots certifying each other;
- synthetic results counted as real;
- members paid for unproven work;
- participant data reused without rights.

## 2. Mechanism cards (extracted, surface discarded)

| # | Source mechanism (from the documents) | Primitive | State | Invariant worth keeping |
|---|---|---|---|---|
| M1 | Mission contract | bounded unit of work | owner, bottleneck, acceptance, cap, deadline | No work without a falsifiable acceptance test |
| M2 | Single owner + Strategos as single assignment writer | exclusive claim | claim / version | One writer per mutable artifact |
| M3 | Handoff packet with written accept/reject | transfer with consent | pending → accepted / rejected + reason | Ownership moves only on acknowledgement |
| M4 | Veritas independent acceptance; "agreement among bots is not evidence" | adversarial verification | verdict + repair path | Producer never accepts its own work |
| M5 | Grants: scoped, expiring, $0 cap shared across bots | expiring capability | grant scope / expiry / cap | Effects need a live human grant |
| M6 | Status vocabulary, DELIVERED ≠ COLLECTED | settlement state machine | lifecycle state | Promises are not cash |
| M7 | VALIDATE … KILL decision verbs | stage gate | decision record | COMMIT needs accepted evidence |
| M8 | 14-day review against one-bot baseline; merge or pause | selection | role usefulness | Roles must earn their cost |
| M9 | Synthetic vs. real separation | sandbox boundary | synthetic flag | Rehearsal never pollutes truth |
| M10 | Mnemosyne promotes reuse only if it improves held-out work | retention with rollback | versioned asset | Learning must be tested, not declared |
| M11 | Founder minutes as a cost line | attention accounting | minutes per outcome | The scarce resource is metered |
| M12 | Eight-side ownership map | control-surface assignment | side → owner | Every side has one owner |
| M13 | Original master plan: "partial ownership… shared benefits to each team member" | participant equity | (missing) | Network members must share the upside |

## 3. Productive tensions

1. **Swarm scale vs. accountability.** More agents means more parallel work, but also more review and coordination.
2. **Speed vs. verification.** Reviewing everything is safe but does not scale; reviewing samples is fast but can be gamed.
3. **Bot independence vs. shared-model bias.** LLM judges favour their own outputs and those of their model family. Sources: [Panickssery et al. 2024](https://arxiv.org/pdf/2404.13076); [rubric-based follow-up, 2026](https://www.alphaxiv.org/abs/2604.06996).
4. **Exploration vs. exploitation.** Routing only to proven agents starves newcomers. Routing evenly wastes missions.
5. **Participant reward vs. gaming.** Paying for contribution invites farming of contributions. SourceCred paid out over $2M with automated credit and then lost funding ([Protocol Labs](https://research.protocol.ai/blog/2020/sourcecred-an-introduction-to-calculating-cred-and-grain/), [PIG proposal](https://forum.summerofprotocols.com/t/pig-revisiting-the-source-improving-the-sourcecred-credit-attribution-protocol/446)).
6. **Autonomy vs. founder sovereignty.** Founder minutes should fall without any authority leaving Alfonso.

## 4. Mutations (at least three per core mechanism)

| Mechanism | Operator | New behaviour | New failure introduced |
|---|---|---|---|
| M4 independent acceptance | *make uncertainty explicit*; *add adversarial verification across lineages* | Acceptance carries a **proof grade**. Same model family = 0, deterministic check = 0.5, different-lineage agent = 1, external actor = 2. Only an outside actor can confer "external". | Lineage labels can be misdeclared. Mitigation: lineage is set at registration, not per review. |
| M4 → M5 | *authority evidence-earned rather than role-assumed* | Graded acceptances set an agent's **tier**, which sets its review sample rate and concurrency. Grants still govern every effect. | Tier inflation from easy missions. Mitigation: standing is per stage, and only external grades unlock T1 and T2. |
| M8 14-day review | *replace periodic optimisation with continuous exploration–selection–retention*; *introduce forgetting* | Standing decays (30-day half-life). Every slot is reviewed continuously: KEEP, MERGE-OR-PAUSE or DORMANT. | Over-reaction to noise. Mitigation: contraction is one tier only, and a dormant slot is not a failed one. |
| M2 single assignment writer | *scale transfer: role → slot*; *route by verified merit* | A role becomes a **slot** that many agents can fill. Strategos routes by earned standing, with one mission in five sent to the least-proven agent. | Exploration can hand a mission to a weak agent. Mitigation: T0 agents are always fully reviewed. |
| M6 + M13 | *convert extraction into shared surplus*; *invert who benefits* | Collected cash, after the treasury waterfall, splits to the **human principals** behind the accepted work and reviews. Only as a plan for ratification. | Collusion between members. Mitigation: a member's own agents cannot review each other for credit, and reciprocal vouching counts half. |
| M9 synthetic boundary | *convert waste into input* | Synthetic rehearsals train procedures (M10) but earn zero standing and zero credit. | None material. |

## 5. Candidate matrix (12 raw configurations, by dominant mechanism)

| # | Dominant mechanism | Verdict |
|---|---|---|
| 1 | More bots per room (static roles, larger groups) | Reject: integration; raises coordination cost (§10 of the compilation) |
| 2 | Peer-rating reputation (bots rate bots) | Reject: self-preference bias and collusion |
| 3 | Token-incentive swarm (stake to participate) | Reject: capital-intensive, securities exposure, gaming |
| 4 | Pure bandit routing on task success | Reject: success judged by the swarm itself has no proof grade |
| 5 | Human-only review of everything | Reject: founder minutes explode |
| 6 | Deterministic checks only | Reject: cannot judge commercial claims |
| 7 | Contribution graph à la SourceCred, no proof grades | Reject: pays activity, not accepted cash |
| 8 | Market-based task auctions between agents | Reject: price discovery is premature with zero revenue |
| 9 | **Proof-graded, decaying, per-stage standing → tiers → routing → contribution settlement** | **Winner** |
| 10 | Winner without settlement | Keep as fallback; loses the "network becomes wealth" effect |
| 11 | Winner + cross-team rail for other human–agent teams | Descendant (Level 5), not now |
| 12 | Winner + work-quality underwriting / insurance | Frontier descendant (Level 6) |

## 6. Emergent capability

What it can do that no source mechanism could alone: **the swarm can grow (new agents, new lineages, new human members) while review load and founder minutes per accepted outcome stay flat or fall. Trust, routing priority and payout all come from the same proof-graded record, and any of them is lost the same way they were earned.**
- Grants alone are static.
- Reputation alone is gameable by bots vouching for bots.
- Contribution graphs alone pay for activity.
- Combined, each mechanism closes the others' attack surface. Proof grades stop the vouching loop. Decay and contraction stop rent-seeking on old standing. Settlement on collected cash only stops activity farming. Grants keep authority human.

## 7. Novelty boundary

**Known.** Each of these exists:
- reputation-weighted task allocation for LLM agents (preprints: [Qi et al.](https://arxiv.org/pdf/2509.16736), [DART](https://arxiv.org/pdf/2609.05529), [DRF](https://arxiv.org/html/2509.05764v1));
- skill-conditional trust ([arXiv 2606.14200](https://arxiv.org/pdf/2606.14200));
- contribution-based payouts (SourceCred);
- qualification tiers (crowdsourcing platforms);
- expiring capabilities (security engineering).

**Claimed distinction (design-level, not legal novelty):**
- reputation that discounts acceptance by **reviewer lineage independence** and counts only **external acceptance** toward higher autonomy;
- autonomy that changes **review intensity and concurrency, never consequence authority**;
- payout attributed to **human principals from collected cash only**, after a regenerative treasury waterfall.

**Uncertain.** Whether a published system already combines lineage-discounted acceptance with principal-level cash settlement. No patent search has been performed.

---

## 8. Governing transaction (Spider-Web)

> **Alfonso (and later each member) must obtain accepted, paid outcomes from a growing set of agents and people, but completion is unreliable because *who did what, how well it was independently proven, and who may therefore be trusted with more* is broken.**

- **Start:** a mission is opened (`uat_missions.open`).
- **End:** cash is collected with evidence.
- **Valid completion:** independent or external acceptance, then a COLLECTED state.
- **Pain owner and payer today:** Alfonso (founder minutes, risk).
- **Beneficiaries:** members, customers.
- **Verifier:** an outside buyer for external grade; a different-lineage agent for independent grade.
- **Workaround today:** Alfonso reads everything himself.
- **Cheapest falsification test:** run two lineages in one slot on the live pilot. If cross-lineage review never catches a defect that same-lineage review missed, the proof grade adds nothing.

**Thesis.** Become the accepted control layer for human–agent paid work by controlling **proof-graded acceptance** at the **moment of review**. Issue a **standing record** (tier plus contribution plan) and tie it to **review load, routing priority and member payout**. Single-vendor bot platforms cannot copy this without admitting their own models are not independent reviewers of themselves (counter-position, §10 side 7).

**Business form now: Service** (internal operating method for UAT ventures).
- **Premature:** Platform or Rail for other teams. Requires ≥3 paid missions with external acceptance, ≥1 external member paid by plan, and a documented catch by cross-lineage review.
- **Kill condition for transition:** contribution plans disputed by members more than once per 10 payouts.

## 9. Four super-nodes

| Super-node | Mechanism | Code |
|---|---|---|
| Eligibility | Tier (T0/T1/T2) per agent per stage; grants for any effect | `SwarmLedger.tier`, `ControlRecord.authorize_effect` |
| Default routing | Proof-weighted assignment with an exploration slot and capacity caps | `SwarmLedger.route` |
| Proof / truth | Graded acceptance; synthetic = 0; reviewer ≠ producer | `SwarmLedger.effective_grade`, `ControlRecord.review` |
| Cashflow / settlement | Evidence-backed collection → treasury waterfall → contribution plan for ratification | `ControlRecord.record_collection`, `RegenerativeTreasury.waterfall`, `SwarmLedger.contribution_plan` |

Chain: eligibility limits what an agent may take on. Routing sends each mission to the best eligible agent. Proof grades decide whether the work counts. Settlement turns counted work on collected cash into member shares.

## 10. Eight sides (compressed)

1. **Failure geometry.** The failure is founder review time per accepted outcome, plus defects that pass same-family review. Denominator: missions per week. Owner: Opportunity Foundry.
2. **Power geometry.** Alfonso is the root. Members are principals. Buyers are external verifiers. Model vendors are dependencies. Coalition: members gain pay and standing; buyers gain cleaner work; Alfonso gains minutes.
3. **Eligibility.** Earned tiers, appealable to Alfonso. T0 is always fully reviewed. *Attack:* farming easy missions. *Defence:* standing is per stage, and only external grades unlock tiers.
4. **Routing.** Earned standing plus 20% exploration, under capacity caps. *Attack:* starving newcomers. *Defence:* the deterministic exploration bucket.
5. **Proof.** Lineage-graded acceptance with explicit downgrades. *Attack:* lineage misdeclaration or collusion. *Defence:* lineage fixed at registration, same-member review refused, reciprocity discount.
6. **Settlement.** Collected cash only. Waterfall first (operating, reserve floor, ≥10% regenerative), then contribution plan, then human ratification. *Attack:* payout disputes. *Defence:* every unit traces to a graded outcome record.
7. **Distribution and counter-position.** Members bring their own agents and networks, and each new member brings access. Single-vendor bot platforms (Grok Bot included) are structurally weak at certifying their own models. Cross-lineage proof is something a mixed swarm has and a single-vendor swarm cannot easily copy.
8. **Reliability and governance.** `execution_authority=False` everywhere. Alfonso alone grants effects. Contraction on rejection is immediate. Slot review is continuous. Kill: pause any slot whose tier rose without an external grade.

## 11. Loops and metrics

**Loops:**
- **Operational:** accepted work → standing → lighter review → more throughput per founder minute.
- **Capital:** collected cash → waterfall → reserves + regenerative share → more missions.
- **Institutional:** cross-lineage catches → evidence that the proof grade works → member trust.
- **Regenerative:** members paid by plan → better members join → more access edges for scouts.

**Metrics:**
- **Active Single Bottleneck Metric:** verified net cash collected from paying customers of network-sourced offers, trailing 30 days (unchanged).
- **Swarm health metric:** founder minutes per externally accepted outcome. It must fall as agents are added. If it rises, the swarm is decorative.
- **Clean completion rate:** externally accepted ÷ missions closed.
- **Integrity metric:** defects caught by cross-lineage review that same-lineage review passed. If this stays at zero after 20 reviews, the proof grade is unproven.

## 12. Adversaries and recursion (key rebuilds)

- **Bots collude to inflate standing.** Same-lineage review earns 0. Same-member review is refused. Reciprocal pairs count half.
- **Model vendor changes behaviour silently.** Decay plus contraction re-prices standing within one window. Tiers never carry effect authority, so the blast radius is review load, not consequences.
- **Members game payouts.** Payout only exists on evidence-backed collected cash, after the waterfall, with human ratification.
- **Round 1: constraint → advantage.**
  - Zero revenue becomes the reason only external acceptance unlocks tiers.
  - Single-vendor risk becomes the cross-lineage proof grade.
  - Founder bandwidth becomes the swarm health metric.
  - A public repository becomes auditability of the rules, not the data.
  - A small network becomes the exploration bucket that lets each new member earn quickly.
- **Round 2: elevation.** Once standing records are trusted internally, the same record can back a member's claim about their own track record to outside buyers. Proof travels with the person, which is the "participants become more eligible" doctrine. *New vulnerability:* outside reliance on a self-issued record, which requires external audit before it is offered.

## 13. Cumulative ladder

| Level | Stage | Status |
|---|---|---|
| 1 | Seed: proof-graded acceptance + tiers | **Built** (`uat_swarm.py`, tests) |
| 2 | Compound: routing + mission record + governor | **Built** (simulation); not yet wired to live bots |
| 3 | Substrate: one ledger shared by Grok bots, Claude agents and member agents | Experimental: needs an adapter from Grok group events into `Outcome` records |
| 4 | Developmental: slots merge, split or pause from `slot_review` evidence | Experimental |
| 5 | Rail: other human–agent teams adopt the standing record | Frontier: needs external demand |
| 6 | Capital layer: work-quality history lowers cost of guarantees and insurance for member services | Frontier |
| 7 | Descendant: portable, independently audited work-standing that institutions accept in place of credentials | Science fiction at required trust levels today |

## 14. Five-outcome scores (current stage)

| Outcome | Score | Blocker |
|---|---|---|
| Commercial | 2 | No paid mission yet |
| Strategic | 3 | Proof grade designed, not yet externally demonstrated |
| Regenerative | 4 | Members can earn from proven work; no payouts yet |
| Institutional | 4 | Authority unchanged; rules auditable; Kernel remains canonical |
| Capital | 3 | $0 spend; waterfall enforced; no surplus yet |

Commercial is below 3, so Commit is barred.

## 15. Decision

Mechanism Recombination Foundry: **EXPERIMENT**. Spider-Web Hegemony: **Validate**.

- **Next external action.** On the live pilot, put two Concord agents of different lineages in the slot (e.g. the Grok Concord plus a Claude agent). Have each draft the same reply; review them crosswise. Record every review as an `Outcome`.
- **Numbers that must change:**
  - first externally accepted outcome (buyer reply that commits scope or price);
  - cross-lineage catches > 0 within 20 reviews;
  - founder minutes per accepted outcome falling across the first five.
- **Evidence:** the outcome records, Alfonso's minute log, and the buyer's written words.
- **Deadline:** 30 days from the first recorded review.
- **Termination:** zero cross-lineage catches after 20 reviews means drop the lineage requirement. If founder minutes per outcome rise for three consecutive outcomes, collapse back to one bot per active slot.
