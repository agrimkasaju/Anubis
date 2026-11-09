/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        void: "#06090F",
        panel: "rgba(12, 18, 30, 0.72)",
        neon: {
          cyan: "#00F0FF",
          emerald: "#10B981",
          rose: "#F43F5E",
          amber: "#F59E0B",
          purple: "#A855F7",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
      boxShadow: {
        "nexus-cyan": "0 0 24px -4px rgba(0, 240, 255, 0.12), inset 0 1px 0 0 rgba(0, 240, 255, 0.2)",
        "nexus-bull": "0 0 24px -4px rgba(16, 185, 129, 0.12), inset 0 1px 0 0 rgba(16, 185, 129, 0.25)",
        "nexus-bear": "0 0 24px -4px rgba(244, 63, 94, 0.12), inset 0 1px 0 0 rgba(244, 63, 94, 0.25)",
      },
    },
  },
  plugins: [],
};
