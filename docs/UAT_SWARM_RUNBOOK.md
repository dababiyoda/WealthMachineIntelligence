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
| Model clients (local by default; any provider by lineage) | `src/swarm/model.py` |
| Durable ledger (append-only, locked, replayed) | `src/services/uat_store.py` |
| Mission rules / swarm standing / gates | `uat_missions.py`, `uat_swarm.py`, `uat_governor.py` |

## Run a cycle

Model routing follows the Kernel's open-source-first intent
(`uniimente-kernel/docs/OPEN_SOURCE_STACK.md`, INTENT-20260930-open-source-first).
The default route is a loopback OpenAI-protocol server: Ollama, llama.cpp, vLLM or LocalAI.
An API key in the environment never changes the route, and a local failure never falls back to a hosted provider.

```bash
OLLAMA_NO_CLOUD=1 ollama serve             # in the server's own environment
ollama pull qwen3.5:4b
export LLM_BASE_URL=http://127.0.0.1:11434/v1 LLM_MODEL=qwen3.5:4b
export UAT_LEDGER_PATH=/data/uat/ledger.jsonl   # private, persistent volume
python -m src.swarm run --focus "capital-light digital businesses ..." --max-opps 4
python -m src.swarm status
```

The local model has no web access. On research stages, any URL it cites that does not appear in its input is removed.
The governor's two-source rule then KILLs ideas the model could not verify.
Live evidence therefore comes in through seeded opportunities, a workflow `ingest`, or a future SearXNG search adapter (a residual capability deficit, not yet built).

The paid Claude route is an explicit legacy opt-in, never a default:
`pip install "anthropic>=2.1.0"`, then `UAT_MODEL_PROVIDER=anthropic` with credentials from `ANTHROPIC_API_KEY` or `ant auth login`.

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
| Call ceiling | `--max-calls` / `UAT_MAX_MODEL_CALLS` (default 60) | Bounds local inference too: zero fees are not unlimited resources |
| Cash cap | `RuntimeConfig.cash_cap_usd` (default $0) | Offers whose worst-case loss exceeds it are RECONFIGURE, never GO |
| Stage failure | refusal / truncation / invalid JSON | That mission is BLOCKED; the cycle continues |
| Resume | rerun the same `--run-id` | Cached scout results, decided missions skipped; nothing is paid twice |
| Refusal fallback (Claude opt-in only) | `fallbacks="default"` | A declined request is retried server-side on Anthropic's recommended model |
| Hosted-route refusal | `LocalClient` | Non-loopback URLs, credentials in the URL, cloud model tags and redirects are refused |

## Authority

The runtime researches, designs and drafts. It never sends, posts, spends, signs, publishes or collects. Every such step appears in the brief's **human decision queue**. A decision of VALIDATE means a capped buyer test awaiting Alfonso. It is never COMMIT, which requires accepted external evidence recorded in the ledger.

## Adding a second model lineage

Implement `complete(system, task, schema, web) -> Completion` with a distinct `lineage` string (e.g. `"grok"`), and pass both clients to `SwarmRuntime`. Red-team stages then route to the lineage that did not produce the diligence. The swarm ledger grants independent-grade credit only across lineages. Until a second lineage or external buyer acceptance exists, agents earn deterministic-grade standing only, so their autonomy rises slowly by design.

## Production checklist

- [ ] Local model server bound to loopback with `OLLAMA_NO_CLOUD=1`; model weight license recorded
- [ ] Local model quality benchmarked on one seeded cycle before scheduling (unmeasured so far)
- [ ] `UAT_LEDGER_PATH` on a private persistent volume, backed up
- [ ] Call ceiling sized to the hardware; if the Claude opt-in is used, budget reviewed against the first invoice
- [ ] Kill switch tested (`UAT_SWARM_PAUSED=1 python -m src.swarm run ...` returns `stopped`)
- [ ] First cycle's brief reviewed by Alfonso before any queued action is approved
