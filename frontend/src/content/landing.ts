export const heroContent = {
  badge: "Private beta · Built for production teams",
  heading:
    "Ship dependable releases with an AI engineer that respects your repo.",
  subheading:
    "Forge reads your architecture, proposes merge-ready diffs, and enforces cost guardrails so you can trust every automated edit.",
  trustSignals: [
    "SOC 2-ready guardrails",
    "$1/day free tier",
    "No credit card",
  ],
  proofStats: [
    { label: "Merged success rate", value: "96%" },
    { label: "Average time saved", value: "10 hrs/wk" },
    { label: "Live teams", value: "140+" },
  ],
};

export const scorecard = [
  { label: "Agent pass rate", value: "96% merged tasks" },
  { label: "p95 latency", value: "2.7 s live" },
  { label: "Dashboards live", value: "3 Grafana views" },
  { label: "Daily free tier", value: "$1 credit" },
];

export const featureHighlights = [
  {
    title: "CodeAct, merge-grade edits",
    description:
      "Structured diffs, unit-test awareness, and automatic rollbacks keep every change ship-ready.",
  },
  {
    title: "Ultimate Editor",
    description:
      "AST-aware editing across 45+ stacks so imports, schemas, and snapshots stay coherent.",
  },
  {
    title: "ACE learning loops",
    description:
      "Learns from your merged PRs and nudges the agent toward team-specific conventions.",
  },
  {
    title: "Hybrid memory",
    description:
      "Semantic + BM25 retrieval with 30-day hygiene so context stays relevant without bloating costs.",
  },
];

export const reliabilityPillars = [
  {
    title: "Guardrails & cost controls",
    description:
      "Quota enforcement, soft stops, and Redis-backed tracking keep experiments predictable.",
  },
  {
    title: "Observability from day one",
    description:
      "Prometheus + Grafana dashboards for latency, retries, and spend, live in under a minute.",
  },
  {
    title: "Transparent billing",
    description:
      "Inline spend meters, weekly digests, and Slack alerts before teams exceed their limits.",
  },
];

export const shippingNow = [
  "CodeAct beta",
  "Ultimate Editor + ACE",
  "Usage caps & monitoring",
  "Core MCP servers",
  "Cursor-grade UX",
];

export const comingLater = [
  "MetaSOP orchestration",
  "Parallel agent batches",
  "Self-remediation loops",
  "Playwright browser runs",
  "Enterprise SSO & audit logs",
];

export const betaChecklist = [
  "Run CodeAct on 10 real tickets",
  "Burn in cost alerts against live traffic",
  "Trip the circuit breaker intentionally",
  "Verify Grafana ingestion",
  "Ship beta comms & support runbook",
];

export const finalCta = {
  heading: "Pair your team with a dependable release engineer.",
  body: "Join the private beta to get transparent spend controls, live observability, and roadmap influence on the workflows that unlock next.",
  primaryCta: "Start a secure workspace",
  secondaryCta: "View the beta plans",
};

export const faqItems = [
  {
    question: "What exactly ships in the private beta?",
    answer:
      "CodeAct, the Ultimate Editor, ACE learning loops, cost controls, and the hybrid memory system are live today. Everything listed on the roadmap column ships after we validate reliability with beta partners.",
  },
  {
    question: "Does Forge run inside our infrastructure?",
    answer:
      "Yes. You connect your own model keys and Forge runs against your repos. Source never leaves your environment and we provide guardrails for cost ceilings, audit trails, and access control.",
  },
  {
    question: "Which models and tools are supported?",
    answer:
      "Any OpenAI, Anthropic, or custom endpoint reachable over HTTPS works. We also ship three MCP servers by default plus adapters for your internal tools.",
  },
  {
    question: "How do pricing and quotas work?",
    answer:
      "Every workspace gets $1/day free tier credit and optional $10/day pro caps. You can bring your own keys, run offline, or let us meter usage in Prometheus with Slack/Webhook alerts.",
  },
  {
    question: "Is there human review in the loop?",
    answer:
      "We encourage beta teams to review diffs just like any PR. Forge proposes merge-ready patches, complete with tests and structured commit messages, so human review stays fast.",
  },
];

export const capabilityShowcase = [
  {
    icon: "sparkles",
    title: "Merge-grade CodeAct",
    description:
      "Understands repo topology, updates tests, and ships structured commits instead of giant prompt dumps.",
    stat: "96% pass rate",
    badge: "Shipping",
    progress: 96,
    theme: "brand",
    size: "large",
  },
  {
    icon: "workflow",
    title: "Ultimate Editor",
    description:
      "AST-aware edits across 45+ stacks so imports, schemas, and snapshots stay consistent.",
    stat: "45+ stacks",
    badge: "Editor",
    progress: 92,
    theme: "accent",
    size: "medium",
  },
  {
    icon: "gauge",
    title: "ACE Learning Loop",
    description:
      "Learns from every merge and tunes prompts toward your definitions of done—no manual guardrails needed.",
    stat: "Self-tuning",
    badge: "Adaptive",
    progress: 88,
    theme: "success",
    size: "medium",
  },
  {
    icon: "brain",
    title: "Hybrid Memory",
    description:
      "Semantic + BM25 retrieval with automated hygiene so context stays relevant without bloating costs.",
    stat: "30-day hygiene",
    badge: "Memory",
    progress: 90,
    theme: "warning",
    size: "small",
  },
  {
    icon: "shield",
    title: "Guardrails & cost",
    description:
      "Redis-backed spend ceilings, circuit breakers, and per-run approvals keep experiments safe.",
    stat: "$1 / $10 caps",
    badge: "Safe",
    progress: 100,
    theme: "brand",
    size: "small",
  },
  {
    icon: "lineChart",
    title: "Observability first",
    description:
      "Prometheus + Grafana dashboards for latency, retries, cost, and memory so incidents never hide.",
    stat: "3 dashboards",
    badge: "Live",
    progress: 85,
    theme: "accent",
    size: "large",
  },
];

