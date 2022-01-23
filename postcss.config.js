module.exports = {
  plugins: [
    require('tailwindcss/nesting'),
    require('tailwindcss'),
    require('postcss-preset-env')({
      features: { 'nesting-rules': false },
      browsers: 'last 2 versions',
    }),
  ]
}
