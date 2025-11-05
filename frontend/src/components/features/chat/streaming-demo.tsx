import React from "react";
import { Code, FileText, Sparkles } from "lucide-react";
import { Button } from "#/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { StreamingChatMessage } from "./streaming-chat-message";
import { StreamingControls } from "./streaming-controls";
import { StreamingFadeIn, StreamingStagger } from "./streaming-transition";
import { useStreaming } from "#/hooks/use-streaming";

const sampleCode = `function fibonacci(n) {
  if (n <= 1) return n;
  return fibonacci(n - 1) + fibonacci(n - 2);
}

// Generate first 10 Fibonacci numbers
for (let i = 0; i < 10; i++) {
  console.log(\`F(\${i}) = \${fibonacci(i)}\`);
}`;

const sampleMessage = `I'll help you create a Fibonacci sequence generator. This function uses recursion to calculate Fibonacci numbers efficiently.

Here's the implementation with some optimizations and a demo of the first 10 numbers in the sequence.`;

export function StreamingDemo() {
  const [isStreamingEnabled, setIsStreamingEnabled] = React.useState(true);
  const [streamingSpeed, setStreamingSpeed] = React.useState(2);
  const [streamingDelay, setStreamingDelay] = React.useState(100);
  const [showDemo, setShowDemo] = React.useState(false);

  const {
    displayedText,
    isStreaming,
    isComplete,
    startStreaming,
    resetStreaming,
  } = useStreaming(sampleMessage, {
    speed: streamingSpeed,
    interval: 30,
    delay: streamingDelay,
    autoStart: false,
  });

  const handleStartDemo = () => {
    setShowDemo(true);
    resetStreaming();
    setTimeout(() => startStreaming(), 500);
  };

  const handleResetDemo = () => {
    setShowDemo(false);
    resetStreaming();
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <StreamingFadeIn delay={0} duration={600}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary-500" />
              Real-time Streaming Demo
            </CardTitle>
            <p className="text-sm text-foreground-secondary">
              Experience smooth, character-by-character streaming for a more
              engaging chat experience
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Controls */}
            <StreamingControls
              isStreamingEnabled={isStreamingEnabled}
              onToggleStreaming={setIsStreamingEnabled}
              streamingSpeed={streamingSpeed}
              onSpeedChange={setStreamingSpeed}
              streamingDelay={streamingDelay}
              onDelayChange={setStreamingDelay}
              isStreaming={isStreaming}
              onStartStreaming={startStreaming}
              onResetStreaming={resetStreaming}
            />

            {/* Demo Controls */}
            <div className="flex items-center gap-4">
              <Button
                onClick={handleStartDemo}
                disabled={!isStreamingEnabled || showDemo}
                className="flex items-center gap-2"
              >
                <Code className="w-4 h-4" />
                Start Demo
              </Button>
              <Button
                variant="outline"
                onClick={handleResetDemo}
                disabled={!showDemo}
              >
                Reset Demo
              </Button>
            </div>

            {/* Demo Messages */}
            {showDemo && (
              <StreamingStagger delay={300} staggerDelay={200}>
                {/* User Message */}
                <StreamingChatMessage
                  type="user"
                  message="Create a Fibonacci sequence generator in JavaScript"
                  isStreaming={false}
                />

                {/* Assistant Message with Streaming */}
                <StreamingChatMessage
                  type="agent"
                  message={displayedText}
                  isStreaming={isStreaming}
                  streamingSpeed={streamingSpeed}
                  streamingInterval={30}
                  onAskAboutCode={(code) => console.log("Ask about:", code)}
                  onRunCode={(code, language) =>
                    console.log("Run:", language, code)
                  }
                >
                  {/* Code Block with Streaming */}
                  {isComplete && (
                    <StreamingFadeIn delay={500} duration={400}>
                      <div className="mt-4 p-4 bg-background-tertiary/50 rounded-lg border border-border/50">
                        <div className="flex items-center gap-2 mb-3">
                          <FileText className="w-4 h-4 text-violet-500" />
                          <span className="text-sm font-medium text-blue-300">
                            fibonacci.js
                          </span>
                        </div>
                        <pre className="text-sm text-foreground font-mono overflow-x-auto">
                          <code>{sampleCode}</code>
                        </pre>
                      </div>
                    </StreamingFadeIn>
                  )}
                </StreamingChatMessage>

                {/* Completion Message */}
                {isComplete && (
                  <StreamingFadeIn delay={800} duration={400}>
                    <div className="flex items-center justify-center p-4 bg-green-900/20 border border-green-700/30 rounded-lg">
                      <div className="flex items-center gap-2 text-success-500">
                        <div className="w-2 h-2 bg-success-500 rounded-full" />
                        <span className="text-sm font-medium">
                          Demo Complete!
                        </span>
                      </div>
                    </div>
                  </StreamingFadeIn>
                )}
              </StreamingStagger>
            )}

            {/* Features List */}
            <StreamingFadeIn delay={1000} duration={500}>
              <Card className="bg-background-tertiary/30 border-border/50">
                <CardHeader>
                  <CardTitle className="text-sm">Streaming Features</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-foreground-secondary">
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                      Character-by-character text streaming
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                      Adjustable speed and delay controls
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                      Smooth transitions and animations
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                      Progress indicators for long operations
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                      Interactive code blocks with streaming
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                      Real-time typing indicators
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </StreamingFadeIn>
          </CardContent>
        </Card>
      </StreamingFadeIn>
    </div>
  );
}
