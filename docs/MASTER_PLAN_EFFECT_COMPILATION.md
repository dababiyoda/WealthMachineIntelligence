# Master Plan Effect Compilation — "My Network Becomes My Wealth-Building Machine"

Status: **interpretation and recommendation only.** WMI assesses and proposes; this document grants no authority to recruit, contract, spend, solicit capital, publish, or contact anyone.
Source: [`docs/intent/MASTER_PLAN_UAT_SOURCE.md`](intent/MASTER_PLAN_UAT_SOURCE.md) (verbatim).
Doctrine: Kernel `INTENT-0030` / `FOUNDER_EFFECT_COMPILER.md` — preserve the effect, do not literalize the metaphor, build only the residual deficit.

## 1. Preserved destination

A group of people drawn from Alfonso's network who, together and augmented by AI, repeatedly **find → validate → build → launch → automate** income streams, so that:

1. the portfolio's reconciled net cash flow compounds as streams are added and reinvested;
2. each member becomes measurably more capable and more trusted over time ("rise by lifting others");
3. members hold real, legally enforceable shares of what they help create;
4. streams eventually run without members operating them day to day, freeing the group to start the next loop.

None of this is shrunk below. What changes is how it is reached and how success is measured.

## 2. Literal requirements vs. aspiration

| Source language | Treat as | Compiled requirement |
|---|---|---|
| "guarantees financial abundance", "little to no risk, and the largest rewards", "bulletproof … can not go wrong", "foolproof", "even if … dumb mistakes, they will succeed" | Aspiration resting on a **false premise** | No plan removes venture risk: roughly a third of U.S. establishments born in 2013 were still operating ten years later (BLS). The real effect is **bounded downside + survival long enough to compound**: every experiment has a pre-set loss cap and kill date, and no single mistake may be fatal to the group. "Foolproof" compiles to *mistake-tolerant*, not *mistake-proof*. |
| High demand + low competition + no capital + low overhead + easy to scale, all at once | Filter wording; literally rare | Open opportunities with all five properties are usually arbitraged away. When they persist, it is because of a **barrier only some people hold** — access, trust, local knowledge, a license, a relationship. That barrier is the network itself. Search for opportunities where the network's access *is* the edge. |
| Eight roles, eight people | Function list, not headcount | Eight **functions** must be covered. At the start, two or three people plus WMI agents and commodity tools can cover all eight. Add a person to a function only when that function is the measured bottleneck. |
| Sequential handoff (Scout → Analyst → Planner → Finance/Legal → Tech/Marketing) | Mechanism, but a slow one | A relay with research before contact with buyers is the slowest learning loop available. The fastest loop is: one member puts a priced offer in front of a real buyer before anything is built. Research supports that conversation; it does not replace it. |
| "Exhaustive market research", ML/LSTM trend prediction | Aspiration | At Phase 1 scale, a paid pre-commitment is stronger evidence than any model forecast. Models earn a role once there is real transaction data to fit. |
| "An AI cog within a larger AI system … granting partial ownership" | Metaphor + real ownership requirement | Each member runs an AI-augmented workflow (achievable today). **Ownership must be a legal instrument** — operating agreement, vesting, profit interests — not a software construct. |
| Phase 2: preservation via "blockchain technologies or disruptive AI platforms" | Internal contradiction | Preservation and speculation are different buckets. Preservation means diversified, boring, liquid assets; any speculative allocation is a capped share of surplus, never the reserve. The existing treasury waterfall already encodes this order. |
| "Networking Specialist … looking for favors … non-equity partnerships" | Mechanism with an incentive gap | Favors do not scale and wear relationships down. Compile to **reciprocal, written** arrangements: referral fees, revenue share, introductions traded for introductions. |

## 3. Red team — how this plan most likely fails

Ranked by probability × severity, with the counter-measure that converts each into an advantage.

1. **People failure inside a friends-and-family team.** Wasserman's research (≈10,000 founders) attributes about 65% of failures among high-potential startups to people problems, and finds the gap between expectation and outcome is widest for co-founders with a prior social relationship. A team assembled from Alfonso's network carries exactly this exposure.
   *Counter:* before the first shared dollar — written roles and decision rights, a single decider per venture, vesting with a cliff, buy-out and exit terms, a dispute process. Written terms protect the relationships the plan depends on.
