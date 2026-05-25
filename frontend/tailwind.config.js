/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        hive: {
          bg: "#0a0e17",
          panel: "#111827",
          card: "#1a2234",
          border: "#2d3a52",
          gold: "#c9a227",
          accent: "#3b82f6",
          muted: "#94a3b8",
          success: "#22c55e",
          warn: "#f59e0b",
          danger: "#ef4444",
        },
      },
      fontFamily: {
        display: ["Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
