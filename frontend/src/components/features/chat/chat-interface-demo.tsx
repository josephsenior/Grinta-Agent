import React, { useState } from "react";
import {
  Sparkles,
  MessageSquare,
  Zap,
  Palette,
  Code2,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import { ModernChatInterface } from "./modern-chat-interface";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";

interface Message {
  id: string;
  content: string;
  sender: "user" | "assistant" | "system";
  timestamp: Date;
  status?: "sending" | "sent" | "delivered" | "error";
}

export function ChatInterfaceDemo() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content:
        "Hello! I'm your new AI assistant. I can help you with coding, debugging, and much more. What would you like to work on today?",
      sender: "assistant",
      timestamp: new Date(Date.now() - 300000), // 5 minutes ago
      status: "delivered",
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);

  const handleSendMessage = (message: string) => {
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: message,
      sender: "user",
      timestamp: new Date(),
      status: "sent",
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      const responses = [
        "That's a great question! Let me help you with that.",
        "I understand what you're looking for. Here's how we can approach this:",
        "Excellent! I can definitely help you implement that feature.",
        "I see what you're trying to achieve. Let me break this down for you:",
        "Perfect! This is a common pattern. Here's the best way to handle it:",
      ];

      const randomResponse =
        responses[Math.floor(Math.random() * responses.length)];

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: randomResponse,
        sender: "assistant",
        timestamp: new Date(),
        status: "delivered",
      };

      setMessages((prev) => [...prev, aiMessage]);
      setIsTyping(false);
    }, 2000);
  };

  const handleStop = () => {
    setIsTyping(false);
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  const handleExportChat = () => {
    const chatData = messages.map((msg) => ({
      timestamp: msg.timestamp.toISOString(),
      sender: msg.sender,
      content: msg.content,
    }));

    const blob = new Blob([JSON.stringify(chatData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "chat-export.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleShareChat = () => {
    if (navigator.share) {
      navigator.share({
        title: "Forge AI Chat",
        text: "Check out this conversation with Forge AI",
        url: window.location.href,
      });
    } else {
      navigator.clipboard.writeText(window.location.href);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background-surface via-background-DEFAULT to-background-elevated p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center gap-3">
            <div className="h-12 w-12 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-4xl font-bold gradient-brand-text">
              Modern Chat Interface
            </h1>
          </div>
          <p className="text-xl text-text-secondary max-w-2xl mx-auto">
            Experience the new Forge AI interface with glass morphism,
            smooth animations, and modern design patterns that harmonize
            perfectly with your Dracula theme.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-background-glass backdrop-blur-xl border border-border-glass hover:shadow-xl transition-all duration-300">
            <CardHeader className="pb-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary-500/20 to-primary-600/20 flex items-center justify-center mb-2">
                <MessageSquare className="h-5 w-5 text-primary-500" />
              </div>
              <CardTitle className="text-lg text-text-primary">
                Glass Morphism
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-text-secondary">
                Beautiful glass morphism effects with backdrop blur and subtle
                transparency
              </p>
            </CardContent>
          </Card>

          <Card className="bg-background-glass backdrop-blur-xl border border-border-glass hover:shadow-xl transition-all duration-300">
            <CardHeader className="pb-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-accent-pink/20 to-accent-purple/20 flex items-center justify-center mb-2">
                <Zap className="h-5 w-5 text-accent-pink" />
              </div>
              <CardTitle className="text-lg text-text-primary">
                Smooth Animations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-text-secondary">
                Fluid transitions and micro-interactions for a premium feel
              </p>
            </CardContent>
          </Card>

          <Card className="bg-background-glass backdrop-blur-xl border border-border-glass hover:shadow-xl transition-all duration-300">
            <CardHeader className="pb-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-accent-cyan/20 to-accent-green/20 flex items-center justify-center mb-2">
                <Palette className="h-5 w-5 text-accent-cyan" />
              </div>
              <CardTitle className="text-lg text-text-primary">
                Dracula Theme
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-text-secondary">
                Perfectly harmonized with your existing color scheme
              </p>
            </CardContent>
          </Card>

          <Card className="bg-background-glass backdrop-blur-xl border border-border-glass hover:shadow-xl transition-all duration-300">
            <CardHeader className="pb-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-success-500/20 to-success-600/20 flex items-center justify-center mb-2">
                <Code2 className="h-5 w-5 text-success-500" />
              </div>
              <CardTitle className="text-lg text-text-primary">
                Modern Components
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-text-secondary">
                Built with shadcn/ui for consistency and accessibility
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Demo Chat Interface */}
        <Card className="bg-background-glass backdrop-blur-xl border border-border-glass shadow-2xl">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-2xl text-text-primary flex items-center gap-2">
                <MessageSquare className="h-6 w-6 text-primary-500" />
                Live Demo
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">
                  <CheckCircle2 className="h-3 w-3 mr-1 text-success-500" />
                  Ready
                </Badge>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearChat}
                  className="text-xs"
                >
                  Clear Chat
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-[600px]">
              <ModernChatInterface
                messages={messages}
                isTyping={isTyping}
                onSendMessage={handleSendMessage}
                onStop={handleStop}
                onClearChat={handleClearChat}
                onExportChat={handleExportChat}
                onShareChat={handleShareChat}
                showQuickActions
                title="Forge AI"
                subtitle="Your intelligent coding assistant"
              />
            </div>
          </CardContent>
        </Card>

        {/* Call to Action */}
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-bold text-text-primary">
            Ready to upgrade your chat interface?
          </h2>
          <p className="text-text-secondary max-w-2xl mx-auto">
            The new modern components are ready to use. Simply replace your
            existing chat components with these new ones to get the enhanced
            experience.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Button className="bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-400 hover:to-primary-500 text-white shadow-lg shadow-primary-500/25">
              Get Started
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
            <Button
              variant="outline"
              className="border-border-glass text-text-primary hover:bg-primary-500/10"
            >
              View Documentation
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
