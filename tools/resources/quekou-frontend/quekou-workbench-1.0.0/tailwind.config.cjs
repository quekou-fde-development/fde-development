module.exports = {
  content: ['./index.html', './app/**/*.{ts,tsx}'],
  presets: [require('./app/generated/preview-preset.cjs')],
};
