# Etapa SAF 3c. Terreno e análise do recorte inteiro, para a aba "Terreno e análise" do site.
# Porte de simulacao_suinocultura2 (terreno.py, analise.py, 16_texturas.py) para GDAL + scipy (Python do QGIS, sem rasterio nem pysheds).
# CALCULADO do MDT (grade de 1 m): declividade, face da encosta, sol de inverno (céu limpo, horizonte local), TWI (MFD).
# CALCULADO do MDS − MDT: cobertura. Aptidão preliminar não entra (critério de piquete, sem sentido para SAF implantado).
# Saídas: work/terreno_tex.json (texturas JPEG em base64, mesma moldura do terreno 3D) e work/terreno.json (estatísticas da área de estudo).
import io, base64, heapq
from saf_comum import *
from scipy import ndimage as ndi
from PIL import Image

TA = CFG.get('terreno') or {}
CLS = list(TA.get('declividade_classes', [3, 8, 15, 25])); PX = float(TA.get('textura_px_m', 2))
R1 = 1.0
z = warp('mdt.tif', R1, 'average').ReadAsArray().astype(float)
v = np.isfinite(z) & (z > -1000)
idx = ndi.distance_transform_edt(~v, return_distances=False, return_indices=True); z = z[tuple(idx)]
zf = ndi.gaussian_filter(z, 1.5)
H, W = zf.shape
IN = mask(R1)
gy, gx = np.gradient(zf, R1); gN = -gy                  # linha cresce para o sul
slope = np.hypot(gx, gN) * 100
aspect = (np.degrees(np.arctan2(-gx, -gN)) + 360) % 360   # para onde a encosta cai, 0 = N

# latitude e longitude reais do centro da área
c = poligono().centroid; s_ = osr.SpatialReference(); s_.ImportFromEPSG(EPSG); ll = osr.SpatialReference(); ll.ImportFromEPSG(4326)
ll.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER); LON, LAT, _ = osr.CoordinateTransformation(s_, ll).TransformPoint(c.x, c.y)

# ---------- sol de inverno: horizonte local em 16 azimutes e soma de céu limpo (jun a ago) ----------
az_list = np.arange(0, 360, 22.5); HOR = np.zeros((16, H, W), np.float32)
rr, cc = np.mgrid[0:H, 0:W].astype(float)
for k, az in enumerate(az_list):
    dx, dy = np.sin(np.radians(az)), np.cos(np.radians(az)); best = np.full((H, W), -90.0)
    for s in np.arange(2, 160, 2):
        r2 = rr - dy * s; c2 = cc + dx * s
        ok = (r2 >= 0) & (r2 < H) & (c2 >= 0) & (c2 < W)
        zz = ndi.map_coordinates(zf, [r2, c2], order=1, mode='nearest')
        best = np.where(ok, np.maximum(best, np.degrees(np.arctan2(zz - zf, s))), best)
    HOR[k] = best
lat = np.radians(LAT); n_ = np.sqrt(1 + gx ** 2 + gN ** 2); nx, ny, nz = -gx / n_, -gN / n_, 1 / n_
Ew = np.zeros((H, W)); Ewf = 0.0
for doy in range(152, 244, 7):
    dec = np.radians(23.44) * np.sin(2 * np.pi * (284 + doy) / 365)
    for hh in np.arange(-6.5, 6.6, 0.5):
        h = np.radians(15 * hh); se = np.sin(lat) * np.sin(dec) + np.cos(lat) * np.cos(dec) * np.cos(h)
        if se <= 0.02: continue
        el = np.arcsin(se); az = np.arctan2(-np.sin(h) * np.cos(dec), np.cos(lat) * np.sin(dec) - np.sin(lat) * np.cos(dec) * np.cos(h))
        sx, sy = np.cos(el) * np.sin(az), np.cos(el) * np.cos(az); Ib = 1361 * 0.7 ** ((1 / max(se, 0.05)) ** 0.678)
        k = int(round(((np.degrees(az) + 360) % 360) / 22.5)) % 16
        Ew += (Ib * np.clip(nx * sx + ny * sy + nz * se, 0, None) * (np.degrees(el) > HOR[k]) + 0.1 * Ib * (1 + nz) / 2)
        Ewf += Ib * se + 0.1 * Ib
relw = Ew / Ewf * 100                                     # % do terreno plano sem obstáculo

# ---------- TWI: preenchimento (priority flood) + acúmulo MFD (Freeman) ----------
fill = zf.copy(); seen = np.zeros((H, W), bool); pq = []
for r in range(H):
    for cq in (0, W - 1): heapq.heappush(pq, (fill[r, cq], r, cq)); seen[r, cq] = True
for cq in range(1, W - 1):
    for r in (0, H - 1): heapq.heappush(pq, (fill[r, cq], r, cq)); seen[r, cq] = True
NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
while pq:
    e, r, cq = heapq.heappop(pq)
    for dr, dc in NB:
        r2, c2 = r + dr, cq + dc
        if 0 <= r2 < H and 0 <= c2 < W and not seen[r2, c2]:
            seen[r2, c2] = True; fill[r2, c2] = max(fill[r2, c2], e + 1e-4); heapq.heappush(pq, (fill[r2, c2], r2, c2))
