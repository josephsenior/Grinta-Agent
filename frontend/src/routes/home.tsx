import React from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BadgeCheck,
  Brain,
  Database,
  Gauge,
  LineChart,
  PauseCircle,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import { Link, useNavigate, redirect } from "react-router-dom";
import AnimatedBackground from "#/components/landing/AnimatedBackground";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { Card, CardContent, CardTitle } from "#/components/ui/card";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useUserProviders } from "#/hooks/use-user-providers";
import {
  heroContent,
  scorecard,
  featureHighlights,
  reliabilityPillars,
  shippingNow,
  comingLater,
  betaChecklist,
  finalCta,
} from "#/content/landing";
import { Route } from "./+types/home";
import Forge from "#/api/forge";
import { queryClient } from "#/query-client-config";

const featureIcons: LucideIcon[] = [Sparkles, Workflow, Gauge, Brain];
const reliabilityIcons: LucideIcon[] = [ShieldCheck, LineChart, Database];
const heroAssurances = [
  "Structured diffs and test awareness keep repos stable.",
  "Hybrid memory auto-cleans context every 30 days.",
  "Circuit breaker + retries stop runaway sessions.",
];

const featureLayoutClasses = [
  "md:col-span-3 lg:row-span-2",
  "md:col-span-3",
  "md:col-span-2",
  "md:col-span-4",
];

const roadmapPhases = [
  { title: "Shipping now", accent: "success" as const, items: shippingNow },
  {
    title: "Post-beta roadmap",
    accent: "warning" as const,
    items: comingLater,
  },
];

// Redirect authenticated users to dashboard
export const clientLoader = async (args: Route.ClientLoaderArgs) => {
  try {
    const config = await queryClient.fetchQuery({
      queryKey: ["config"],
      queryFn: Forge.getConfig,
    });

    // Only redirect in SaaS mode
    if (config.APP_MODE === "saas") {
      try {
        await Forge.authenticate(config.APP_MODE);
        // User is authenticated, redirect to dashboard
        return redirect("/dashboard");
      } catch (error) {
        // User is not authenticated, show landing page
        return null;
      }
    }

    // In OSS mode, always show landing page
    return null;
  } catch (error) {
    // If config fails, show landing page
    return null;
  }
};

const reliabilityMetrics = [
  { label: "Circuit breaker cooldown", value: "90s" },
  { label: "Retry budget", value: "6 attempts" },
  { label: "Cost ceilings", value: "$1 / $10" },
];

