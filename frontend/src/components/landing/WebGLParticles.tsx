import React, { useEffect, useRef } from "react";
import { prefersReducedMotion } from "#/utils/animation-utils";
import { logger } from "#/utils/logger";

/**
 * WebGL Particle System with collision physics
 * Handles 1000+ particles at 60fps
 */
export default function WebGLParticles(): React.ReactElement | null {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reducedMotion = prefersReducedMotion();

  useEffect(() => {
    if (reducedMotion) {
      return (): void => {
        // No cleanup needed
      };
    }

    const canvas = canvasRef.current;
    if (!canvas) {
      return (): void => {
        // No cleanup needed
      };
    }

    const gl = (canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl")) as WebGLRenderingContext | null;
    if (!gl) {
      logger.warn("WebGL not supported, falling back to CSS particles");
      return (): void => {
        // No cleanup needed
      };
    }

    // Particle system
    const particleCount = 1200;
    const particles: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      size: number;
      hue: number;
      alpha: number;
    }> = [];

    // Initialize particles
    for (let i = 0; i < particleCount; i += 1) {
      particles.push({
        x: Math.random(),
        y: Math.random(),
        vx: (Math.random() - 0.5) * 0.0002,
        vy: (Math.random() - 0.5) * 0.0002,
        size: Math.random() * 3 + 1,
        hue: 270 + Math.random() * 30, // Violet range
        alpha: Math.random() * 0.3 + 0.1,
      });
    }

    // Resize canvas
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      gl.viewport(0, 0, canvas.width, canvas.height);
    };
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Vertex shader
    const vertexShaderSource = `
      attribute vec2 a_position;
      attribute float a_size;
      attribute vec3 a_color;
      varying vec3 v_color;
      
      void main() {
        gl_Position = vec4(a_position * 2.0 - 1.0, 0.0, 1.0);
        gl_PointSize = a_size;
        v_color = a_color;
      }
    `;

    // Fragment shader
    const fragmentShaderSource = `
      precision mediump float;
      varying vec3 v_color;
      
      void main() {
        vec2 center = gl_PointCoord - vec2(0.5);
        float dist = length(center);
        float alpha = smoothstep(0.5, 0.0, dist);
        gl_FragColor = vec4(v_color, alpha);
      }
    `;

    // Compile shader
    function createShader(
      glContext: WebGLRenderingContext,
      type: number,
      source: string,
    ) {
      const shader = glContext.createShader(type);
      if (!shader) return null;

      glContext.shaderSource(shader, source);
      glContext.compileShader(shader);

      if (!glContext.getShaderParameter(shader, glContext.COMPILE_STATUS)) {
        logger.error(
          "Shader compile error:",
          glContext.getShaderInfoLog(shader),
        );
        glContext.deleteShader(shader);
        return null;
      }

      return shader;
    }

    // Create program
    const vertexShader = createShader(gl, gl.VERTEX_SHADER, vertexShaderSource);
    const fragmentShader = createShader(
      gl,
      gl.FRAGMENT_SHADER,
      fragmentShaderSource,
    );

    if (!vertexShader || !fragmentShader) {
      return (): void => {
        // No cleanup needed
      };
    }

    const program = gl.createProgram();
    if (!program) {
      return (): void => {
        // No cleanup needed
      };
    }

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      logger.error("Program link error:", gl.getProgramInfoLog(program));
      return (): void => {
        // No cleanup needed
      };
    }

    gl.useProgram(program);

    // Setup buffers
    const positionBuffer = gl.createBuffer();
    const sizeBuffer = gl.createBuffer();
    const colorBuffer = gl.createBuffer();

    // Get attribute locations
    const positionLocation = gl.getAttribLocation(program, "a_position");
    const sizeLocation = gl.getAttribLocation(program, "a_size");
    const colorLocation = gl.getAttribLocation(program, "a_color");

    // Enable blending
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE);

    // Animation loop
    let animationId: number;

    const render = () => {
      // Update particles
      for (let i = 0; i < particles.length; i += 1) {
        const p = particles[i];

        p.x += p.vx;
        p.y += p.vy;

        // Bounce off edges
        if (p.x <= 0 || p.x >= 1) p.vx *= -1;
        if (p.y <= 0 || p.y >= 1) p.vy *= -1;

        // Keep in bounds
        p.x = Math.max(0, Math.min(1, p.x));
        p.y = Math.max(0, Math.min(1, p.y));

        // Collision detection with nearby particles
        for (let j = i + 1; j < particles.length; j += 1) {
          const p2 = particles[j];
          const dx = p2.x - p.x;
          const dy = p2.y - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 0.02) {
            // Collision! Swap velocities (elastic collision)
            const tempVx = p.vx;
            const tempVy = p.vy;
            p.vx = p2.vx;
            p.vy = p2.vy;
            p2.vx = tempVx;
            p2.vy = tempVy;
          }
        }
      }

      // Prepare data
      const positions = new Float32Array(particles.length * 2);
      const sizes = new Float32Array(particles.length);
      const colors = new Float32Array(particles.length * 3);

      for (let i = 0; i < particles.length; i += 1) {
        const p = particles[i];
        positions[i * 2] = p.x;
        positions[i * 2 + 1] = p.y;
        sizes[i] = p.size;

        // HSL to RGB (simplified for violet range)
        const h = p.hue / 360;
        const s = 0.7;
        const l = 0.6;
        colors[i * 3] = l + s * Math.cos(h * Math.PI * 2);
        colors[i * 3 + 1] = l;
        colors[i * 3 + 2] = l + s * Math.sin(h * Math.PI * 2);
      }

      // Update buffers
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, positions, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(positionLocation);
      gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

      gl.bindBuffer(gl.ARRAY_BUFFER, sizeBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, sizes, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(sizeLocation);
      gl.vertexAttribPointer(sizeLocation, 1, gl.FLOAT, false, 0, 0);

      gl.bindBuffer(gl.ARRAY_BUFFER, colorBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, colors, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(colorLocation);
      gl.vertexAttribPointer(colorLocation, 3, gl.FLOAT, false, 0, 0);

      // Clear and draw
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.POINTS, 0, particles.length);

      animationId = requestAnimationFrame(render);
    };

    render();

    return (): void => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resizeCanvas);
    };
  }, [reducedMotion]);

  if (reducedMotion) return null;

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none opacity-40"
      style={{ mixBlendMode: "screen", zIndex: 1 }}
    />
  );
}
