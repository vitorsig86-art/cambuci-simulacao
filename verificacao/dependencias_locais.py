from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parents[1]
p=R/'pipeline/site/template_imp.html';s=p.read_text(encoding='utf-8')
imports={'imports':{'three':'./vendor/three.module.js','three/addons/controls/OrbitControls.js':'./vendor/OrbitControls.js'}}
s=re.sub(r'<script type="importmap">.*?</script>','<script type="importmap">'+json.dumps(imports)+'</script>',s,flags=re.S)
s=re.sub(r'<link[^>]+fonts.googleapis.com[^>]*>','',s)
p.write_text(s,encoding='utf-8')
files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (R/'pipeline/site/vendor').iterdir()}
(R/'verificacao/dependencias.json').write_text(json.dumps({'three':'0.187.0','origem':'cópia da instalação local, licença MIT incluída; substitui referência CDN 0.160/OrbitControls 0.165 por versão única','sha256':files},indent=2),encoding='utf-8')
print('Three.js e OrbitControls locais; fontes do sistema; sem requisições externas')