function HomeScreen() {
  useUserProviders();
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();

  const onStart = () => {
    createConversation(
      {},
      {
        onSuccess: (data) => {
          try {
            localStorage.setItem(
              "RECENT_CONVERSATION_ID",
              data.conversation_id,
            );
          } catch (err) {
            // ignore storage write issues
          }
          navigate(`/conversations/${data.conversation_id}`);
        },
      },
    );
  };

  return (
    <div
      data-testid="home-screen"
      className="relative min-h-screen overflow-hidden bg-black text-foreground"
    >
      <div aria-hidden className="pointer-events-none">
        <AnimatedBackground />
      </div>

      <main className="relative z-[1] mx-auto flex w-full max-w-6xl flex-col gap-20 px-6 pb-20 pt-28 lg:px-0">
        {/* Hero */}
        <section className="relative overflow-hidden rounded-[40px] border border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/80 shadow-[0_40px_120px_rgba(0,0,0,0.45)]">
          <div aria-hidden className="absolute inset-0">
            <div className="absolute inset-y-0 left-1/2 w-1/2 rounded-l-[40px] bg-gradient-to-r from-brand-500/10 via-accent-500/5 to-transparent blur-3xl" />
            <div className="absolute -top-24 right-6 h-60 w-60 rounded-full bg-brand-500/25 blur-[130px]" />
            <div className="absolute -bottom-20 left-10 h-48 w-48 rounded-full bg-accent-emerald/20 blur-[110px]" />
          </div>

          <div className="relative grid gap-12 px-8 py-12 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)] lg:items-center">
            <div className="space-y-8 text-center lg:text-left">
              <Badge
                variant="secondary"
                className="mx-auto inline-flex items-center gap-2 rounded-full border border-brand-500/40 bg-white/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.25em] text-foreground-secondary lg:mx-0"
              >
                <Sparkles className="h-4 w-4" />
                {heroContent.badge}
              </Badge>

              <div className="space-y-6">
                <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl">
                  {heroContent.heading}
                </h1>
                <p className="text-lg leading-relaxed text-foreground-secondary sm:text-xl">
                  {heroContent.subheading}
                </p>
              </div>

              <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-start">
                <Button
                  size="lg"
                  onClick={onStart}
                  disabled={isPending}
                  className="w-full sm:w-auto"
                >
                  {isPending ? "Starting..." : "Start a secure workspace"}
                  <ArrowRight className="h-5 w-5" />
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto border border-white/20 bg-transparent text-foreground"
                >
                  <Link to="/dashboard">Go to Dashboard</Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto border border-white/20 bg-transparent text-foreground"
                >
                  <Link to="/chat-demo">Watch the product tour</Link>
                </Button>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-3 text-sm text-foreground-tertiary lg:justify-start">
                {heroContent.trustSignals.map((signal) => (
                  <span
                    key={signal}
                    className="inline-flex items-center gap-2 rounded-full border border-white/15 px-3 py-1"
                  >
                    <BadgeCheck className="h-4 w-4 text-success-400" />
                    {signal}
                  </span>
                ))}
              </div>
            </div>

            <div className="space-y-5">
              <div className="rounded-3xl border border-white/15 bg-black/70 p-6">
                <div className="flex items-center justify-between text-sm text-foreground-secondary">
                  <span>Beta scorecard</span>
                  <span className="text-foreground-tertiary">Live targets</span>
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  {scorecard.map(({ label, value }) => (
                    <div
                      key={label}
                      className="rounded-2xl border border-white/10 bg-gradient-to-b from-white/5 to-transparent p-4"
                    >
                      <div className="text-xs uppercase tracking-[0.2em] text-foreground-tertiary">
                        {label}
                      </div>
                      <div className="mt-3 text-2xl font-semibold text-foreground">
                        {value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-3xl border border-brand-500/30 bg-black/60 p-6">
                <p className="text-sm font-medium text-foreground">
                  Why CodeAct ships first
                </p>
                <div className="mt-4 space-y-3">
                  {heroAssurances.map((item) => (
                    <div key={item} className="flex items-start gap-3">
                      <span className="mt-1 h-2 w-2 rounded-full bg-brand-400" />
                      <span className="text-sm text-foreground-secondary">
                        {item}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-[32px] border border-white/5 bg-black/60 px-6 py-8">
          <div className="grid gap-6 sm:grid-cols-3">
            {heroContent.proofStats.map(({ label, value }) => (
              <div
                key={label}
                className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 via-transparent to-transparent p-5"
              >
                <div className="text-sm text-foreground-tertiary">{label}</div>
                <div className="mt-2 text-3xl font-semibold text-foreground">
                  {value}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Beta feature focus */}
        <section className="relative overflow-hidden rounded-[36px] border border-white/10 bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.35),_rgba(0,0,0,0.8))] p-8">
          <div className="relative z-[1] space-y-6">
            <Badge
              variant="secondary"
              className="inline-flex items-center gap-2 border border-white/20 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.2em] text-foreground-secondary"
            >
              What ships in beta
            </Badge>
            <div className="space-y-3">
              <h2 className="text-3xl font-semibold text-foreground sm:text-4xl">
                The systems already holding up under pressure.
              </h2>
              <p className="text-base text-foreground-secondary sm:text-lg">
                Every surface listed here runs daily on active customer repos—no
                prototypes, just production-ready workflows.
              </p>
            </div>

            <div className="grid auto-rows-[minmax(180px,1fr)] gap-6 md:grid-cols-6">
              {featureHighlights.map(({ title, description }, index) => {
                const Icon = featureIcons[index] ?? Sparkles;
                const layoutClass =
                  featureLayoutClasses[index] ?? "md:col-span-3";
                return (
                  <Card
                    key={title}
                    className={`${layoutClass} group flex h-full flex-col border-white/10 bg-black/60 p-6 transition hover:border-brand-500/40`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-white/5 p-3 text-brand-300">
                        <Icon className="h-6 w-6" />
                      </div>
                      <CardTitle className="text-lg font-semibold text-foreground">
                        {title}
                      </CardTitle>
                    </div>
                    <p className="mt-4 text-sm leading-relaxed text-foreground-secondary">
                      {description}
                    </p>
                    <div className="mt-auto pt-6 text-xs uppercase tracking-[0.35em] text-brand-200">
                      Proven in beta
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          <div
            className="pointer-events-none absolute inset-0 opacity-40"
            aria-hidden
          >
            <div className="absolute inset-0 bg-gradient-to-br from-brand-500/20 via-transparent to-accent-500/10" />
            <div className="absolute inset-0 blur-3xl bg-brand-500/10" />
          </div>
        </section>

        {/* Roadmap */}
        <section className="rounded-[32px] border border-white/5 bg-black/70 p-8">
          <div className="flex flex-col gap-8 lg:flex-row">
            {roadmapPhases.map(({ title, accent, items }, phaseIdx) => {
              const isSuccess = accent === "success";
              const badgeClasses = isSuccess
                ? "border-success-500/40 bg-success-500/10 text-success-200"
                : "border-warning-500/40 bg-warning-500/10 text-warning-200";
              const dotClasses = isSuccess
                ? "border-success-400 bg-success-500/30"
                : "border-warning-400 bg-warning-500/30";
              const phaseLabel = phaseIdx === 0 ? "Now" : "Next";
              return (
                <div
                  key={title}
                  className="flex-1 rounded-2xl border border-white/10 bg-black/60 p-6"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-12 w-12 items-center justify-center rounded-full border text-sm font-semibold ${badgeClasses}`}
                    >
                      {phaseLabel}
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.35em] text-foreground-tertiary">
                        Phase {phaseIdx + 1}
                      </p>
                      <h3 className="text-xl font-semibold text-foreground">
                        {title}
                      </h3>
                    </div>
                  </div>

                  <div className="relative mt-8 space-y-6">
                    <span
                      aria-hidden
                      className="absolute left-5 top-1 h-[calc(100%_-_0.5rem)] w-px bg-white/10"
                    />
                    <ol className="space-y-6">
                      {items.map((item) => (
                        <li
                          key={item}
                          className="relative pl-12 text-sm text-foreground-secondary"
                        >
                          <span
                            className={`absolute left-4 top-1.5 block h-3 w-3 rounded-full border-2 ${dotClasses}`}
                          />
                          {item}
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Reliability */}
        <section className="rounded-[36px] border border-white/5 bg-black/70 p-8">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
            <div>
              <Badge
                variant="secondary"
                className="inline-flex items-center gap-2 border border-white/15 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.2em] text-foreground-secondary"
              >
                Production-grade reliability
              </Badge>
              <h2 className="mt-4 text-3xl font-semibold text-foreground sm:text-4xl">
                Infrastructure ready for real beta traffic.
              </h2>
              <div className="mt-8 grid gap-6 md:grid-cols-2">
                {reliabilityPillars.map(({ title, description }, index) => {
                  const Icon = reliabilityIcons[index] ?? ShieldCheck;
                  return (
                    <div
                      key={title}
                      className="rounded-2xl border border-white/10 bg-black/60 p-5 transition hover:border-brand-500/30"
                    >
                      <div className="flex items-center gap-3">
                        <div className="rounded-xl bg-white/5 p-3 text-brand-300">
                          <Icon className="h-6 w-6" />
                        </div>
                        <h3 className="text-base font-semibold text-foreground">
                          {title}
                        </h3>
                      </div>
                      <p className="mt-3 text-sm text-foreground-secondary">
                        {description}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-6 rounded-3xl border border-white/10 bg-black/60 p-6">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-foreground-tertiary">
                  Guardrails
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-foreground">
                  Reliability control panel
                </h3>
                <p className="mt-3 text-sm text-foreground-secondary">
                  Every beta run is paired with live Prometheus alerts,
                  Redis-backed cost limits, and circuit-breaker policies.
                </p>
              </div>
              <div className="grid gap-4">
                {reliabilityMetrics.map(({ label, value }) => (
                  <div
                    key={label}
                    className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/50 px-4 py-3"
                  >
                    <span className="text-sm text-foreground-tertiary">
                      {label}
                    </span>
                    <span className="text-lg font-semibold text-foreground">
                      {value}
                    </span>
                  </div>
                ))}
              </div>
              <div className="rounded-2xl border border-brand-500/30 bg-brand-500/5 p-4 text-sm text-foreground-secondary">
                <p className="font-medium text-foreground">Runtime snapshot</p>
                <ul className="mt-3 space-y-2">
                  <li className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-success-400" /> 96%
                    agent pass rate this week
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-accent-500" /> 2.7s
                    p95 latency across live tenants
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-brand-400" />{" "}
                    $10/day spend cap with Slack alerts
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Checklist */}
        <section className="space-y-10">
          <div className="max-w-3xl">
            <Badge
              variant="secondary"
              className="inline-flex items-center gap-2 border border-brand-500/30 bg-brand-500/10 px-4 py-1.5 text-xs uppercase tracking-[0.35em] text-brand-200"
            >
              Launch checklist
            </Badge>
            <h2 className="mt-4 text-3xl font-semibold text-foreground sm:text-4xl">
              How we hold ourselves accountable before widening access.
            </h2>
          </div>

          <Card className="border-white/10 bg-black/60">
            <CardContent className="space-y-5 p-8">
              <ol className="space-y-5">
                {betaChecklist.map((item, index) => (
                  <li key={item} className="flex items-start gap-4">
                    <span className="flex h-12 w-12 items-center justify-center rounded-full border border-brand-500/40 bg-brand-500/10 text-base font-semibold text-brand-200">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="flex-1 rounded-2xl border border-white/10 bg-black/50 px-5 py-4 text-sm text-foreground-secondary">
                      {item}
                    </div>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>

          <Card className="border-brand-500/20 bg-black/60">
            <CardContent className="flex flex-col gap-4 p-6 text-sm text-foreground-secondary md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-3 text-foreground-secondary">
                <PauseCircle className="h-5 w-5 text-brand-300" />
                Launch window: 2–3 days of focused testing, monitoring, and
                polish.
              </div>
              <Button asChild variant="link" className="text-brand-200">
                <Link to="/pricing" className="inline-flex items-center gap-2">
                  View beta-ready plans
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </section>

        {/* Final CTA */}
        <section>
          <Card className="relative overflow-hidden border-brand-500/40 bg-gradient-to-r from-brand-500/20 via-black/80 to-black/95">
            <div aria-hidden className="pointer-events-none absolute inset-0">
              <div className="absolute -top-24 left-1/3 h-64 w-64 rounded-full bg-brand-500/40 blur-[160px]" />
              <div className="absolute -bottom-20 right-10 h-52 w-52 rounded-full bg-accent-emerald/30 blur-[140px]" />
            </div>
            <CardContent className="relative flex flex-col items-center gap-6 px-8 py-12 text-center sm:px-12">
              <h2 className="text-3xl font-semibold sm:text-4xl">
                {finalCta.heading}
              </h2>
              <p className="max-w-3xl text-base text-foreground-secondary sm:text-lg">
                {finalCta.body}
              </p>
              <div className="grid gap-3 text-sm text-foreground-tertiary sm:grid-cols-3">
                <span className="rounded-full border border-white/15 px-4 py-2">
                  Transparent spend tracking
                </span>
                <span className="rounded-full border border-white/15 px-4 py-2">
                  Prometheus + Grafana dashboards
                </span>
                <span className="rounded-full border border-white/15 px-4 py-2">
                  Roadmap influence
                </span>
              </div>
              <div className="flex flex-col items-center gap-3 sm:flex-row">
                <Button
                  size="lg"
                  onClick={onStart}
                  disabled={isPending}
                  className="w-full sm:w-auto"
                >
                  {isPending ? "Starting..." : finalCta.primaryCta}
                  <ArrowRight className="h-5 w-5" />
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  asChild
                  className="w-full sm:w-auto"
                >
                  <Link to="/pricing">{finalCta.secondaryCta}</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;

export default HomeScreen;
