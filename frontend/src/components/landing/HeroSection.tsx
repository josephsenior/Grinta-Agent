import React, { useState, useEffect, useRef } from "react";
import {
  ArrowRight,
  Sparkles,
  Code,
  Zap,
  Star,
  Play,
  Github,
  CheckCircle,
  Users,
  TrendingUp,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { I18nKey } from "#/i18n/declaration";
import logoImage from "#/assets/branding/logo2.png";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import { Card, CardContent } from "#/components/ui/card";
import { Progress } from "#/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "#/components/ui/tabs";
import { useMagneticHover } from "#/hooks/use-mouse-position";
import { soundEffects } from "#/utils/sound-effects";

export default function HeroSection(): React.ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();
  const [progress, setProgress] = useState(0);
  const [activeTab, setActiveTab] = useState("code");
  const [displayedText, setDisplayedText] = useState("");
  const [showCursor, setShowCursor] = useState(true);
  const [cardTilt, setCardTilt] = useState({ rotateX: 0, rotateY: 0 });
  
  const primaryButtonRef = useRef<HTMLButtonElement>(null);
  const secondaryButtonRef = useRef<HTMLButtonElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  
  const primaryMagnetic = useMagneticHover(primaryButtonRef, 0.25);
  const secondaryMagnetic = useMagneticHover(secondaryButtonRef, 0.2);

  // Typing animation for headline
  const fullText = t(I18nKey.LANDING$SUBTITLE);
  
  useEffect(() => {
    let currentIndex = 0;
    const typingSpeed = 80;
    const typingTimeout: { id: ReturnType<typeof setTimeout> | null } = { id: null };

    const typeText = () => {
      if (currentIndex < fullText.length) {
        setDisplayedText(fullText.slice(0, currentIndex + 1));
        currentIndex++;
        typingTimeout.id = setTimeout(typeText, typingSpeed);
      }
    };

    typeText();
    
    // Cursor blink
    const cursorInterval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530);

    return () => {
      clearInterval(cursorInterval);
      if (typingTimeout.id != null) clearTimeout(typingTimeout.id);
    };
  }, [fullText]);

  // Detect Playwright test runs
  type WindowWithE2E = Window & { __Forge_PLAYWRIGHT?: boolean };
  const isPlaywrightRun =
    typeof window !== "undefined" &&
    (window as unknown as WindowWithE2E).__Forge_PLAYWRIGHT === true;

  const onStart = () => {
    soundEffects.success(); // Play success sound
    
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

  // Animated progress
  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((prev) => (prev >= 100 ? 0 : prev + 1));
    }, 50);
    return () => clearInterval(timer);
  }, []);

  // 3D card tilt effect
  const handleCardMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    
    const rotateY = ((x - centerX) / centerX) * 10;
    const rotateX = ((centerY - y) / centerY) * 10;
    
    setCardTilt({ rotateX, rotateY });
  };

  const handleCardMouseLeave = () => {
    setCardTilt({ rotateX: 0, rotateY: 0 });
  };

  return (
    <section
      className={`relative w-full flex items-center justify-center ${
        isPlaywrightRun ? "pointer-events-none" : "pointer-events-auto"
      }`}
    >
      <div className="max-w-6xl mx-auto w-full">
        <div className="flex flex-col gap-12 lg:gap-16 items-center w-full text-center">
          {/* Main Content */}
          <div className="text-center space-y-6 w-full">
            {/* Badges with stagger animation */}
            <div className="inline-flex items-center gap-4 mb-8">
              <Badge
                variant="secondary"
                className="glass-modern border-brand-500/30 text-foreground px-6 py-3 text-sm font-medium stagger-item delay-0 interactive-scale"
              >
                <Sparkles className="w-4 h-4 mr-2 text-violet-500 floating-icon" />
                {t(I18nKey.LANDING$CHANGE_PROMPT)}
              </Badge>
              <Badge
                variant="outline"
                className="border-success-500/50 text-success-500 bg-success-500/10 backdrop-blur-sm px-6 py-3 shadow-lg stagger-item delay-100 interactive-scale"
              >
                <Star className="w-3 h-3 mr-2" />
                New
              </Badge>
            </div>

            {/* Logo with glow effect */}
            <div className="flex justify-center mb-8 stagger-item delay-200">
              <div className="relative group">
                <img
                  src={logoImage}
                  alt="Forge Pro Logo"
                  className="w-20 h-20 object-contain group-hover:scale-110 transition-transform duration-500 logo-glow gpu-accelerated"
                />
                <div className="absolute inset-0 bg-gradient-to-r from-brand-500/30 to-accent-500/30 rounded-full blur-3xl -z-10 group-hover:blur-[60px] transition-all duration-500" />
                <div className="absolute -inset-8 bg-gradient-to-r from-brand-500/15 to-accent-500/15 rounded-full blur-2xl -z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              </div>
            </div>

            {/* Main Heading with typing animation */}
            <h1
              data-testid="page-title"
              className="section-heading text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.15] tracking-tight mb-6"
            >
              <span className="bg-gradient-to-r from-foreground via-foreground-secondary to-foreground-tertiary bg-clip-text text-transparent block mb-4 stagger-item delay-300">
                Ship Code 10x Faster
              </span>
              <span className="block text-gradient-animated bg-gradient-to-r from-brand-500 via-accent-500 to-brand-600 bg-clip-text text-transparent stagger-item delay-400 text-glow">
                {displayedText}
                {showCursor && <span className="typing-cursor inline-block w-1 h-[0.9em] bg-brand-500 ml-1" />}
              </span>
            </h1>

            {/* Subtitle - Benefit-driven */}
            <p className="text-lg sm:text-xl text-foreground-secondary max-w-3xl leading-relaxed font-light mx-auto mb-8 stagger-item delay-500">
              Your AI-powered software engineer that writes, tests, and deploys production-ready code in minutes, not days.
            </p>

            {/* CTA Buttons with magnetic hover */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8 stagger-item delay-600">
              <button
                ref={primaryButtonRef}
                onClick={onStart}
                onMouseEnter={() => soundEffects.hover()}
                disabled={isPending}
                className="cta-primary magnetic-button button-shine relative group px-12 py-6 text-lg font-bold rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/30 hover:shadow-2xl hover:shadow-brand-500/40 transition-all duration-300 disabled:opacity-60 disabled:cursor-not-allowed gpu-accelerated overflow-hidden"
                style={{
                  transform: `translate(${primaryMagnetic.offset.x}px, ${primaryMagnetic.offset.y}px)`,
                }}
              >
                {isPending ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-3 inline-block" />
                    Creating Your Workspace...
                  </>
                ) : (
                  <>
                    Start Building for Free
                    <ArrowRight className="w-5 h-5 ml-3 inline-block group-hover:translate-x-2 transition-transform duration-300" />
                  </>
                )}
              </button>

              <button
                ref={secondaryButtonRef}
                onMouseEnter={() => soundEffects.hover()}
                onClick={() => soundEffects.click()}
                className="magnetic-button relative group px-12 py-6 text-lg font-semibold rounded-xl border-2 border-brand-500/30 text-foreground hover:text-violet-500 backdrop-blur-sm bg-brand-500/5 hover:bg-violet-500/10 hover:border-brand-500/50 transition-all duration-300 gpu-accelerated"
                style={{
                  transform: `translate(${secondaryMagnetic.offset.x}px, ${secondaryMagnetic.offset.y}px)`,
                }}
              >
                <Play className="w-5 h-5 mr-3 inline-block" />
                See Live Demo
              </button>
            </div>

            {/* Enhanced Social Proof with hover effects */}
            <div className="flex flex-wrap items-center justify-center gap-4 text-sm stagger-item delay-700">
              <div className="flex items-center gap-3 glass-modern px-6 py-3 rounded-full shadow-lg hover:shadow-brand-500/20 interactive-scale group gpu-accelerated">
                <Github className="w-4 h-4 text-violet-500 group-hover:rotate-12 transition-transform duration-300" />
                <span className="font-medium text-foreground">
                  34k+ stars
                </span>
              </div>
              <div className="flex items-center gap-3 glass-modern px-6 py-3 rounded-full shadow-lg hover:shadow-success-500/20 interactive-scale group gpu-accelerated">
                <Users className="w-4 h-4 text-success-500 group-hover:scale-110 transition-transform duration-300" />
                <span className="font-medium text-foreground">
                  50k+ developers
                </span>
              </div>
              <div className="flex items-center gap-3 glass-modern px-6 py-3 rounded-full shadow-lg hover:shadow-accent-500/20 interactive-scale group gpu-accelerated">
                <TrendingUp className="w-4 h-4 text-accent-500 group-hover:translate-y-[-2px] transition-transform duration-300" />
                <span className="font-medium text-foreground">
                  99.8% uptime
                </span>
              </div>
            </div>

            {/* Trust Indicators */}
            <div className="flex items-center justify-center gap-3 mt-4 text-xs text-foreground-tertiary stagger-item delay-800">
              <div className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-success-500" />
                <span>No credit card required</span>
              </div>
              <div className="w-1 h-1 bg-foreground-tertiary/30 rounded-full" />
              <div className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-success-500" />
                <span>Open source</span>
              </div>
              <div className="w-1 h-1 bg-foreground-tertiary/30 rounded-full" />
              <div className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-success-500" />
                <span>Privacy first</span>
              </div>
            </div>
          </div>

          {/* Interactive Demo with 3D tilt */}
          <div 
            ref={cardRef}
            className="relative w-full max-w-3xl stagger-item delay-900"
            onMouseMove={handleCardMouseMove}
            onMouseLeave={handleCardMouseLeave}
          >
            <div 
              className="card-3d gpu-accelerated"
              style={{
                transform: `perspective(1000px) rotateX(${cardTilt.rotateX}deg) rotateY(${cardTilt.rotateY}deg)`,
              }}
            >
              <Card className="glass-modern gradient-border-animated shadow-2xl shadow-brand-500/20 hover:shadow-brand-500/30 transition-all duration-500 overflow-hidden">
                <CardContent className="p-8 card-3d-inner">
                  <Tabs
                    value={activeTab}
                    onValueChange={setActiveTab}
                    className="w-full"
                  >
                    <TabsList className="grid w-full grid-cols-3 glass-modern p-1 gap-1">
                      <TabsTrigger
                        value="code"
                        className="relative flex items-center justify-center gap-2 px-4 py-3 rounded-lg data-[state=active]:bg-brand-500/20 data-[state=active]:text-violet-500 data-[state=active]:shadow-lg data-[state=active]:shadow-brand-500/20 transition-all duration-300"
                      >
                        <Code className="w-4 h-4" />
                        Code
                      </TabsTrigger>
                      <TabsTrigger
                        value="test"
                        className="relative flex items-center justify-center gap-2 px-4 py-3 rounded-lg data-[state=active]:bg-success-500/20 data-[state=active]:text-success-500 data-[state=active]:shadow-lg data-[state=active]:shadow-success-500/20 transition-all duration-300"
                      >
                        <Zap className="w-4 h-4" />
                        Test
                      </TabsTrigger>
                      <TabsTrigger
                        value="deploy"
                        className="relative flex items-center justify-center gap-2 px-4 py-3 rounded-lg data-[state=active]:bg-accent-500/20 data-[state=active]:text-accent-500 data-[state=active]:shadow-lg data-[state=active]:shadow-accent-500/20 transition-all duration-300"
                      >
                        <ArrowRight className="w-4 h-4" />
                        Deploy
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="code" className="mt-8">
                      <div className="space-y-6">
                        <div className="glass-modern rounded-xl p-6 border border-brand-500/20 spotlight-effect">
                          <div className="flex items-center gap-3 mb-4">
                            <div className="w-3 h-3 bg-danger-500 rounded-full shadow-lg shadow-danger-500/50 animate-pulse" />
                            <div className="w-3 h-3 bg-warning-500 rounded-full shadow-lg shadow-warning-500/50 animate-pulse" style={{ animationDelay: "0.2s" }} />
                            <div className="w-3 h-3 bg-success-500 rounded-full shadow-lg shadow-success-500/50 animate-pulse" style={{ animationDelay: "0.4s" }} />
                            <span className="text-sm text-foreground ml-3 font-medium">
                              app.py
                            </span>
                          </div>
                          <div className="font-mono text-sm text-foreground leading-relaxed">
                            <div className="text-violet-500 font-semibold inline">
                              def
                            </div>{" "}
                            <span className="text-accent-500 font-semibold">
                              create_app
                            </span>
                            ():
                            <div className="ml-4 text-foreground-tertiary italic">
                              # AI-generated code
                            </div>
                            <div className="ml-4 text-success-500 font-semibold inline">
                              return
                            </div>{" "}
                            <span className="text-accent-500">app</span>
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="relative">
                            <Progress
                              value={progress}
                              className="h-3 bg-background-tertiary overflow-hidden"
                            />
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer pointer-events-none" />
                          </div>
                          <p className="text-sm text-foreground-secondary text-center font-medium">
                            Generating production-ready code...
                          </p>
                        </div>
                      </div>
                    </TabsContent>

                    <TabsContent value="test" className="mt-8">
                      <div className="space-y-6">
                        <div className="glass-modern rounded-xl p-6 border border-success-500/20 shadow-lg shadow-success-500/10 spotlight-effect">
                          <div className="flex items-center gap-3 mb-4">
                            <div className="w-3 h-3 bg-success-500 rounded-full shadow-lg shadow-success-500/50 animate-pulse" />
                            <span className="text-sm text-foreground font-medium">
                              test_app.py
                            </span>
                          </div>
                          <div className="font-mono text-sm text-foreground leading-relaxed space-y-1">
                            {["Test case 1 passed", "Test case 2 passed", "All tests passed"].map((text, i) => (
                              <div key={i} className="flex items-center gap-2 stagger-item" style={{ animationDelay: `${i * 100}ms` }}>
                                <span className="text-success-500 text-lg">✓</span>
                                <span className="text-foreground">{text}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="text-center glass-modern rounded-xl p-6 border border-success-500/20 shadow-lg shadow-success-500/10 interactive-scale">
                          <div className="text-5xl font-bold text-success-500 mb-2 count-up">
                            100%
                          </div>
                          <div className="text-sm text-foreground-secondary font-medium">
                            Test Coverage
                          </div>
                        </div>
                      </div>
                    </TabsContent>

                    <TabsContent value="deploy" className="mt-8">
                      <div className="space-y-6">
                        <div className="glass-modern rounded-xl p-6 border border-accent-500/20 shadow-lg shadow-accent-500/10 spotlight-effect">
                          <div className="flex items-center gap-3 mb-4">
                            <div className="w-3 h-3 bg-accent-500 rounded-full shadow-lg shadow-accent-500/50 animate-pulse" />
                            <span className="text-sm text-foreground font-medium">
                              deployment.yml
                            </span>
                          </div>
                          <div className="font-mono text-sm text-foreground leading-relaxed space-y-1">
                            {["Build successful", "Deployed to production", "Health check passed"].map((text, i) => (
                              <div key={i} className="flex items-center gap-2 stagger-item" style={{ animationDelay: `${i * 100}ms` }}>
                                <span className="text-accent-500 text-lg">✓</span>
                                <span className="text-foreground">{text}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="text-center glass-modern rounded-xl p-6 border border-accent-500/20 shadow-lg shadow-accent-500/10 interactive-scale">
                          <div className="text-5xl font-bold text-accent-500 mb-2">
                            Live
                          </div>
                          <div className="text-sm text-foreground-secondary font-medium">
                            Production Ready
                          </div>
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            </div>

            {/* Floating decorative elements */}
            <div className="absolute -top-6 -right-6 w-12 h-12 bg-gradient-to-r from-brand-500/40 to-brand-600/40 rounded-full blur-sm morphing-icon shadow-lg shadow-brand-500/40" />
            <div className="absolute -bottom-6 -left-6 w-8 h-8 bg-gradient-to-r from-success-500/40 to-success-600/40 rounded-full blur-sm floating-icon shadow-lg shadow-success-500/40" />
            <div className="absolute top-1/2 -right-10 w-6 h-6 bg-gradient-to-r from-accent-500/40 to-accent-600/40 rounded-full blur-sm animate-ping shadow-lg shadow-accent-500/40" />
          </div>
        </div>

        {/* Luxury Stats Section with enhanced cards */}
        <div className="mt-32 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <Card className="group glass-modern gradient-border-animated card-hover-lift spotlight-effect gpu-accelerated">
            <CardContent className="p-10 text-center">
              <div className="text-5xl font-bold bg-gradient-to-r from-brand-500 to-accent-500 bg-clip-text text-transparent mb-4 count-up">
                {t("LANDING$STATS_PROJECTS_VALUE", { defaultValue: "10K+" })}
              </div>
              <div className="text-foreground font-medium text-lg">
                {t("LANDING$STATS_PROJECTS_LABEL", {
                  defaultValue: "Projects Completed",
                })}
              </div>
            </CardContent>
          </Card>

          <Card className="group glass-modern gradient-border-animated card-hover-lift spotlight-effect gpu-accelerated">
            <CardContent className="p-10 text-center">
              <div className="text-5xl font-bold bg-gradient-to-r from-accent-emerald to-accent-sapphire bg-clip-text text-transparent mb-4 count-up">
                {t("LANDING$STATS_AVAILABLE_VALUE", { defaultValue: "24/7" })}
              </div>
              <div className="text-foreground font-medium text-lg">
                {t("LANDING$STATS_AVAILABLE_LABEL", {
                  defaultValue: "Always Available",
                })}
              </div>
            </CardContent>
          </Card>

          <Card className="group glass-modern gradient-border-animated card-hover-lift spotlight-effect gpu-accelerated">
            <CardContent className="p-10 text-center">
              <div className="text-5xl font-bold bg-gradient-to-r from-accent-sapphire to-brand-500 bg-clip-text text-transparent mb-4 count-up">
                {t("LANDING$STATS_QUALITY_VALUE", { defaultValue: "100%" })}
              </div>
              <div className="text-foreground font-medium text-lg">
                {t("LANDING$STATS_QUALITY_LABEL", {
                  defaultValue: "Code Quality",
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
