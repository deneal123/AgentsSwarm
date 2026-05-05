const fs = require('fs');
const puppeteer = require('puppeteer-core');
const axe = require('axe-core');

async function run() {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/chromium-browser',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--headless=new'],
  });

  const page = await browser.newPage();
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle2', timeout: 60000 });

  // Inject axe source and run
  await page.evaluate(axe.source);
  const results = await page.evaluate(async () => await axe.run());

  fs.writeFileSync('axe-report.json', JSON.stringify(results, null, 2));
  console.log('axe report written to axe-report.json');

  await browser.close();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
