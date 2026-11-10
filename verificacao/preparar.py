"""Prepara exclusivamente cópias dos cinco insumos, sem alterar coordenadas."""
import json, hashlib, shutil, sys
from pathlib import Path
import numpy as np
import yaml
from osgeo import gdal, ogr, osr
from shapely.geometry import shape, box, mapping

ROOT = Path(__file__).resolve().parents[1]
O, D = ROOT/'originais', ROOT/'dados'
gdal.UseExceptions()
def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
crs = {'type':'name','properties':{'name':'urn:ogc:def:crs:EPSG::31984'}}
bounds = [194130.082938933,7616382.736833424,194330.082938933,7616565.736833424]
meta = {'crs':'EPSG:31984','crs_vetores':'atribuído por inferência; procedência pendente',
        'unidade_vertical':'m','datum_vertical':None,'moldura':bounds,'rasters':{},'entradas':{}}
for p in sorted(O.iterdir()):
    meta['entradas'][p.name] = {'sha256':sha(p),'bytes':p.stat().st_size}
    if p.suffix == '.geojson':
        j=json.loads(p.read_text(encoding='utf-8')); assert not j.get('crs')
        j['crs']=crs
        for i,f in enumerate(j['features']):
            f['properties']['id_origem']=f.get('id',i+1)
        dump(D/p.name,j)
        ds=ogr.Open(str(D/p.name)); sr=ds.GetLayer().GetSpatialRef()
        assert sr.GetAuthorityCode(None)=='31984'
        for feat,original in zip(ds.GetLayer(),j['features']):
            assert json.loads(feat.GetGeometryRef().ExportToJson())['coordinates'] == original['geometry']['coordinates']
            if p.name=='linhas_cultivo.geojson':
                assert feat.GetField('ELEVATION')==original['properties']['ELEVATION']
        meta.setdefault('vetores',{})[p.name]={'feicoes':len(j['features']),'ogr_xy_z_identicos':True,'crs_atribuido':'EPSG:31984, inferido'}
    else:
        shutil.copy2(p,D/p.name)
        ds=gdal.Open(str(p)); gt=ds.GetGeoTransform(); s=osr.SpatialReference(wkt=ds.GetProjection())
        assert s.GetAuthorityCode(None)=='31984'
        assert np.allclose([gt[0],gt[3]],[bounds[0],bounds[3]],rtol=0,atol=1e-7)
        assert gt[2]==gt[4]==0 and gt[5]<0
        is_orto=p.name=='orto.tif'; expected=(2002,1837) if is_orto else (334,306)
        assert (ds.RasterXSize,ds.RasterYSize)==expected
        assert np.isclose(gt[1],.1 if is_orto else .6)
        masks=[]
        for b in range(1,ds.RasterCount+1):
            band=ds.GetRasterBand(b); a=band.ReadAsArray(); m=band.GetMaskBand().ReadAsArray()!=0
            assert np.isfinite(a[m]).all() and m.all()
            assert band.GetNoDataValue() == (None if is_orto else -32767)
            masks.append({'banda':b,'invalidos':int((~m).sum()),'min':float(a.min()),'max':float(a.max())})
        if is_orto: assert ds.RasterCount==4 and np.all(ds.GetRasterBand(4).ReadAsArray()==255)
        meta['rasters'][p.name]={'geotransform':gt,'dimensoes':expected,'epsg':31984,'bandas':masks,'nodata':ds.GetRasterBand(1).GetNoDataValue()}
dump(D/'bbox.geojson',{'type':'FeatureCollection','crs':crs,'features':[{'type':'Feature','properties':{'origem':'interseção coberta, moldura 200 x 183 m'},'geometry':mapping(box(*bounds))}]})
area=shape(json.loads((D/'area_estudo.geojson').read_text(encoding='utf-8'))['features'][0]['geometry'])
assert area.is_valid and area.geom_type=='Polygon' and len(area.interiors)==0
assert abs(area.area-12183.37)<.02 and abs(area.length-504.24)<.02
meta['poligono']={'area_m2':area.area,'perimetro_m':area.length,'valido':True,'furos':0}
cfg=yaml.safe_load((ROOT/'projeto.yaml').read_text(encoding='utf-8'))
cfg.update(modo='implantacao',id='cambuci_implantacao',nome='Cambuci · implantação demonstrativa',
           titulo_html='Cambuci: <em>hipótese de café, banana e quebra-vento</em>',regiao='Cambuci, RJ',crs='EPSG:31984',latitude=None,
           clima=None,demonstracao=True,base_monetaria=2026,fuso='America/Sao_Paulo',utc_offset_h=-3,
           pendentes=['espécies e cultivares','data de implantação','uso anterior','espaçamentos','manejo','clima local','direção do vento','carbono e solo','custos e preços','datum vertical','procedência CRS vetorial'])
cfg['dados'].update(pasta='dados',estradas=None)
cfg['site'].update(cenario_inicial='provavel',desenho_inicial='sem',ano_inicial=0)
cfg['site']['camera_inicial'].update(lado='norte',inclinacao_graus=45,largura_area=.8)
cfg['saf'].update(ano0=2026,anos=30,uso_anterior='pastagem_hipotetica')
cfg['vento']['fonte']='hipótese demonstrativa herdada da Jurema: vento de 45 graus (NE); sem medição ou rosa dos ventos de Cambuci'
(ROOT/'projeto.yaml').write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False),encoding='utf-8')
# Todas as fontes herdadas ficam identificadas como hipóteses, sem validar clima/preços locais.
for filename in ['parametros_especies.yaml','parametros_economicos.yaml']:
    obj=yaml.safe_load((ROOT/filename).read_text(encoding='utf-8'))
    def mark(v):
        if isinstance(v,dict):
            if 'fonte' in v:
                if not str(v['fonte']).startswith('HIPÓTESE Cambuci'):
                    v['fonte']='HIPÓTESE Cambuci, valor herdado da Jurema, sem calibração local. Referência histórica não revalidada: '+str(v['fonte'])
                v['confianca']='baixa'
            for x in v.values(): mark(x)
    mark(obj)
    (ROOT/filename).write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False),encoding='utf-8')
dump(ROOT/'verificacao/entradas.json',meta)
print(json.dumps(meta,ensure_ascii=False,indent=1))
