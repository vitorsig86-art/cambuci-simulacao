from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
p=R/'pipeline/site/template_imp.html';s=p.read_text(encoding='utf-8')
s=s.replace("const TOQUE=matchMedia('(pointer:coarse)').matches;", """const TOQUE=matchMedia('(pointer:coarse)').matches;
const gl=renderer.getContext(), dbg=gl.getExtension('WEBGL_debug_renderer_info'), gpu=dbg?gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
const LEVE=TOQUE||/swiftshader|llvmpipe|software/i.test(gpu); // medição de QA: software saturou no detalhe desktop
""")
s=s.replace('TOQUE?', 'LEVE?')
s=s.replace("const on=!TOQUE||$('solPainel').open", "const on=$('solPainel').open")
s=s.replace('POOL,camera,controls,', 'POOL,gpu,LEVE,camera,controls,')
s=s.replace('<summary>Sol e sombra</summary>','<summary>Sol e sombra · ativar sombras visuais</summary>')
p.write_text(s,encoding='utf-8')
(R/'verificacao/desempenho_preliminar.json').write_text(json.dumps({'ambiente':'Chromium headless / SwiftShader','carregamento_ms':985,'triangulos_iniciais_com_sombras':5221794,'vertices_terreno':146400,'cpu_gpu_s_observada':763.171875,'observacao':'QA interativo interrompido após vários minutos sem completar a matriz; processo de software saturado. Não é medição de FPS.','ajuste':'detalhe móvel para GPU de software; sombras visuais ativadas pelo painel solar; grade métrica e número de plantas preservados'},ensure_ascii=False,indent=2),encoding='utf-8')
