import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0f",
        surface: "#12121a",
        border: "#1e1e2e",
        accent: "#6c63ff",
        "accent-hover": "#5a52e0",
        "text-primary": "#e2e8f0",
        "text-muted": "#64748b",
        "score-high": "#22c55e",
        "score-mid": "#f59e0b",
        "score-low": "#ef4444",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
