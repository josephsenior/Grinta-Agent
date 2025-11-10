import React, { useState, useEffect } from "react";
import {
  Workflow,
  Users,
  Code,
  TestTube,
  Rocket,
  CheckCircle,
  ArrowRight,
  Sparkles,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";

export default function MetaSOPShowcase(): React.ReactElement {
  const [activeStep, setActiveStep] = useState(0);
  const [progress, setProgress] = useState(0);

  const steps = [
    {
      id: "pm",
      icon: Users,
      role: "Product Manager",
      task: "Define requirements",
      output: "User stories & acceptance criteria",
      color: "brand",
      status: "completed",
    },
    {
      id: "architect",
      icon: Workflow,
      role: "Architect",
      task: "Design system",
      output: "API specs & architecture docs",
      color: "accent",
      status: "completed",
    },
    {
      id: "engineer",
      icon: Code,
      role: "Engineer",
      task: "Implement code",
      output: "Production-ready code",
      color: "success",
      status: "in_progress",
    },
    {
      id: "qa",
      icon: TestTube,
      role: "QA Engineer",
      task: "Test & verify",
      output: "Test reports & coverage",
      color: "warning",
      status: "pending",
    },
    {
      id: "deploy",
      icon: Rocket,
      role: "DevOps",
      task: "Deploy & monitor",
      output: "Live production deployment",
      color: "info",
      status: "pending",
    },
  ];

  // Auto-advance through steps
  useEffect(() => {
    const stepTimer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
      setProgress(0);
    }, 4000);

    const progressTimer = setInterval(() => {
      setProgress((prev) => (prev >= 100 ? 0 : prev + 2.5));
    }, 100);

    return () => {
      clearInterval(stepTimer);
      clearInterval(progressTimer);
    };
  }, []);

  const getColorClasses = (color: string) => {
    const colors = {
      brand: {
        bg: "bg-brand-500/10",
        border: "border-brand-500/30",
        text: "text-violet-500",
        glow: "shadow-brand-500/20",
      },
      accent: {
        bg: "bg-accent-500/10",
        border: "border-accent-500/30",
        text: "text-accent-500",
        glow: "shadow-accent-500/20",
      },
      success: {
        bg: "bg-success-500/10",
        border: "border-success-500/30",
        text: "text-success-500",
        glow: "shadow-success-500/20",
      },
      warning: {
        bg: "bg-warning-500/10",
        border: "border-warning-500/30",
        text: "text-warning-500",
        glow: "shadow-warning-500/20",
      },
      info: {
        bg: "bg-info-500/10",
        border: "border-info-500/30",
        text: "text-info-500",
        glow: "shadow-info-500/20",
      },
    };
    return colors[color as keyof typeof colors] || colors.brand;
  };

  return (
    <section className="relative w-full py-24 px-6 overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0 bg-gradient-to-b from-background-secondary/50 to-background-primary pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-r from-brand-500/5 to-accent-500/5 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto z-10">
        {/* Section Header */}
        <div className="text-center mb-16 space-y-4">
          <Badge
            variant="secondary"
            className="glass border-brand-500/30 text-violet-500 px-6 py-3 text-sm font-medium"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            MetaSOP Orchestration
          </Badge>

          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold">
            <span className="bg-gradient-to-r from-foreground to-foreground-secondary bg-clip-text text-transparent">
              Full Team,
            </span>{" "}
            <span className="text-gradient-brand">One AI</span>
          </h2>

          <p className="text-lg md:text-xl text-foreground-secondary max-w-3xl mx-auto leading-relaxed">
            Watch as MetaSOP orchestrates an entire development team - from
            product managers to QA engineers - working in perfect harmony to
            deliver your project.
          </p>
        </div>

        {/* Orchestration Visualization */}
        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Left: Step Cards */}
          <div className="space-y-4">
            {steps.map((step, index) => {
              const colors = getColorClasses(step.color);
              const isActive = index === activeStep;
              const isCompleted = index < activeStep;
              const Icon = step.icon;

              return (
                <Card
                  key={step.id}
                  className={`group transition-all duration-500 cursor-pointer ${
                    isActive
                      ? `${colors.border} ${colors.glow} shadow-xl scale-105 border-2`
                      : isCompleted
                        ? "border-success-500/20 bg-success-500/5"
                        : "border-border/30 opacity-60"
                  }`}
                  onClick={() => setActiveStep(index)}
                >
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div
                        className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center ${
                          isActive
                            ? `${colors.bg} ${colors.border} border-2`
                            : isCompleted
                              ? "bg-success-500/20 border-success-500/30 border"
                              : "bg-background-tertiary border border-border"
                        }`}
                      >
                        {isCompleted ? (
                          <CheckCircle className="w-6 h-6 text-success-500" />
                        ) : (
                          <Icon
                            className={`w-6 h-6 ${isActive ? colors.text : "text-foreground-tertiary"}`}
                          />
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                          <h3
                            className={`font-bold text-lg ${isActive ? colors.text : "text-foreground"}`}
                          >
                            {step.role}
                          </h3>
                          {isActive && (
                            <Badge
                              variant="outline"
                              className={`${colors.border} ${colors.text} ${colors.bg} text-xs animate-pulse`}
                            >
                              <Zap className="w-3 h-3 mr-1" />
                              Active
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-foreground-secondary mb-2">
                          {step.task}
                        </p>
                        <p className="text-xs text-foreground-tertiary">
                          Delivers: {step.output}
                        </p>

                        {/* Progress Bar */}
                        {isActive && (
                          <div className="mt-3 space-y-2">
                            <div className="h-1.5 bg-background-tertiary rounded-full overflow-hidden">
                              <div
                                className={`h-full ${colors.bg.replace("/10", "/50")} transition-all duration-100`}
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Right: Live Preview */}
          <Card className="sticky top-24 glass border-border/30 shadow-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-500 to-accent-500 flex items-center justify-center">
                  <Workflow className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="text-lg font-bold text-foreground">
                    Live Orchestration
                  </div>
                  <div className="text-sm font-normal text-foreground-secondary">
                    Step {activeStep + 1} of {steps.length}
                  </div>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Current Step Details */}
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-12 h-12 rounded-xl flex items-center justify-center ${getColorClasses(steps[activeStep].color).bg} ${getColorClasses(steps[activeStep].color).border} border-2`}
                  >
                    {React.createElement(steps[activeStep].icon, {
                      className: `w-6 h-6 ${getColorClasses(steps[activeStep].color).text}`,
                    })}
                  </div>
                  <div>
                    <h4 className="font-bold text-foreground">
                      {steps[activeStep].role}
                    </h4>
                    <p className="text-sm text-foreground-secondary">
                      {steps[activeStep].task}
                    </p>
                  </div>
                </div>

                {/* Code Preview */}
                <div className="bg-background-tertiary/50 rounded-lg p-4 border border-border font-mono text-sm">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2.5 h-2.5 bg-danger-500 rounded-full" />
                    <div className="w-2.5 h-2.5 bg-warning-500 rounded-full" />
                    <div className="w-2.5 h-2.5 bg-success-500 rounded-full" />
                    <span className="text-xs text-foreground-tertiary ml-2">
                      output.
                      {activeStep === 0
                        ? "json"
                        : activeStep === 1
                          ? "yaml"
                          : activeStep === 2
                            ? "py"
                            : activeStep === 3
                              ? "test"
                              : "sh"}
                    </span>
                  </div>
                  <div className="text-foreground-secondary space-y-1">
                    {activeStep === 0 && (
                      <>
                        <div>
                          <span className="text-violet-500">"user_story"</span>:{" "}
                          "Build authentication system"
                        </div>
                        <div>
                          <span className="text-accent-500">"priority"</span>:{" "}
                          "high"
                        </div>
                      </>
                    )}
                    {activeStep === 1 && (
                      <>
                        <div>
                          <span className="text-accent-500">endpoints</span>:
                        </div>
                        <div className="ml-4">
                          - <span className="text-success-500">POST</span>{" "}
                          /api/auth/login
                        </div>
                      </>
                    )}
                    {activeStep === 2 && (
                      <>
                        <div>
                          <span className="text-violet-500">def</span>{" "}
                          <span className="text-accent-500">
                            authenticate_user
                          </span>
                          ():
                        </div>
                        <div className="ml-4 text-foreground-tertiary">
                          # Implementation...
                        </div>
                      </>
                    )}
                    {activeStep === 3 && (
                      <>
                        <div>
                          <span className="text-success-500">✓</span> Test case
                          1 passed
                        </div>
                        <div>
                          <span className="text-success-500">✓</span> Coverage:
                          98%
                        </div>
                      </>
                    )}
                    {activeStep === 4 && (
                      <>
                        <div>
                          <span className="text-accent-500">→</span> Deploying
                          to production...
                        </div>
                        <div>
                          <span className="text-success-500">✓</span> Deploy
                          successful
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Output Badge */}
                <div className="flex items-center gap-2 p-4 bg-gradient-to-r from-success-500/10 to-success-500/5 rounded-lg border border-success-500/20">
                  <CheckCircle className="w-5 h-5 text-success-500" />
                  <span className="text-sm font-medium text-foreground">
                    {steps[activeStep].output}
                  </span>
                </div>
              </div>

              {/* Try It Button */}
              <Button className="w-full gradient-brand hover:opacity-90 text-white font-bold py-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105">
                Try MetaSOP Now
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Benefits Grid */}
        <div className="mt-24 grid md:grid-cols-3 gap-6">
          <Card className="glass border-border/30 hover:border-brand-500/30 transition-all duration-300">
            <CardContent className="p-8 text-center">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-brand-500/20 to-brand-600/20 flex items-center justify-center border border-brand-500/30">
                <Zap className="w-7 h-7 text-violet-500" />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-2">
                10x Faster Development
              </h3>
              <p className="text-sm text-foreground-secondary">
                Complete projects in hours, not weeks. MetaSOP orchestrates the
                entire team simultaneously.
              </p>
            </CardContent>
          </Card>

          <Card className="glass border-border/30 hover:border-success-500/30 transition-all duration-300">
            <CardContent className="p-8 text-center">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-success-500/20 to-success-600/20 flex items-center justify-center border border-success-500/30">
                <CheckCircle className="w-7 h-7 text-success-500" />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-2">
                Zero Bottlenecks
              </h3>
              <p className="text-sm text-foreground-secondary">
                No waiting for team members. Each role executes in parallel with
                perfect coordination.
              </p>
            </CardContent>
          </Card>

          <Card className="glass border-border/30 hover:border-accent-500/30 transition-all duration-300">
            <CardContent className="p-8 text-center">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent-500/20 to-accent-600/20 flex items-center justify-center border border-accent-500/30">
                <Workflow className="w-7 h-7 text-accent-500" />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-2">
                Enterprise Quality
              </h3>
              <p className="text-sm text-foreground-secondary">
                Every output meets professional standards with built-in best
                practices and quality checks.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
