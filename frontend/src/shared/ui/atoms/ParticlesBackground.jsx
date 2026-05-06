import React, { useEffect, useRef, useCallback } from "react";
import { Box } from "@chakra-ui/react";
import { colors } from "@theme/tokens";

/**
 * ChatParticlesBackground - Optimized animated particles for chat background
 * Creates a smooth, performant background effect that doesn't interfere with typing
 *
 * Features:
 * - Canvas-based rendering for smooth performance
 * - Particles distributed across entire chat window
 * - Optimized to not re-initialize on re-renders
 * - Higher opacity for better visibility
 */
function ChatParticlesBackground({
  particleCount = 150,
  connectionDistance = 200,
  particleColor = colors.brand.primary,
  lineColor = "rgba(47, 116, 255, 0.25)",
  speed = 0.4,
  ...props
}) {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const particlesRef = useRef([]);
  const isInitializedRef = useRef(false);

  const initializeParticles = useCallback((width, height) => {
    if (isInitializedRef.current) return; // Don't re-initialize

    particlesRef.current = Array.from({ length: particleCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * speed,
      vy: (Math.random() - 0.5) * speed,
      radius: Math.random() * 2 + 1,
      opacity: Math.random() * 0.6 + 0.4, // Higher opacity
      pulsePhase: Math.random() * Math.PI * 2,
    }));

    isInitializedRef.current = true;
  }, [particleCount, speed]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let width = canvas.offsetWidth;
    let height = canvas.offsetHeight;

    const handleResize = () => {
      width = canvas.offsetWidth;
      height = canvas.offsetHeight;
      canvas.width = width * window.devicePixelRatio;
      canvas.height = height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

      // Re-initialize particles on resize
      isInitializedRef.current = false;
      initializeParticles(width, height);
    };

    handleResize();
    initializeParticles(width, height);

    const animate = () => {
      ctx.clearRect(0, 0, width, height);

      const particles = particlesRef.current;

      // Update and draw particles
      particles.forEach((p, i) => {
        // Update position
        p.x += p.vx;
        p.y += p.vy;

        // Bounce off edges
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        // Pulse animation
        p.pulsePhase += 0.02;
        const pulse = Math.sin(p.pulsePhase) * 0.3 + 0.7;

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * pulse, 0, Math.PI * 2);
        ctx.fillStyle = particleColor
          .replace(")", `, ${p.opacity * pulse})`)
          .replace("rgb", "rgba");
        ctx.fill();

        // Draw glow
        const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius * 3);
        gradient.addColorStop(
          0,
          particleColor.replace(")", `, ${p.opacity * 0.4 * pulse})`).replace("rgb", "rgba"),
        );
        gradient.addColorStop(1, "transparent");
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * 3, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Draw connections (full connectivity for dense network)
        for (let j = i + 1; j < Math.min(i + 12, particles.length); j++) { // Check more particles for connections
          const p2 = particles[j];
          const dx = p2.x - p.x;
          const dy = p2.y - p.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < connectionDistance) {
            const opacity = 1 - distance / connectionDistance;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = lineColor.replace(/[\d.]+\)$/, `${opacity * 0.6})`);
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [initializeParticles, connectionDistance, particleColor, lineColor]);

  return (
    <Box
      as="canvas"
      ref={canvasRef}
      position="absolute"
      top={0}
      left={0}
      w="100%"
      h="100%"
      pointerEvents="none"
      opacity={0.9} // Even higher opacity for better visibility
      zIndex={0}
      {...props}
    />
  );
}

export default ChatParticlesBackground;
