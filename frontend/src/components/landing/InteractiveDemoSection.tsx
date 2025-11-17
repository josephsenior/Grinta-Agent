import React, { useState, useEffect } from "react";
import { Code, Terminal, Eye, Play, Sparkles } from "lucide-react";
import { Card, CardContent } from "#/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "#/components/ui/tabs";
import { Badge } from "#/components/ui/badge";
import { useScrollReveal } from "#/hooks/use-scroll-reveal";
import { interactiveDemo } from "#/content/landing";

/**
 * Interactive demo section with bolt.new-style split-screen code editor
 */
export default function InteractiveDemoSection(): React.ReactElement {
  const [activeTab, setActiveTab] = useState("code");
  const [typedCode, setTypedCode] = useState("");
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const { ref, isVisible } = useScrollReveal({
    threshold: 0.2,
    triggerOnce: true,
  });

  const fullCode = interactiveDemo.codeSample;

  // Typing animation for code
  useEffect(() => {
    if (!isVisible) return;

    let index = 0;
    const typingSpeed = 30;

    const typeCode = () => {
      if (index < fullCode.length) {
        setTypedCode(fullCode.slice(0, index + 1));
        index++;
        setTimeout(typeCode, typingSpeed);
      }
    };

    const timeout = setTimeout(typeCode, 500);
    return () => clearTimeout(timeout);
  }, [isVisible]);

  // Simulate terminal output
  useEffect(() => {
    if (!isVisible || activeTab !== "terminal") return;

    const outputs = interactiveDemo.terminalLines;

    let index = 0;
    const addOutput = () => {
      if (index < outputs.length) {
        setTerminalOutput((prev) => [...prev, outputs[index]]);
        index++;
        setTimeout(addOutput, 600);
      }
    };

    setTerminalOutput([]);
    const timeout = setTimeout(addOutput, 300);
    return () => clearTimeout(timeout);
  }, [isVisible, activeTab]);

  return (
    <section ref={ref} className="py-20 px-6 relative">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div
          className={`text-center mb-16 max-w-3xl mx-auto ${isVisible ? "stagger-item delay-0" : "opacity-0"}`}
        >
          <Badge
            variant="secondary"
            className="glass-modern border-brand-500/30 text-violet-500 px-5 py-2.5 text-sm font-medium shadow-lg interactive-scale mb-8"
          >
            <Sparkles className="w-4 h-4 mr-2 floating-icon" />
            Live Demo
          </Badge>

          <h2 className="text-4xl md:text-5xl font-semibold mb-6 text-white">
            {interactiveDemo.title}
          </h2>

          <p className="text-lg text-foreground-secondary leading-relaxed">
            {interactiveDemo.subtitle}
          </p>
        </div>

        {/* Interactive Demo Card */}
        <Card
          className={`glass-modern gradient-border-animated shadow-2xl overflow-hidden gpu-accelerated ${isVisible ? "bento-card delay-200" : "opacity-0"}`}
        >
          <CardContent className="p-0">
            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="w-full"
            >
              {/* Tab Navigation */}
              <div className="border-b border-border/50 px-6 pt-6">
                <TabsList className="glass-modern p-1 gap-1">
                  <TabsTrigger
                    value="code"
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg data-[state=active]:bg-brand-500/20 data-[state=active]:text-violet-500 data-[state=active]:shadow-lg data-[state=active]:shadow-brand-500/20 transition-all duration-300"
                  >
                    <Code className="w-4 h-4" />
                    Code
                  </TabsTrigger>
                  <TabsTrigger
                    value="terminal"
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg data-[state=active]:bg-success-500/20 data-[state=active]:text-success-500 data-[state=active]:shadow-lg data-[state=active]:shadow-success-500/20 transition-all duration-300"
                  >
                    <Terminal className="w-4 h-4" />
                    Terminal
                  </TabsTrigger>
                  <TabsTrigger
                    value="preview"
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg data-[state=active]:bg-accent-500/20 data-[state=active]:text-accent-500 data-[state=active]:shadow-lg data-[state=active]:shadow-accent-500/20 transition-all duration-300"
                  >
                    <Eye className="w-4 h-4" />
                    Preview
                  </TabsTrigger>
                </TabsList>
              </div>

              {/* Code Tab */}
              <TabsContent value="code" className="p-6 m-0">
                <div className="glass-modern rounded-xl p-6 border border-brand-500/20 min-h-[400px]">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="flex gap-2">
                      <div className="w-3 h-3 bg-danger-500 rounded-full shadow-lg shadow-danger-500/50 animate-pulse" />
                      <div
                        className="w-3 h-3 bg-warning-500 rounded-full shadow-lg shadow-warning-500/50 animate-pulse"
                        style={{ animationDelay: "0.2s" }}
                      />
                      <div
                        className="w-3 h-3 bg-success-500 rounded-full shadow-lg shadow-success-500/50 animate-pulse"
                        style={{ animationDelay: "0.4s" }}
                      />
                    </div>
                    <span className="text-sm text-foreground-secondary font-medium ml-3">
                      App.tsx
                    </span>
                    <Badge className="ml-auto bg-brand-500/10 text-violet-500 border-brand-500/30 text-xs">
                      AI Generated
                    </Badge>
                  </div>

                  <pre className="font-mono text-sm text-foreground leading-relaxed overflow-auto">
                    <code className="block whitespace-pre">{typedCode}</code>
                    {typedCode.length < fullCode.length && (
                      <span className="inline-block w-2 h-4 bg-brand-500 typing-cursor ml-1" />
                    )}
                  </pre>
                </div>
              </TabsContent>

              {/* Terminal Tab */}
              <TabsContent value="terminal" className="p-6 m-0">
                <div className="glass-modern rounded-xl p-6 border border-success-500/20 min-h-[400px] bg-black/40">
                  <div className="flex items-center gap-3 mb-6">
                    <Terminal className="w-5 h-5 text-success-500" />
                    <span className="text-sm text-foreground-secondary font-medium">
                      Terminal Output
                    </span>
                  </div>

                  <div className="font-mono text-sm space-y-2">
                    {terminalOutput.map((line, i) => (
                      <div
                        key={i}
                        className="stagger-item"
                        style={{ animationDelay: `${i * 100}ms` }}
                      >
                        {line.startsWith("$") ? (
                          <span className="text-violet-500">{line}</span>
                        ) : line.includes("✓") ? (
                          <span className="text-success-500">{line}</span>
                        ) : (
                          <span className="text-foreground-secondary">
                            {line}
                          </span>
                        )}
                      </div>
                    ))}
                    {terminalOutput.length > 0 && terminalOutput.length < 4 && (
                      <span className="inline-block w-2 h-4 bg-success-500 typing-cursor" />
                    )}
                  </div>
                </div>
              </TabsContent>

              {/* Preview Tab */}
              <TabsContent value="preview" className="p-6 m-0">
                <div className="glass-modern rounded-xl p-8 border border-accent-500/20 min-h-[400px] flex items-center justify-center">
                  <div className="text-center space-y-6">
                    <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-brand-500/20 to-accent-500/20 rounded-2xl backdrop-blur-sm border border-brand-500/30 shadow-lg shadow-brand-500/20">
                      <Play className="w-10 h-10 text-violet-500" />
                    </div>
                    <button className="px-8 py-4 rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 text-white font-semibold shadow-lg shadow-brand-500/30 hover:shadow-xl hover:shadow-brand-500/40 hover:scale-105 transition-all duration-300 button-shine interactive-scale overflow-hidden">
                      Hello World
                    </button>
                    <p className="text-sm text-foreground-secondary">
                      Live preview of generated component
                    </p>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
