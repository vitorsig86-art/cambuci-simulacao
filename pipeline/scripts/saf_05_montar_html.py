# Etapa SAF 5. Junta base 3D + modelo e injeta no template_saf.html -> site/index.html.
import base64
from saf_comum import *
from osgeo import osr

b = json.load(open(os.path.join(WORK, 'base3d.json')))
mo = json.load(open(os.path.join(WORK, 'modelo.json'), encoding='utf-8'))
if CFG.get('latitude') is not None: lat = float(CFG['latitude'])
else:
    c = poligono().centroid; s = osr.SpatialReference(); s.ImportFromEPSG(EPSG); l = osr.SpatialReference(); l.ImportFromEPSG(4326)
    l.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER); lat = osr.CoordinateTransformation(s, l).TransformPoint(c.x, c.y)[1]
en = json.load(open(os.path.join(WORK, 'entorno.json')))
TEX = json.load(open(os.path.join(WORK, 'terreno_tex.json'))); TER = json.load(open(os.path.join(WORK, 'terreno.json'), encoding='utf-8'))
TEX.update(json.load(open(os.path.join(WORK, 'agua_tex.json')))); AGUA = json.load(open(os.path.join(WORK, 'agua.json'), encoding='utf-8'))
PE = yaml.safe_load(open(os.path.join(ROOT, SAF.get('parametros_economicos', 'parametros_economicos.yaml')), encoding='utf-8'))
PE = json.loads(json.dumps(PE, default=str))   # datas do yaml viram texto
for k in 'cpo': PE['geral']['ano_plantio'][k] = SAF['ano_plantio']   # um só ano de plantio (projeto.yaml)
json.dump(PE, open(os.path.join(WORK, 'economia_parametros.json'), 'w', encoding='utf-8'), ensure_ascii=False)   # para o relatório (node)
site = dict(W=b['W'], H=b['H'], zmin=b['zmin'], terrain=dict(nx=b['nx'], ny=b['ny'], res=b['res'], b64=b['b64']),
            perimetro=b['perimetro'], recorte=b['recorte'], modelo=mo, entorno=en, economia=PE, tex=TEX, terreno=TER, agua=AGUA,
            cfg=dict(lat=round(lat, 4), lon=TER['lon'], ano0=SAF['ano0'], anos=SAF['anos'], regiao=CFG.get('regiao') or '', crs=CFG['crs'],
                     entrelinha=SAF['espacamento']['entrelinha'], entreplantas=SAF['espacamento']['entreplantas'],
                     kcal_dia=SAF['kcal_pessoa_dia'], poda=SAF['manejo']['poda_servico_frac_copa']))
s = json.dumps(site, ensure_ascii=False, separators=(',', ':'))
t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site', 'template_saf.html'), encoding='utf-8').read()
orto = base64.b64encode(open(os.path.join(WORK, 'orto_saf.jpg'), 'rb').read()).decode()
econ_js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site', 'economia.js'), encoding='utf-8').read()
os.makedirs(os.path.join(ROOT, 'site'), exist_ok=True)
html = t.replace('__NOME__', CFG['nome']).replace('__TITULO__', CFG['titulo_html']).replace('__SITE__', s.replace('</', '<\\/')).replace('__ORTO__', orto).replace('__ECONOMIA_JS__', econ_js)
open(os.path.join(ROOT, 'site', 'index.html'), 'w', encoding='utf-8').write(html)
print('site/index.html gerado, MB', round(len(html.encode('utf-8')) / 1e6, 2))
