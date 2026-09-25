/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        legal: {
          50: '#f0f5fa',
          100: '#e1ecf5',
          200: '#c3daeb',
          300: '#95bedc',
          400: '#5f9ecb',
          500: '#3981b7',
          600: '#27669a',
          700: '#20517d',
          800: '#1d4467',
          900: '#1a3a55',
          950: '#0f2438',
        },
        evidence: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          700: '#1d4ed8',
        },
        synthetic: {
          50: '#faf5ff',
          100: '#f3e8ff',
          500: '#a855f7',
          700: '#7e22ce',
        },
        userdoc: {
          50: '#fff7ed',
          100: '#ffedd5',
          500: '#f97316',
          700: '#c2410c',
        }
      },
    },
  },
  plugins: [],
}
