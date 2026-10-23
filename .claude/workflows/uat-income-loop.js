export const meta = {
  name: 'uat-income-loop',
  description: 'UAT Opportunity Foundry run by the named bots (Prometheus, Logos, Veritas, Aegis, Daedalus, Aurelius, Mythos, Concord, Strategos): scout, diligence, red-team, design, govern and hand off income-stream proposals (no external effects)',
  whenToUse: 'Run one Income Streams Loop + Team Loop cycle of the master plan. Args: {focus, network, loss_cap_usd, timebox_days, min_gross_margin, max_opportunities, out_dir, run_label}',
  phases: [
    { title: 'Scout', detail: 'Venture Scout + Networking Specialist sweep three lenses' },
    { title: 'Validate', detail: 'Analyst, red team, product/model/tech, finance, legal, brand/network per opportunity' },
    { title: 'Govern', detail: 'Deterministic gate: src/services/uat_governor.py' },
    { title: 'Team Loop', detail: 'Portfolio brief, SMART goals traced to the SBM, decision queue' },
  ],
}

// Source: docs/intent/MASTER_PLAN_UAT_SOURCE.md
// Interpretation: docs/MASTER_PLAN_EFFECT_COMPILATION.md
// Every role is an agent. Agents research, argue and draft; the Python
// governor decides; Alfonso authorizes every consequence.

const A = args || {}
const FOCUS = A.focus || 'recurring, paid, physical-world problems reachable through a personal network in the United States'
const NETWORK = A.network || 'not provided: infer access edges only from the focus, and mark network_edge false unless the access is stated'
const POLICY = {
  loss_cap_usd: A.loss_cap_usd ?? 500,
  timebox_days: A.timebox_days ?? 30,
  min_gross_margin: A.min_gross_margin ?? 0.4,
  min_sources: 2,
}
const MAX_OPPS = A.max_opportunities ?? 6
const OUT = A.out_dir || 'runs/uat'
const LABEL = A.run_label || 'run'

const AUTHORITY = `
AUTHORITY ENVELOPE (non-negotiable): you are one role on Alfonso Lopez's Universally Adaptive Team, running as an agent.
You may research (web search, reading public pages, reading this repository) and write drafts.
You may NOT send, post, email, message, call, sign up, purchase, spend, sign, or contact any person or business.
Outreach is DRAFT text only. Any real-world action is proposed as an "action" for Alfonso to approve.
Cite a URL for every factual claim; label estimates as estimates. Prefer primary sources (government data, filings, regulators, official docs).
The plan's false premise is "risk-free, foolproof". Your job is bounded downside, not certainty: say what could kill the idea.
Single Bottleneck Metric: verified net cash collected from paying customers of network-sourced offers, trailing 30 days.`

const SRC = { type: 'array', items: { type: 'object', properties: { url: { type: 'string' }, claim: { type: 'string' } }, required: ['url', 'claim'] } }

const SCOUT_SCHEMA = {
  type: 'object',
  properties: {
    opportunities: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string', description: 'short kebab-case id' },
          one_liner: { type: 'string' },
          buyer: { type: 'string' },
          recurring_paid_problem: { type: 'string' },
          access_edge: { type: 'string', description: 'why this network can reach/serve buyers a stranger cannot; empty if none' },
          network_edge: { type: 'boolean' },
          why_now: { type: 'string' },
          evidence: SRC,
        },
        required: ['name', 'one_liner', 'buyer', 'recurring_paid_problem', 'access_edge', 'network_edge', 'evidence'],
      },
    },
  },
  required: ['opportunities'],
}

const ANALYST_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['viable', 'weak', 'not_viable'] },
    demand_evidence: SRC,
    competitors: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, url: { type: 'string' }, price: { type: 'string' } }, required: ['name'] } },
    price_anchor_usd: { type: 'number' },
    notes: { type: 'string' },
  },
  required: ['verdict', 'demand_evidence', 'competitors', 'notes'],
}

const RED_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    refuted: { type: 'boolean' },
    severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] },
    argument: { type: 'string' },
    evidence: SRC,
  },
  required: ['lens', 'refuted', 'severity', 'argument'],
}

const OFFER_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    deliverable: { type: 'string' },
    price_usd: { type: 'number' },
    unit_cost_usd: { type: 'number' },
    delivery_days: { type: 'number' },
    delivered_manually_first: { type: 'boolean' },
    refundable: { type: 'boolean' },
    tools: { type: 'array', items: { type: 'string' }, description: 'existing tools/APIs/AI used; build nothing new for the first sale' },
    differentiation: { type: 'string' },
    expansion_paths: { type: 'array', items: { type: 'string' }, description: 'sub-niches, B2B/B2C, adjacent offers once paid demand is proven' },
  },
  required: ['title', 'deliverable', 'price_usd', 'unit_cost_usd', 'delivery_days', 'refundable'],
}

