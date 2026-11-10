# Etapa IMP 5. Junta base 3D, entorno, terreno, água, estradas, plantio e modelo e injeta em template_imp.html -> site/index.html.
import base64, shutil
from saf_comum import *

b = json.load(open(os.path.join(WORK, 'base3d.json')))
mo = json.load(open(os.path.join(WORK, 'modelo.json'), encoding='utf-8'))
en = json.load(open(os.path.join(WORK, 'entorno.json')))
TEX = json.load(open(os.path.join(WORK, 'terreno_tex.json'))); TER = json.load(open(os.path.join(WORK, 'terreno.json'), encoding='utf-8'))
TEX.update(json.load(open(os.path.join(WORK, 'agua_tex.json')))); AGUA = json.load(open(os.path.join(WORK, 'agua.json'), encoding='utf-8'))
EST = json.load(open(os.path.join(WORK, 'estradas.json'), encoding='utf-8'))
AGUA['limites_externos'] = json.load(open(os.path.join(ROOT,'verificacao','territorio_passagem2.json'),encoding='utf-8'))['contribuicao_externa_possivel']
PE = yaml.safe_load(open(os.path.join(ROOT, SAF.get('parametros_economicos', 'parametros_economicos.yaml')), encoding='utf-8'))
PE = json.loads(json.dumps(PE, default=str))   # datas do yaml viram texto
json.dump(PE, open(os.path.join(WORK, 'economia_parametros.json'), 'w', encoding='utf-8'), ensure_ascii=False)   # para o relatório (node)
ST = CFG.get('site') or {}   # estado inicial do site
lat = float(CFG['latitude']) if CFG.get('latitude') is not None else TER['lat']
copas=json.load(open(os.path.join(F1,'exclusao_copas.geojson'),encoding='utf-8'))
rings=[]
for f in copas['features']:
    for poly in ([f['geometry']['coordinates']] if f['geometry']['type']=='Polygon' else f['geometry']['coordinates']):
        rings.append([[x-X0,y-Y0] for x,y in poly[0]])
site = dict(copas_exclusao=rings, georreferencia=dict(id=CFG['id'], crs=CFG['crs'], origem_SW=[b['X0'],b['Y0']], extensao=[b['X0'],b['Y0'],b['X0']+b['W'],b['Y0']+b['H']], eixos='X leste; Y vertical; Z sul (norte negativo); centrado em W/2,H/2', pixel='centro: E=X0+(c+0.5)*passo, N=Y1-(r+0.5)*passo', passo_m=b['res'], unidade_vertical='m', datum_vertical=None,zmin=b['zmin'], entradas=json.load(open(os.path.join(ROOT,'verificacao','entradas.json'),encoding='utf-8'))['entradas']), W=b['W'], H=b['H'], zmin=b['zmin'], terrain=dict(nx=b['nx'], ny=b['ny'], res=b['res'], b64=b['b64']),
            perimetro=b['perimetro'], recorte=b['recorte'], modelo=mo, entorno=en, economia=PE, tex=TEX, terreno=TER, agua=AGUA, estradas=EST,
            cfg=dict(id=CFG['id'], fuso=CFG['fuso'], utc_offset_h=CFG['utc_offset_h'],base_monetaria=CFG['base_monetaria'],pendentes=CFG['pendentes'],lat=round(lat, 4), lon=TER['lon'], ano0=SAF['ano0'], anos=SAF['anos'], regiao=CFG.get('regiao') or '', crs=CFG['crs'],
                     entrelinha=mo['diag']['linhas']['entrelinha_m_mediana'], recuo_cafe=CFG['quebra_vento']['recuo_cafe_m'], folga_dren=CFG['quebra_vento']['folga_drenagem_m'],
                     cenario_inicial=str(ST.get('cenario_inicial', 'provavel')), desenho_inicial=str(ST.get('desenho_inicial', 'sem')), ano_inicial=int(ST.get('ano_inicial', 1)), camera_inicial=ST.get('camera_inicial') or {}))
s = json.dumps(site, ensure_ascii=False, separators=(',', ':'))
aqui = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(aqui, '..', 'site', 'template_imp.html'), encoding='utf-8').read()
orto = base64.b64encode(open(os.path.join(WORK, 'orto_saf.jpg'), 'rb').read()).decode()
econ_js = open(os.path.join(aqui, '..', 'site', 'economia.js'), encoding='utf-8').read()
os.makedirs(os.path.join(ROOT, 'site'), exist_ok=True)
shutil.copytree(os.path.join(aqui,'..','site','vendor'),os.path.join(ROOT,'site','vendor'),dirs_exist_ok=True)
html = t.replace('__NOME__', CFG['nome']).replace('__TITULO__', CFG['titulo_html']).replace('__SITE__', s.replace('</', '<' + chr(92) + '/')).replace('__ORTO__', orto).replace('__ECONOMIA_JS__', econ_js)
open(os.path.join(ROOT, 'site', 'index.html'), 'w', encoding='utf-8').write(html)
print('site/index.html gerado, MB', round(len(html.encode('utf-8')) / 1e6, 2))
