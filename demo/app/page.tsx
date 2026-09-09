'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock3,
  Database,
  Eye,
  FlaskConical,
  Info,
  Link2Off,
  Network,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Users,
  Workflow,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import experimentSummary from '../../synthetic/results/experiment_summary.json';

type ScenarioKey = 'clean_target' | 'implemented_baseline' | 'gap_injected';
type EvidenceMode = 'object' | 'details' | 'project';
const scenarioData = Object.fromEntries(
  experimentSummary.scenarios.map((item) => [
    item.scenario,
    {
      label:
        item.scenario === 'clean_target'
          ? 'Reference lifecycle'
          : item.scenario === 'implemented_baseline'
            ? 'Documented lifecycle'
            : 'Fault-injected test',
      note:
        item.scenario === 'clean_target'
          ? 'Intended lifecycle with complete Review 1–3 coverage'
          : item.scenario === 'implemented_baseline'
            ? 'Documented behavior; R1-only by generator design'
            : 'Controlled conditions for detector evaluation',
      events: item.events,
      objects: item.objects,
      e2o: item.e2o_relations,
      o2o: item.o2o_relations,
    },
  ]),
) as Record<
  ScenarioKey,
  {
    label: string;
    note: string;
    events: number;
    objects: number;
    e2o: number;
    o2o: number;
  }
>;
const riskLabels: Record<string, string> = {
  E10_DUPLICATE_VERIFICATION: 'Duplicate verification',
  E12_NULL_SCORE_LOCKOUT: 'Null-score lockout',
  E15_COUNTER_SKEW: 'Counter divergence',
  E5_CAPACITY_OVERRUN: 'Capacity overrun',
  G5_STAGE_STALL: 'Stage stall',
  G9_ATTEMPT_DEADLOCK: 'Attempt deadlock',
};
const colors = ['#f59e0b', '#fb7185', '#8b5cf6', '#14b8a6'];
const flattening = experimentSummary.flattening.map((item, index) => ({
  name: item.representation.replace('ReportVersion', 'Version'),
  preserve: item.relation_preservation_pct,
  cooc: experimentSummary.observability.cross_object_observability_coverage
    .ablation[index].cooc_pct,
  color: colors[index],
}));
const policies = experimentSummary.digital_twin.map((item) => ({
  name:
    item.policy === 'synthetic baseline'
      ? 'Synthetic baseline'
      : item.policy === 'attempt escape transition'
        ? 'Attempt escape'
        : item.policy === 'capacity reallocation'
          ? 'Capacity reallocation'
          : 'Combined intervention',
  deadlock: item.deadlock_rate_pct,
  capacity: item.capacity_violation_pct,
  completion: item.stage_completion_pct,
  wait: item.median_review_wait_hours,
}));
const anomalies = experimentSummary.anomaly_detection.per_type.map((item) => ({
  code: item.anomaly_type.split('_')[0],
  label: riskLabels[item.anomaly_type],
  positives: item.positives,
  precision: item.precision,
  recall: item.recall,
  f1: item.f1,
}));
const evidenceModes: Record<
  EvidenceMode,
  { label: string; risks: number; coverage: number; hidden: string }
> = {
  object: {
    label: 'Linked objects',
    risks:
      experimentSummary.observability.source_instrumentation_coverage[2]
        .observable_risks,
    coverage:
      experimentSummary.observability.source_instrumentation_coverage[2]
        .coverage_pct,
    hidden: 'No tested risk predicate is hidden',
  },
  details: {
    label: 'Audit + details',
    risks:
      experimentSummary.observability.source_instrumentation_coverage[1]
        .observable_risks,
    coverage:
      experimentSummary.observability.source_instrumentation_coverage[1]
        .coverage_pct,
    hidden: 'Null-score lockout is not computable',
  },
  project: {
    label: 'Project-only log',
    risks:
      experimentSummary.observability.source_instrumentation_coverage[0]
        .observable_risks,
    coverage:
      experimentSummary.observability.source_instrumentation_coverage[0]
        .coverage_pct,
    hidden: 'Attempts, capacity, counters and scores lose context',
  },
};
const walkthrough = [
  {
    id: 'risk-lab',
    label: 'Risk lab',
    hint: 'See when evidence disappears',
  },
  {
    id: 'model',
    label: 'Object model',
    hint: 'One event, many linked objects',
  },
  {
    id: 'evidence',
    label: 'Flattening loss',
    hint: 'Relations disappear in flat logs',
  },
  { id: 'detection', label: 'Detection', hint: 'Controlled anomaly benchmark' },
  { id: 'twin', label: 'Interventions', hint: 'What-if simulation evidence' },
];
const fmt = (value: number) => new Intl.NumberFormat('en-IN').format(value);
const signedDelta = (value: number, unit: string) =>
  `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value).toFixed(1)} ${unit}`;

