'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  Check,
  CheckCircle2,
  Database,
  Eye,
  FlaskConical,
  Info,
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

type ScenarioKey = 'clean_target' | 'implemented_baseline' | 'gap_injected';
const scenarioData: Record<
  ScenarioKey,
  {
    label: string;
    note: string;
    events: number;
    objects: number;
    e2o: number;
    o2o: number;
  }
> = {
  clean_target: {
    label: 'Clean target',
    note: 'Intended lifecycle with complete Review 1–3 coverage',
    events: 2346,
    objects: 1530,
    e2o: 8412,
    o2o: 1860,
  },
  implemented_baseline: {
    label: 'Baseline',
    note: 'Current documented behavior and known gaps',
    events: 811,
    objects: 1005,
    e2o: 3152,
    o2o: 1095,
  },
  gap_injected: {
    label: 'Gap-injected',
    note: 'Controlled faults for detector evaluation',
    events: 2083,
    objects: 1411,
    e2o: 7471,
    o2o: 1670,
  },
};
const flattening = [
  { name: 'Project flat log', preserve: 27.9, cooc: 33.3, color: '#f59e0b' },
  { name: 'Student flat log', preserve: 19.8, cooc: 16.7, color: '#fb7185' },
  { name: 'Version flat log', preserve: 26.3, cooc: 50, color: '#8b5cf6' },
  { name: 'OCEL 2.0', preserve: 100, cooc: 100, color: '#14b8a6' },
];
const policies = [
  { name: 'Synthetic baseline', deadlock: 11.2, completion: 74.5, wait: 36.2 },
  { name: 'Attempt escape', deadlock: 2.2, completion: 84.9, wait: 36.9 },
  {
    name: 'Capacity reallocation',
    deadlock: 10.8,
    completion: 78.8,
    wait: 27.3,
  },
  {
    name: 'Combined intervention',
    deadlock: 1.3,
    completion: 89.5,
    wait: 27.9,
  },
];
const anomalies = [
  { code: 'G9', label: 'Attempt deadlock', positives: 17, f1: 1 },
  { code: 'E5', label: 'Capacity overrun', positives: 13, f1: 1 },
  { code: 'E12', label: 'Null-score lockout', positives: 18, f1: 0.909 },
  { code: 'G5', label: 'Stage stall', positives: 11, f1: 0.952 },
];
const walkthrough = [
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
  const [step, setStep] = useState(0);
  const [analysisState, setAnalysisState] = useState<
    'idle' | 'running' | 'done'
  >('idle');
  const [policy, setPolicy] = useState(3);
  const activeScenario = scenarioData[scenario];
  const delta = useMemo(
    () => ({
      deadlock: (policies[0].deadlock - policies[policy].deadlock).toFixed(1),
      completion: (
        policies[policy].completion - policies[0].completion
      ).toFixed(1),
      wait: (policies[0].wait - policies[policy].wait).toFixed(1),
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
        'Change the visible experiment console to one of the three packaged synthetic scenarios.',
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
      title: 'Run synthetic benchmark',
      description:
        'Run the visible controlled anomaly benchmark and reveal the packaged detector results.',
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
        return { status: 'complete', synthetic: true, detectorMacroF1: 0.977 };
      },
    });
    register({
      name: 'compare_intervention_policy',
      title: 'Compare intervention policy',
      description:
        'Select one visible synthetic digital-twin policy and return its displayed outcomes.',
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
          completionPct: policies[index].completion,
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
            <strong>OCEL Capstone Lab</strong>
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
            <Play /> Present step {step + 1}
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
            Can one event log preserve the <em>whole</em> academic process?
          </h1>
          <p>
            We model projects, students, faculty, review stages, report versions
            and scores together—then test what conventional case-centric logs
            lose.
          </p>
          <div className="hero-actions">
            <Button size="lg" onClick={() => jumpTo('model', 0)}>
              Start the 5-minute demo <ArrowRight />
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => jumpTo('evidence', 1)}
            >
              See the headline result
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
                <CardTitle>Experiment console</CardTitle>
                <CardDescription>
                  Seed 4971 · 120 projects per scenario
                </CardDescription>
              </div>
              <span className="status-dot">
                <i /> Ready
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="field-label">Scenario</div>
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
            <div className="console-metrics">
              <Metric
                label="Events"
                value={fmt(activeScenario.events)}
                detail="OCEL events"
              />
              <Metric
                label="Objects"
                value={fmt(activeScenario.objects)}
                detail="7 object types"
              />
              <Metric
                label="E2O links"
                value={fmt(activeScenario.e2o)}
                detail="event-to-object"
              />
              <Metric
                label="O2O links"
                value={fmt(activeScenario.o2o)}
                detail="object-to-object"
              />
            </div>
            <div className="integrity-row">
              <span>
                <CheckCircle2 /> 0 dangling E2O/O2O
              </span>
              <span>
                <CheckCircle2 /> Monotonic timestamps
              </span>
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

      <section className="content-section" id="model">
        <SectionHeading
          eyebrow="01 · The representation problem"
          title="One review event touches more than one ‘case’"
          copy="Selecting a single case notion forces the other relationships into duplicated rows, attributes or silence. OCEL keeps the event once and links every involved object explicitly."
        />
        <div className="model-grid">
          <Card className="object-map-card">
            <CardHeader>
              <CardTitle>Selected event · R2 score published</CardTitle>
              <CardDescription>EVT-00482 · 21 Aug 2026, 14:32</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="object-map">
                <div className="event-node">
                  <Workflow />
                  <strong>R2 score published</strong>
                  <small>one immutable event</small>
                </div>
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <span key={n} className={`connector c${n}`} />
                ))}
                <div className="object-node n1">
                  <b>P</b>
                  <span>
                    Project<small>PRJ-041</small>
                  </span>
                </div>
                <div className="object-node n2">
                  <b>T</b>
                  <span>
                    Team<small>TEAM-041</small>
                  </span>
                </div>
                <div className="object-node n3">
                  <b>S</b>
                  <span>
                    Student<small>3 linked</small>
                  </span>
                </div>
                <div className="object-node n4">
                  <b>F</b>
                  <span>
                    Faculty<small>FAC-017</small>
                  </span>
                </div>
                <div className="object-node n5">
                  <b>R</b>
                  <span>
                    Review stage<small>R2</small>
                  </span>
                </div>
                <div className="object-node n6">
                  <b>V</b>
                  <span>
                    Report version<small>v2.3</small>
                  </span>
                </div>
              </div>
              <div className="map-legend">
                <Info /> Illustrative event from the synthetic OCEL schema, not a
                production record.
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
          eyebrow="02 · Controlled ablation"
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
          eyebrow="03 · Analysis proof"
          title="The linked log supports detection and next-step prediction"
          copy="A deterministic gap detector validates the observability mechanism; a grouped Markov baseline tests whether lifecycle context supports useful transition prediction."
        />
        <div className="analysis-grid">
          <Card className="run-card">
            <CardHeader>
              <CardTitle>Run controlled analysis</CardTitle>
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
                    <Play /> Run synthetic benchmark
                  </>
                )}
                {analysisState === 'running' && (
                  <>
                    <span className="spinner" /> Evaluating 6 risk predicates…
                  </>
                )}
                {analysisState === 'done' && (
                  <>
                    <Check /> Analysis complete
                  </>
                )}
              </Button>
              {analysisState === 'idle' ? (
                <div className="waiting-state">
                  <Database />
                  <p>
                    Results are precomputed from the packaged generator. Run to
                    reveal the audit.
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
                      <strong>{item.f1.toFixed(3)}</strong>
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
                <strong>0.977</strong>
                <small>Controlled injected anomalies</small>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Next-transition baseline</CardTitle>
                <CardDescription>70 / 15 / 15 split by project</CardDescription>
              </CardHeader>
              <CardContent className="mini-scores">
                <div>
                  <strong>91.2%</strong>
                  <span>Top-1 accuracy</span>
                </div>
                <div>
                  <strong>98.6%</strong>
                  <span>Top-2 accuracy</span>
                </div>
                <div>
                  <strong>0.673</strong>
                  <span>Macro-F1</span>
                </div>
              </CardContent>
            </Card>
            <div className="caution">
              <TriangleAlert />
              <p>
                <strong>Interpretation boundary</strong>Detectors target the
                documented structures used for injection. Generalisation to
                real institutional logs remains untested.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="content-section dark-section" id="twin">
        <SectionHeading
          eyebrow="04 · Prescriptive extension"
          title="From diagnosis to an intervention hypothesis"
          copy="A synthetic digital twin compares process policies before any platform change is recommended. Choose a policy to inspect its simulated outcomes."
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
              <CardTitle>{policies[policy].name}</CardTitle>
              <CardDescription>
                5,000 simulated projects · synthetic assumptions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="twin-kpis">
                <Metric
                  label="Deadlock rate"
                  value={`${policies[policy].deadlock}%`}
                  detail={policy === 0 ? 'reference' : `↓ ${delta.deadlock} pp`}
                />
                <Metric
                  label="Completion"
                  value={`${policies[policy].completion}%`}
                  detail={
                    policy === 0 ? 'reference' : `↑ ${delta.completion} pp`
                  }
                />
                <Metric
                  label="Median wait"
                  value={`${policies[policy].wait}h`}
                  detail={policy === 0 ? 'reference' : `↓ ${delta.wait} hours`}
                />
              </div>
              <div className="completion-track">
                <span style={{ width: `${policies[policy].completion}%` }} />
                <i>stage completion</i>
              </div>
              {policy === 3 && (
                <div className="best-result">
                  <Sparkles />
                  <p>
                    <strong>Best simulated trade-off</strong>Combined
                    intervention reduces deadlock from 11.2% to 1.3% while
                    lifting completion from 74.5% to 89.5%.
                  </p>
                </div>
              )}
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
              <strong>Next</strong>Map approved portal audit fields, pseudonymise
              identifiers and recalibrate thresholds.
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
        <p>
          All displayed outcomes are synthetic prototype validation, not
          observed institutional outcomes.
        </p>
        <Button
          variant="outline"
          onClick={() => {
            setStep(0);
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
            : 'Share of OCEL event-to-object and object-to-object relations retained'}
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
