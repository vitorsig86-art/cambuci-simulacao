# Funções comuns do modo saf_existente (agrofloresta já implantada).
# Usa só GDAL, numpy, scipy, shapely e yaml (roda no Python do QGIS, sem rasterio nem scikit-image).
import os, json, yaml
import numpy as np
from osgeo import gdal, ogr, osr
from shapely.geometry import shape
gdal.UseExceptions()

ROOT = os.path.abspath(os.environ.get('PROJETO', os.getcwd()))
CFG = yaml.safe_load(open(os.path.join(ROOT, 'projeto.yaml'), encoding='utf-8'))
D = os.path.join(ROOT, CFG['dados']['pasta'])
SAF = CFG['saf']
AREA_GJ = os.path.join(D, CFG['dados'].get('area_estudo', 'area_estudo.geojson'))
RECORTE_GJ = os.path.join(D, CFG['dados'].get('recorte', 'bbox.geojson'))
F1 = os.path.join(ROOT, 'fase1'); WORK = os.path.join(ROOT, 'work')
os.makedirs(F1, exist_ok=True); os.makedirs(WORK, exist_ok=True)
EPSG = int(str(CFG['crs']).split(':')[1])

def caminho(f): return os.path.join(D, f)

# Uma única moldura explícita controla todas as grades e a cena.
X0, Y0, X1, Y1 = shape(json.load(open(RECORTE_GJ, encoding='utf-8'))['features'][0]['geometry']).bounds
for _res in (0.1, 0.25, 0.5, 1.0):
    assert np.allclose(np.array([X1-X0,Y1-Y0])/_res, np.round(np.array([X1-X0,Y1-Y0])/_res), atol=1e-7)

def warp(f, res, alg):
    d = gdal.Warp('', caminho(f), format='MEM', dstSRS=CFG['crs'], outputBounds=(X0, Y0, X1, Y1), xRes=res, yRes=res, resampleAlg=alg)
    for b in range(1, d.RasterCount+1):
        band=d.GetRasterBand(b); a=band.ReadAsArray(); valid=band.GetMaskBand().ReadAsArray()!=0
        if not valid.all() or not np.isfinite(a).all():
            raise ValueError(f'Falha de cobertura em {f} / {res} m, banda {b}')
    return d

def mask(res, gj=None):
    d = warp('mdt.tif', res, 'near')
    m = gdal.GetDriverByName('MEM').Create('', d.RasterXSize, d.RasterYSize, 1, gdal.GDT_Byte)
    m.SetGeoTransform(d.GetGeoTransform()); m.SetProjection(d.GetProjection())
    ds = ogr.Open(gj or AREA_GJ); gdal.RasterizeLayer(m, [1], ds.GetLayer(), burn_values=[1])
    a = m.ReadAsArray().astype(bool); ds = None
    return a

def poligono(gj=None):
    return shape(json.load(open(gj or AREA_GJ, encoding='utf-8'))['features'][0]['geometry'])

def chm_grade(r=0.25):
    """CHM = MDS - MDT, filtrado (mediana 3x3). Devolve (bruto filtrado, limpo com <0,3 m = 0)."""
    from scipy import ndimage as ndi
    # warp valida máscaras antes da subtração. 0,25 m é reamostragem de 0,60 m.
    mds = warp('mds.tif', r, 'bilinear').ReadAsArray().astype(float)
    mdt = warp('mdt.tif', r, 'bilinear').ReadAsArray().astype(float)
    bruto = ndi.median_filter(np.clip(mds - mdt, 0, 30), 3)
    limpo = bruto.copy(); limpo[limpo < 0.3] = 0
    return bruto, limpo

def exg_grade(r):
    o = warp('orto.tif', r, 'average').ReadAsArray()[:3].astype(float)
    s = o.sum(0) + 1e-6
    return o, 2 * o[1] / s - o[0] / s - o[2] / s

def geojson_pontos(nome, feats):
    return {'type': 'FeatureCollection', 'name': nome,
            'crs': {'type': 'name', 'properties': {'name': f'urn:ogc:def:crs:EPSG::{EPSG}'}}, 'features': feats}

def ler_individuos():
    """Usa o geojson corrigido à mão se existir; senão o detectado."""
    corr = os.path.join(ROOT, SAF.get('individuos_corrigidos', 'fase1/individuos_corrigidos.geojson'))
    f = corr if os.path.exists(corr) else os.path.join(F1, 'individuos_detectados.geojson')
    return json.load(open(f, encoding='utf-8')), f
