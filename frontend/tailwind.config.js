/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#1a1a1a', // Dark background Bloomberg style
        foreground: '#e0e0e0',
        accent: '#f5a623',     // Amber
        bull: '#00d4aa',       // Positive green
        bear: '#ff4757',       // Negative red
        panel: '#242424',
        border: '#333333',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'monospace'],
      },
      keyframes: {
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' }, // Translates 50% because we duplicate the content to make it seamless
        }
      },
      animation: {
        marquee: 'marquee 90s linear infinite',
      }
    },
  },
  plugins: [],
}