function SectionHeading({
  eyebrow,
  title,
  copy,
}: {
  eyebrow: string;
  title: string;
  copy: string;
}) {
  return (
    <div className="section-heading">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p>{copy}</p>
    </div>
  );
}
function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export default function Home() {
  const [scenario, setScenario] = useState<ScenarioKey>('gap_injected');
  const [evidenceMode, setEvidenceMode] = useState<EvidenceMode>('object');
  const [relationshipDropout, setRelationshipDropout] = useState(0);
  const [step, setStep] = useState(0);
  const [analysisState, setAnalysisState] = useState<
    'idle' | 'running' | 'done'
  >('idle');
  const [policy, setPolicy] = useState(3);
  const activeScenario = scenarioData[scenario];
  const delta = useMemo(
    () => ({
      deadlock: policies[policy].deadlock - policies[0].deadlock,
      capacity: policies[policy].capacity - policies[0].capacity,
      completion: policies[policy].completion - policies[0].completion,
      wait: policies[policy].wait - policies[0].wait,
    }),
    [policy],
  );
  function jumpTo(id: string, index: number) {
    setStep(index);
    document
      .getElementById(id)
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function runAnalysis() {
    if (analysisState === 'running') return;
    setAnalysisState('running');
    window.setTimeout(() => setAnalysisState('done'), 850);
  }

  useEffect(() => {
    const context = (
      document as Document & {
        modelContext?: {
          registerTool: (
            tool: Record<string, unknown>,
            options?: { signal?: AbortSignal },
          ) => void | Promise<void>;
        };
      }
    ).modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    const register = (tool: Record<string, unknown>) => {
      try {
        void Promise.resolve(
          context.registerTool(tool, { signal: lifecycle.signal }),
        ).catch(() => undefined);
      } catch {
        /* Unsupported preview contexts fail silently. */
      }
    };
    register({
      name: 'select_research_scenario',
      title: 'Select research scenario',
      description:
        'Change the visible benchmark provenance card to one of the three packaged synthetic scenarios.',
      inputSchema: {
        type: 'object',
        properties: {
          scenario: {
            type: 'string',
            enum: ['clean_target', 'implemented_baseline', 'gap_injected'],
          },
        },
        required: ['scenario'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      execute(input: unknown) {
        const value = (input as { scenario?: string })?.scenario;
        if (!value || !(value in scenarioData))
          throw new Error('Unknown scenario');
        setScenario(value as ScenarioKey);
        return {
          scenario: value,
          visibleLabel: scenarioData[value as ScenarioKey].label,
        };
      },
    });
    register({
      name: 'run_synthetic_benchmark',
      title: 'Reveal synthetic benchmark',
      description:
        'Reveal the packaged controlled anomaly benchmark in the visible interface.',
      inputSchema: {
        type: 'object',
        properties: {},
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      async execute() {
        setAnalysisState('running');
        document
          .getElementById('detection')
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        await new Promise((resolve) => window.setTimeout(resolve, 850));
        setAnalysisState('done');
        return {
          status: 'complete',
          synthetic: true,
          detectorMacroF1: experimentSummary.anomaly_detection.macro_f1,
        };
      },
    });
    register({
      name: 'set_risk_evidence_view',
      title: 'Set risk evidence view',
      description:
        'Compare which of the six controlled risk predicates remain observable under one evidence representation.',
      inputSchema: {
        type: 'object',
        properties: {
          representation: {
            type: 'string',
            enum: ['object', 'details', 'project'],
          },
        },
        required: ['representation'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      execute(input: unknown) {
        const value = (input as { representation?: string })?.representation;
        if (!value || !(value in evidenceModes))
          throw new Error('Unknown representation');
        setEvidenceMode(value as EvidenceMode);
        document
          .getElementById('risk-lab')
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return {
          representation: value,
          observableRisks: evidenceModes[value as EvidenceMode].risks,
          totalRisks: 6,
          synthetic: true,
        };
      },
    });
    register({
      name: 'compare_intervention_policy',
      title: 'Compare intervention policy',
      description:
        'Select one offline what-if policy and return its assumption-driven simulated outcomes.',
      inputSchema: {
        type: 'object',
        properties: {
          policy: {
            type: 'string',
            enum: [
              'baseline',
              'attempt_escape',
              'capacity_reallocation',
              'combined',
            ],
          },
        },
        required: ['policy'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      execute(input: unknown) {
        const value = (input as { policy?: string })?.policy;
        const index = [
          'baseline',
          'attempt_escape',
          'capacity_reallocation',
          'combined',
        ].indexOf(value ?? '');
        if (index < 0) throw new Error('Unknown policy');
        setPolicy(index);
        document
          .getElementById('twin')
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return {
          policy: value,
          deadlockRatePct: policies[index].deadlock,
          capacityViolationPct: policies[index].capacity,
          completionPct: policies[index].completion,
          medianReviewWaitHours: policies[index].wait,
          synthetic: true,
        };
      },
    });
    return () => lifecycle.abort();
  }, []);

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top">
          <span className="brand-mark">
            <Network />
          </span>
          <span>
            <strong>Capstone Risk Twin</strong>
            <small>Team 1 · Review 2</small>
          </span>
        </a>
        <div className="top-actions">
          <Badge className="synthetic-badge">
            <FlaskConical /> Synthetic proof-of-mechanism
          </Badge>
          <Button
            className="present-button"
            onClick={() => jumpTo(walkthrough[step].id, step)}
          >
            <Play /> Go to: {walkthrough[step].label}
          </Button>
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="kicker">
            <span>Research prototype</span>
            <i /> Educational capstone process
          </div>
          <h1>
            Can a process twin expose risk <em>before</em> it becomes a failure?
          </h1>
          <p>
            Explore how linked projects, students, faculty, report versions and
            scores reveal cross-object risks—and what disappears when that
            evidence is flattened.
          </p>
          <div className="hero-actions">
            <Button size="lg" onClick={() => jumpTo('risk-lab', 0)}>
              Start the 5-minute demo <ArrowRight />
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => jumpTo('twin', 4)}
            >
              Compare interventions
            </Button>
          </div>
          <div className="team-line">
            <Users />
            <span>Aakaash S. · Mitisha Sharma · Tanmay Khambete</span>
            <span className="dot" />
            <span>Guide: Dr. Kalyanaraman P.</span>
          </div>
        </div>
        <Card className="hero-console">
          <CardHeader>
            <div className="console-title-row">
              <div>
                <CardTitle>Offline risk-twin snapshot</CardTitle>
                <CardDescription>
                  Baseline → combined intervention
                </CardDescription>
              </div>
              <span className="status-dot">
                <i /> Synthetic
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="snapshot-list">
              <div>
                <span>Attempt deadlock</span>
                <strong>{policies[0].deadlock}%</strong>
                <ArrowRight />
                <strong className="improved">{policies[3].deadlock}%</strong>
              </div>
              <div>
                <span>Stage completion</span>
                <strong>{policies[0].completion}%</strong>
                <ArrowRight />
                <strong className="improved">{policies[3].completion}%</strong>
              </div>
              <div>
                <span>Median review wait</span>
                <strong>{policies[0].wait}h</strong>
                <ArrowRight />
                <strong className="improved">{policies[3].wait}h</strong>
              </div>
            </div>
            <div className="snapshot-note">
              <FlaskConical />
              <p>
                <strong>What these numbers mean</strong>
                5,000 simulated projects per policy under fixed assumptions.
                These are what-if outcomes, not an institutional forecast.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      <nav className="story-nav">
        {walkthrough.map((item, index) => (
          <button
            key={item.id}
            className={step === index ? 'active' : ''}
            onClick={() => jumpTo(item.id, index)}
          >
            <span>{index + 1}</span>
            <div>
              <strong>{item.label}</strong>
              <small>{item.hint}</small>
            </div>
            <ArrowRight />
          </button>
        ))}
      </nav>

      <section className="content-section risk-lab" id="risk-lab">
        <SectionHeading
          eyebrow="01 · Risk observability lab"
          title="The warning changes when the evidence changes"
          copy="Switch between three representations of the same synthetic process. The measured result is analysis readiness: whether each preregistered risk predicate can still be computed—not a claim of real-world prediction."
        />
        <div className="risk-workbench">
          <Card className="evidence-control-card">
            <CardHeader>
              <CardTitle>Available evidence</CardTitle>
              <CardDescription>
                Controlled source-instrumentation ablation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <fieldset className="evidence-selector">
                <legend className="sr-only">Evidence representation</legend>
                {(Object.keys(evidenceModes) as EvidenceMode[]).map((mode) => (
                  <button
                    key={mode}
                    className={evidenceMode === mode ? 'active' : ''}
                    onClick={() => setEvidenceMode(mode)}
                  >
                    {mode === 'object' ? (
                      <Network />
                    ) : mode === 'details' ? (
                      <Activity />
                    ) : (
                      <Link2Off />
                    )}
                    <span>{evidenceModes[mode].label}</span>
                    <strong>{evidenceModes[mode].coverage}%</strong>
                  </button>
                ))}
              </fieldset>
              <div className="dropout-control">
                <div>
                  <span>Planned relationship-dropout test</span>
                  <strong>{relationshipDropout}%</strong>
                </div>
                <input
                  aria-label="Relationship dropout preview"
                  type="range"
                  min="0"
                  max="30"
                  step="10"
                  value={relationshipDropout}
                  onChange={(event) =>
                    setRelationshipDropout(Number(event.target.value))
                  }
                />
                <small>
                  Protocol preview only · degradation results not measured yet
                </small>
              </div>
              <div className="risk-readout">
                <Metric
                  label="Observable risks"
                  value={`${evidenceModes[evidenceMode].risks}/6`}
                  detail="measured on the packaged benchmark"
                />
                <div className="evidence-note">
                  <Eye />
                  <p>
                    <strong>What the twin can see</strong>
                    {evidenceModes[evidenceMode].hidden}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="prefix-card">
            <CardHeader>
              <CardTitle>Project trace · duplicate verification</CardTitle>
              <CardDescription>
                P-0004 · tracked synthetic events
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="prefix-timeline">
                {[
                  ['Compilation failed', '03 Jul · 03:38', 'done'],
                  ['Report submitted', '03 Jul · 13:28', 'done'],
                  ['Verification started', '04 Jul · 01:34', 'done'],
                  [
                    'Verification started again',
                    '04 Jul · 01:36 · risk manifests',
                    'active',
                  ],
                  ['Faculty accepted', '05 Jul · 12:51', 'future'],
                ].map(([title, detail, status]) => (
                  <div className={status} key={title}>
                    <span>{status === 'active' ? <Clock3 /> : <Check />}</span>
                    <p>
                      <strong>{title}</strong>
                      <small>{detail}</small>
                    </p>
                  </div>
                ))}
              </div>
              <div className="prefix-boundary">
                <TriangleAlert />
                <p>
                  <strong>Current boundary</strong>The rule detects the second
                  verification when it occurs. Earlier forecasting requires
                  regenerated traces with causal precursors.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
        <div className="risk-context-grid">
          <Card className="portfolio-card">
            <CardHeader>
              <CardTitle>Shared faculty context</CardTitle>
              <CardDescription>
                F-004 links four projects · capacity 6 · no observed breach
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="portfolio-map">
                <div className="faculty-node">
                  <Users />
                  <strong>F-004</strong>
                  <small>4 linked / capacity 6</small>
                </div>
                {[
                  ['P-0004', 'Duplicate verification'],
                  ['P-0034', 'Multiple injected conditions'],
                  ['P-0064', 'Duplicate verification'],
                  ['P-0094', 'Stall + deadlock injected'],
                ].map(([project, condition], index) => (
                  <div
                    className="project-node"
                    key={project}
                    style={{
                      opacity:
                        relationshipDropout > 0 &&
                        index >= 4 - relationshipDropout / 10
                          ? 0.28
                          : 1,
                    }}
                  >
                    <span>{project}</span>
                    <small>{condition}</small>
                  </div>
                ))}
              </div>
              <p className="mechanism-note">
                This confirms the shared-resource relation path. Workload-caused
                propagation is a planned experiment, not a current result. The
                slider visually previews controlled link removal.
              </p>
            </CardContent>
          </Card>
          <Card className="provenance-card">
            <CardHeader>
              <CardTitle>Benchmark provenance</CardTitle>
              <CardDescription>
                Seed {experimentSummary.configuration.seed} ·{' '}
                {experimentSummary.configuration.projects_per_scenario} projects
                per scenario
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="field-label">Dataset scenario</div>
              <div className="scenario-control">
                {(Object.keys(scenarioData) as ScenarioKey[]).map((key) => (
                  <button
                    key={key}
                    className={scenario === key ? 'active' : ''}
                    onClick={() => setScenario(key)}
                  >
                    {scenarioData[key].label}
                  </button>
                ))}
              </div>
              <p className="scenario-note">{activeScenario.note}</p>
              <div className="compact-provenance">
                <span>
                  <strong>{fmt(activeScenario.events)}</strong> events
                </span>
                <span>
                  <strong>{fmt(activeScenario.objects)}</strong> objects
                </span>
                <span>
                  <strong>{fmt(activeScenario.e2o)}</strong> E2O
                </span>
                <span>
                  <strong>{fmt(activeScenario.o2o)}</strong> O2O
                </span>
              </div>
              <div className="integrity-row">
                <span>
                  <CheckCircle2 /> 0 dangling links
                </span>
                <span>
                  <CheckCircle2 /> Monotonic timestamps
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="content-section" id="model">
        <SectionHeading
          eyebrow="02 · The representation problem"
          title="One review event touches more than one ‘case’"
          copy="Selecting a single case notion forces the other relationships into duplicated rows, attributes or silence. OCEL keeps the event once and links every involved object explicitly."
        />
        <div className="model-grid">
          <Card className="object-map-card">
            <CardHeader>
              <CardTitle>Selected event · faculty accepted R1</CardTitle>
              <CardDescription>
                E-GAP-000064 · 05 Jul 2026, 12:51
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="object-map">
                <div className="event-node">
                  <Workflow />
                  <strong>FACULTY_ACCEPTED</strong>
                  <small>one immutable event</small>
                </div>
                {[1, 2, 3, 4, 5].map((n) => (
                  <span key={n} className={`connector c${n}`} />
                ))}
                <div className="object-node n1">
                  <b>P</b>
                  <span>
                    Project<small>P-0004</small>
                  </span>
                </div>
                <div className="object-node n2">
                  <b>T</b>
                  <span>
                    Team<small>T-0004</small>
                  </span>
                </div>
                <div className="object-node n3">
                  <b>F</b>
                  <span>
                    Faculty<small>F-004</small>
                  </span>
                </div>
                <div className="object-node n4">
                  <b>V</b>
                  <span>
                    Report version<small>RV-0004-R1-V1</small>
                  </span>
                </div>
                <div className="object-node n5">
                  <b>S</b>
                  <span>
                    Score<small>SC-0004-R1</small>
                  </span>
                </div>
              </div>
              <div className="map-legend">
                <Info /> Exact event and links from the packaged synthetic log,
                not a production record.
              </div>
            </CardContent>
          </Card>
          <Card className="why-card">
            <CardHeader>
              <CardTitle>What this enables</CardTitle>
              <CardDescription>
                Questions that cross object boundaries
              </CardDescription>
            </CardHeader>
            <CardContent>
              {[
                [
                  'G9',
                  'Did retry limits trap a project before score publication?',
                ],
                [
                  'E5',
                  'Did a guide exceed capacity when the team was assigned?',
                ],
                [
                  'E12',
                  'Did a null score block progression for all linked students?',
                ],
              ].map(([code, text]) => (
                <div className="question-row" key={code}>
                  <span>{code}</span>
                  <p>{text}</p>
                  <Eye />
                </div>
              ))}
              <div className="claim-box">
                <Sparkles />
                <p>
                  <strong>Proposed novelty</strong>Cross-Object Observability
                  Coverage (COOC) measures whether a representation can compute
                  preregistered cross-object risk predicates.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="content-section tinted" id="evidence">
        <SectionHeading
          eyebrow="03 · Controlled ablation"
          title="Flattening preserves at most half of the tested risk questions"
          copy="We remove object relations by projecting the same synthetic process into three conventional flat logs, then measure relation retention and analysis readiness."
        />
        <Tabs defaultValue="cooc" className="evidence-tabs">
          <TabsList>
            <TabsTrigger value="cooc">COOC</TabsTrigger>
            <TabsTrigger value="relations">Relation retention</TabsTrigger>
          </TabsList>
          <TabsContent value="cooc">
            <ComparisonBars metric="cooc" />
          </TabsContent>
          <TabsContent value="relations">
            <ComparisonBars metric="preserve" />
          </TabsContent>
        </Tabs>
        <div className="result-strip">
          <div>
            <strong>16.7–50%</strong>
            <span>flat-log COOC range</span>
          </div>
          <ArrowRight />
          <div className="highlight">
            <strong>100%</strong>
            <span>OCEL COOC on 6/6 risks</span>
          </div>
          <p>
            <ShieldCheck /> Oracle-tested on the controlled benchmark
          </p>
        </div>
      </section>

      <section className="content-section" id="detection">
        <SectionHeading
          eyebrow="04 · Analysis proof"
          title="The linked log supports structured detection—not a production forecast"
          copy="A deterministic detector validates the observability mechanism; a grouped Markov baseline tests next-transition prediction. Neither result establishes real-world risk forecasting."
        />
        <div className="analysis-grid">
          <Card className="run-card">
            <CardHeader>
              <CardTitle>Reveal controlled benchmark</CardTitle>
              <CardDescription>
                Gap-injected scenario · fixed seed · reproducible
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                className="run-button"
                onClick={runAnalysis}
                disabled={analysisState === 'running'}
              >
                {analysisState === 'idle' && (
                  <>
                    <Play /> Reveal packaged benchmark
                  </>
                )}
                {analysisState === 'running' && (
                  <>
                    <span className="spinner" /> Loading 6 risk predicates…
                  </>
                )}
                {analysisState === 'done' && (
                  <>
                    <Check /> Benchmark visible
                  </>
                )}
              </Button>
              {analysisState === 'idle' ? (
                <div className="waiting-state">
                  <Database />
                  <p>
                    Results are precomputed from the packaged generator. Reveal
                    them for the Review 2 walkthrough.
                  </p>
                </div>
              ) : analysisState === 'running' ? (
                <div className="running-state">
                  <span />
                  <p>
                    Link traversal · rule evaluation · project-grouped scoring
                  </p>
                </div>
              ) : (
                <div className="anomaly-list">
                  {anomalies.map((item) => (
                    <div key={item.code}>
                      <span>{item.code}</span>
                      <p>
                        {item.label}
                        <small>{item.positives} positives</small>
                      </p>
                      <strong>F1 {item.f1.toFixed(3)}</strong>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
          <div className="score-stack">
            <Card className="headline-score">
              <CardContent>
                <span>Detector macro-F1</span>
                <strong>
                  {experimentSummary.anomaly_detection.macro_f1.toFixed(3)}
                </strong>
                <small>Controlled injected anomalies</small>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Next-transition baseline</CardTitle>
                <CardDescription>
                  {experimentSummary.next_transition.grouped_split}
                </CardDescription>
              </CardHeader>
              <CardContent className="mini-scores">
                <div>
                  <strong>
                    {(
                      experimentSummary.next_transition.top1_accuracy * 100
                    ).toFixed(1)}
                    %
                  </strong>
                  <span>Top-1 accuracy</span>
                </div>
                <div>
                  <strong>
                    {(
                      experimentSummary.next_transition.top2_accuracy * 100
                    ).toFixed(1)}
                    %
                  </strong>
                  <span>Top-2 accuracy</span>
                </div>
                <div>
                  <strong>
                    {experimentSummary.next_transition.macro_f1.toFixed(3)}
                  </strong>
                  <span>Macro-F1</span>
                </div>
              </CardContent>
            </Card>
            <div className="caution">
              <TriangleAlert />
              <p>
                <strong>Interpretation boundary</strong>Detectors target the
                documented structures used for injection. Generalisation to real
                institutional logs remains untested.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="content-section dark-section" id="twin">
        <SectionHeading
          eyebrow="05 · Prescriptive extension"
          title="Stress-test an intervention hypothesis"
          copy="The offline process simulator compares candidate policies under fixed synthetic assumptions. Use the result to frame an experiment—not to recommend an institutional change."
        />
        <div className="twin-grid">
          <div className="policy-picker">
            {policies.map((item, index) => (
              <button
                key={item.name}
                className={policy === index ? 'active' : ''}
                onClick={() => setPolicy(index)}
              >
                <span>{'ABCD'[index]}</span>
                <p>
                  <strong>{item.name}</strong>
                  <small>
                    {
                      [
                        'No intervention',
                        'Retry recovery path',
                        'Redistribute faculty load',
                        'Recovery + reallocation',
                      ][index]
                    }
                  </small>
                </p>
                {policy === index && <CheckCircle2 />}
              </button>
            ))}
          </div>
          <Card className="twin-result">
            <CardHeader>
              <CardTitle>Baseline versus {policies[policy].name}</CardTitle>
              <CardDescription>
                Grey = baseline · teal = selected · 5,000 simulated projects
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="policy-comparison">
                {[
                  {
                    label: 'Attempt deadlock',
                    baseline: policies[0].deadlock,
                    selected: policies[policy].deadlock,
                    delta: delta.deadlock,
                    max: 15,
                    unit: '%',
                    deltaUnit: 'pp',
                  },
                  {
                    label: 'Capacity violation',
                    baseline: policies[0].capacity,
                    selected: policies[policy].capacity,
                    delta: delta.capacity,
                    max: 15,
                    unit: '%',
                    deltaUnit: 'pp',
                  },
                  {
                    label: 'Stage completion',
                    baseline: policies[0].completion,
                    selected: policies[policy].completion,
                    delta: delta.completion,
                    max: 100,
                    unit: '%',
                    deltaUnit: 'pp',
                  },
                  {
                    label: 'Median review wait',
                    baseline: policies[0].wait,
                    selected: policies[policy].wait,
                    delta: delta.wait,
                    max: 50,
                    unit: 'h',
                    deltaUnit: 'h',
                  },
                ].map((item) => (
                  <div className="comparison-row" key={item.label}>
                    <div className="comparison-label">
                      <span>{item.label}</span>
                      <strong>{signedDelta(item.delta, item.deltaUnit)}</strong>
                    </div>
                    <div className="paired-bars">
                      <div>
                        <span
                          style={{
                            width: `${(item.baseline / item.max) * 100}%`,
                          }}
                        />
                        <i>
                          {item.baseline}
                          {item.unit}
                        </i>
                      </div>
                      <div className="selected-bar">
                        <span
                          style={{
                            width: `${(item.selected / item.max) * 100}%`,
                          }}
                        />
                        <i>
                          {item.selected}
                          {item.unit}
                        </i>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="best-result">
                <FlaskConical />
                <p>
                  <strong>Assumption-driven comparison</strong>
                  These deltas come from manually specified Monte Carlo
                  probabilities. Calibration against held-out event logs is the
                  next research step.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="takeaway">
        <div>
          <p className="eyebrow">Review 2 takeaway</p>
          <h2>
            We are validating the representation before claiming operational
            impact.
          </h2>
        </div>
        <ol>
          <li>
            <span>1</span>
            <p>
              <strong>Now</strong>OCEL 2.0 schema, synthetic benchmark, COOC
              ablation and analytical baselines.
            </p>
          </li>
          <li>
            <span>2</span>
            <p>
              <strong>Next</strong>Map approved portal audit fields,
              pseudonymise identifiers and recalibrate thresholds.
            </p>
          </li>
          <li>
            <span>3</span>
            <p>
              <strong>Then</strong>External validation, stronger predictive
              models and publication-oriented evaluation.
            </p>
          </li>
        </ol>
      </section>
      <footer>
        <div>
          <Network />
          <strong>
            Object-Centric Event Log Mining for Academic Capstone Processes
          </strong>
        </div>
        <p>{experimentSummary.disclaimer}</p>
        <Button
          variant="outline"
          onClick={() => {
            setStep(0);
            setScenario('gap_injected');
            setEvidenceMode('object');
            setRelationshipDropout(0);
            setAnalysisState('idle');
            setPolicy(3);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        >
          <RotateCcw /> Reset demo
        </Button>
      </footer>
    </main>
  );
}

function ComparisonBars({ metric }: { metric: 'cooc' | 'preserve' }) {
  return (
    <Card className="comparison-card">
      <CardHeader>
        <CardTitle>
          {metric === 'cooc'
            ? 'Cross-Object Observability Coverage'
            : 'Original relation preservation'}
        </CardTitle>
        <CardDescription>
          {metric === 'cooc'
            ? 'Share of six preregistered risk predicates computable and oracle-correct'
            : 'Share of original event-to-object relations retained'}
        </CardDescription>
      </CardHeader>
      <CardContent className="bar-list">
        {flattening.map((item) => {
          const value = item[metric];
          return (
            <div className="bar-row" key={item.name}>
              <span>{item.name}</span>
              <div>
                <i style={{ width: `${value}%`, background: item.color }} />
              </div>
              <strong>{value.toFixed(value === 100 ? 0 : 1)}%</strong>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