acc = np.ones((H, W)); ordem = np.argsort(-fill, axis=None)
fp = np.pad(fill, 1, constant_values=np.inf)
for f_ in ordem:
    r, cq = divmod(int(f_), W); e = fill[r, cq]; w_ = []
    for dr, dc in NB:
        d = e - fp[r + 1 + dr, cq + 1 + dc]
        if d > 0: w_.append((dr, dc, (d / np.hypot(dr, dc)) ** 1.1))
    if not w_: continue
    tot = sum(t[2] for t in w_)
    for dr, dc, t in w_: acc[r + dr, cq + dc] += acc[r, cq] * t / tot
twi = np.log(acc / np.maximum(slope / 100, 0.01))

# ---------- cobertura (MDS − MDT) em 0,5 m: máximo do MDS e mínimo do MDT na célula ----------
ch = np.clip(warp('mds.tif', 0.5, 'max').ReadAsArray().astype(float) - warp('mdt.tif', 0.5, 'min').ReadAsArray().astype(float), 0, 30)
IN05 = mask(0.5)

# ---------- texturas na moldura do terreno 3D (fora da área: esmaecido) ----------
Wm, Hm = X1 - X0, Y1 - Y0; TW, TH = int(round(Wm * PX)), int(round(Hm * PX))
gy2, gx2 = np.gradient(zf); hs = np.clip(0.78 + 0.3 * (-gx2 + gy2) / 1.4, 0.5, 1.1)
def tex(rgb, inside, sombreado, nearest=False):
    if sombreado is not None: rgb = rgb * sombreado[..., None]
    rgb = rgb.copy(); rgb[~inside] = rgb[~inside] * 0.55 + np.array([120, 125, 110]) * 0.45
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((TW, TH), Image.NEAREST if nearest else Image.BILINEAR)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=82, optimize=True); return base64.b64encode(buf.getvalue()).decode()
TX = {}
C5 = [(46, 125, 50), (124, 179, 66), (240, 200, 40), (240, 130, 30), (200, 40, 40)]; lim = [0] + CLS + [1e9]
c_ = np.zeros((H, W, 3))
for i, col in enumerate(C5): c_[(slope >= lim[i]) & (slope < lim[i + 1])] = col
TX['decl'] = tex(c_, IN, hs, True)
cols = [(220, 60, 40), (245, 150, 40), (240, 220, 60), (120, 190, 90), (60, 120, 200), (100, 90, 190), (160, 90, 170), (200, 80, 120)]
k8 = ((aspect + 22.5) % 360 // 45).astype(int); c_ = np.zeros((H, W, 3))
for i, col in enumerate(cols): c_[k8 == i] = col
TX['face'] = tex(c_, IN, hs, True)
t = np.clip((relw - 70) / 50, 0, 1)[..., None]; TX['sol'] = tex(t * np.array([255, 200, 40]) + (1 - t) * np.array([60, 90, 160]), IN, None)
lo, hi = np.percentile(twi[IN], [10, 99]); t = np.clip((twi - lo) / max(hi - lo, 1e-6), 0, 1)[..., None]
TX['agua'] = tex((1 - t) * np.array([230, 225, 200]) + t * np.array([80, 135, 255]), IN, hs)
c_ = np.zeros(ch.shape + (3,)) + (225, 220, 190); c_[ch > 0.3] = (170, 200, 110); c_[ch > 1.0] = (90, 150, 70); c_[ch > 2.5] = (30, 90, 40)
TX['cobertura'] = tex(c_, IN05, None, True)
json.dump(TX, open(os.path.join(WORK, 'terreno_tex.json'), 'w'))

# ---------- estatísticas da área de estudo ----------
A = int(IN.sum()); zi = zf[IN]; frac = lambda m: round(100 * float((m & IN).sum()) / A, 1)
nomes8 = ['norte', 'nordeste', 'leste', 'sudeste', 'sul', 'sudoeste', 'oeste', 'noroeste']
twi_lim = float(np.percentile(twi[IN], 90))
res = dict(lat=round(LAT, 5), lon=round(LON, 5), area_ha=round(poligono().area / 1e4, 3), perimetro_m=round(poligono().length, 1),
           cota_min=round(float(zi.min()), 1), cota_max=round(float(zi.max()), 1), desnivel=round(float(zi.max() - zi.min()), 1),
           decl_media=round(float(slope[IN].mean()), 1), decl_p90=round(float(np.percentile(slope[IN], 90)), 1), decl_max=round(float(slope[IN].max()), 1),
           decl_classes=CLS, decl_pct=[frac((slope >= lim[i]) & (slope < lim[i + 1])) for i in range(5)],
           face_pct={nomes8[i]: frac(k8 == i) for i in range(8)},
           sol_inverno_pct=dict(p10=round(float(np.percentile(relw[IN], 10)), 0), p50=round(float(np.percentile(relw[IN], 50)), 0), p90=round(float(np.percentile(relw[IN], 90)), 0)),
           twi=dict(p50=round(float(np.percentile(twi[IN], 50)), 1), p90=round(twi_lim, 1), area_acima_p90_pct=10.0),
           cobertura_pct={k: round(100 * float(((ch > a_) & (ch <= b_) & IN05).sum()) / IN05.sum(), 1) for k, a_, b_ in [('ate_0_3', -1, 0.3), ('0_3_a_1', 0.3, 1), ('1_a_2_5', 1, 2.5), ('acima_2_5', 2.5, 99)]},
           textura_px=[TW, TH])
json.dump(res, open(os.path.join(WORK, 'terreno.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(json.dumps(res, ensure_ascii=False)); print('texturas KB', {k: len(v) // 1024 for k, v in TX.items()})