const FINANCE_SCHEMA = {
  type: 'object',
  properties: {
    max_loss_usd: { type: 'number', description: 'worst-case cash loss of this experiment' },
    expected_paid_commitments_14d: { type: 'number', description: 'estimate from 10 buyer conversations' },
    fermi: { type: 'string', description: 'show the arithmetic and anchors' },
    kill_rules: { type: 'array', items: { type: 'string' } },
    reinvestment_note: { type: 'string' },
  },
  required: ['max_loss_usd', 'expected_paid_commitments_14d', 'fermi', 'kill_rules'],
}

const LEGAL_SCHEMA = {
  type: 'object',
  properties: {
    flags: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          issue: { type: 'string' },
          blocking: { type: 'boolean', description: 'true if the first sale cannot lawfully happen until resolved' },
          requires_counsel: { type: 'boolean' },
          source_url: { type: 'string' },
        },
        required: ['issue', 'blocking', 'requires_counsel'],
      },
    },
    member_terms_note: { type: 'string', description: 'how contribution becomes ownership for this venture' },
  },
  required: ['flags', 'member_terms_note'],
}

const GTM_SCHEMA = {
  type: 'object',
  properties: {
    buyer_profile: { type: 'string' },
    positioning: { type: 'string' },
    outreach_drafts: { type: 'array', items: { type: 'object', properties: { channel: { type: 'string' }, draft: { type: 'string' } }, required: ['channel', 'draft'] } },
    conversation_script: { type: 'array', items: { type: 'string' } },
    partners: { type: 'array', items: { type: 'object', properties: { who: { type: 'string' }, ask: { type: 'string' }, give: { type: 'string' } }, required: ['who', 'ask', 'give'] } },
    actions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['contact', 'spend', 'sign', 'publish', 'collect_payment', 'raise_capital', 'form_entity', 'research'] },
          description: { type: 'string' },
          passive_investors: { type: 'boolean' },
        },
        required: ['type', 'description'],
      },
    },
  },
  required: ['buyer_profile', 'outreach_drafts', 'conversation_script', 'partners', 'actions'],
}

const slug = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
const brief = o => `Opportunity "${o.name}": ${o.one_liner}\nBuyer: ${o.buyer}\nProblem: ${o.recurring_paid_problem}\nAccess edge: ${o.access_edge || 'none stated'}\nScout evidence: ${JSON.stringify(o.evidence)}`

// ---------------------------------------------------------------- Scout
phase('Scout')
const LENSES = [
  { key: 'network', role: 'Concord (Customer Access, Sales and Partnerships), scouting with Prometheus',
    ask: `Mine the network for wedges. Network description: ${NETWORK}. Find recurring paid problems that people in this network can see from the inside (their employers, trades, customers, communities), where their trusted access is the edge.` },
  { key: 'street', role: 'Prometheus (Opportunity Discovery), brick-and-mortar lens',
    ask: 'Find recurring, paid, physical-world problems local businesses already spend money on and complain about (reviews, trade forums, public procurement, licensing boards). Favor little capital, low overhead, and a service that can be delivered manually first.' },
  { key: 'tech', role: 'Prometheus (Opportunity Discovery), emerging-technology lens',
    ask: 'Find tasks that recently became cheap to deliver because of AI or new tools, where buyers still pay incumbent prices. The tool is commodity; the edge must be access, trust or execution.' },
]
const scouted = await parallel(LENSES.map(l => () => agent(
  `${AUTHORITY}\n\nROLE: ${l.role}.\nFOCUS: ${FOCUS}\nTASK: ${l.ask}\nReturn 3-5 opportunities, each with at least 2 independent source URLs. Mark network_edge true only when the access is real and stated.`,
  { label: `scout:${l.key}`, phase: 'Scout', schema: SCOUT_SCHEMA })))

// Barrier: dedupe across lenses before spending on validation.
const seen = new Map()
for (const r of scouted.filter(Boolean)) {
  for (const o of r.opportunities) {
    const k = slug(o.name)
    if (!seen.has(k)) seen.set(k, { ...o, name: k })
  }
}
const pool = [...seen.values()].sort((a, b) => Number(b.network_edge) - Number(a.network_edge))
const opps = pool.slice(0, MAX_OPPS)
log(`Scouted ${pool.length} unique opportunities; validating ${opps.length}`)
if (pool.length > opps.length) log(`Not validated this run (cap ${MAX_OPPS}): ${pool.slice(MAX_OPPS).map(o => o.name).join(', ')}`)

