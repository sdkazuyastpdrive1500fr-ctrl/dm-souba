/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{astro,html,js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070b16",
          900: "#0c1426",
          800: "#15213d",
          700: "#1e2f52",
        },
        ember: {
          400: "#ff6b4a",
          500: "#e83b2a",
          600: "#c42218",
        },
        mist: {
          100: "#e8eef8",
          300: "#a8b8d4",
          500: "#6b7f9e",
        },
      },
      fontFamily: {
        display: ['"Outfit"', "system-ui", "sans-serif"],
        body: ['"Noto Sans JP"', "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "hero-glow":
          "radial-gradient(ellipse 80% 60% at 70% 20%, rgba(232,59,42,0.22), transparent 55%), radial-gradient(ellipse 70% 50% at 15% 80%, rgba(40,90,180,0.28), transparent 50%), linear-gradient(165deg, #070b16 0%, #0c1426 45%, #15213d 100%)",
      },
    },
  },
  plugins: [],
};
