import React from "react";
import { ArrowRight, Sparkles, Brain, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useUserProviders } from "#/hooks/use-user-providers";
import DarkVeil from "#/components/ui/dark-veil";

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
            localStorage.setItem("RECENT_CONVERSATION_ID", data.conversation_id);
          } catch (err) {
            // ignore
          }
          navigate(`/conversations/${data.conversation_id}`);
        },
      },
    );
  };

  return (
    <div
      data-testid="home-screen"
      className="min-h-screen w-full relative bg-black"
    >
      {/* Animated background with violet theme */}
      <div className="fixed inset-0 w-full h-full z-0">
        <DarkVeil 
          hueShift={260}
          speed={0.3}
          noiseIntensity={0.02}
          warpAmount={0.4}
          resolutionScale={1}
        />
      </div>
      
      {/* Overlay gradient for better text readability */}
      <div className="fixed inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60 z-[1]" />
      
      {/* Content */}
      <main className="relative z-[2] flex flex-col items-center justify-center min-h-screen px-6 py-20">
        {/* Hero */}
        <div className="max-w-4xl mx-auto text-center space-y-8">
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <img
              src="/forge-logo.png"
              alt="Forge"
              className="h-16 w-auto opacity-90"
              draggable={false}
            />
          </div>

          {/* Beta Badge */}
          <div className="flex justify-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-violet-500/10 border border-violet-500/20">
              <Sparkles className="w-4 h-4 text-violet-400" />
              <span className="text-sm font-light text-violet-300">Private Beta</span>
            </div>
          </div>

          {/* Main Headline */}
          <h1 className="text-6xl md:text-7xl font-light tracking-tight">
            <span className="text-white">Build software with</span>
            <br />
            <span className="bg-gradient-to-r from-violet-400 to-violet-600 bg-clip-text text-transparent font-normal">
              AI agents
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg md:text-xl text-gray-400 font-light max-w-2xl mx-auto leading-relaxed">
            Production-grade AI coding assistant with persistent memory, 
            multi-agent orchestration, and self-improving capabilities.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-8">
            <button
              onClick={onStart}
              disabled={isPending}
              className="group relative px-8 py-4 bg-violet-600 hover:bg-violet-500 text-white rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-violet-500/20 hover:shadow-violet-500/40"
            >
              {isPending ? "Starting..." : "Start Building"}
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            
            <a
              href="https://github.com/All-Hands-AI/Forge"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-4 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-lg font-medium transition-all duration-200 border border-white/10 hover:border-violet-500/30"
            >
              View on GitHub
            </a>
          </div>

          {/* Key Features - Minimal */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-16 max-w-3xl mx-auto">
            {/* Feature 1 */}
            <div className="group p-6 rounded-xl bg-violet-500/5 border border-violet-500/10 hover:border-violet-500/20 transition-all duration-200">
              <Brain className="w-8 h-8 text-violet-400 mb-4" />
              <h3 className="text-white font-medium mb-2">Advanced Memory</h3>
              <p className="text-sm text-gray-400 font-light">
                92% accuracy semantic search with persistent context across sessions
              </p>
            </div>

            {/* Feature 2 */}
            <div className="group p-6 rounded-xl bg-violet-500/5 border border-violet-500/10 hover:border-violet-500/20 transition-all duration-200">
              <Zap className="w-8 h-8 text-violet-400 mb-4" />
              <h3 className="text-white font-medium mb-2">Multi-Agent</h3>
              <p className="text-sm text-gray-400 font-light">
                PM → Architect → Engineer → QA workflow with causal reasoning
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group p-6 rounded-xl bg-violet-500/5 border border-violet-500/10 hover:border-violet-500/20 transition-all duration-200">
              <Sparkles className="w-8 h-8 text-violet-400 mb-4" />
              <h3 className="text-white font-medium mb-2">Self-Improving</h3>
              <p className="text-sm text-gray-400 font-light">
                ACE framework learns from patterns and improves over time
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;

export default HomeScreen;
