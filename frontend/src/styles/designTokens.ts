// Design tokens exported for runtime usage in components
export const spacing = {
  xs: "0.25rem",
  sm: "0.5rem",
  md: "1rem",
  lg: "1.5rem",
  xl: "2rem",
  "2xl": "3rem",
  "3xl": "4rem",
  "4xl": "6rem",
};

export const typography = {
  xxs: { size: "0.75rem", lineHeight: 1.5 },
  xs: { size: "0.875rem", lineHeight: 1.5 },
  s: { size: "1rem", lineHeight: 1.5 },
  m: { size: "1.125rem", lineHeight: 1.5 },
  l: { size: "1.5rem", lineHeight: 1.2 },
  xl: { size: "2rem", lineHeight: 1.2 },
  xxl: { size: "2.25rem", lineHeight: 1.2 },
  xxxl: { size: "3rem", lineHeight: 1.2 },
};

export const colors = {
  brand: {
    violet: "#8b5cf6",
    violetDark: "#7c3aed",
    violetLight: "#a78bfa",
  },
  text: {
    primary: "#FFFFFF",
    secondary: "#F1F5F9",
    tertiary: "#94A3B8",
    muted: "#6a6f7f",
  },
  border: {
    primary: "#1a1a1a",
    glass: "rgba(139, 92, 246, 0.1)",
  },
  semantic: {
    success: "#10B981",
    warning: "#F59E0B",
    danger: "#EF4444",
    info: "#3B82F6",
  },
};

export const gradients = {
  luxury: "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 50%, #6d28d9 100%)",
  brandText: "linear-gradient(90deg,#a78bfa,#8b5cf6,#7c3aed)",
};

export const borderRadius = {
  sm: "0.25rem",
  md: "0.5rem",
  lg: "0.75rem",
  xl: "1rem",
  full: "9999px",
};

export const shadows = {
  luxury: "0 4px 20px rgba(0, 0, 0, 0.15)",
  luxuryLg: "0 8px 40px rgba(0, 0, 0, 0.2)",
  glow: "0 0 20px rgba(245, 158, 11, 0.3)",
};

export default {
  spacing,
  typography,
  colors,
  gradients,
  borderRadius,
  shadows,
};
