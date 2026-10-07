const playwright = require(process.env.WORKBENCH_PLAYWRIGHT_PATH || 'playwright');
const name = process.env.WORKBENCH_BROWSER || 'chromium';
if (!['chromium', 'webkit', 'firefox'].includes(name)) throw new Error('Unsupported WORKBENCH_BROWSER');
module.exports = {
  chromium: playwright[name],
  launchOptions: {
    headless: true,
    ...(name === 'chromium' && process.env.WORKBENCH_BROWSER_CHANNEL ? {channel: process.env.WORKBENCH_BROWSER_CHANNEL} : {}),
  },
};
