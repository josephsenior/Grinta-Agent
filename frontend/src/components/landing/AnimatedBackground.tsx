import React, { useEffect, useState, useRef } from "react";
import { useMousePosition } from "#/hooks/use-mouse-position";
import { useScrollProgress } from "#/hooks/use-scroll-reveal";
import { randomInRange, prefersReducedMotion } from "#/utils/animation-utils";
import MeshGradient from "./MeshGradient";
import WebGLParticles from "./WebGLParticles";

type Particle = {
  id: string;
  x: number;
  y: number;
  size: number;
  vx: number;
  vy: number;
  opacity: number;
  hue: number;
};

export default function AnimatedBackground(): React.ReactElement {
  const [particles, setParticles] = useState<Particle[]>([]);
  const mousePosition = useMousePosition(32); // Throttled mouse tracking
  const scrollProgress = useScrollProgress();
  const reducedMotion = prefersReducedMotion();
  const animationFrameId = useRef<number | null>(null);

  useEffect(() => {
    // Generate interactive particles
    const uid = () => Math.random().toString(36).slice(2, 11);

    const newParticles: Particle[] = Array.from({ length: 80 }).map(() => ({
      id: uid(),
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: randomInRange(2, 8),
      vx: randomInRange(-0.02, 0.02),
      vy: randomInRange(-0.02, 0.02),
      opacity: randomInRange(0.1, 0.4),
      hue: randomInRange(260, 290), // Violet range
    }));

    setParticles(newParticles);
  }, []);

  useEffect(() => {
    if (reducedMotion || particles.length === 0) return;

    // Animate particles with mouse interaction
    const animate = () => {
      setParticles((prev) =>
        prev.map((particle) => {
          let newX = particle.x + particle.vx;
          let newY = particle.y + particle.vy;

          // Bounce off edges
          if (newX <= 0 || newX >= 100) particle.vx *= -1;
          if (newY <= 0 || newY >= 100) particle.vy *= -1;

          // Magnetic pull towards mouse (subtle)
          if (mousePosition.x > 0 && mousePosition.y > 0) {
            const mouseXPercent = (mousePosition.x / window.innerWidth) * 100;
            const mouseYPercent = (mousePosition.y / window.innerHeight) * 100;

            const dx = mouseXPercent - newX;
            const dy = mouseYPercent - newY;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < 20) {
              newX += dx * 0.001;
              newY += dy * 0.001;
            }
          }

          return {
            ...particle,
            x: Math.max(0, Math.min(100, newX)),
            y: Math.max(0, Math.min(100, newY)),
          };
        }),
      );

      animationFrameId.current = requestAnimationFrame(animate);
    };

    animationFrameId.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, [mousePosition, reducedMotion, particles.length]);

  return (
    <>
      <style>{`
        @keyframes float-smooth {
          0%, 100% { 
            transform: translateY(0px) translateX(0px) scale(1);
          }
          50% { 
            transform: translateY(-20px) translateX(10px) scale(1.1);
          }
        }

        @keyframes glow-pulse {
          0%, 100% {
            opacity: 0.3;
            filter: blur(20px);
          }
          50% {
            opacity: 0.6;
            filter: blur(30px);
          }
        }

        @keyframes mesh-shift {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(-20px, -20px) scale(1.05); }
          66% { transform: translate(20px, -10px) scale(0.95); }
        }

        .particle-glow {
          will-change: transform, opacity;
          transform: translateZ(0);
        }

        .parallax-layer {
          will-change: transform;
        }
      `}</style>

      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        {/* Mesh gradient background */}
        <MeshGradient />

        {/* WebGL Particle System (1200+ particles with collision) */}
        <WebGLParticles />

        {/* Interactive particles with mouse tracking */}
        <div
          className="absolute inset-0"
          style={{ transform: "translateZ(0)" }}
        >
          {particles.map((p, index) => (
            <div
              key={p.id}
              className="particle-glow absolute rounded-full transition-all duration-1000 ease-out"
              style={{
                width: `${p.size}px`,
                height: `${p.size}px`,
                left: `${p.x}%`,
                top: `${p.y}%`,
                background: `radial-gradient(circle, hsla(${p.hue}, 70%, 60%, ${p.opacity}), hsla(${p.hue}, 70%, 60%, 0))`,
                boxShadow: `0 0 ${p.size * 3}px ${p.size}px hsla(${p.hue}, 70%, 60%, ${p.opacity * 0.3})`,
                animation: reducedMotion
                  ? "none"
                  : `float-smooth ${12 + (index % 8)}s ease-in-out infinite`,
                animationDelay: `${index * 0.1}s`,
                opacity: p.opacity - scrollProgress * 0.2,
              }}
            />
          ))}
        </div>

        {/* Layered gradient overlays with parallax */}
        <div
          className="parallax-layer absolute inset-0 bg-gradient-to-br from-brand-500/8 via-transparent to-accent-emerald/6 transition-opacity duration-700"
          style={{
            transform: `translateY(${scrollProgress * 50}px)`,
            opacity: 1 - scrollProgress * 0.3,
          }}
        />
        <div
          className="parallax-layer absolute inset-0 bg-gradient-to-tl from-accent-500/5 via-transparent to-brand-600/4"
          style={{
            transform: `translateY(${scrollProgress * 30}px)`,
            opacity: 1 - scrollProgress * 0.2,
          }}
        />

        {/* Animated orbs with glow (bolt.new style) */}
        <div
          className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-gradient-to-r from-brand-500/12 to-accent-500/8 rounded-full blur-3xl"
          style={{
            animation: reducedMotion
              ? "none"
              : "glow-pulse 8s ease-in-out infinite, mesh-shift 20s ease-in-out infinite",
            transform: `translateY(${scrollProgress * -100}px)`,
          }}
        />
        <div
          className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-gradient-to-r from-accent-emerald/10 to-accent-sapphire/6 rounded-full blur-3xl"
          style={{
            animation: reducedMotion
              ? "none"
              : "glow-pulse 10s ease-in-out infinite 2s, mesh-shift 25s ease-in-out infinite 5s",
            transform: `translateY(${scrollProgress * -80}px)`,
          }}
        />

        {/* Additional depth layer */}
        <div
          className="absolute top-1/2 left-1/2 w-[400px] h-[400px] -translate-x-1/2 -translate-y-1/2 bg-gradient-to-r from-brand-600/8 to-accent-emerald/5 rounded-full blur-2xl"
          style={{
            animation: reducedMotion
              ? "none"
              : "glow-pulse 12s ease-in-out infinite 4s, mesh-shift 30s ease-in-out infinite 10s",
            opacity: 0.6 - scrollProgress * 0.3,
          }}
        />

        {/* Radial gradient vignette */}
        <div className="absolute inset-0 bg-radial-gradient from-transparent via-transparent to-black/40" />
      </div>
    </>
  );
}
