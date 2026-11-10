"""Adiciona diagnóstico de falhas de inicialização ao template ativo."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'pipeline/site/template_imp.html';s=p.read_text(encoding='utf-8')
if 'window.__erroCambuci' not in s:
    anchor='<script type="importmap">'
    guard='''<script>
window.__erroCambuci=function(message){const e=document.getElementById('loading');if(!e)return;e.style.padding='24px';e.style.textAlign='center';e.style.whiteSpace='pre-line';e.textContent=message;};
window.addEventListener('error',e=>window.__erroCambuci(location.protocol==='file:'?'Abra o site por HTTP. No PowerShell, na pasta cambuci_implantacao, execute .\\qpy.bat -m http.server 8090 --bind 127.0.0.1 --directory site e visite http://127.0.0.1:8090/':('Falha ao montar a cena: '+(e.message||'erro de módulo, WebGL ou imagem'))));
window.addEventListener('unhandledrejection',e=>window.__erroCambuci('Falha ao montar a cena: '+String(e.reason)));
if(location.protocol==='file:')window.__erroCambuci('Este site usa módulos locais do Three.js e precisa ser servido por HTTP.\\n\\nNo PowerShell, na pasta cambuci_implantacao, execute:\\n.\\\\qpy.bat -m http.server 8090 --bind 127.0.0.1 --directory site\\n\\nDepois visite http://127.0.0.1:8090/');
setTimeout(()=>{const e=document.getElementById('loading');if(e&&e.textContent.startsWith('montando'))window.__erroCambuci('A montagem do terreno excedeu 30 segundos. Confira WebGL e memória do navegador. Consulte erros no console.');},30000);
</script>
'''
    assert anchor in s;s=s.replace(anchor,guard+anchor,1)
needle="img.onload=()=>{tex.needsUpdate=true; sujo=true; $('loading').remove();};"
if "img.onerror=()=>window.__erroCambuci" not in s:
    assert needle in s;s=s.replace(needle,needle+" img.onerror=()=>window.__erroCambuci('Não foi possível decodificar a textura do terreno. Confira se site/index.html está íntegro.');")
p.write_text(s,encoding='utf-8')
print('Falhas de carregamento agora aparecem ao usuário com orientação file:// ou erro WebGL/imagem.')
