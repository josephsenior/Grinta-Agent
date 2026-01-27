# GSAP Integration Guide - Professional Animation Enhancement

## Why GSAP for Forge?

GSAP (GreenSock Animation Platform) is the industry standard for professional web animations. While you already have Framer Motion, GSAP excels at:

1. **Performance** - Hardware-accelerated, 60fps animations even with complex sequences
2. **ScrollTrigger** - Professional scroll-based animations (perfect for landing pages)
3. **Timeline Control** - Precise orchestration of complex animation sequences
4. **Professional Polish** - The kind of animations you see on premium SaaS products
5. **Small Bundle** - Tree-shakeable, only import what you need

## Current State vs. GSAP Enhancement

### Current Approach (CSS + Framer Motion)
- ✅ Good for simple transitions
- ✅ React-friendly with Framer Motion
- ⚠️ Limited scroll-based animations
- ⚠️ Complex sequences require more code
- ⚠️ Performance can degrade with many animations

### With GSAP
- ✅ Professional scroll-triggered animations
- ✅ Complex timelines with precise control
- ✅ Better performance for heavy animations
- ✅ Industry-standard polish
- ✅ Works alongside Framer Motion (use each where best)

---

## Installation

```bash
cd frontend
pnpm add gsap
```

**Note:** GSAP is free for most use cases. Premium plugins (ScrollTrigger, etc.) are free for most commercial use.

---

## Professional Use Cases for Forge

### 1. Landing Page Scroll Animations

**Current:** Basic fade-in with `useScrollReveal`  
**With GSAP:** Professional reveal animations with parallax, stagger, and smooth easing

```typescript
// frontend/src/hooks/use-gsap-scroll-reveal.ts
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface ScrollRevealOptions {
  from?: 'top' | 'bottom' | 'left' | 'right';
  distance?: number;
  duration?: number;
  delay?: number;
  stagger?: number;
  ease?: string;
}

export function useGSAPScrollReveal<T extends HTMLElement = HTMLDivElement>(
  options: ScrollRevealOptions = {}
) {
  const ref = useRef<T>(null);
  const {
    from = 'bottom',
    distance = 50,
    duration = 1,
    delay = 0,
    stagger = 0,
    ease = 'power3.out',
  } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const children = element.children;
    const hasChildren = children.length > 0;

    // Set initial state
    gsap.set(hasChildren ? children : element, {
      opacity: 0,
      y: from === 'bottom' ? distance : from === 'top' ? -distance : 0,
      x: from === 'left' ? -distance : from === 'right' ? distance : 0,
    });

    // Animate on scroll
    const animation = gsap.to(hasChildren ? children : element, {
      opacity: 1,
      y: 0,
      x: 0,
      duration,
      delay,
      stagger: hasChildren ? stagger : 0,
      ease,
      scrollTrigger: {
        trigger: element,
        start: 'top 80%',
        end: 'bottom 20%',
        toggleActions: 'play none none reverse',
        // Respect reduced motion
        onEnter: () => {
          if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            gsap.set(hasChildren ? children : element, { opacity: 1, y: 0, x: 0 });
            return false;
          }
        },
      },
    });

    return () => {
      animation.kill();
      ScrollTrigger.getAll().forEach(trigger => {
        if (trigger.vars.trigger === element) {
          trigger.kill();
        }
      });
    };
  }, [from, distance, duration, delay, stagger, ease]);

  return ref;
}
```

### 2. Hero Section Animations

**Enhancement:** Smooth text reveal, gradient animations, particle effects

```typescript
// frontend/src/components/landing/HeroSection.tsx
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { useGSAPScrollReveal } from '#/hooks/use-gsap-scroll-reveal';

export default function HeroSection() {
  const heroRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!heroRef.current) return;

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    // Animate title with split text effect
    if (titleRef.current) {
      const text = titleRef.current.textContent || '';
      titleRef.current.innerHTML = text
        .split(' ')
        .map(word => `<span class="inline-block">${word}</span>`)
        .join(' ');

      tl.from(titleRef.current.children, {
        opacity: 0,
        y: 30,
        duration: 0.8,
        stagger: 0.1,
      });
    }

    // Subtitle fade in
    tl.from(subtitleRef.current, {
      opacity: 0,
      y: 20,
      duration: 0.6,
    }, '-=0.4');

    // CTA buttons with stagger
    tl.from(ctaRef.current?.children || [], {
      opacity: 0,
      scale: 0.9,
      duration: 0.5,
      stagger: 0.1,
    }, '-=0.3');

    // Parallax effect on scroll
    gsap.to(heroRef.current, {
      y: -50,
      scrollTrigger: {
        trigger: heroRef.current,
        start: 'top top',
        end: 'bottom top',
        scrub: 1,
      },
    });

    return () => {
      tl.kill();
    };
  }, []);

  return (
    <section ref={heroRef} className="hero-section">
      <h1 ref={titleRef}>Build with AI</h1>
      <p ref={subtitleRef}>Professional development platform</p>
      <div ref={ctaRef}>
        <button>Get Started</button>
        <button>Learn More</button>
      </div>
    </section>
  );
}
```

