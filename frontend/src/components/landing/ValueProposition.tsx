import React from "react";
import {
  Check,
  X,
  Sparkles,
  Zap,
  Shield,
  Star,
  ArrowRight,
  Users,
  Code,
  TrendingUp,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";

export default function ValueProposition(): React.ReactElement {
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
            // ignore localStorage write errors
          }
          navigate(`/conversations/${data.conversation_id}`);
        },
      },
    );
  };

  const traditionalApproach = [
    { item: "Hire full development team", cost: "$300k+/year" },
    { item: "Long onboarding process", cost: "2-3 months" },
    { item: "Limited to working hours", cost: "40 hrs/week" },
    { item: "Communication overhead", cost: "20% productivity loss" },
    { item: "Bug fixes & maintenance", cost: "$50k+/year" },
  ];

  const withForge = [
    { item: "AI-powered full team", cost: "Included" },
    { item: "Instant availability", cost: "0 seconds" },
    { item: "24/7 productivity", cost: "168 hrs/week" },
    { item: "Zero communication lag", cost: "100% efficiency" },
    { item: "Automated quality checks", cost: "Built-in" },
  ];

  const benefits = [
    {
      icon: TrendingUp,
      title: "10x Faster",
      description: "Deliver projects in days, not months",
      color: "brand",
    },
    {
      icon: Shield,
      title: "Enterprise Quality",
      description: "Production-ready code with tests",
      color: "success",
    },
    {
      icon: Zap,
      title: "Instant Scaling",
      description: "From prototype to production instantly",
      color: "warning",
    },
    {
      icon: Users,
      title: "Full Team",
      description: "PM, Architect, Engineer, QA, DevOps",
      color: "accent",
    },
  ];

  return (
    <section className="relative w-full py-24 px-6 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-background-primary via-background-secondary to-background-primary" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-px bg-gradient-to-r from-transparent via-border to-transparent" />
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-full h-px bg-gradient-to-r from-transparent via-border to-transparent" />

      <div className="relative max-w-7xl mx-auto z-10">
        {/* Header */}
        <div className="text-center mb-16 space-y-4">
          <Badge
            variant="secondary"
            className="glass border-brand-500/30 text-violet-500 px-6 py-3 text-sm font-medium"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Value Proposition
          </Badge>

          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold">
            <span className="text-foreground block mb-2">
              Why Choose Forge Pro?
            </span>
            <span className="text-gradient-brand">The Smart Alternative</span>
          </h2>

          <p className="text-lg md:text-xl text-foreground-secondary max-w-3xl mx-auto leading-relaxed">
            Compare the traditional development approach with the power of
            AI-driven orchestration
          </p>
        </div>

        {/* Comparison Cards */}
        <div className="grid lg:grid-cols-2 gap-8 mb-16">
          {/* Traditional Approach */}
          <Card className="relative overflow-hidden border-2 border-danger-500/20 bg-danger-500/5">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-danger-500 to-warning-500" />
            <CardHeader>
              <div className="flex items-center justify-between mb-4">
                <CardTitle className="text-2xl font-bold text-foreground flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-danger-500/20 flex items-center justify-center">
                    <X className="w-6 h-6 text-danger-500" />
                  </div>
                  Traditional Approach
                </CardTitle>
                <Badge
                  variant="outline"
                  className="border-danger-500/50 text-danger-500 bg-danger-500/10"
                >
                  Outdated
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {traditionalApproach.map((item, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-4 rounded-lg bg-background-tertiary/50 border border-border/30"
                >
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-danger-500/20 flex items-center justify-center mt-0.5">
                    <X className="w-4 h-4 text-danger-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-foreground mb-1">
                      {item.item}
                    </div>
                    <div className="text-sm text-foreground-tertiary">
                      {item.cost}
                    </div>
                  </div>
                </div>
              ))}

              <div className="mt-6 p-6 rounded-xl bg-danger-500/10 border-2 border-danger-500/20">
                <div className="text-center">
                  <div className="text-sm text-foreground-tertiary mb-1">
                    Total Annual Cost
                  </div>
                  <div className="text-4xl font-bold text-danger-500">
                    $400k+
                  </div>
                  <div className="text-xs text-foreground-tertiary mt-2">
                    + Months of setup time
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* With Forge Pro */}
          <Card className="relative overflow-hidden border-2 border-success-500/30 bg-success-500/5 shadow-xl">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-brand-500 via-success-500 to-accent-500" />
            <CardHeader>
              <div className="flex items-center justify-between mb-4">
                <CardTitle className="text-2xl font-bold text-foreground flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-500/20 to-success-500/20 flex items-center justify-center">
                    <Star className="w-6 h-6 text-violet-500" />
                  </div>
                  With Forge Pro
                </CardTitle>
                <Badge
                  variant="outline"
                  className="border-success-500/50 text-success-500 bg-success-500/10 animate-pulse"
                >
                  Recommended
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {withForge.map((item, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-4 rounded-lg bg-gradient-to-r from-success-500/5 to-brand-500/5 border border-success-500/20"
                >
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-success-500/20 flex items-center justify-center mt-0.5">
                    <Check className="w-4 h-4 text-success-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-foreground mb-1">
                      {item.item}
                    </div>
                    <div className="text-sm font-semibold text-success-500">
                      {item.cost}
                    </div>
                  </div>
                </div>
              ))}

              <div className="mt-6 p-6 rounded-xl bg-gradient-to-br from-brand-500/10 to-success-500/10 border-2 border-brand-500/30">
                <div className="text-center">
                  <div className="text-sm text-foreground-tertiary mb-1">
                    Open Source
                  </div>
                  <div className="text-4xl font-bold bg-gradient-to-r from-brand-500 to-success-500 bg-clip-text text-transparent">
                    FREE
                  </div>
                  <div className="text-xs text-foreground-tertiary mt-2">
                    + Instant setup
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Benefits Grid */}
        <div className="grid md:grid-cols-4 gap-6 mb-16">
          {benefits.map((benefit, index) => {
            const Icon = benefit.icon;
            const colorClasses = {
              brand: {
                bg: "bg-brand-500/10",
                text: "text-violet-500",
                border: "border-brand-500/20",
              },
              success: {
                bg: "bg-success-500/10",
                text: "text-success-500",
                border: "border-success-500/20",
              },
              warning: {
                bg: "bg-warning-500/10",
                text: "text-warning-500",
                border: "border-warning-500/20",
              },
              accent: {
                bg: "bg-accent-500/10",
                text: "text-accent-500",
                border: "border-accent-500/20",
              },
            };
            const colors =
              colorClasses[benefit.color as keyof typeof colorClasses];

            return (
              <Card
                key={index}
                className={`glass border ${colors.border} hover:scale-105 transition-all duration-300`}
              >
                <CardContent className="p-6 text-center">
                  <div
                    className={`w-12 h-12 mx-auto mb-4 rounded-xl ${colors.bg} flex items-center justify-center`}
                  >
                    <Icon className={`w-6 h-6 ${colors.text}`} />
                  </div>
                  <h3 className="font-bold text-foreground mb-2">
                    {benefit.title}
                  </h3>
                  <p className="text-sm text-foreground-secondary">
                    {benefit.description}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* CTA Section */}
        <Card className="glass border-brand-500/30 shadow-2xl">
          <CardContent className="p-12 text-center">
            <div className="max-w-3xl mx-auto space-y-6">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-500/10 border border-brand-500/20 mb-4">
                <Zap className="w-4 h-4 text-violet-500" />
                <span className="text-sm font-medium text-violet-500">
                  No credit card required
                </span>
              </div>

              <h3 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                Ready to Transform Your Development?
              </h3>

              <p className="text-lg text-foreground-secondary mb-8">
                Join 50,000+ developers who are building faster, smarter, and
                better with Forge Pro
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button
                  onClick={onStart}
                  disabled={isPending}
                  size="lg"
                  className="gradient-brand hover:opacity-90 text-white px-12 py-6 text-lg font-bold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
                >
                  {isPending ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-3" />
                      Starting...
                    </>
                  ) : (
                    <>
                      Start Building Now
                      <ArrowRight className="w-5 h-5 ml-3" />
                    </>
                  )}
                </Button>

                <Button
                  size="lg"
                  variant="outline"
                  className="border-border hover:border-brand-500/50 text-foreground hover:text-violet-500 px-12 py-6 text-lg font-semibold"
                >
                  <Code className="w-5 h-5 mr-3" />
                  View Documentation
                </Button>
              </div>

              <div className="flex items-center justify-center gap-6 text-sm text-foreground-tertiary mt-6">
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-success-500" />
                  <span>Open source</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-success-500" />
                  <span>Self-hosted</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-success-500" />
                  <span>Privacy first</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
