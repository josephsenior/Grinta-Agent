import React from "react";
import { Star, Quote } from "lucide-react";
import { Card, CardContent } from "#/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "#/components/ui/avatar";
import { testimonials as testimonialsData } from "#/content/landing";

export default function TestimonialsSection(): React.ReactElement {
  const testimonials = testimonialsData.map((testimonial) => ({
    ...testimonial,
    avatar: null,
    rating: 5,
  }));

  return (
    <section className="relative py-24 px-6">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.15),_transparent_55%)]" />
      <div className="relative max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 mb-6">
            <div className="w-2 h-2 bg-brand-500 rounded-full shadow-lg shadow-brand-500/50" />
            <div className="w-8 h-px bg-gradient-to-r from-brand-500 to-accent-500" />
            <div className="w-2 h-2 bg-accent-500 rounded-full shadow-lg shadow-accent-500/50" />
          </div>

          <h2 className="text-4xl md:text-5xl font-bold mb-6 text-white">
            What our beta partners report from production workloads.
          </h2>

          <p className="text-lg text-foreground-secondary max-w-3xl mx-auto leading-relaxed">
            Every quote comes from a current pilot sending Forge into their
            regulated repos.
          </p>
        </div>

        {/* Testimonials Grid */}
        <div className="grid gap-6 md:grid-cols-3">
          {testimonials.map((testimonial, index) => (
            <Card
              key={index}
              className="card-modern group transition-all duration-300 hover:shadow-2xl border-white/10 bg-background-primary/80"
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
                <p className="text-sm leading-relaxed text-foreground-secondary font-medium">
                  “{testimonial.quote}”
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
                          e.currentTarget.style.display = "none";
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
                    <div className="font-bold text-sm text-white">
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
              Join 140+ teams already piloting Forge
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
