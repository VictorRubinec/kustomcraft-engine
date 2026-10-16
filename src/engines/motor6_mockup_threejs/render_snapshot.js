#!/usr/bin/env node
/**
 * Script CLI headless para renderização 3D com Three.js e Playwright.
 * Uso:
 *   node render_snapshot.js --scene mug --art ./output/caneca.png --out ./output/mockup.png
 */

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

async function main() {
  const args = process.argv.slice(2);
  const options = {
    scene: 'mug',
    art: null,
    backArt: null,
    out: 'mockup_out.png',
    resolution: 1024,
    angle: 'front_left',
    holo: true,
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--scene' && args[i + 1]) options.scene = args[++i];
    else if (args[i] === '--art' && args[i + 1]) options.art = args[++i];
    else if (args[i] === '--back' && args[i + 1]) options.backArt = args[++i];
    else if (args[i] === '--out' && args[i + 1]) options.out = args[++i];
    else if (args[i] === '--res' && args[i + 1]) options.resolution = parseInt(args[++i], 10);
    else if (args[i] === '--angle' && args[i + 1]) options.angle = args[++i];
  }

  let artDataUrl = null;
  if (options.art && fs.existsSync(options.art)) {
    const ext = path.extname(options.art).replace('.', '') || 'png';
    const b64 = fs.readFileSync(options.art).toString('base64');
    artDataUrl = `data:image/${ext};base64,${b64}`;
  }

  let backArtDataUrl = null;
  if (options.backArt && fs.existsSync(options.backArt)) {
    const ext = path.extname(options.backArt).replace('.', '') || 'png';
    const b64 = fs.readFileSync(options.backArt).toString('base64');
    backArtDataUrl = `data:image/${ext};base64,${b64}`;
  }

  const viewerHtml = path.resolve(__dirname, 'viewer.html');
  const browser = await chromium.launch({
    headless: true,
    args: ['--allow-file-access-from-files', '--enable-webgl', '--use-gl=angle']
  });

  const page = await browser.newPage({
    viewport: { width: options.resolution, height: options.resolution }
  });

  await page.addInitScript((cfg) => {
    window.__SCENE_CONFIG__ = cfg;
  }, {
    scene: options.scene,
    width: options.resolution,
    height: options.resolution,
    transparent: true,
    angle: options.angle,
    is_holographic: options.holo,
    art_data_url: artDataUrl,
    back_art_data_url: backArtDataUrl,
  });

  await page.goto(`file://${viewerHtml}`);
  await page.waitForFunction('window.__RENDER_READY__ === true', { timeout: 10000 });

  const renderError = await page.evaluate('window.__RENDER_ERROR__');
  if (renderError) {
    throw new Error(`Erro na renderização Three.js: ${renderError}`);
  }

  const outDir = path.dirname(path.resolve(options.out));
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  await page.screenshot({ path: options.out, omitBackground: true });
  await browser.close();
  console.log(`Mockup salvo com sucesso em: ${options.out}`);
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
