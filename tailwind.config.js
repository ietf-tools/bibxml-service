const colors = require('tailwindcss/colors')

module.exports = {
  content: [
    "./templates/**/*.html",
    "./main/templates/**/*.html",
    "./management/templates/**/*.html",
    "./static/js/*.js",
    "./**/views.py",
  ],
  // Currently it is required to re-run Django compressor after template changes,
  // and since it won’t pick up styling change
  // you must touch the main.css file for compressor to update mtime.
  // TODO: Figure out how to speed up Tailwind style iteration
  // safelist: [
  //   { pattern: /.*/, variants: ['hover', 'focus'] }
  // ],
  theme: {
    extend: {
      colors: {
        dark: colors.slate,
        // Necessary for gradient workaround
        'dark700transparentfix': 'rgb(30 41 59 / 0)',
      },
      screens: {
        'xl': '1368px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/line-clamp'),
  ],
}