2. **Accidental securities offering.** If members (or their friends and family) put in money expecting profits mainly from others' efforts, that can be an investment contract under *SEC v. W.J. Howey Co.* (investment of money, common enterprise, expectation of profit, efforts of others). "Everyone's LLC is in the business" can trigger this when some members are passive.
   *Counter:* ownership goes only to active contributors, earned through recorded contribution. No outside or passive capital is raised without securities counsel and a documented exemption. Phase 1 is designed to need no outside capital at all.
3. **Research loop with no revenue.** Eight functions, weekly SMART goals and a strong business plan can produce motion with no customers. *Counter:* the Single Bottleneck Metric below; every SMART goal must trace to it.
4. **Unclear ownership of contribution.** The plan never says how a scout's lead, a networker's introduction or a builder's hours turn into equity or cash. Without that rule, the "interdependent loop" degrades into resentment. *Counter:* a contribution ledger (§6).
5. **Over-building the machine before it has fuel.** This repository already holds a sophisticated simulation stack while recorded real-world economic outcomes remain zero (`Instructions.md`: "CMC and VDM remain zero"). More orchestration code does not move the bottleneck.

## 4. Single Bottleneck Metric

**Verified net cash collected from paying customers of network-sourced offers, trailing 30 days.**

Leading indicator for Phase 1: **paid pre-commitments (deposit, signed paid pilot, or prepayment) per opportunity within 14 days of first buyer contact.**

Everything else — opportunities scouted, partnerships formed, brand awareness, prediction accuracy — is reported only as a driver of these two numbers. A role whose weekly SMART goal cannot be traced to one of them is not yet a role.

## 5. The deeper control layer

The plan's real asset is not the eight roles. It is **trusted access**: people in the network who are already inside businesses, trades and communities and can get an honest answer and a paid commitment that a stranger cannot. That matches the operating doctrine directly — money trapped behind broken trust, routed through people who already hold it.

So the rail to build is the one that makes each member **more capable, more trusted, and easier to transact with**:

- a standard, reusable member agreement (how contribution becomes ownership);
- a contribution ledger (who sourced, sold, built, delivered — with timestamps and evidence);
- standard kill rules and loss caps (bounded downside, applied the same way every time);
- the treasury waterfall (operating → reserve floor → regenerative share → distributions), already implemented.

Each new member enters a working system rather than an idea; each successful stream strengthens the record that makes the next member, partner and customer easier to admit. That is the compounding loop the source describes, made mechanical.

## 6. What already exists, and the residual deficit

| Plan component | Existing WMI capability | Status |
|---|---|---|
| Venture Scout / Market Analyst | `src/services/opportunity_intake.py`, `src/services/market_monitor.py`, `roles/EmergingTechSpecialist.md`, `roles/StrategicMarketTrendAnalyst.md` | Present (synthetic inputs) |
| Adversarial validation ("fact-check, confirm viability") | `src/services/adversarial.py` underwriting cases | Present |
| Product / Business Planner, offer definition | `src/services/venture_protocol.py`, `src/services/business_loop.py` (`Offer`) | Present |
| Financial Strategist, reinvestment | `src/services/treasury.py` waterfall (human-ratified), `src/services/risk_management.py` | Present |
| Phases 1–3 gates | `src/services/phase_management.py`, `phases/` | Present |
| Weekly SMART goals, Team Loop | `src/core/performance.py` (`SMARTGoal`, `PerformanceTracker`), `loops/TeamLoop.md` | Present |
| Eight role agents | `src/agents/specialized.py`, `roles/*.md`, `src/network_my_networth/system.py` | Present (simulation) |
| Legal Counsel | Compliance flags only | Correctly a human/counsel function |

**Residual CapabilityDeficit — mostly not code:**

1. **Real members.** Zero people recruited into functions under signed terms.
2. **Real buyers.** Zero real offers sold; the pipeline has only processed synthetic packets.
3. **Contribution → ownership rule and ledger.** Not defined anywhere. Start with a shared spreadsheet or Airtable base (resourcefulness ladder rung 3), not new code. Build software only once the manual ledger is in use and its rules have stabilised.
4. **A real-evidence path into intake.** Assessments should accept the result of an actual buyer conversation (quote, objection, price, deposit) as evidence, not only scored signals. Small adapter, deferred until (1)–(2) produce data.

No new orchestration, agent hierarchy or ML layer is warranted until the metric in §4 is non-zero.

