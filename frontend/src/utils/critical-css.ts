// Critical CSS utilities for performance optimization

export interface CriticalCSSOptions {
  includeAboveFold?: boolean;
  includeKeyframes?: boolean;
  includeFonts?: boolean;
  maxWidth?: number;
  maxHeight?: number;
}

// Critical CSS for above-the-fold content
export const CRITICAL_CSS = `
/* Critical CSS for above-the-fold content */
* {
  box-sizing: border-box;
}

html {
  font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  padding: 0;
  background: var(--bg-primary);
  color: var(--text-primary);
  overflow-x: hidden;
}

#root {
  min-height: 100vh;
  width: 100%;
}

/* Critical layout styles */
.min-h-screen {
  min-height: 100vh;
}

.bg-black {
  background-color: var(--bg-primary);
}

.bg-gradient-to-br {
  background-image: linear-gradient(to bottom right, var(--tw-gradient-stops));
}

.from-grey-985 {
  --tw-gradient-from: #0a0a0a;
  --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgba(10, 10, 10, 0));
}

.via-grey-950 {
  --tw-gradient-to: rgba(5, 5, 5, 0);
  --tw-gradient-stops: var(--tw-gradient-from), #050505, var(--tw-gradient-to);
}

.to-neutral-985 {
  --tw-gradient-to: #0a0a0a;
}

/* Critical animations */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes slide-down {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.animate-slide-down {
  animation: slide-down 0.3s ease-out;
}

@keyframes slide-up {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.animate-slide-up {
  animation: slide-up 0.3s ease-out;
}

/* Critical responsive utilities */
@media (min-width: 1024px) {
  .lg\\:min-w-\\[1024px\\] {
    min-width: 1024px;
  }
}

/* Critical glass effect */
.glass {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Critical scrollbar styles */
.scrollbar-thin {
  scrollbar-width: thin;
}

.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.scrollbar-thumb-grey-700::-webkit-scrollbar-thumb {
  background-color: #374151;
  border-radius: 3px;
}

.scrollbar-track-transparent::-webkit-scrollbar-track {
  background-color: transparent;
}

/* Critical loading states */
.route-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9998; /* Lower than header z-index */
}

.route-loading::after {
  content: '';
  width: 40px;
  height: 40px;
  border: 3px solid #374151;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Critical typography */
.font-outfit {
  font-family: 'Outfit', sans-serif;
}

/* Critical spacing */
.p-3 {
  padding: 0.75rem;
}

.p-4 {
  padding: 1rem;
}

.p-6 {
  padding: 1.5rem;
}

.gap-3 {
  gap: 0.75rem;
}

.gap-4 {
  gap: 1rem;
}

.gap-5 {
  gap: 1.25rem;
}

/* Critical flexbox utilities */
.flex {
  display: flex;
}

.flex-col {
  flex-direction: column;
}

.flex-1 {
  flex: 1 1 0%;
}

.items-center {
  align-items: center;
}

.justify-center {
  justify-content: center;
}

/* Critical positioning */
.relative {
  position: relative;
}

.absolute {
  position: absolute;
}

.fixed {
  position: fixed;
}

.inset-0 {
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
}

/* Critical overflow */
.overflow-hidden {
  overflow: hidden;
}

.overflow-auto {
  overflow: auto;
}

.overflow-x-hidden {
  overflow-x: hidden;
}

/* Critical sizing */
.w-full {
  width: 100%;
}

.h-full {
  height: 100%;
}

.min-h-0 {
  min-height: 0px;
}

.min-w-0 {
  min-width: 0px;
}

/* Critical borders */
.rounded-xl {
  border-radius: 0.75rem;
}

.rounded-2xl {
  border-radius: 1rem;
}

.rounded-lg {
  border-radius: 0.5rem;
}

/* Critical z-index */
.z-10 {
  z-index: 10;
}

/* Critical opacity */
.opacity-5 {
  opacity: 0.05;
}

.opacity-50 {
  opacity: 0.5;
}

.opacity-70 {
  opacity: 0.7;
}

.opacity-100 {
  opacity: 1;
}

/* Critical pointer events */
.pointer-events-none {
  pointer-events: none;
}

/* Critical transitions */
.transition-opacity {
  transition-property: opacity;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

.duration-300 {
  transition-duration: 300ms;
}

/* Page transition animations - Fade out 150ms, Fade in 300ms (Total 450ms) */
@keyframes fade-out {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.route-fade-out {
  animation: fade-out 0.15s ease-out forwards;
}

.route-fade-in {
  animation: fade-in 0.3s ease-in forwards;
}
`;

// Function to inject critical CSS into the document head
export function injectCriticalCSS(css: string = CRITICAL_CSS): void {
  if (typeof document === "undefined") return;

  // Check if critical CSS is already injected
  const existingStyle = document.getElementById("critical-css");
  if (existingStyle) return;

  const style = document.createElement("style");
  style.id = "critical-css";
  style.textContent = css;

  // Insert at the beginning of head for highest priority
  document.head.insertBefore(style, document.head.firstChild);
}

// Function to load non-critical CSS asynchronously
export function loadNonCriticalCSS(href: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof document === "undefined") {
      resolve();
      return;
    }

    // Check if stylesheet is already loaded
    const existingLink = document.querySelector(`link[href="${href}"]`);
    if (existingLink) {
      resolve();
      return;
    }

    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.media = "print";
    link.onload = () => {
      link.media = "all";
      resolve();
    };
    link.onerror = reject;

    document.head.appendChild(link);
  });
}

// Function to preload critical resources
export function preloadCriticalResources(
  resources: Array<{ href: string; as: string; type?: string }>,
): void {
  if (typeof document === "undefined") return;

  resources.forEach(({ href, as, type }) => {
    const existingLink = document.querySelector(`link[href="${href}"]`);
    if (existingLink) return;

    const link = document.createElement("link");
    link.rel = "preload";
    link.href = href;
    link.as = as;
    if (type) link.type = type;

    document.head.appendChild(link);
  });
}

// Function to extract critical CSS from existing stylesheets
export function extractCriticalCSS(
  selectors: string[],
  options: CriticalCSSOptions = {},
): string {
  // Options are reserved for future implementation
  // Access options to prevent unused parameter warning
  // eslint-disable-next-line no-void
  void options;

  // This would typically be implemented with a tool like critical
  // For now, we return the predefined critical CSS
  return CRITICAL_CSS;
}

// NOTE: Critical CSS injection has been moved to React lifecycle (root-layout.tsx)
// to prevent DOM manipulation before React components mount.
// This prevents conflicts with component rendering and layout calculations.
//
// If you need to inject critical CSS, use the injectCriticalCSS() function
// in a React useEffect hook instead of at module load time.
