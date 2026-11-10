# Etapa SAF 1. Diagnóstico do terreno, CHM, linhas de plantio e copas individuais (fase 1).
# Saídas em fase1/: chm_limpo.tif, diagnostico.json, individuos_detectados.geojson, conferencia.png
from saf_comum import *
from scipy import ndimage as ndi
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

OUT = F1
r = 0.25                       # grade de trabalho do CHM (m)
H_MIN = 0.8                    # altura mínima de um indivíduo detectável (ruído do CHM ~0,5 m)
ESTRATOS = [(5.0, 'arboreo_alto'), (2.5, 'arboreo_medio'), (H_MIN, 'arbustivo')]

def salvar_tif(nome, a, res, tipo=gdal.GDT_Float32):
    ref = warp('mdt.tif', res, 'near')
    d = gdal.GetDriverByName('GTiff').Create(os.path.join(OUT, nome), a.shape[1], a.shape[0], 1, tipo, ['COMPRESS=DEFLATE'])
    d.SetGeoTransform(ref.GetGeoTransform()); d.SetProjection(ref.GetProjection())
    d.GetRasterBand(1).WriteArray(a); d.GetRasterBand(1).SetNoDataValue(-9999); d = None

# ---------- 1. terreno ----------
diag = {}
srs = osr.SpatialReference(); srs.ImportFromEPSG(EPSG)
ll = osr.SpatialReference(); ll.ImportFromEPSG(4326); ll.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
from shapely.geometry import shape
geo = shape(json.load(open(AREA_GJ))['features'][0]['geometry'])
bb = shape(json.load(open(RECORTE_GJ))['features'][0]['geometry'])
cx, cy = geo.centroid.x, geo.centroid.y
lon, lat, _ = osr.CoordinateTransformation(srs, ll).TransformPoint(cx, cy)
diag['area_estudo_ha'] = round(geo.area / 1e4, 3)
diag['recorte_ha'] = round(bb.area / 1e4, 3)
diag['area_dentro_do_recorte'] = bool(bb.buffer(0.5).contains(geo))
diag['centro'] = {'E': round(cx, 1), 'N': round(cy, 1), 'lat': round(lat, 5), 'lon': round(lon, 5)}

mdt1 = warp('mdt.tif', 1.0, 'bilinear').ReadAsArray().astype(float)
M1 = mask(1.0)
gy, gx = np.gradient(mdt1, 1.0)
decl = np.hypot(gx, gy) * 100
asp = (np.degrees(np.arctan2(-gx, gy)) + 360) % 360      # direção para onde a encosta desce (0 = N)
v = decl[M1]
diag['altitude_m'] = {k: round(float(f(mdt1[M1])), 1) for k, f in [('min', np.min), ('media', np.mean), ('max', np.max)]}
diag['declividade_pct'] = {'media': round(float(v.mean()), 1), 'p10': round(float(np.percentile(v, 10)), 1),
                           'mediana': round(float(np.median(v)), 1), 'p90': round(float(np.percentile(v, 90)), 1)}
ang = np.radians(asp[M1]); w = decl[M1]
diag['face_dominante_graus'] = round(float((np.degrees(np.arctan2((np.sin(ang) * w).sum(), (np.cos(ang) * w).sum())) + 360) % 360), 0)

# ---------- 2. CHM ----------
mds = warp('mds.tif', r, 'bilinear').ReadAsArray().astype(float)
mdt = warp('mdt.tif', r, 'bilinear').ReadAsArray().astype(float)
M = mask(r)
chm = np.clip(mds - mdt, 0, 30)
chm = ndi.median_filter(chm, 3)                 # tira pixels isolados
chm[chm < 0.3] = 0                              # abaixo de 0,3 m é ruído do par MDS/MDT
salvar_tif('chm_limpo.tif', np.where(True, chm, 0).astype(np.float32), r)
vc = chm[M]
diag['chm_m'] = {'media': round(float(vc.mean()), 2), 'p50': round(float(np.median(vc)), 2),
                 'p90': round(float(np.percentile(vc, 90)), 2), 'p99': round(float(np.percentile(vc, 99)), 2),
                 'max': round(float(vc.max()), 2)}
diag['cobertura_pct'] = {f'>{t}m': round(float((vc > t).mean() * 100), 1) for t in [0.5, 1, 2, 2.5, 5]}

# ---------- 3. orto e ExG ----------
o = warp('orto.tif', r, 'average').ReadAsArray()[:3].astype(float)
s = o.sum(0) + 1e-6
exg = 2 * o[1] / s - o[0] / s - o[2] / s
brilho = o.mean(0)
sombra = brilho < np.percentile(brilho[M], 8)

