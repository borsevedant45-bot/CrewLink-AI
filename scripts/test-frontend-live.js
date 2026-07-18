const puppeteer = require('puppeteer-core');
const fs = require('fs');

// Possible browser paths on Windows
const paths = [
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', // Standard Edge
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',         // 64-bit Chrome
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',   // 32-bit Chrome
];

// Find the first path that actually exists on your machine
const executablePath = paths.find(p => fs.existsSync(p));

(async () => {
    const url = 'https://crewlink-frontend.onrender.com'; 
    console.log(`=== Testing Live Frontend: ${url} ===`);

    if (!executablePath) {
        console.error("❌ Could not automatically find Chrome or Edge. Please open the URL directly in your browser and press F12 to check the console!");
        process.exit(1);
    }

    console.log(`Using browser at: ${executablePath}\n`);
    
    const browser = await puppeteer.launch({ 
        headless: "new",
        executablePath: executablePath
    });
    
    const page = await browser.newPage();
    let errorCount = 0;

    page.on('pageerror', (error) => {
        console.error(`❌ JS Error: ${error.message}`);
        errorCount++;
    });

    page.on('requestfailed', (request) => {
        console.error(`❌ Failed Resource: ${request.url()} (${request.failure().errorText || 'Failed'})`);
        errorCount++;
    });

    try {
        // Render free tier can be slow, giving it 60 seconds to wake up
        await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
        
        if (errorCount === 0) {
            console.log('\n✓ Success! Deployed frontend loaded with 0 console errors.');
        } else {
            console.log(`\n💥 Found ${errorCount} error(s) on the live page.`);
        }
    } catch (err) {
        console.error(`❌ Connection failed or timed out. Render might still be waking up: ${err.message}`);
    }

    await browser.close();
})();