export const valueComparison = {
  traditional: [
    { item: "Hire and onboard a full squad", cost: "$300k+/year" },
    { item: "Wait on blockers and handoffs", cost: "Weeks of delay" },
    { item: "Coordinate QA + releases", cost: "20% productivity tax" },
    { item: "Maintain custom tooling", cost: "$50k+/year" },
    {
      item: "Monitor cost + reliability manually",
      cost: "Night and weekend work",
    },
  ],
  forge: [
    { item: "AI engineer with full toolkit", cost: "Included" },
    { item: "Instant availability", cost: "0 sec warmup" },
    { item: "24/7 execution", cost: "168 hrs/week" },
    { item: "Built-in guardrails", cost: "Automated" },
    { item: "Live observability + budgets", cost: "One click" },
  ],
};

export const valueBenefits = [
  {
    title: "10x faster delivery",
    description: "Ship real features in days, not quarters.",
  },
  {
    title: "Enterprise guardrails",
    description: "Compliance, approvals, and audit trails baked in.",
  },
  {
    title: "Self-tuning agents",
    description: "Forge adapts to your conventions automatically.",
  },
  {
    title: "Team-wide visibility",
    description: "Dashboards, alerts, and cost caps in one place.",
  },
];

export const simpleFeatureCards = [
  {
    title: "AI-native development",
    description:
      "Autonomous agents that reason about architecture, tests, and deployments the way seniors do.",
    gradient: "from-brand-500 to-accent-500",
  },
  {
    title: "Production velocity",
    description:
      "Parallel editing, streaming diffs, and cached runs mean no one waits on the agent.",
    gradient: "from-accent-500 to-brand-600",
  },
  {
    title: "Enterprise posture",
    description:
      "Security scanning, approval workflows, and isolation ensure the beta is ready for serious teams.",
    gradient: "from-accent-emerald to-success-500",
  },
];

export const howItWorksSteps = [
  {
    title: "Describe the outcome",
    description:
      "Drop a ticket, Loom, or PR comment. Forge maps the ask to a scoped plan instantly.",
  },
  {
    title: "Review structured diffs",
    description:
      "The agent edits files, updates tests, and explains every change with inline context.",
  },
  {
    title: "Approve & deploy",
    description:
      "Merge-ready commits, cost + latency stats, and rollout commands are packaged automatically.",
  },
];

export const statsHighlights = [
  {
    label: "Merged tickets",
    value: "1.4K",
    description: "Completed during internal dogfood.",
  },
  {
    label: "Latency",
    value: "2.7s p95",
    description: "Measured on live beta repos.",
  },
  {
    label: "Coverage",
    value: "98%",
    description: "Average test coverage when Forge edits.",
  },
  {
    label: "Teams onboarded",
    value: "140+",
    description: "Across startups and enterprise pilots.",
  },
];

export const testimonials = [
  {
    name: "Sarah Chen",
    role: "VP Engineering",
    company: "Northstar",
    quote:
      "Forge is the first AI engineer we actually trust in production. It respects our repo and ships high-signal diffs every time.",
  },
  {
    name: "Marcus Johnson",
    role: "CTO",
    company: "Atlas Labs",
    quote:
      "We cancelled three contractor engagements after onboarding Forge. The guardrails and transparency are unmatched.",
  },
  {
    name: "Elena Rodriguez",
    role: "Lead Architect",
    company: "Pulse",
    quote:
      "Observability and cost controls gave our security team immediate buy-in. Now Forge handles the boring 80%.",
  },
];

export const interactiveDemo = {
  title: "See it generate, test, and preview in real time.",
  subtitle: "A split-view demo showing the exact flow beta users get.",
  codeSample: `import { forge } from "@forge/runtime";

export async function handler() {
  const plan = await forge.plan("Add usage caps");
  return forge.apply(plan, { withTests: true });
}`,
  terminalLines: [
    "$ pnpm forge run",
    "Bootstrapping agents...",
    "✓ Generated plan with 3 steps",
    "✓ Tests and lint passed",
    "Workspace ready on http://localhost:4173",
  ],
};

export const metaSopSteps = [
  {
    role: "Product Manager",
    task: "Scope the request",
    output: "User story + acceptance criteria",
  },
  {
    role: "Architect",
    task: "Design the approach",
    output: "API + component blueprint",
  },
  {
    role: "Engineer",
    task: "Write the code",
    output: "Merge-ready diff",
  },
  {
    role: "QA",
    task: "Validate + measure",
    output: "Tests & coverage report",
  },
  {
    role: "DevOps",
    task: "Deploy + monitor",
    output: "Release + health signal",
  },
];

export const metaSopHighlights = [
  {
    title: "Orchestrated roles",
    description:
      "Every software role coordinates in one run so nothing blocks.",
  },
  {
    title: "Guarded execution",
    description: "Circuit breakers, approvals, and live metrics keep it safe.",
  },
  {
    title: "Observable outputs",
    description:
      "Each step emits artifacts, coverage stats, and rollout notes.",
  },
];