// ---------------------------------------------------------------- Validate
const RED_LENSES = [
  { lens: 'market', bot: 'Veritas (Evidence, Falsification and Acceptance)', ask: 'Refute demand: is the problem really paid for, recurring, and not already solved cheaply? Is the "low competition" claim false?' },
  { lens: 'legal', bot: 'Aegis (Permissions, Risk and Resilience)', ask: 'Refute lawfulness: licensing, consumer protection, privacy, platform terms, securities (Howey) if members or others invest money.' },
  { lens: 'people', bot: 'Strategos (Mission Operations and Production Coordination)', ask: 'Refute execution: incentive conflicts inside a friends-and-family team, who does the unglamorous delivery, what happens when a member quits.' },
]

const dossiers = await pipeline(
  opps,
  // Strategic Market Trend Analyst: validate and fact-check the scout.
  o => agent(
    `${AUTHORITY}\n\nROLE: Logos (Market Diligence and Decision Analysis). Validate and fact-check the scout's claims; independently find demand evidence, competitors and their prices.\n${brief(o)}`,
    { label: `analyst:${o.name}`, phase: 'Validate', schema: ANALYST_SCHEMA })
    .then(analyst => ({ o, analyst })),
  // Red team: three independent refuters.
  s => parallel(RED_LENSES.map(r => () => agent(
    `${AUTHORITY}\n\nROLE: ${r.bot}, adversarial reviewer on the ${r.lens} lens. Try to REFUTE this opportunity. ${r.ask}\nSet refuted=true only with a concrete, sourced reason; severity "critical" means it cannot lawfully or economically work at all.\n${brief(s.o)}\nAnalyst: ${JSON.stringify(s.analyst)}`,
    { label: `red:${r.lens}:${s.o.name}`, phase: 'Validate', schema: RED_SCHEMA })))
    .then(red => ({ ...s, red: red.filter(Boolean) })),
  // Product Development Specialist + Business Model / Tech Innovator.
  s => {
    const refuted = s.red.filter(r => r.refuted)
    if (s.analyst?.verdict === 'not_viable' || refuted.length >= 2 || refuted.some(r => r.severity === 'critical')) {
      log(`${s.o.name}: stopped after red team (${s.analyst?.verdict}, ${refuted.length} refuted)`)
      return { ...s, stopped: true }
    }
    return agent(
      `${AUTHORITY}\n\nROLES: Daedalus (Business Architecture and Mechanism Invention) with Vulcan (Product Engineering) on minimum tooling.\nDesign the smallest refundable, priced offer that a real buyer can pay for within ${POLICY.timebox_days} days, delivered manually first with existing tools (build no new software for the first sale). Answer the red team's live objections in the design. Include expansion paths for after paid demand is proven.\n${brief(s.o)}\nAnalyst: ${JSON.stringify(s.analyst)}\nRed team: ${JSON.stringify(s.red)}`,
      { label: `offer:${s.o.name}`, phase: 'Validate', schema: OFFER_SCHEMA })
      .then(offer => ({ ...s, offer }))
  },
  // Financial Strategist + Regulatory Expert/Legal Counsel, side by side.
  s => s.stopped ? s : parallel([
    () => agent(
      `${AUTHORITY}\n\nROLE: Aurelius (Economic Truth and Capital Continuity). Bound the downside. Loss cap per experiment: $${POLICY.loss_cap_usd}. Estimate worst-case cash loss and paid commitments from 10 buyer conversations (Fermi, with anchors). Write kill rules. Phase 1 needs no outside capital.\n${brief(s.o)}\nOffer: ${JSON.stringify(s.offer)}\nAnalyst: ${JSON.stringify(s.analyst)}`,
      { label: `finance:${s.o.name}`, phase: 'Validate', schema: FINANCE_SCHEMA }),
    () => agent(
      `${AUTHORITY}\n\nROLE: Aegis (Permissions, Risk and Resilience); issue-spotter, not a lawyer. List what must be true for the first sale to be lawful, and how member contribution should become ownership. Mark blocking only when the first sale cannot lawfully happen until resolved.\n${brief(s.o)}\nOffer: ${JSON.stringify(s.offer)}\nRed team legal: ${JSON.stringify(s.red.filter(r => r.lens === 'legal'))}`,
      { label: `legal:${s.o.name}`, phase: 'Validate', schema: LEGAL_SCHEMA }),
  ]).then(([finance, legal]) => ({ ...s, finance, legal })),
  // Brand Strategist + Networking Specialist: drafts and proposed actions.
  s => s.stopped ? s : agent(
    `${AUTHORITY}\n\nROLES: Mythos (Positioning, Brand and Owned Distribution) + Concord (Customer Access, Sales and Partnerships). Write DRAFT outreach for 10 buyer conversations, a short discovery-and-ask script that ends in a paid commitment, and reciprocal partner/referral terms (no unpaid favors). List every real-world step as an action for Alfonso to approve.\n${brief(s.o)}\nOffer: ${JSON.stringify(s.offer)}\nFinance: ${JSON.stringify(s.finance)}`,
    { label: `gtm:${s.o.name}`, phase: 'Validate', schema: GTM_SCHEMA })
    .then(gtm => ({ ...s, gtm })),
)

