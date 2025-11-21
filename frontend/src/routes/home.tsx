import React from "react";
import { redirect } from "react-router-dom";
import Header from "#/components/landing/Header";
import HeroSection from "#/components/landing/HeroSection";
import FeaturesGrid from "#/components/landing/FeaturesGrid";
import HowItWorks from "#/components/landing/HowItWorks";
import Testimonials from "#/components/landing/Testimonials";
import Pricing from "#/components/landing/Pricing";
import FinalCTA from "#/components/landing/FinalCTA";
import Footer from "#/components/landing/Footer";
import Forge from "#/api/forge";
import { queryClient } from "#/query-client-config";
import { SEO } from "#/components/shared/SEO";

// Redirect authenticated users to dashboard
export const clientLoader = async () => {
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

/**
 * Landing Page
 * Pure Tailwind implementation - no custom CSS conflicts
 */
function HomeScreen() {
  return (
    <>
      <SEO
        title="Forge - AI Development Platform"
        description="Build software faster with Forge, the AI-powered development platform. Advanced agents, real-time collaboration, and intelligent code generation."
        keywords="AI development, code generation, software development, AI agents, development platform, coding assistant"
        ogTitle="Forge - AI Development Platform"
        ogDescription="Forge your software with AI - Code less, build more. Advanced AI agents, real-time collaboration, and intelligent code generation."
        ogType="website"
        twitterCard="summary_large_image"
      />
      <div
        data-testid="home-screen"
        className="relative min-h-screen w-full overflow-x-hidden"
        style={{
          backgroundColor: "var(--bg-primary)",
          color: "var(--text-primary)",
        }}
      >
        <Header />
        <main className="relative w-full flex-1 flex flex-col pt-20 md:pt-24">
          <HeroSection />
          <FeaturesGrid />
          <HowItWorks />
          <Testimonials />
          <Pricing />
          <FinalCTA />
        </main>
        <Footer />
      </div>
    </>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;

export default HomeScreen;
