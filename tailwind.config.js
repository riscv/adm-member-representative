/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'berkeley-blue': '#003262',
        'california-gold': '#FDB515',
      },
    },
  },
  plugins: [],
}
