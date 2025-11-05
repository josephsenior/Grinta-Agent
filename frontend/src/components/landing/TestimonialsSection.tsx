import React from "react";
import { Star, Quote } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "#/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "#/components/ui/avatar";

export default function TestimonialsSection(): React.ReactElement {
  const { t } = useTranslation();

  const testimonials = [
    {
      name: "Sarah Chen",
      role: "Senior Developer",
      company: "TechCorp",
      avatar: null, // Use fallback initials instead of external images
      content:
        "CodePilot Pro has revolutionized our development workflow. What used to take days now takes hours. The code quality is consistently excellent.",
      rating: 5,
    },
    {
      name: "Marcus Johnson",
      role: "CTO",
      company: "StartupXYZ",
      avatar: null, // Use fallback initials instead of external images
      content:
        "The AI understands our codebase better than some of our junior developers. It's like having a senior engineer available 24/7.",
      rating: 5,
    },
    {
      name: "Elena Rodriguez",
      role: "Lead Engineer",
      company: "InnovateLab",
      avatar: null, // Use fallback initials instead of external images
      content:
        "CodePilot Pro's ability to generate production-ready code with comprehensive tests is unmatched. It's become an essential part of our stack.",
      rating: 5,
    },
  ];

  return (
    <section className="py-20 px-6 relative">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 mb-6">
            <div className="w-2 h-2 bg-brand-500 rounded-full shadow-lg shadow-brand-500/50" />
            <div className="w-8 h-px bg-gradient-to-r from-brand-500 to-accent-500" />
            <div className="w-2 h-2 bg-accent-500 rounded-full shadow-lg shadow-accent-500/50" />
          </div>

          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            <span className="text-foreground">
              What Developers Say
            </span>
          </h2>

          <p className="text-lg text-foreground-secondary max-w-3xl mx-auto leading-relaxed">
            Join thousands of developers who have transformed their workflow
            with CodePilot Pro
          </p>
        </div>

        {/* Testimonials Grid */}
        <div className="features-grid">
          {testimonials.map((testimonial, index) => (
            <Card
              key={index}
              className="card-modern group transition-all duration-300 hover:shadow-lg"
            >
              <CardContent className="p-6 space-y-4">
                {/* Quote Icon */}
                <Quote className="w-8 h-8 text-violet-500/50" />

                {/* Rating */}
                <div className="flex items-center gap-1">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star
                      key={i}
                      className="w-4 h-4 fill-warning-500 text-warning-500"
                    />
                  ))}
                </div>

                {/* Content */}
                <p className="text-sm leading-relaxed text-foreground opacity-95 font-medium">
                  "{testimonial.content}"
                </p>

                {/* Author */}
                <div className="flex items-center gap-3 pt-4">
                  <Avatar className="w-10 h-10">
                    {testimonial.avatar && (
                      <AvatarImage
                        src={testimonial.avatar}
                        alt={testimonial.name}
                        onError={(e) => {
                          // Hide the image on error, fallback will show
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    )}
                    <AvatarFallback className="bg-brand-500/10 text-violet-500 font-bold">
                      {testimonial.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="font-bold text-sm text-foreground">
                      {testimonial.name}
                    </div>
                    <div className="text-xs text-foreground opacity-70 font-medium">
                      {testimonial.role} at {testimonial.company}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="text-center mt-16">
          <div className="inline-flex items-center gap-2 px-6 py-3 rounded-full glass border border-brand-500/30 shadow-lg hover:border-brand-500/50 hover:shadow-brand-500/20 transition-all duration-300">
            <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse shadow-lg shadow-success-500/50" />
            <span className="text-foreground font-medium">
              Join 10,000+ developers building with CodePilot Pro
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
