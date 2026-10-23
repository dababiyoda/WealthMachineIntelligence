# UAT Swarm — Production Runbook

The UAT swarm is the founder's thirteen-role team run as real agents inside WealthMachine:
- **Scouting:** Prometheus.
- **Diligence:** Logos.
- **Red team:** Veritas, Aegis and Strategos.
- **Offer design:** Daedalus.
- **Downside limits:** Aurelius.
- **Legal:** Aegis.
- **Drafts:** Concord.
- **Decisions:** a deterministic governor, the Direction & Capital verbs, and an independent review.

Every step lands in one durable ledger.

| Piece | Code |
|---|---|
| Agent runtime (one cycle, guards, brief) | `src/swarm/runtime.py` |
| Roles, prompts, strict output schemas | `src/swarm/roles.py` |
| Model clients (Claude now; any provider by lineage) | `src/swarm/model.py` |
| Durable ledger (append-only, locked, replayed) | `src/services/uat_store.py` |
| Mission rules / swarm standing / gates | `uat_missions.py`, `uat_swarm.py`, `uat_governor.py` |

## Run a cycle

```bash
pip install -r requirements.txt            # includes anthropic>=2.1.0
export ANTHROPIC_API_KEY=...               # or: ant auth login
export UAT_LEDGER_PATH=/data/uat/ledger.jsonl   # private, persistent volume
python -m src.swarm run --focus "capital-light digital businesses ..." --budget 25 --max-opps 4
python -m src.swarm status
```

Outputs:
- **Ledger:** every mission, decision and graded outcome, written to `UAT_LEDGER_PATH`.
- **Artifacts:** each stage's output as JSON in `runs/uat/<mission>/<stage>.json`.
- **Founder brief:** `runs/uat/<run-id>-brief.md`. It covers the VALIDATE list, the human decision queue, and items marked RECONFIGURE, PARK or KILL.

To bring a Claude Code workflow run (`.claude/workflows/uat-income-loop.js`) into the same ledger:

```bash
python -m src.swarm ingest runs/uat/<label>-dossier.json
```

## Schedule (Docker or cron)

```bash
# weekly cycle, Monday 08:41 America/New_York
41 8 * * 1  cd /app && UAT_LEDGER_PATH=/data/uat/ledger.jsonl python -m src.swarm run --focus "$UAT_FOCUS" >> /data/uat/cycles.log 2>&1
```

The ledger must sit on a private, persistent volume. **Never commit it to this public repository.**

## Guards

| Guard | Setting | Behaviour |
|---|---|---|
| Kill switch | `UAT_SWARM_PAUSED=1` | No cycle starts |
| Spend ceiling | `--budget` / `UAT_CYCLE_BUDGET_USD` (default $25) | The next model call is refused once reached; the in-flight mission is marked BLOCKED |
| Cash cap | `RuntimeConfig.cash_cap_usd` (default $0) | Offers whose worst-case loss exceeds it are RECONFIGURE, never GO |
| Stage failure | refusal / truncation / invalid JSON | That mission is BLOCKED; the cycle continues |
| Resume | rerun the same `--run-id` | Cached scout results, decided missions skipped; nothing is paid twice |
| Refusal fallback | `fallbacks="default"` | A declined request is retried server-side on Anthropic's recommended model |

## Authority

The runtime researches, designs and drafts. It never sends, posts, spends, signs, publishes or collects. Every such step appears in the brief's **human decision queue**. A decision of VALIDATE means a capped buyer test awaiting Alfonso. It is never COMMIT, which requires accepted external evidence recorded in the ledger.

## Adding a second model lineage

Implement `complete(system, task, schema, web) -> Completion` with a distinct `lineage` string (e.g. `"grok"`), and pass both clients to `SwarmRuntime`. Red-team stages then route to the lineage that did not produce the diligence. The swarm ledger grants independent-grade credit only across lineages. Until a second lineage or external buyer acceptance exists, agents earn deterministic-grade standing only, so their autonomy rises slowly by design.

## Production checklist

- [ ] `ANTHROPIC_API_KEY` stored as a secret, not in `.env` committed to git
- [ ] `UAT_LEDGER_PATH` on a private persistent volume, backed up
- [ ] Budget set per cycle and reviewed against the first invoice (cost estimates in `model.py` are estimates)
- [ ] Kill switch tested (`UAT_SWARM_PAUSED=1 python -m src.swarm run ...` returns `stopped`)
- [ ] First cycle's brief reviewed by Alfonso before any queued action is approved
