/** @type {import('tailwindcss').Config} */
import daisyui from "daisyui";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        quant: {
          bg: "#07111f",
          fg: "#eef6ff",
          muted: "#91a3b8",
          accent: "#55e48b",
          "accent-2": "#5aa7ff",
          danger: "#ff6b6b",
          warn: "#ffd166",
          surface: "rgba(255,255,255,.075)",
          panel: "rgba(5,10,18,.82)",
          bar: "rgba(14,20,31,.86)",
        },
      },
      borderRadius: {
        "quant-sm": "12px",
        "quant-md": "16px",
        "quant-lg": "22px",
        "quant-xl": "28px",
      },
      fontFamily: {
        quant: ["-apple-system", "BlinkMacSystemFont", '"PingFang SC"', '"Microsoft YaHei"', "sans-serif"],
        "quant-mono": ["ui-monospace", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [daisyui],
  daisyui: {
    themes: [
      {
        "quant-dark": {
          "primary": "#55e48b",
          "secondary": "#5aa7ff",
          "accent": "#ff6b6b",
          "neutral": "#3d4451",
          "base-100": "#07111f",
          "info": "#3abff8",
          "success": "#55e48b",
          "warning": "#ffd166",
          "error": "#ff6b6b",
        },
      },
      {
        "quant-light": {
          "primary": "#0e7a43",
          "secondary": "#2563eb",
          "accent": "#dc2626",
          "neutral": "#3d4451",
          "base-100": "#f6f8fb",
          "info": "#3abff8",
          "success": "#16a34a",
          "warning": "#d97706",
          "error": "#dc2626",
        },
      },
    ],
  },
};