## 7. Backcast — first 30 days (proposal, requires Alfonso's decision)

| Week | Action | Kill / continue rule |
|---|---|---|
| 1 | List roughly 50 network contacts; tag the industry, access and recurring paid problem each one sees. Choose 2–3 candidate wedges where the network's access is the edge. | Fewer than 3 contacts confirming the same paid problem → drop that wedge. |
| 1 | Draft the one-page member terms (roles, decision rights, vesting, contribution rule, exit) for counsel review. No shared money moves before this. | — |
| 2 | One priced offer per surviving wedge, in front of at least 10 real buyers, by people already holding that access. | Fewer than 2 paid pre-commitments in 14 days → kill or re-price once. |
| 3–4 | Deliver manually to the first payers. Record every contribution in the ledger and every dollar through the treasury waterfall (human-ratified). | Gross margin below the agreed floor after first deliveries → kill. |
| 30 | Review: SBM value, ledger, what each member learned. Only then decide which function to staff or automate next. | Retain / modify / regress / kill per the Kernel loop. |

Loss cap per experiment (recommended, Alfonso to set): small fixed cash ceiling and 30-day time box, so that ten failed experiments are survivable and one success pays for them.

## 8. All-agent workflow

The eight roles run as agents in one Claude Code workflow, [`.claude/workflows/uat-income-loop.js`](../.claude/workflows/uat-income-loop.js). One run is one cycle of the Income Streams Loop and the Team Loop. Agents research, argue and draft. A deterministic governor, [`src/services/uat_governor.py`](../src/services/uat_governor.py) (tested in `tests/test_uat_governor.py`), decides. Alfonso authorizes every consequence.

| Stage | Agent(s) | Output |
|---|---|---|
| Scout | Networking Specialist (network wedges), Venture Scout (brick-and-mortar pain), Emerging Tech Specialist (newly cheap delivery), run in parallel | Opportunities with access edge and ≥2 sources, deduplicated, network-edge first |
| Validate | Strategic Market Trend Analyst | Fact-check, demand evidence, competitors, price anchor |
| Red team | Three independent refuters: market, legal, people | Refutations with severity; ideas with ≥2 refutations or one critical refutation stop here |
| Design | Product Development + Business Model + Tech Innovator | Smallest refundable priced offer, delivered manually first with existing tools |
| Bound | Financial Strategist and Legal Counsel, in parallel | Worst-case loss, Fermi estimate, kill rules; lawfulness flags and contribution-to-ownership note |
| Go-to-market | Brand Strategist + Networking Specialist | Draft outreach, buyer script, reciprocal partner terms, proposed actions |
| Govern | `uat_governor.py` (no model judgment) | KILL / REWORK / HOLD_FOR_COUNSEL / GO, ranked by projected SBM per dollar of worst-case loss, plus the human decision queue |
| Team Loop | Whole team | Decision brief: ranked GOs, decision queue, 30-day backcast, weekly SMART goal per role traced to the SBM, contribution ledger, next scouting focus |

To run it in Claude Code, say "run the uat-income-loop workflow" with optional args: `{focus, network, loss_cap_usd, timebox_days, min_gross_margin, max_opportunities, out_dir, run_label}`. The richer `network` is (who you know, where they work, what they can see), the stronger the wedges. Outputs go to `runs/uat/` (git-ignored, because drafts may name real people).

Authority envelope for every agent: research and drafts only. Agents never send, post, contact, purchase, sign or spend. Every real-world step comes back as a queued action requiring approval, and the governor hardcodes `execution_authority: false`.

## 9. The thirteen-bot institution (Grok group chats)

Source: Alfonso's *UAT Group-Chat Operating System* and *Grok Bot Builder Answers* (both dated 2026-10-22). They are held outside this repository: the repository is public, and both files name founder mailboxes and pilot counterparties. They turn the eight roles into thirteen named bots in five mission groups of at most six bots each. Each group has a coordinator, and work moves between groups through written handoffs.

**Mapping to the workflow.** `.claude/workflows/uat-income-loop.js` is the Opportunity Foundry run as one cycle, with stages named after the bots:

