// QA do contrato IMP atual. Uso: npm install; npx playwright install chromium; npm test
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
const R=path.resolve(__dirname,'..'), out=path.join(R,'verificacao');
const read=p=>JSON.parse(fs.readFileSync(path.join(R,p),'utf8'));
const MO=read('work/modelo.json'), expected=read('work/economia_relatorio.json');
const E=require('../pipeline/site/economia.js'), PE=read('work/economia_parametros.json');
const result={series:[],browser:{},paridade:[]};
let maxDelta=0;
function close(a,b,p=''){
  if(typeof a==='number'&&typeof b==='number'){const delta=Math.abs(a-b);maxDelta=Math.max(maxDelta,delta);assert(delta<=1e-7,p+': '+a+' != '+b);}
  else if(a&&b&&typeof a==='object'&&typeof b==='object'){assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),p);for(const k of Object.keys(a))close(a[k],b[k],p+'.'+k);}
  else assert.deepEqual(a,b,p);
}
const finite=(obj,p='')=>{if(typeof obj==='number')assert(Number.isFinite(obj),p);else if(obj&&typeof obj==='object')for(const [k,v]of Object.entries(obj))finite(v,p+'.'+k);};
finite(MO);finite(expected);
for(const d of ['com','sem']){
  const M=E.desenho(MO,d);assert.equal(M.plantas.length,M.n);
  for(const c of ['conservador','provavel','otimista']){
    const C=M.cen[c];assert.equal(C.ind.length,31);assert.deepEqual(C.ind.map(i=>i.ano),Array.from({length:31},(_,i)=>i));
    for(const k of ['V','H','R','F'])assert.equal(Buffer.from(C[k],'base64').length,31*M.n);
    const rows=E.cenario(M,PE,c,E.padroes(M,PE));assert.deepEqual(rows,expected[d].cen[c].rows);
    assert.deepEqual(E.resumo(rows,true,.08),expected[d].cen[c].com);
    result.series.push({desenho:d,cenario:c,n:M.n,anos:31,bytes_por_serie:31*M.n});
  }
}
// Mesmo motor exatamente embutido no HTML.
const html=fs.readFileSync(path.join(R,'site/index.html'),'utf8'),econ=fs.readFileSync(path.join(R,'pipeline/site/economia.js'),'utf8');
assert(html.replace(/\r\n/g,'\n').includes(econ.replace(/\r\n/g,'\n')));result.motor_embutido_identico=true;result.html_bytes=Buffer.byteLength(html);
const root=path.join(R,'site'),server=http.createServer((req,res)=>{
  const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  if(pathname==='/favicon.ico'){res.writeHead(204);return res.end();}
  const f=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
  if(!f.startsWith(root+path.sep)){res.writeHead(403);return res.end();}
  fs.readFile(f,(err,data)=>{if(err){res.writeHead(404);return res.end();}res.setHeader('Content-Type',f.endsWith('.js')?'text/javascript':f.endsWith('.html')?'text/html; charset=utf-8':'application/octet-stream');res.end(data);});
});
(async()=>{
  await new Promise(ok=>server.listen(0,'127.0.0.1',ok));const url='http://127.0.0.1:'+server.address().port;
  let browser;
  try{
    browser=await chromium.launch({headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
    const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
    const p=await context.newPage(),errors=[],failed=[],external=[];
    p.setDefaultTimeout(30000);
    p.on('pageerror',e=>errors.push(e.stack));p.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    p.on('requestfailed',req=>failed.push(req.url()));p.on('request',req=>{if(!req.url().startsWith(url)&&!req.url().startsWith('data:'))external.push(req.url());});
    const t=Date.now();await p.goto(url,{waitUntil:'networkidle',timeout:60000});await p.waitForFunction(()=>window.__app&&!document.getElementById('loading'),{timeout:60000});
    result.browser.carregamento_ms=Date.now()-t;
    console.log('Carregou',result.browser.carregamento_ms,'ms');
    assert.equal(await p.locator('#btEst').isDisabled(),true);
    const mesh=await p.evaluate(()=>{const a=__app,g=a.TERR.mesh.geometry;return {vertices:g.attributes.position.count,triangulos:g.index.count/3,tipo_indice:g.index.array.constructor.name,three:a.THREE.REVISION,render:a.renderer.info.render,webgl:a.renderer.capabilities.isWebGL2};});
    assert.equal(mesh.vertices,146400);assert.equal(mesh.triangulos,291270);assert.equal(mesh.tipo_indice,'Uint32Array');result.browser.malha=mesh;
    for(const d of ['com','sem']){
      await p.locator(`[data-des="${d}"]`).click();
      for(const [i,c]of ['conservador','provavel','otimista'].entries()){
        console.log('Conferindo',d,c);
        await p.locator('#cenarios button').nth(i).click();
        for(const y of [0,30]){
          const info=await p.evaluate(({y})=>{const a=__app;document.getElementById('ano').value=y;document.getElementById('ano').dispatchEvent(new Event('input'));return {des:a.des,ano:a.ano,cen:a.cen,series:a.IND(a.CEN[a.cen].id).length,render:a.renderer.info.render};},{y});
          assert.equal(info.ano,y);assert.equal(info.des,d);assert.equal(info.series,31);
        }
        const got=await p.evaluate(({d,c})=>__app.ECOD()[d][c],{d,c});
        close(got.rows,expected[d].cen[c].rows);close(got.com,expected[d].cen[c].com);close(got.sem,expected[d].cen[c].sem);
        result.paridade.push({desenho:d,cenario:c,relatorio_interface:'iguais ao centavo; tolerância numérica absoluta 1e-7',vpl:got.com.vpl});
      }
    }
    console.log('Câmeras e camadas');
    for(const view of ['geral','cima','pe']){await p.locator(`[data-vue="${view}"]`).click();await p.waitForTimeout(200);}
    for(const id of ['btLinhas','btDren','btCopas','btEnt']){await p.locator('#'+id).click();await p.locator('#'+id).click();}
    await p.locator('[data-des="com"]').click();await p.locator('#btQV').click();await p.locator('#btQV').click();
    await p.locator('[data-aba="terreno"]').click();
    for(const key of ['orto','decl','agua','acum','cobertura','face','sol'])await p.locator('#camBase').selectOption(key);
    await p.locator('#camBase').selectOption('orto');
    await p.locator('#solPainel summary').click();await p.locator('#solData').selectOption('livre');await p.locator('#solDia').fill('2026-06-21');await p.locator('#solDia').dispatchEvent('change');
    await p.locator('#solHora').fill('14');await p.locator('#solHora').dispatchEvent('input');
    result.browser.relogio=await p.locator('#solInfo').textContent();
    await p.locator('#solPainel summary').click();
    console.log('Animação');
    // Animação com rAF real, não teste histórico do trator.
    await p.evaluate(()=>{const e=document.getElementById('ano');e.value=0;e.dispatchEvent(new Event('input'));});
    result.browser.construir_ms=await p.evaluate(()=>{const a=__app,r=[];for(const y of [0,5,15,30]){a.ano=y;const t=performance.now();a.construir();r.push({ano:y,ms:performance.now()-t});}return r;});
    await p.evaluate(()=>{const e=document.getElementById('ano');e.value=0;e.dispatchEvent(new Event('input'));});
    await p.locator('#play').click();
    result.browser.animacao=await p.evaluate(async()=>{const times=[];await new Promise(ok=>{const start=performance.now();function tick(t){times.push(t);if(t-start>=2200)ok();else requestAnimationFrame(tick);}requestAnimationFrame(tick);});return {ano:__app.ano,frames:times.length,duracao_ms:times.at(-1)-times[0],fps:(times.length-1)*1000/(times.at(-1)-times[0])};});
    await p.locator('#play').click();assert(result.browser.animacao.ano>0);
    await p.locator('[data-aba="prem"]').click();await p.locator('#u_preco_cafe').fill('1717');await p.locator('#u_preco_cafe').dispatchEvent('change');
    console.log('Persistência');
    assert.equal(await p.evaluate(()=>__app.U.preco_cafe),1717);
    await p.evaluate(()=>localStorage.setItem('jurema.implantacao.premissas.v2','sentinela-isolamento'));
    await p.reload({waitUntil:'networkidle'});await p.waitForFunction(()=>window.__app);
    assert.equal(await p.evaluate(()=>__app.U.preco_cafe),1717);assert.equal(await p.evaluate(()=>localStorage.getItem('jurema.implantacao.premissas.v2')),'sentinela-isolamento');
    result.browser.persistencia_isolada=true;
    await p.locator('[data-aba="prem"]').click();await p.locator('#premReset').click();
    await p.locator('[data-des="com"]').click();await p.locator('#cenarios button').nth(1).click();
    await p.evaluate(()=>{const e=document.getElementById('ano');e.value=30;e.dispatchEvent(new Event('input'));});
    await p.locator('[data-vue="geral"]').click();await p.locator('#btCopas').click();await p.locator('[data-aba="hoje"]').click();
    await p.screenshot({path:path.join(out,'desktop.png'),timeout:60000});
    result.browser.enquadramento=await p.evaluate(()=>{const a=__app,S=JSON.parse(document.getElementById('site').textContent);let outside=0,min=1e9,max=-1e9;for(const [x,y]of S.perimetro){const v=a.P(x,y,a.zAt(x,y)).project(a.camera);if(Math.abs(v.x)>1||Math.abs(v.y)>1||Math.abs(v.z)>1)outside++;min=Math.min(min,v.x);max=Math.max(max,v.x);}return {vertices_fora:outside,largura_fracao:(max-min)/2};});
    assert.equal(result.browser.enquadramento.vertices_fora,0);
    await p.setViewportSize({width:390,height:844});await p.waitForTimeout(300);
    await p.locator('[data-vue="geral"]').click();
    result.browser.mobile=await p.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,canvasWidth:document.querySelector('#scene canvas').getBoundingClientRect().width}));
    await p.screenshot({path:path.join(out,'mobile.png'),timeout:60000});
    for(const d of ['sem','com']){await p.locator(`[data-des="${d}"]`).click();await p.locator('#mAno').fill('30');await p.locator('#mAno').dispatchEvent('input');assert.equal(await p.evaluate(()=>Math.round(__app.ano)),30);}
    assert(result.browser.mobile.scrollWidth<=392,'overflow móvel');
    result.browser.erros=errors;result.browser.requisicoes_falhas=failed;result.browser.externas=external;
    assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);assert.deepEqual(external,[]);
    result.max_diferenca_numerica=maxDelta;result.status='PASSOU';console.log(JSON.stringify(result,null,2));
  }catch(e){result.status='FALHOU';result.erro=e.stack;console.error(e);process.exitCode=1;}
  finally{fs.writeFileSync(path.join(out,'aceite.json'),JSON.stringify(result,null,2));if(browser)await browser.close();server.close();}
})();
