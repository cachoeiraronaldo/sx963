/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./**/*.{html,js}"], // Ajuste se necessário, para apontar para as pastas corretas
  theme: {
    extend: {
      backgroundImage: {
        "home": "url('/static/assets/sx694.png')" // Caminho ajustado
      },
      fontFamily: {
        'sans': ['Poppins', 'sans-serif'], // Fonte personalizada
      },
    },
  },
  plugins: [],
}