| Workflow stage | Bot | Group |
|---|---|---|
| Scout (network / street / tech) | Concord with Prometheus; Prometheus | Opportunity Foundry / Revenue |
| Diligence | Logos | Opportunity Foundry |
| Red team: market / legal / people | Veritas / Aegis / Strategos | Foundry / Direction |
| Offer design | Daedalus with Vulcan | Foundry / Delivery |
| Bound downside | Aurelius and Aegis | Foundry / Direction |
| Go-to-market drafts | Mythos and Concord | Revenue & Partnerships |
| Govern (code) | `uat_governor.py`: GO→VALIDATE, REWORK→RECONFIGURE, HOLD→PARK, KILL→KILL | Direction & Capital decides |
| Team Loop brief | Strategos, Hegemony, Mnemosyne | Direction / Compounding |

A gate pass earns VALIDATE, a bounded buyer test, and never COMMIT. COMMIT requires accepted external evidence.

**Enforced vs. instructed.** The design itself warns that chat cannot enforce its rules ("never pretend textual claims are locks"). [`src/services/uat_missions.py`](../src/services/uat_missions.py) is the canonical record those rules point to, made checkable (tests in `tests/test_uat_missions.py`):

| Rule from the design | Where it holds |
|---|---|
| Five groups, ≤6 bots each, all 13 roles covered | Enforced (`validate_roster`) |
| Mission contract fields present; unknown fields named | Enforced (`open`) |
| One owner per mission; stale artifact versions refused | Enforced (`claim`, `save_artifact`) |
| Handoff needs current artifact and written accept/reject with reason | Enforced (`handoff`, `respond_handoff`) |
| Reviewer ≠ producer; unsupported claims rejected with repair path | Enforced (`review`) |
| External effect needs an unexpired grant naming that action, within cap | Enforced (`authorize_effect`) |
| Uncertain external result → reconcile, never blind retry | Enforced (`record_effect_result`) |
| No collection without evidence; synthetic never counted as real | Enforced (`record_collection`, `totals`) |
| COMMIT only after accepted evidence | Enforced (`decide`) |
| Connector scope, mailbox identity, profile isolation, group approvals, timers | **Instruction only.** Grok profiles do not provide technical isolation. Verify each one on the live platform. |

The record never acts (`execution_authority = False`). It is WMI's reference implementation. Where the live record sits (Notion, Airtable or the Kernel ledger) is Alfonso's choice. Institutional authority stays with the Kernel.

**Assessment.**
- **Strengths.** The design is unusually self-skeptical. It already embodies this compilation: $0 new spend, one active mission, no fabricated acceptance, and a review after 14 days against a single bot with simple tools.
- **Main risk: coordination cost before the first dollar.** Thirteen bots and five rooms carry overhead. Anthropic's own multi-agent report shows that coordination cost is high and that tightly dependent tasks fit multi-agent setups poorly ([Anthropic, 2025](https://www.anthropic.com/research/multi-agent-research-system)).
- **Recommendation.** Activate only Opportunity Foundry and Revenue & Partnerships until the first paid commitment exists. Alfonso and Strategos can carry Direction & Capital.
- **Platform facts checked.** Grok groups hold two to six bots, and @-mentions target a specific bot ([xAI docs](https://docs.x.ai/grok-bot/chat-and-collaboration)). The approvals and privacy page could not be reached from this environment, so the group-approval limits in the design remain unverified here.

## 10. Decisions reserved to Alfonso

- Whether to proceed with §7, and the loss cap per experiment.
- Who the first two or three members are, and the contribution-to-ownership rule.
- Engagement of legal counsel before any shared money or entity formation.

## Evidence and sources

- U.S. Bureau of Labor Statistics, *34.7 percent of business establishments born in 2013 were still operating in 2023* — https://www.bls.gov/opub/ted/2024/34-7-percent-of-business-establishments-born-in-2013-were-still-operating-in-2023.htm
- Cornell LII, *Howey test* (SEC v. W.J. Howey Co., 328 U.S. 293 (1946)) — https://www.law.cornell.edu/wex/howey_test
- Noam Wasserman, *The Founder's Dilemmas* (Princeton UP, 2012); the 65% "people problems" figure as reported from his Techstars talk — https://builtin.com/articles/noam-wasserman-visits-techstars-boulder-shines-light-made-data-founding-pitfalls-can-kill-your-
- Wasserman on co-founders with prior social relationships — https://thecrimson.com/article/2012/4/9/hbs-start-noam-founder

This document is not legal advice. Securities and entity questions require licensed counsel in the relevant jurisdiction.
