const defaultTheme = require('tailwindcss/defaultTheme')
const windmill = require('@windmill/react-ui/config')

module.exports = windmill({
  purge: ['src/**/*.js'],
  theme: {
    extend: {
      fontFamily: {
        // Font di sistema: niente dipendenza da Google Fonts (self-hosted, Tailscale)
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          ...defaultTheme.fontFamily.sans.slice(-1),
        ],
      },
      maxWidth: {
        // Contenitore principale: ampio su desktop, cap su ultrawide
        '9xl': '120rem',
      },
      boxShadow: {
        bottom: '0 5px 6px -7px rgba(0, 0, 0, 0.6), 0 2px 4px -5px rgba(0, 0, 0, 0.06)',
      },
    },
  },
})
