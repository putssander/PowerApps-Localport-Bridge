/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'vowel-correct': '#22c55e',
        'vowel-warning': '#f59e0b',
        'vowel-error': '#ef4444',
      }
    },
  },
  plugins: [],
}