# ---------- 4. linhas de plantio (projeção do verde em cada ângulo) ----------
yy, xx = np.nonzero(M)
E = X0 + (xx + 0.5) * r; N = Y1 - (yy + 0.5) * r
sinal = exg[yy, xx] - exg[yy, xx].mean()
melhor = None
for a in np.arange(0, 180, 0.5):
    t = np.radians(a)                            # a = azimute da linha (0 = N, horário)
    d = E * np.cos(t) - N * np.sin(t)            # distância perpendicular à linha
    h, _ = np.histogram(d, bins=np.arange(d.min(), d.max() + r, r), weights=sinal)
    n, _ = np.histogram(d, bins=np.arange(d.min(), d.max() + r, r))
    p = np.where(n > 20, h / np.maximum(n, 1), 0)
    F = np.abs(np.fft.rfft(p - p.mean())); fr = np.fft.rfftfreq(len(p), r)
    ok = (fr > 1 / 12) & (fr < 1 / 1.5)
    k = np.argmax(F * ok)
    if melhor is None or F[k] > melhor[0]:
        melhor = (F[k], a, 1 / fr[k])
_, az, esp_fft = melhor
# refina o espaçamento pela autocorrelação no ângulo escolhido
t = np.radians(az); d = E * np.cos(t) - N * np.sin(t)
bins = np.arange(d.min(), d.max() + r, r)
h, _ = np.histogram(d, bins=bins, weights=sinal); n, _ = np.histogram(d, bins=bins)
p = np.where(n > 20, h / np.maximum(n, 1), 0); p = p - p.mean()
ac = np.correlate(p, p, 'full')[len(p) - 1:]; ac /= ac[0]
lo, hi = int(1.5 / r), int(12 / r)
lag = lo + np.argmax(ac[lo:hi])
esp_linhas = lag * r
diag['linhas'] = {'azimute_graus': float(az), 'entrelinha_m_fft': round(float(esp_fft), 2),
                  'entrelinha_m': round(float(esp_linhas), 2), 'autocorrelacao': round(float(ac[lag]), 2)}

# ---------- 5. copas individuais ----------
chs = ndi.gaussian_filter(chm, 1.0)
# janela variável: raio maior para plantas mais altas
topo = np.zeros_like(chs, bool)
for h0, h1, rad in [(H_MIN, 2.5, 0.75), (2.5, 5, 1.25), (5, 99, 1.75)]:
    k = int(round(rad / r)); fp = np.hypot(*np.mgrid[-k:k + 1, -k:k + 1]) <= k
    mx = ndi.maximum_filter(chs, footprint=fp)
    topo |= (chs == mx) & (chs >= h0) & (chs < h1)
# candidatos pequenos (0,6 a 0,8 m) só se destacam do entorno (não é capim uniforme)
k = int(round(0.6 / r)); fp = np.hypot(*np.mgrid[-k:k + 1, -k:k + 1]) <= k
mx = ndi.maximum_filter(chs, footprint=fp)
promin = chs - ndi.minimum_filter(chs, size=int(2.5 / r))
topo |= (chs == mx) & (chs >= 0.6) & (chs < H_MIN) & (promin >= 0.45)
topo &= ndi.binary_dilation(M, iterations=2)
lab_top, ntop = ndi.label(topo)
cen = ndi.center_of_mass(topo, lab_top, range(1, ntop + 1))
markers = np.zeros(chs.shape, np.int32)
pts = []
for i, (cy_, cx_) in enumerate(cen):
    iy, ix = int(round(cy_)), int(round(cx_))
    markers[iy, ix] = i + 1; pts.append((iy, ix))
fundo = chs < 0.5
markers[fundo] = ntop + 1
inv = (np.clip(chs.max() - chs, 0, None) / chs.max() * 65000).astype(np.uint16)
ws = ndi.watershed_ift(inv, markers)
ws[fundo] = 0

