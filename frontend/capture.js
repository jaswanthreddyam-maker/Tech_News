const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => {
    console.log(`[PAGE LOG]: ${msg.text()}`);
  });

  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  
  // Scroll down to trigger observer
  await page.evaluate(() => {
    window.scrollBy(0, 1200);
  });
  
  await new Promise(r => setTimeout(r, 2000));
  
  await page.evaluate(() => {
    window.scrollBy(0, 800);
  });
  
  await new Promise(r => setTimeout(r, 2000));

  await browser.close();
})();