// ---------------------------------------------------------------- Govern
phase('Govern')
const valid = dossiers.filter(Boolean)
const dossier = {
  policy: POLICY,
  opportunities: valid.map(s => ({
    name: s.o.name,
    network_edge: !!s.o.network_edge,
    evidence: [...(s.o.evidence || []), ...(s.analyst?.demand_evidence || [])],
    red_team: s.analyst?.verdict === 'not_viable'
      ? [...s.red, { lens: 'analyst', refuted: true, severity: 'critical', argument: s.analyst.notes }]
      : s.red,
    offer: s.offer || {},
    finance: s.finance || {},
    legal: s.legal || { flags: [] },
    actions: s.gtm?.actions || [],
  })),
}
const path = `${OUT}/${LABEL}-dossier.json`
const govRaw = await agent(
  `Write the JSON below to ${path} exactly as given (create the directory if needed; change nothing), then run:\n  python -m src.services.uat_governor ${path}\nReturn ONLY the command's stdout, unmodified.\n\n${JSON.stringify(dossier)}`,
  { label: 'governor', phase: 'Govern', effort: 'low' })
let gov
try {
  gov = JSON.parse(String(govRaw).slice(String(govRaw).indexOf('{'), String(govRaw).lastIndexOf('}') + 1))
} catch (e) {
  log('Governor output did not parse; returning the raw output and no decisions')
  return { error: 'governor_unparsed', governor_raw: govRaw, dossier_path: path }
}
log(`Governor: ${JSON.stringify(gov.counts)}; ranked GO: ${(gov.ranked_go || []).join(', ') || 'none'}`)

// ---------------------------------------------------------------- Team Loop
phase('Team Loop')
const full = valid.map(s => ({ name: s.o.name, scout: s.o, analyst: s.analyst, red: s.red, offer: s.offer, finance: s.finance, legal: s.legal, gtm: s.gtm }))
const report = `${OUT}/${LABEL}-brief.md`
const synthesis = await agent(
  `${AUTHORITY}\n\nROLE: Strategos writing the founder digest, with Hegemony framing each decision and Mnemosyne recording reuse. Write a decision brief for Alfonso to ${report} (markdown) and return a 10-line summary.\nThe governor's decisions are final for this cycle; do not overturn them. Include, in this order:\n1. The ranked GO list (decision verb VALIDATE: a bounded buyer test, never COMMIT) with each one's offer, price, worst-case loss, kill rules, and the governor's reasons.\n2. The human decision queue verbatim: every contact, spend, sign, publish, collect or capital action awaiting approval.\n3. For each GO: a filled standard mission contract (mission_id, venture_id, origin_group Opportunity Foundry, destination_group Revenue & Partnerships, bounded_outcome, active_bottleneck, owner Concord, reviewer Veritas, acceptance_criteria, cash_cap 0, deadline; mark unknown fields missing), a 30-day backcast, and one weekly SMART goal for each bot whose group touches it, each traced to the Single Bottleneck Metric.\n4. RECONFIGURE (REWORK) items with exactly what must change to pass; KILL and PARK (HOLD) items with reasons (counsel questions for PARK).\n5. Contribution ledger entries: which bot produced which evidence or draft.\n6. What this cycle learned and what the next cycle should scout.\nCite sources from the dossiers. Do not add claims they do not support.\n\nGovernor: ${JSON.stringify(gov)}\nDossiers: ${JSON.stringify(full)}`,
  { label: 'team-loop', phase: 'Team Loop' })

return {
  sbm: gov.sbm,
  ranked_go: gov.ranked_go,
  counts: gov.counts,
  human_decision_queue: gov.human_decision_queue,
  execution_authority: gov.execution_authority,
  dossier_path: path,
  brief_path: report,
  summary: synthesis,
}
