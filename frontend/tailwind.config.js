/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gov: {
          navy: '#0A2540',
          blue: '#1E3A8A',
          light: '#F8FAFC',
          border: '#E2E8F0',
          dark: '#0F172A',
          accent: '#B45309', // Restrained gold/amber
        },
      },
    },
  },
  plugins: [],
}
