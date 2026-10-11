/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: { colors: { shield: { bg: '#07111F', panel: '#0B1728', teal: '#12C8B0', blue: '#4388FF' } } } },
  plugins: [],
}

