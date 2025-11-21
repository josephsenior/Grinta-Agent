import React, { useEffect, useRef } from "react";
import { useScrollProgress } from "#/hooks/use-scroll-reveal";

/**
 * Animated mesh gradient background (bolt.new style)
 * Creates flowing, organic gradient animations
 */
export default function MeshGradient(): React.ReactElement {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scrollProgress = useScrollProgress();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return (): void => {
        // No cleanup needed
      };
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return (): void => {
        // No cleanup needed
      };
    }

    let animationId: number;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Gradient mesh points
    const meshPoints = [
      { x: 0.2, y: 0.3, vx: 0.0005, vy: 0.0003 },
      { x: 0.8, y: 0.2, vx: -0.0004, vy: 0.0005 },
      { x: 0.4, y: 0.7, vx: 0.0003, vy: -0.0004 },
      { x: 0.6, y: 0.8, vx: -0.0005, vy: -0.0003 },
    ];

    const animate = () => {
      // Update mesh points
      meshPoints.forEach((point, index) => {
        const newX = point.x + point.vx;
        const newY = point.y + point.vy;

        // Bounce off edges
        let newVx = point.vx;
        let newVy = point.vy;
        if (newX <= 0 || newX >= 1) newVx *= -1;
        if (newY <= 0 || newY >= 1) newVy *= -1;

        // Keep in bounds - update array element instead of mutating parameter
        meshPoints[index] = {
          ...point,
          x: Math.max(0, Math.min(1, newX)),
          y: Math.max(0, Math.min(1, newY)),
          vx: newVx,
          vy: newVy,
        };
      });

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Create gradient
      const gradient = ctx.createRadialGradient(
        meshPoints[0].x * canvas.width,
        meshPoints[0].y * canvas.height,
        0,
        meshPoints[0].x * canvas.width,
        meshPoints[0].y * canvas.height,
        canvas.width * 0.8,
      );

      // Violet/lavender theme colors
      gradient.addColorStop(
        0,
        `rgba(139, 92, 246, ${0.15 + scrollProgress * 0.05})`,
      );
      gradient.addColorStop(
        0.4,
        `rgba(189, 147, 249, ${0.08 + scrollProgress * 0.03})`,
      );
      gradient.addColorStop(
        0.7,
        `rgba(99, 102, 241, ${0.05 + scrollProgress * 0.02})`,
      );
      gradient.addColorStop(1, "rgba(139, 92, 246, 0)");

      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Add secondary gradient
      const gradient2 = ctx.createRadialGradient(
        meshPoints[1].x * canvas.width,
        meshPoints[1].y * canvas.height,
        0,
        meshPoints[1].x * canvas.width,
        meshPoints[1].y * canvas.height,
        canvas.width * 0.6,
      );

      gradient2.addColorStop(0, "rgba(16, 185, 129, 0.08)");
      gradient2.addColorStop(0.5, "rgba(59, 130, 246, 0.05)");
      gradient2.addColorStop(1, "rgba(16, 185, 129, 0)");

      ctx.fillStyle = gradient2;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return (): void => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resizeCanvas);
    };
  }, [scrollProgress]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none opacity-60"
      style={{ mixBlendMode: "screen" }}
    />
  );
}