### 3. Feature Cards Stagger Animation

**Enhancement:** Professional card reveal with hover effects

```typescript
// frontend/src/components/landing/FeaturesGrid.tsx
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export default function FeaturesGrid() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cards = containerRef.current?.children;
    if (!cards || cards.length === 0) return;

    // Initial state
    gsap.set(cards, {
      opacity: 0,
      y: 60,
      scale: 0.9,
    });

    // Stagger animation on scroll
    gsap.to(cards, {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 0.8,
      stagger: 0.15,
      ease: 'back.out(1.2)',
      scrollTrigger: {
        trigger: containerRef.current,
        start: 'top 75%',
        toggleActions: 'play none none reverse',
      },
    });

    // Hover effects
    Array.from(cards).forEach(card => {
      card.addEventListener('mouseenter', () => {
        gsap.to(card, {
          y: -10,
          scale: 1.02,
          duration: 0.3,
          ease: 'power2.out',
        });
      });

      card.addEventListener('mouseleave', () => {
        gsap.to(card, {
          y: 0,
          scale: 1,
          duration: 0.3,
          ease: 'power2.out',
        });
      });
    });

    return () => {
      ScrollTrigger.getAll().forEach(trigger => trigger.kill());
    };
  }, []);

  return (
    <div ref={containerRef} className="features-grid">
      {/* Feature cards */}
    </div>
  );
}
```

### 4. Header Scroll Effects

**Enhancement:** Smooth header transitions with blur and shadow

```typescript
// frontend/src/components/landing/Header.tsx
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export default function Header() {
  const headerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!headerRef.current) return;

    const header = headerRef.current;

    // Animate header on scroll
    ScrollTrigger.create({
      trigger: document.body,
      start: 'top -80',
      end: 'top -100',
      onEnter: () => {
        gsap.to(header, {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(24px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          duration: 0.3,
          ease: 'power2.out',
        });
      },
      onLeaveBack: () => {
        gsap.to(header, {
          backgroundColor: 'transparent',
          backdropFilter: 'blur(0px)',
          borderBottom: '1px solid transparent',
          duration: 0.3,
          ease: 'power2.out',
        });
      },
    });

    // Logo glow on scroll
    const logo = header.querySelector('[data-logo]');
    if (logo) {
      ScrollTrigger.create({
        trigger: document.body,
        start: 'top -100',
        onEnter: () => {
          gsap.to(logo, {
            boxShadow: '0 0 20px rgba(139, 92, 246, 0.5)',
            duration: 0.5,
          });
        },
        onLeaveBack: () => {
          gsap.to(logo, {
            boxShadow: 'none',
            duration: 0.5,
          });
        },
      });
    }

    return () => {
      ScrollTrigger.getAll().forEach(trigger => trigger.kill());
    };
  }, []);

  return (
    <header ref={headerRef} className="header">
      {/* Header content */}
    </header>
  );
}
```

### 5. Number Counter Animation

**Enhancement:** Smooth counting animation for stats

```typescript
// frontend/src/components/landing/StatsSection.tsx
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface StatProps {
  value: number;
  suffix?: string;
  duration?: number;
}

function AnimatedStat({ value, suffix = '', duration = 2 }: StatProps) {
  const numberRef = useRef<HTMLSpanElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!numberRef.current || !containerRef.current) return;

    const obj = { count: 0 };

    ScrollTrigger.create({
      trigger: containerRef.current,
      start: 'top 80%',
      onEnter: () => {
        gsap.to(obj, {
          count: value,
          duration,
          ease: 'power2.out',
          onUpdate: () => {
            if (numberRef.current) {
              numberRef.current.textContent = Math.floor(obj.count) + suffix;
            }
          },
        });
      },
    });
  }, [value, suffix, duration]);

  return (
    <div ref={containerRef}>
      <span ref={numberRef}>0{suffix}</span>
    </div>
  );
}
```

### 6. Page Transitions

**Enhancement:** Smooth page transitions (works with React Router)

```typescript
// frontend/src/components/shared/PageTransition.tsx
import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { gsap } from 'gsap';

export function PageTransition({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!contentRef.current) return;

    const content = contentRef.current;

    // Fade out
    const fadeOut = gsap.to(content, {
      opacity: 0,
      y: -20,
      duration: 0.3,
      ease: 'power2.in',
    });

    // Fade in
    fadeOut.then(() => {
      gsap.fromTo(
        content,
        { opacity: 0, y: 20 },
        {
          opacity: 1,
          y: 0,
          duration: 0.4,
          ease: 'power2.out',
        }
      );
    });
  }, [location.pathname]);

  return (
    <div ref={contentRef} className="page-content">
      {children}
    </div>
  );
}
```

### 7. Loading States

**Enhancement:** Professional loading animations