feats, est_cnt, descartados = [], {}, []
copa_area_tot = 0
for i, (iy, ix) in enumerate(pts):
    lab = i + 1
    h = float(chm[iy - 2:iy + 3, ix - 2:ix + 3].max())
    reg = (ws == lab) & (chs >= 0.5 * h)          # copa = parte da bacia acima de metade da altura
    reg_l, nl = ndi.label(reg)
    if nl > 1: reg = reg_l == reg_l[iy, ix] if reg_l[iy, ix] else reg_l == (np.bincount(reg_l.ravel())[1:].argmax() + 1)
    a = reg.sum() * r * r
    if not M[iy, ix] or h < 0.6: continue
    diam = 2 * np.sqrt(max(a, r * r) / np.pi)
    estr = next((nm for lim, nm in ESTRATOS if h >= lim), 'arbustivo')
    rr = reg if reg.any() else (np.arange(reg.size).reshape(reg.shape) == iy * reg.shape[1] + ix)
    cc = (slice(iy - 2, iy + 3), slice(ix - 2, ix + 3))      # centro da copa, 1,25 m
    g = min(float(np.mean(exg[rr])), float(np.mean(exg[cc])))
    azul = max(float(np.mean(o[2][rr] - o[1][rr])), float(np.mean(o[2][cc] - o[1][cc])))
    sh = float(np.mean(sombra[rr]))
    E_, N_ = X0 + (ix + 0.5) * r, Y1 - (iy + 0.5) * r
    if azul > 5 or (g < -0.02 and h < 2.5):          # caixa d'água, lona, veículo
        descartados.append({'E': round(E_, 1), 'N': round(N_, 1), 'h': round(h, 2), 'motivo': 'objeto nao vegetal (cor)'}); continue
    obs = None; exg_c = float(np.mean(exg[cc]))
    if exg_c < 0.16 and h >= 2.5: obs = 'copa sem folha verde: possivel arvore seca ou podada'
    if h < H_MIN: obs = 'planta pequena (0,6 a 0,8 m): conferir'
    # confiança: altura bem acima do ruído, copa com área mínima, verde, pouca sombra
    c = 0.35 * min(1, max(0, h - 0.6) / 1.9) + 0.25 * min(1, a / 2.0) + 0.25 * (g > 0.03) + 0.15 * (1 - sh)
    feats.append(dict(E=E_, N=N_, h=round(h, 2), copa=round(diam, 2),
                      area=round(a, 2), estrato=estr, exg=round(g, 3), exg_c=round(exg_c, 3), conf=round(c, 2), obs=obs))
    est_cnt[estr] = est_cnt.get(estr, 0) + 1
    copa_area_tot += a

# atribui linha de plantio e espaçamento na linha
t = np.radians(az)
for f in feats:
    f['dperp'] = f['E'] * np.cos(t) - f['N'] * np.sin(t)
    f['dlong'] = f['E'] * np.sin(t) + f['N'] * np.cos(t)
d0 = min(f['dperp'] for f in feats)
fase = np.median([((f['dperp'] - d0) % esp_linhas) for f in feats])
for f in feats:
    f['linha'] = int(np.floor((f['dperp'] - d0 - fase + esp_linhas / 2) / esp_linhas)) + 1
    f['desvio_linha_m'] = round(float(((f['dperp'] - d0 - fase + esp_linhas / 2) % esp_linhas) - esp_linhas / 2), 2)
na_linha = [f for f in feats if abs(f['desvio_linha_m']) <= 0.3 * esp_linhas]
gaps = []
from collections import defaultdict
porlinha = defaultdict(list)
for f in na_linha: porlinha[f['linha']].append(f['dlong'])
for l, L in porlinha.items():
    L = np.sort(L); g = np.diff(L); gaps += list(g[(g > 0.4) & (g < 15)])
gaps = np.array(gaps)
diag['linhas'].update({'n_linhas_com_plantas': len(porlinha),
                       'entre_plantas_detectadas_m': {'p25': round(float(np.percentile(gaps, 25)), 2),
                                                      'mediana': round(float(np.median(gaps)), 2),
                                                      'moda_aprox': round(float(np.bincount(np.round(gaps * 2).astype(int)).argmax() / 2), 2),
                                                      'p75': round(float(np.percentile(gaps, 75)), 2)},
                       'pct_individuos_sobre_linha': round(100 * len(na_linha) / len(feats), 1),
                       'grade': {'d0': float(d0), 'fase': float(fase)}})

conf_cls = lambda c: 'alta' if c >= 0.75 else ('media' if c >= 0.5 else 'baixa')
diag['individuos'] = {'total': len(feats), 'por_estrato': est_cnt,
                      'por_confianca': {k: sum(conf_cls(f['conf']) == k for f in feats) for k in ['alta', 'media', 'baixa']},
                      'soma_area_copas_m2': round(copa_area_tot, 0),
                      'cobertura_copas_detectadas_pct': round(100 * copa_area_tot / (diag['area_estudo_ha'] * 1e4), 1),
                      'pequenos_0_6_a_0_8m': sum(f['h'] < H_MIN for f in feats),
                      'possiveis_secas': sum(bool(f['obs'] and 'seca' in f['obs']) for f in feats),
                      'descartados_nao_vegetais': descartados}
for nm in ['arboreo_alto', 'arboreo_medio', 'arbustivo']:
    sel = [f for f in feats if f['estrato'] == nm]
    if sel:
        diag['individuos'][nm] = {'altura_media': round(np.mean([f['h'] for f in sel]), 2),
                                  'altura_max': round(max(f['h'] for f in sel), 2),
                                  'copa_media_m': round(np.mean([f['copa'] for f in sel]), 2)}
