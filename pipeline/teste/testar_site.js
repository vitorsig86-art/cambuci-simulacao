// Teste do site gerado: carrega o HTML com three.js local, imprime receita e horas médias (anos 6 a 15)
// de cada desenho, tira 3 capturas e lista erros de JavaScript.
//   cd pipeline/teste && npm i playwright three@0.160.0 && npx playwright install chromium
//   node testar_site.js <raiz_do_projeto>
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
const raiz = path.resolve(process.argv[2] || '.');
const html = path.join(raiz, 'site', 'index.html');
const three = process.env.THREE_DIR || path.join(__dirname, 'node_modules', 'three');
const out = path.join(raiz, 'work'); fs.mkdirSync(out, { recursive: true });
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1440, height: 980 } }); const errs = [];
  p.on('pageerror', e => errs.push('ERR ' + e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  // three servido do node_modules local (qualquer versão pedida no importmap usa a instalada)
  await p.route(/https:\/\/cdn\.jsdelivr\.net\/npm\/three@[\d.]+\//, r => { const rel = r.request().url().replace(/^.*three@[\d.]+\//, ''); r.fulfill({ path: path.join(three, rel), contentType: 'application/javascript' }); });
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  await p.goto('file://' + html, { timeout: 180000 }); await p.waitForFunction(() => window.__app, null, { timeout: 180000 }); await p.waitForTimeout(5000);
  const shot = async f => { const bb = await p.locator('.stage').boundingBox(); await p.screenshot({ path: path.join(out, f), clip: bb, timeout: 180000 }); };
  const info = await p.evaluate(() => { const a = window.__app; return a.CEN.map((c, i) => { const s = a.simular(i); let r = 0, h = 0; for (let y = 6; y <= 15; y++) { r += s.ind[y].receita; h += s.ind[y].hsem; } return [c.id, +(r / 10).toFixed(1), +(h / 10).toFixed(1)]; }); });
  console.log('desenho, mil R$/ha, h/semana (média anos 6-15):', JSON.stringify(info));
  console.log('trechos:', await p.evaluate(() => [...document.querySelectorAll('#trecho option')].map(o => o.value + '=' + o.textContent).join(' | ')));
  console.log('lede:', await p.textContent('#lede'));
  await shot('t_geral.png');
  await p.evaluate(() => window.__app.pausa(true, 0)); if (await p.isVisible('#btTrator')) await p.click('#btTrator'); else console.log('sem trator (rota vazia)'); await p.click('[data-vue="cima"]'); await p.waitForTimeout(3000); await shot('t_cima.png');
  await p.setViewportSize({ width: 1440, height: 2600 }); await p.waitForTimeout(800);
  const bb = await p.locator('aside').boundingBox(); await p.screenshot({ path: path.join(out, 't_painel.png'), clip: { x: bb.x, y: bb.y, width: bb.width, height: Math.min(bb.height, 1400) }, timeout: 180000 });
  console.log(errs.length ? 'ERROS:\n' + errs.join('\n') : 'sem erros de JavaScript'); await b.close();
})();
