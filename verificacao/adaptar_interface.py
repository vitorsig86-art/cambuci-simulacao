from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'pipeline/site/template_imp.html';s=p.read_text(encoding='utf-8')
s=s.replace("UK='jurema.implantacao.premissas.v2'", "UK=CFG.id+'.premissas.v1'")
s=s.replace('Date.UTC(2026,','Date.UTC(ANO0,')
s=s.replace("(LON-(-45))/15", "(LON-(CFG.utc_offset_h*15))/15")
s=s.replace('Hora solar','Hora solar local')
s=s.replace('Aptidão do café pelo clima: aba Diagnóstico e plantio.','Clima local indisponível; aptidão não avaliada.')
s=s.replace('estradas em cinza com os pontos onde o fluxo cruza a pista em magenta e os trechos onde a água corre ao longo dela em vermelho grosso. ', 'Vias indisponíveis. ')
s=s.replace('ha de pasto${CFG.regiao', 'ha de talhão${CFG.regiao')
s=s.replace('São estimativas de modelagem, sem validação de campo.', 'HIPÓTESE demonstrativa: café, banana, grevílea, implantação em 2026 e pastagem anterior não confirmados. Projeções condicionais, sem validação local.')
s=s.replace('plantável fora do corredor das estradas', 'no limite geométrico de plantio')
a=s.index("    ['Clima provável'");b=s.index("    ['Árvores existentes",a)
s=s[:a]+"    ['Clima local','Indisponível; aptidão não avaliada'],\n"+s[b:]
a=s.index("    ['Cortados no corredor da estrada'");b=s.index("    QVon?",a)
s=s[:a]+"    ['Vias','Indisponíveis; sem métricas de corredores ou logística'],\n"+s[b:]
s=s.replace("'<b>Alertas de clima:</b> '+Cl.alertas.join('. ')+'. '+Cl.metodo+'.'", "'<b>Premissas pendentes:</b> '+CFG.pendentes.join(', ')+'. '+Cl.metodo+'. <b>CHM nativo:</b> '+fmt(D.chm_nativo.negativos_pct,2)+'% negativo, preservado no diagnóstico. Copas propostas para preservação, a conferir. As árvores de contexto afetam a sombra visual e as exclusões; o efeito produtivo das copas existentes não está calibrado.'")
s=s.replace('nas bordas norte e leste (${fmt(Qz.perimetro_exposto_pct,0)}% do perímetro), com abertura de ${fmt(Qz.abertura_estrada_m,0)} m em cada estrada e sem árvore', "nas bordas ${Qz.bordas_usadas.join(', ')} (${fmt(Qz.perimetro_exposto_pct,0)}% do perímetro), sem vias fornecidas e sem árvore")
s=s.replace('como o renque norte fica morro abaixo, ele protege menos que em terreno plano.', 'cada ponto usa o desnível até o renque a barlavento; não se assume uma orientação de encosta fixa.')
a=s.index("  const cz=EST.cruz, pr=EST.pontas_resumo, lg=EST.logistica;");b=s.index("  $('metodo').innerHTML",a)
s=s[:a]+'''  const B=EST.proximidade_borda;
  $('estTab').innerHTML=`<tr><td>Vias</td><td>Indisponíveis: nenhum vetor fornecido</td></tr><tr><td>Proximidade à borda</td><td>${B.pontas_abaixo_3m} de ${B.pontas.length} pontas a menos de 3 m do limite, incluindo trechos curtos</td></tr>`;
  $('estTxt').textContent='Corredores, acessos e logística não calculados. Proximidade à borda é medida separada e não confirma cabeceira operacional. Drenagem é indicação estática do MDT; contribuições externas podem cruzar as bordas da moldura.';
''' +s[b:]
s=s.replace("$('btEst').onclick=", "if(!EST.disponivel){$('btEst').textContent='Vias indisponíveis';$('btEst').disabled=true;grpEst.visible=false;}\n$('btEst').onclick=")
s=s.replace("(grpEst.visible?`", "(EST.disponivel&&grpEst.visible?`")
# Camada auditável de copas/exclusões, distinta das copas instanciadas de contexto.
s=s.replace('<span>Estradas</span>', '<span>Copas preservadas</span><button id="btCopas" type="button" aria-pressed="false">Mostrar exclusões</button>\n        <span>Estradas</span>')
at=s.index('/* ---------- peças instanciadas')
s=s[:at]+'''const grpCopas=new THREE.Group();scene.add(grpCopas);grpCopas.visible=false;
for(const ring of S.copas_exclusao){grpCopas.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(drape(ring,.22,.5)),new THREE.LineBasicMaterial({color:'#00e676'})));}
$('btCopas').onclick=()=>{grpCopas.visible=!grpCopas.visible;$('btCopas').setAttribute('aria-pressed',grpCopas.visible);$('btCopas').textContent=grpCopas.visible?'Ocultar exclusões':'Mostrar exclusões';sujo=true;};
''' +s[at:]
s=s.replace('g.setIndex(idx); g.computeVertexNormals();','g.setIndex(new THREE.BufferAttribute(new Uint32Array(idx),1)); g.computeVertexNormals();',1)
s=s.replace('window.__app={construir,', 'window.__app={construir,maj,zAt,P,TERR,grpCopas,grpLinhas,ECON,get U(){return U},get cen(){return cen},')
# Notas visíveis em todos os tamanhos e separação física/visual/analítica.
s=s.replace('<main>', '<p style="margin:0 3vw 14px;padding:12px;border:1px solid #b39a42;border-radius:8px"><b>HIPÓTESE demonstrativa · Cambuci</b> — território medido; café, banana, grevílea e uso anterior hipotético a validar. Sombra 3D é visual; produção usa sobreposição de copas simuladas; insolação usa apenas o relevo; drenagem é estática. Valores em R$ constantes de 2026.</p><main>')
p.write_text(s,encoding='utf-8')
p=R/'pipeline/site/template_imp.html';s=p.read_text(encoding='utf-8')
s=s.replace('<div class="loading" id="loading">montando o terreno…</div>','<div class="loading" id="loading">montando o terreno…</div>')
# Captura falhas de ES modules/WebGL e impede que a tela de carregamento pareça travada.
anchor='<script type="importmap">'
guard='''<script>
window.__erroCambuci=function(message){const e=document.getElementById('loading');if(!e)return;e.style.padding='24px';e.style.textAlign='center';e.style.whiteSpace='pre-line';e.textContent=message;};
window.addEventListener('error',e=>window.__erroCambuci(location.protocol==='file:'?'Abra o site por HTTP. No PowerShell, execute .\\qpy.bat -m http.server 8090 --bind 127.0.0.1 --directory site e visite http://127.0.0.1:8090/':('Falha ao montar a cena: '+(e.message||'erro de módulo, WebGL ou imagem'))));
window.addEventListener('unhandledrejection',e=>window.__erroCambuci('Falha ao montar a cena: '+String(e.reason)));
if(location.protocol==='file:')window.__erroCambuci('Este site usa módulos locais do Three.js e precisa ser servido por HTTP.\n\nNo PowerShell, na pasta cambuci_implantacao, execute:\n.\\qpy.bat -m http.server 8090 --bind 127.0.0.1 --directory site\n\nDepois visite http://127.0.0.1:8090/');
setTimeout(()=>{const e=document.getElementById('loading');if(e&&e.textContent.startsWith('montando'))window.__erroCambuci('A montagem do terreno excedeu 30 segundos. Confira WebGL e memória do navegador. Consulte logs de erro no console.');},30000);
</script>
'''
s=s.replace(anchor,guard+anchor,1)
s=s.replace("img.onload=()=>{tex.needsUpdate=true; sujo=true; $('loading').remove();};", "img.onload=()=>{tex.needsUpdate=true; sujo=true; $('loading').remove();}; img.onerror=()=>window.__erroCambuci('Não foi possível decodificar a textura do terreno. Confira se site/index.html está íntegro.');")
p.write_text(s,encoding='utf-8')
p=R/'pipeline/scripts/imp_05_montar_html.py';s=p.read_text(encoding='utf-8')
s=s.replace('site = dict(georreferencia=', "copas=json.load(open(os.path.join(F1,'exclusao_copas.geojson'),encoding='utf-8'))\nrings=[]\nfor f in copas['features']:\n    for poly in ([f['geometry']['coordinates']] if f['geometry']['type']=='Polygon' else f['geometry']['coordinates']):\n        rings.append([[x-X0,y-Y0] for x,y in poly[0]])\nsite = dict(copas_exclusao=rings, georreferencia=")
p.write_text(s,encoding='utf-8')
p=R/'pipeline/scripts/imp_06_relatorio.py';s=p.read_text(encoding='utf-8')
s=s.replace("L = []", "L = ['> HIPÓTESE demonstrativa de café, banana e grevílea. Espécies, uso anterior, data, manejo, clima, carbono e economia pendentes de validação local. Não constitui diagnóstico de aptidão.\\n']")
s=s.replace('plantio em {ANO0}', 'plantio hipotético em {ANO0}')
s=s.replace("open(os.path.join(ROOT, 'relatorio.md')", "json.dump(EC,open(os.path.join(WORK,'economia_relatorio.json'),'w',encoding='utf-8'),ensure_ascii=False,allow_nan=False)\nopen(os.path.join(ROOT, 'relatorio.md')")
p.write_text(s,encoding='utf-8')
print('Interface e relatório adaptados')