```typescript
// frontend/src/components/shared/LoadingSpinner.tsx
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

export function LoadingSpinner() {
  const spinnerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!spinnerRef.current) return;

    const spinner = spinnerRef.current;
    const dots = spinner.querySelectorAll('.dot');

    // Pulse animation
    gsap.to(dots, {
      scale: 1.2,
      opacity: 0.5,
      duration: 0.6,
      stagger: 0.2,
      repeat: -1,
      yoyo: true,
      ease: 'power2.inOut',
    });
  }, []);

  return (
    <div ref={spinnerRef} className="loading-spinner">
      <div className="dot"></div>
      <div className="dot"></div>
      <div className="dot"></div>
    </div>
  );
}
```

---

## Best Practices for Professional Animations

### 1. Respect Reduced Motion

```typescript
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (prefersReducedMotion) {
  // Skip animations or use instant transitions
  gsap.set(element, { opacity: 1, y: 0 });
} else {
  // Normal animation
  gsap.to(element, { opacity: 1, y: 0, duration: 1 });
}
```

### 2. Performance Optimization

```typescript
// Use will-change for animated elements
gsap.set(element, { willChange: 'transform, opacity' });

// Clean up after animation
animation.eventCallback('onComplete', () => {
  gsap.set(element, { willChange: 'auto' });
});
```

### 3. Clean Up ScrollTriggers

```typescript
useEffect(() => {
  // Create animations
  const trigger = ScrollTrigger.create({ /* ... */ });

  return () => {
    // Always clean up
    trigger.kill();
    // Or kill all
    ScrollTrigger.getAll().forEach(t => t.kill());
  };
}, []);
```

### 4. Use GSAP Easing

```typescript
// Professional easing curves
const easings = {
  smooth: 'power2.out',
  bouncy: 'back.out(1.2)',
  sharp: 'power3.inOut',
  elastic: 'elastic.out(1, 0.3)',
};
```

---

## Integration Strategy

### Phase 1: Landing Page (High Impact)
1. Hero section animations
2. Feature cards stagger
3. Scroll-triggered reveals
4. Header scroll effects

### Phase 2: Dashboard (Subtle Polish)
1. Card hover effects
2. Stat counter animations
3. Smooth transitions
4. Loading states

### Phase 3: Conversation Interface (Micro-interactions)
1. Message animations
2. Typing indicators
3. Smooth scrolling
4. Status updates

---

## Bundle Size Consideration

GSAP is tree-shakeable. Only import what you need:

```typescript
// ✅ Good - Only import what you need
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

// ❌ Bad - Don't import everything
import { gsap, ScrollTrigger, TextPlugin, ... } from 'gsap';
```

**Estimated bundle impact:**
- Core GSAP: ~45KB (gzipped)
- ScrollTrigger: ~15KB (gzipped)
- **Total: ~60KB** (acceptable for professional animations)

---

## When to Use GSAP vs. Framer Motion

### Use GSAP for:
- ✅ Scroll-triggered animations
- ✅ Complex timelines
- ✅ Performance-critical animations
- ✅ Landing page effects
- ✅ Number counters
- ✅ Parallax effects

### Use Framer Motion for:
- ✅ React component animations
- ✅ Layout animations
- ✅ Gesture-based interactions
- ✅ Simple transitions
- ✅ Component state animations

**They work great together!** Use each where it excels.

---

## Example: Enhanced Landing Page

```typescript
// Complete example with GSAP
import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export default function LandingPage() {
  const heroRef = useRef<HTMLElement>(null);
  const featuresRef = useRef<HTMLElement>(null);
  const pricingRef = useRef<HTMLElement>(null);

  useEffect(() => {
    // Hero animation
    if (heroRef.current) {
      gsap.from(heroRef.current.children, {
        opacity: 0,
        y: 50,
        duration: 1,
        stagger: 0.2,
        ease: 'power3.out',
      });
    }

    // Features stagger
    if (featuresRef.current) {
      gsap.from(featuresRef.current.children, {
        opacity: 0,
        y: 60,
        scale: 0.9,
        duration: 0.8,
        stagger: 0.15,
        ease: 'back.out(1.2)',
        scrollTrigger: {
          trigger: featuresRef.current,
          start: 'top 75%',
        },
      });
    }

    // Pricing cards
    if (pricingRef.current) {
      gsap.from(pricingRef.current.children, {
        opacity: 0,
        y: 40,
        duration: 0.6,
        stagger: 0.1,
        scrollTrigger: {
          trigger: pricingRef.current,
          start: 'top 80%',
        },
      });
    }

    return () => {
      ScrollTrigger.getAll().forEach(trigger => trigger.kill());
    };
  }, []);

  return (
    <>
      <section ref={heroRef}>Hero</section>
      <section ref={featuresRef}>Features</section>
      <section ref={pricingRef}>Pricing</section>
    </>
  );
}
```

---

## Conclusion

GSAP will add **professional polish** to Forge without sacrificing performance. The animations will feel premium and smooth, matching the quality of your backend architecture.

**Recommendation:** Start with landing page animations (highest impact), then gradually enhance other areas. Keep animations subtle and professional - they should enhance, not distract.

---

**Next Steps:**
1. Install GSAP: `pnpm add gsap`
2. Create `use-gsap-scroll-reveal.ts` hook
3. Enhance hero section first
4. Add feature card animations
5. Polish header scroll effects

