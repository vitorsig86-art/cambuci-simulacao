# Etapa SAF 3. Base 3D do recorte inteiro (não corta no limite da área de estudo).
# Superfície em grade de 0,5 m: MDT no recorte inteiro (o MDS nunca vira malha do terreno).
# A vegetação do entorno vem como árvores 3D da etapa 3b; dentro da área, só as plantas simuladas.
# Textura: orto na resolução nativa, entorno levemente esmaecido para destacar a área de estudo.
import io, base64
from saf_comum import *
from scipy import ndimage as ndi
from PIL import Image, ImageEnhance

RES = 0.5
mdt = warp('mdt.tif', RES, 'average').ReadAsArray().astype(float)
Z = mdt
assert np.isfinite(Z).all() and Z.max()-Z.min()<655.35
zmin = float(Z.min()); Tq = np.round((Z - zmin) * 100).astype(np.uint16)
ny, nx = Tq.shape; W, H = nx * RES, ny * RES
print('grade 3D', nx, ny, 'm', W, H, 'zmin', round(zmin, 1))

o = gdal.Open(caminho('orto.tif')); res_o = abs(o.GetGeoTransform()[1]); o = None
tw = int(min(4096, round(W / res_o))); th = int(round(tw * H / W)); r = W / tw
O = gdal.Warp('', caminho('orto.tif'), format='MEM', outputBounds=(X0, Y0, X1, Y1), width=tw, height=th, dstSRS=CFG['crs'], resampleAlg='average').ReadAsArray()
assert np.isfinite(O).all() and O.shape == (4, 1830, 2000) and (O[3] == 255).all(), 'máscara da textura inválida'
img = Image.fromarray(np.moveaxis(O[:3], 0, -1))
d = gdal.Warp('', caminho('mdt.tif'), format='MEM', outputBounds=(X0, Y0, X1, Y1), width=tw, height=th, dstSRS=CFG['crs'], resampleAlg='near')
m = gdal.GetDriverByName('MEM').Create('', tw, th, 1, gdal.GDT_Byte); m.SetGeoTransform(d.GetGeoTransform()); m.SetProjection(d.GetProjection())
ds = ogr.Open(AREA_GJ); gdal.RasterizeLayer(m, [1], ds.GetLayer(), burn_values=[1]); mm = m.ReadAsArray().astype(bool); ds = None
dim = ImageEnhance.Color(ImageEnhance.Brightness(img).enhance(0.82)).enhance(0.6)
a = np.clip(ndi.distance_transform_edt(~mm) * r / 3.0, 0, 1)[..., None]   # rampa de 3 m: sem corte no limite
arr = np.array(img) * (1 - a) + np.array(dim) * a
if O.shape[0] > 3: arr[O[3] == 0] = [128, 134, 116]
buf = io.BytesIO(); Image.fromarray(arr.astype(np.uint8)).save(buf, 'JPEG', quality=78, optimize=True)
open(os.path.join(WORK, 'orto_saf.jpg'), 'wb').write(buf.getvalue())
print('orto jpg MB', round(len(buf.getvalue()) / 1e6, 2), tw, th)

loc = lambda g: [[round(x - X0, 2), round(y - Y0, 2)] for x, y in g.exterior.coords]
json.dump(dict(X0=X0, Y0=Y0, W=W, H=H, zmin=zmin, nx=nx, ny=ny, res=RES, perimetro=loc(poligono()), recorte=loc(poligono(RECORTE_GJ)),
               b64=base64.b64encode(Tq.tobytes()).decode()), open(os.path.join(WORK, 'base3d.json'), 'w'))