# classes de cobertura por pixel na área
cls = np.select([chm >= 5, chm >= 2.5, chm >= H_MIN, exg > 0.05], [4, 3, 2, 1], 0)
diag['cobertura_por_estrato_pct'] = {nm: round(float((cls[M] == k).mean() * 100), 1) for k, nm in
                                     [(4, 'arboreo_alto'), (3, 'arboreo_medio'), (2, 'arbustivo'),
                                      (1, 'herbaceo_pasto_verde'), (0, 'solo_palha_ou_sombra')]}

# ---------- 6. saídas ----------
gj = {'type': 'FeatureCollection', 'name': 'individuos_detectados',
      'crs': {'type': 'name', 'properties': {'name': f'urn:ogc:def:crs:EPSG::{EPSG}'}}, 'features': []}
for i, f in enumerate(sorted(feats, key=lambda f: (f['linha'], f['dlong']))):
    gj['features'].append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(f['E'], 2), round(f['N'], 2)]},
                           'properties': {'id': i + 1, 'altura_m': f['h'], 'copa_m': f['copa'], 'estrato': f['estrato'],
                                          'confianca': conf_cls(f['conf']), 'conf_valor': f['conf'], 'linha': f['linha'],
                                          'exg': f['exg'], 'especie': None, 'obs': f['obs']}})
json.dump(gj, open(f'{OUT}/individuos_detectados.geojson', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(diag, open(f'{OUT}/diagnostico.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(diag, ensure_ascii=False, indent=1))

# imagem de conferência
ro = 0.1
oo = warp('orto.tif', ro, 'average').ReadAsArray()[:3].transpose(1, 2, 0)
Mo = mask(ro)
ys, xs = np.nonzero(Mo); y0, y1_, x0, x1_ = max(ys.min() - 40, 0), ys.max() + 40, max(xs.min() - 40, 0), xs.max() + 40
fig, ax = plt.subplots(figsize=(13, 13 * (y1_ - y0) / (x1_ - x0)))
ax.imshow(oo[y0:y1_, x0:x1_], extent=(X0 + x0 * ro, X0 + x1_ * ro, Y1 - y1_ * ro, Y1 - y0 * ro))
ax.contour(np.arange(Mo.shape[1]) * ro + X0, Y1 - np.arange(Mo.shape[0]) * ro, Mo, [0.5], colors='yellow', linewidths=1.5)
cor = {'arboreo_alto': '#d7191c', 'arboreo_medio': '#fdae61', 'arbustivo': '#2c7bb6'}
for nm in cor:
    sel = [f for f in feats if f['estrato'] == nm]
    ax.scatter([f['E'] for f in sel], [f['N'] for f in sel], s=[max(6, (f['copa'] * 7) ** 2 / 4) for f in sel],
               facecolors='none', edgecolors=cor[nm], linewidths=1.2, label=f"{nm} ({len(sel)})")
    ax.scatter([f['E'] for f in sel], [f['N'] for f in sel], s=4, c=cor[nm])
pq = [f for f in feats if f['h'] < H_MIN]
ax.scatter([f['E'] for f in pq], [f['N'] for f in pq], marker='+', s=30, c='cyan', linewidths=1, label=f'pequena 0,6 a 0,8 m ({len(pq)})')
sc = [f for f in feats if f['obs'] and 'seca' in f['obs']]
ax.scatter([f['E'] for f in sc], [f['N'] for f in sc], marker='s', s=60, facecolors='none', edgecolors='magenta', linewidths=1.2, label=f'possível seca ({len(sc)})')
ax.scatter([d['E'] for d in descartados], [d['N'] for d in descartados], marker='D', s=30, facecolors='none', edgecolors='black', label=f'descartado, não vegetal ({len(descartados)})')
bx = [f for f in feats if conf_cls(f['conf']) == 'baixa']
ax.scatter([f['E'] for f in bx], [f['N'] for f in bx], marker='x', s=14, c='white', linewidths=0.8, label=f'confiança baixa ({len(bx)})')
ax.set_xlim(X0 + x0 * ro, X0 + x1_ * ro); ax.set_ylim(Y1 - y1_ * ro, Y1 - y0 * ro)
ax.legend(loc='lower right', fontsize=9, framealpha=0.85)
ax.set_title(f"Indivíduos detectados: {len(feats)} | linhas az {az:.1f}°, entrelinha {esp_linhas:.2f} m | círculo = copa", fontsize=10)
ax.tick_params(labelsize=7)
plt.tight_layout(); plt.savefig(f'{OUT}/conferencia.png', dpi=110)
