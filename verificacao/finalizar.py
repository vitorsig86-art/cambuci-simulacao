"""Consolida evidências e compara a referência sem escrever fora do pacote."""
from pathlib import Path
import json,hashlib,sys,importlib.metadata
R=Path(__file__).resolve().parents[1]
REF=Path(r'C:\Users\Usuario\Desktop\projetos\simu_jurema')
def load(p):return json.loads((R/p).read_text(encoding='utf-8-sig'))
def write(p,x): (R/p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def signature(root):
    return [{'path':str(p.relative_to(root)).replace('/','\\'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest().upper()} for p in sorted(root.rglob('*')) if p.is_file()]
before=load('verificacao/referencia_antes.json');after=signature(REF)
write('verificacao/referencia_depois.json',after)
lookup=lambda rows:{x['path']:(x['bytes'],x['sha256']) for x in rows}
b,a=lookup(before),lookup([x for x in after if '.git' not in Path(x['path']).parts])
delta=[p for p in set(b)|set(a) if b.get(p)!=a.get(p)]
comp={'referencia':str(REF),'arquivos_antes':len(b),'arquivos_depois':len(a),'alterados':sorted(delta),'identica':not delta,
      'escopo':'111 arquivos de conteúdo da referência; inventário PowerShell inicial não incluiu .git oculto; metadados Git não foram alterados pela tarefa e não têm assinatura anterior',
      'metadados_git_fora_da_linha_base':[x['path'] for x in after if '.git' in Path(x['path']).parts]}
assert not delta,comp
adaptados=[];recalculados=[]
for row in before:
    p=R/row['path']
    if p.exists() and p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest().upper()!=row['sha256']:
        if '__pycache__' in p.parts:continue
        if row['path'].startswith('pipeline\\') or row['path'] in ('projeto.yaml','parametros_especies.yaml','parametros_economicos.yaml'):
            adaptados.append(row['path'])
        else:recalculados.append(row['path'])
comp['arquivos_adaptados_na_replica']=sorted(adaptados)
comp['novo_modulo_territorial']='pipeline/scripts/territorio_cambuci.py'
comp['artefatos_recalculados']=sorted(recalculados)
write('verificacao/comparacao_referencia.json',comp)
diag=load('fase1/diagnostico.json');terr=load('verificacao/territorio_passagem2.json');model=load('verificacao/modelo_quantizacao.json')
accept=load('verificacao/aceite.json');assert accept['status']=='PASSOU',accept.get('erro')
html=(R/'site/index.html').read_text(encoding='utf-8')
import re
site=json.loads(re.search(r'<script id="site"[^>]*>(.*?)</script>',html,re.S).group(1))
base_now=load('work/base3d.json')
assert site['terrain']['b64']==base_now['b64'] and site['terrain']['nx']==base_now['nx']
assert site['modelo']==load('work/modelo.json')
assert site['georreferencia']['entradas']==load('verificacao/entradas.json')['entradas']
for name,info in load('verificacao/entradas.json')['entradas'].items():
    for parent in (R/'originais',R.parent):
        assert hashlib.sha256((parent/name).read_bytes()).hexdigest()==info['sha256'],f'Insumo mudou: {parent/name}'
package_path=Path(r'C:\Users\Usuario\AppData\Local\Temp\claude\54be1be44004af29\e8eacfa9-ac81-45be-aba6-830b55548f35\scratchpad\rel\node_modules\playwright\package.json')
if package_path.exists():
    accept['playwright']=json.loads(package_path.read_text(encoding='utf-8'))['version']
    write('verificacao/aceite.json',accept)
from osgeo import gdal
env={'python':sys.version,'executavel':sys.executable,'GDAL':gdal.VersionInfo('--version')}
for m in ['numpy','scipy','shapely','pillow','PyYAML','matplotlib']:
    env[m]=importlib.metadata.version(m)
write('verificacao/ambiente.json',env)
ch=diag['chm_nativo'];ln=diag['linhas']['comprimentos_precisos_m'];base=load('work/base3d.json');qv=load('fase2/plantio_resumo.json')['quebra_vento']
L=['# Diagnóstico territorial gerado · Cambuci\n',
   'Data da réplica: 10/11/2026. Calculado exclusivamente dos cinco insumos em `originais/`; hashes e metadados em `verificacao/entradas.json`. Auditoria local da referência de 30/10/2026 consultada; auditoria citada de 10/11 e diagnóstico territorial anterior não localizados. Critérios numéricos da solicitação conferidos diretamente.\n',
   '## Medido nos arquivos\n',
   f"Polígono válido, sem furos: {diag['area_estudo_ha']:.4f} ha; área precisa {load('verificacao/entradas.json')['poligono']['area_m2']:.6f} m² e perímetro {load('verificacao/entradas.json')['poligono']['perimetro_m']:.6f} m. Centroide {diag['centro']}.\n",
   'Rasters EPSG:31984, norte para cima, origem E 194130,082938933 / N 7616565,736833424 m. Orto 2002 × 1837 a 0,10 m, RGBA opaco, sem NoData numérico. MDT/MDS 334 × 306 a 0,60 m, NoData −32767; máscaras integralmente válidas. Coincidência espacial por transformações e coordenadas, sem confundir borda com centro de célula.\n',
   'Moldura comum oeste/sul/leste/norte: 194130,082938933 / 7616382,736833424 / 194330,082938933 / 7616565,736833424 m. Cobertura integral validada antes de relevo/hidrologia/exportação. Grades 0,50 m: 400 × 366; 1 m: 200 × 183; 0,25 m: 800 × 732; textura 0,10 m: 2000 × 1830. Todas compartilham bordas.\n',
   f"Linhas: 30 LineString Z, ELEVATION textual, preservadas nos insumos. Bruto {ln['bruto']:.5f} m; fora {ln['fora']:.5f} m; dentro {ln['dentro']:.5f} m em 30 trechos; elegível {ln['elegivel']:.5f} m em 27 trechos. Recorte feito uma vez no diagnóstico; etapas posteriores usam `fase1b/linhas_tratadas.geojson`.\n",
   f"Curtos excluídos por mínimo de 3 m: {diag['linhas']['curtos_detalhes']}. Sobreposições: {diag['linhas']['sobreposicoes']}; cruzamentos: {diag['linhas']['cruzamentos_entre_linhas']}. Pontas a menos de 3 m da borda: {diag['proximidade_borda']['pontas_abaixo_3m']} de {len(diag['proximidade_borda']['pontas'])}, incluindo curtos. Não se infere capacidade de manobra desse indicador.\n",
   f"MDS − MDT nativo antes de filtro: {ch['min']:.5f} a {ch['max']:.5f} m; {ch['negativos_pct']:.5f}% negativos; {ch['maior_igual_2_5_pct']:.5f}% ≥ 2,50 m; {ch['validas']} células válidas no talhão. `fase1/chm_bruto_nativo.tif` preserva diferenças negativas.\n",
   '## Inferido e operacional\n',
   'Vetores sem declaração original: atribuição inferida de EPSG:31984 nas cópias normalizadas, sem reprojetar coordenadas. CRS explícito conferido via OGR e coordenadas conferidas com leitura JSON/Shapely. Procedência ainda pendente. Não foi necessário gerar GeoJSON RFC 7946. Z/ELEVATION não substituem o MDT na cena. Unidade vertical metro, datum vertical pendente.\n',
   f"CHM operacional: {diag['chm_operacional']}. Área proposta para preservação/exclusão: {diag['arvores_existentes']}. Interferência por trecho em `fase1/diagnostico.json`, campo `interferencia_copas_linhas`.\n",
   'Conferência visual no orto: a grande mancha alta a sudeste acompanha árvores visíveis; negativos se distribuem também em terreno e carreadores abertos, não são alturas físicas de vegetação. Sem pontos de controle não se corrige viés ou datum. Propostas de copa precisam de campo; as árvores instanciadas de contexto não são inventário botânico.\n',
   f"Sem vetor de vias: contrato `work/estradas.json` mantém arrays vazios, disponibilidade falsa e métricas nulas. Consumidores testados. Nenhuma exclusão por corredor ativada. Drenagem estática pelo MDT, contribuição externa possível por gradiente nas bordas: {terr['contribuicao_externa_possivel']}. Esses comprimentos indicativos podem incluir cantos; não representam bacias externas medidas ou vazão.\n",
   '## Hipóteses demonstrativas e contagens\n',
   'Café a 0,80 m e banana a 8 m com alternância de 4 m; mínimo de linha 3 m; vento assumido de NE 45°; grevílea em dois renques, 3 m entre árvores e renques, primeiro recuo 1 m, afastamento café–grevílea 2 m e drenagem 2 m. São regras herdadas da Jurema para demonstração.\n',
   f"Quebra-vento efetivo: bordas {qv['bordas_usadas']}, {qv['trechos']} trechos, {qv['comprimento_m']} m, {qv['arvores']} árvores. Cortes de candidatos do renque: {qv['cortes']}. Textos do site usam essas bordas reais, não uma orientação fixa herdada.\n"]
for d in ('com','sem'):
    L.append(f"Desenho {d}: {terr['desenhos'][d]}. Pontos precisos em `fase2/plantas_{d}_precisas.geojson`. As contagens brutas de café/banana fecham com aceitas + exclusões por motivo, em ordem de prioridade.\n")
L += ['Pendentes: '+', '.join(diag['premissas']['assumidos'])+'. Uso anterior de pastagem e ano 2026 são hipóteses, não fatos do talhão. Clima local indisponível; sem diagnóstico de aptidão.\n',
      '## Cena, quantização e testes\n',
      f"Origem local SW ({base['X0']}, {base['Y0']}); cena centrada, X leste, Y vertical acima de zmin={base['zmin']:.6f} m, Z sul (norte negativo). MDT sozinho, quantizado em 0,01 m, erro máximo {terr['terreno']['quantizacao_erro_max_m']:.6f} m. Malha completa com 146400 vértices, 291270 triângulos e Uint32.\n",
      f"Quantização de plantas/consistência: {model}. São 31 estados por desenho/cenário, V/H/R/F têm 31 × n bytes; sobrevivência confrontada com contagens anuais, sem saturação H/R.\n",
      'Sombra visual, efeito produtivo de copas simuladas, insolação do relevo e drenagem estática aparecem separados. Árvores existentes geram exclusões e sombra visual; efeito produtivo adicional não calibrado. Carbono é projeção de novas plantas e solo hipotético, sem crédito certificado.\n',
      f"Navegador: {accept['status']}; HTML {accept['html_bytes']} bytes; carregamento {accept['browser']['carregamento_ms']} ms; animação {accept['browser']['animacao']}; reconstrução de plantas {accept['browser']['construir_ms']}. Software SwiftShader, detalhe móvel adaptativo, malha e contagem de plantas preservadas. Viewport móvel {accept['browser']['mobile']}; GPU física e telefone real não medidos.\n",
      f"Paridade site/relatório nos seis pares de desenho/cenário, em todos os anos e nos dois modos de mão de obra: diferença numérica máxima {accept['max_diferenca_numerica']:.12g}, abaixo de 1e-7 e idêntica ao centavo. Mesmo motor econômico embutido, com teste de conteúdo normalizado para LF. Sem erros JS ou requisições falhas/externas; câmeras, camadas, anos 0/30, reprodução, edição, persistência isolada e viewport móvel testados.\n",
      f"Referência preservada: {comp['identica']}; {len(before)} arquivos antes/depois, zero alterações. Arquivos adaptados na cópia: "+', '.join('`'+s+'`' for s in adaptados)+'.\n',
      'Publicação externa não realizada. Comandos reproduzíveis em README.md; resultados integrais em verificacao/ e logs/.\n']
(R/'diagnostico_territorial.md').write_text('\n'.join(L),encoding='utf-8')
# Hashes finais dos entregáveis e fontes; exclui pycache e o próprio manifesto.
files=[]
for p in sorted(R.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts or p.name=='manifesto_final.json':continue
    files.append({'path':p.relative_to(R).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
write('verificacao/manifesto_final.json',files)
print(json.dumps({'referencia_identica':comp['identica'],'arquivos_referencia':len(before),'adaptados':adaptados,'aceite':accept['status'],'arquivos_pacote':len(files)},ensure_ascii=False,indent=1))
