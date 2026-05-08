import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        cinzel: ["var(--font-cinzel)", "serif"],
        ibm: ["var(--font-ibm)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      colors: {
        bg: {
          primary:   "#0d1a0d",
          secondary: "#122012",
          card:      "#1a2e1a",
          sidebar:   "#0a150a",
        },
        gold: {
          dim:     "#4a3a10",
          muted:   "#8a6520",
          DEFAULT: "#c9910a",
          bright:  "#f0b429",
          light:   "#ffd166",
        },
        parchment: {
          DEFAULT: "#f5f0e8",
          muted:   "#8a7d5a",
          dim:     "#4a4535",
        },
        danger: "#8b2020",
      },
      boxShadow: {
        gold:         "0 0 12px rgba(240,180,41,0.15)",
        "gold-sm":    "0 0 6px rgba(240,180,41,0.10)",
        "card-inset": "inset 0 1px 0 rgba(240,180,41,0.08)",
      },
      borderColor: {
        "gold-border":        "rgba(201,145,10,0.20)",
        "gold-border-hover":  "rgba(201,145,10,0.45)",
        "gold-border-active": "#f0b429",
      },
    },
  },
  plugins: [],
};
export default config;
