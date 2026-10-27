import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const args=process.argv.slice(2);
function arg(k,d){let i=args.indexOf(k);return i<0?d:args[i+1]}
const root=path.resolve(arg('--out',path.join(path.dirname(fileURLToPath(import.meta.url)),'..')));
const chrome=arg('--chrome',process.env.CHROME_BINARY);
if(!chrome)throw Error('Supply --chrome or CHROME_BINARY');
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const browser=await chromium.launch({executablePath:chrome,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width:1280,height:900},javaScriptEnabled:false,deviceScaleFactor:1});
const page=await context.newPage();const requests=[],errors=[];
page.on('request',r=>{if(!r.url().startsWith('file:'))requests.push(r.url())});
page.on('pageerror',e=>errors.push(String(e)));
await page.goto(pathToFileURL(path.join(root,'minimax-m31-flash.html')).href);
await page.evaluate(()=>document.fonts.ready);
const measure=()=>page.evaluate(()=>({
  clearChecked:document.getElementById('clear').checked,
  neutralChecked:document.getElementById('neutral').checked,
  visibleArtwork:Array.from(document.querySelectorAll('.art')).filter(e=>getComputedStyle(e).display!=='none').map(e=>({
    classes:e.className,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,
    textCount:e.querySelectorAll('text').length,
    minRenderedTextPx:Math.min(...Array.from(e.querySelectorAll('text')).map(t=>parseFloat(getComputedStyle(t).fontSize)*t.getScreenCTM().a)),
    foreignObject:e.querySelectorAll('foreignObject').length,images:e.querySelectorAll('image').length
  })),
  horizontalOverflow:document.documentElement.scrollWidth>innerWidth,
  scripts:document.scripts.length,
  externalAssets:Array.from(document.querySelectorAll('[src],[href]')).map(e=>e.getAttribute('src')||e.getAttribute('href')).filter(v=>/^https?:/.test(v))
}));
const clear=await measure();
await page.screenshot({path:path.join(root,'evidence/html-clear-no-js.png'),fullPage:true});
await page.locator('label[for=neutral]').click();
const neutral=await measure();
await page.screenshot({path:path.join(root,'evidence/html-neutral-no-js.png'),fullPage:true});
await page.setViewportSize({width:390,height:844});
const mobile=await measure();
await page.screenshot({path:path.join(root,'evidence/html-mobile-neutral.png'),fullPage:true});
const report={
  method:'Actual local Chromium at1280×900; document JavaScript disabled; native HTML radio-label click changes CSS palette; secondary390×844 layout check.',
  desktopClear:clear,desktopNeutral:neutral,mobile,
  networkRequests:requests,javascriptErrors:errors,
  pass:clear.visibleArtwork.length===3&&neutral.visibleArtwork.length===3&&clear.clearChecked&&neutral.neutralChecked&&!clear.horizontalOverflow&&!neutral.horizontalOverflow&&requests.length===0&&errors.length===0,
  caveat:'Mobile check measures containment only. Scientific figure text is intended for desktop viewing, zooming, or standalone SVG; mobile full-figure text legibility is not claimed.'
};
fs.writeFileSync(path.join(root,'evidence/browser-qa.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
await browser.close();
