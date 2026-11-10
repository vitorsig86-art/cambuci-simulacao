# Etapa SAF 3d. Estudo da água: drenagem simulada no MDT do RECORTE INTEIRO (a água de fora entra na conta).
# Ideia herdada de simulacao_suinocultura2 (agua.py: caminhos pelo gradiente do MDT, linhas fundidas no site),
# trocada por uma rede de drenagem D8 em GDAL + numpy + scipy + shapely (Python do QGIS, sem pysheds nem rasterio).
# Passos: MDT a 1 m (média) + suavização gaussiana; preenchimento de depressões (priority flood com declive mínimo);
# direção D8; acumulação; rede por limiar de área; ordem de Strahler; trechos; bacias dos trechos principais e da
# área de estudo; entradas e saídas; pontos de concentração; comprimento de rampa; cruzamento com as linhas de cultivo.
# Só diagnóstico. Não calibrado com chuva nem vazão.
# Saídas: work/agua.json (site), work/agua_tex.json (mapa de acumulação), fase1/drenagem.geojson, fase1/agua_resumo.json
import io, base64, heapq
from saf_comum import *
from scipy import ndimage as ndi
from shapely.geometry import LineString, Point, shape, mapping
from shapely.ops import unary_union
from PIL import Image

AG = CFG.get('agua') or {}
SIG = float(AG.get('suavizacao_sigma_m', 1.0))         # suavização do MDT (m), tira ruído fotogramétrico
FMAX = float(AG.get('preenchimento_max_m', 0.30))      # depressões mais fundas que isto são marcadas (possível microrelevo real)
LIM = float(AG.get('limiar_rede_m2', 1000))            # área contribuinte mínima para virar rede
LCON = float(AG.get('limiar_concentracao_m2', 400))    # início da concentração dentro da área
RISCO_D = float(AG.get('risco_declividade_pct', 30)); RISCO_A = float(AG.get('risco_acumulacao_m2', 300))
ALIN = float(AG.get('conducao_alinhamento', 0.7)); COND_S = float(AG.get('conducao_declive_pct', 2)); COND_L = float(AG.get('conducao_trecho_min_m', 10))
R = 1.0

# ---------- MDT do recorte a 1 m ----------
z = warp('mdt.tif', R, 'average').ReadAsArray().astype(float)
REC = mask(R, RECORTE_GJ); val = np.isfinite(z) & (z > -1000) & REC
idx = ndi.distance_transform_edt(~val, return_distances=False, return_indices=True); z = z[tuple(idx)]
z = ndi.gaussian_filter(z, SIG / R)
H, W = z.shape; N = H * W; IN = mask(R) & val
dom = val.copy()

# ---------- preenchimento: priority flood (Barnes 2014) com epsilon, semeado na borda do domínio ----------
F = z.copy(); F[~dom] = np.inf
borda = dom & ~ndi.binary_erosion(dom, border_value=0)
seen = ~dom.copy(); pq = []
for r_, c_ in zip(*np.nonzero(borda)): heapq.heappush(pq, (F[r_, c_], int(r_), int(c_))); seen[r_, c_] = True
NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
while pq:
    e, r_, c_ = heapq.heappop(pq)
    for dr, dc in NB:
        r2, c2 = r_ + dr, c_ + dc
        if 0 <= r2 < H and 0 <= c2 < W and not seen[r2, c2]:
            seen[r2, c2] = True; F[r2, c2] = max(F[r2, c2], e + 1e-5); heapq.heappush(pq, (F[r2, c2], r2, c2))
prof = np.where(dom, F - z, 0)
dep_lab, ndep = ndi.label(dom & (prof > 0.02))
dep_real = []                                          # depressões fundas: mantidas como alerta, não apagadas do relatório
for k, sl in enumerate(ndi.find_objects(dep_lab)):
    m_ = dep_lab[sl] == k + 1; pmax = float(prof[sl][m_].max())
    if pmax > FMAX:
        cy, cx = ndi.center_of_mass(m_); dep_real.append(dict(x=round(sl[1].start + cx + 0.5, 1), y=round(H - (sl[0].start + cy + 0.5), 1), prof_m=round(pmax, 2), area_m2=int(m_.sum())))

# ---------- D8 e acumulação ----------
Fp = np.pad(F, 1, constant_values=np.inf)
best = np.zeros((H, W)); down = np.full((H, W), -1, np.int64); dist = np.ones((H, W))
for dr, dc in NB:
    d = np.hypot(dr, dc); s = (F - Fp[1 + dr:1 + dr + H, 1 + dc:1 + dc + W]) / d
    m_ = s > best; best[m_] = s[m_]
    rr_, cc_ = np.nonzero(m_); down[m_] = (rr_ + dr) * W + (cc_ + dc); dist[m_] = d
down[~dom] = -1
# borda do recorte: o terreno de fora é estimado por extrapolação (2 z - z do vizinho oposto). Se o maior declive aponta
# para fora, a água sai do recorte ali; sem isso ela correria colada na borda e criaria canais falsos.
n_out = 0
for r_, c_ in zip(*np.nonzero(borda)):
    melhor_out = 0.0
    for dr, dc in NB:
        r2, c2 = r_ + dr, c_ + dc
        if 0 <= r2 < H and 0 <= c2 < W and dom[r2, c2]: continue
        r3, c3 = r_ - dr, c_ - dc
        if not (0 <= r3 < H and 0 <= c3 < W and dom[r3, c3]): continue
        melhor_out = max(melhor_out, (z[r3, c3] - z[r_, c_]) / np.hypot(dr, dc))   # z_fora = 2 z - z_oposto
    if melhor_out > best[r_, c_]: down[r_, c_] = -1; n_out += 1
dn = down.ravel(); dd = dist.ravel(); Ff = np.where(dom, F, -np.inf).ravel()
ordem = np.argsort(-Ff, kind='stable'); ordem = ordem[np.isfinite(Ff[ordem])]
acc = dom.ravel().astype(float) * R * R
for i in ordem:
    j = dn[i]
    if j >= 0: acc[j] += acc[i]
ACC = acc.reshape(H, W)

# ---------- rede, Strahler e comprimento de rampa ----------
rede = (acc >= LIM) & dom.ravel()
up_n = np.zeros(N, int); maxin = np.zeros(N, int); cnt = np.zeros(N, int); strah = np.zeros(N, int); Lr = np.zeros(N)
for i in ordem:
    j = dn[i]
    if rede[i]:
        strah[i] = 1 if maxin[i] == 0 else (maxin[i] + 1 if cnt[i] >= 2 else maxin[i])
        if j >= 0 and rede[j]:
            up_n[j] += 1
            if strah[i] > maxin[j]: maxin[j] = strah[i]; cnt[j] = 1
            elif strah[i] == maxin[j]: cnt[j] += 1
    elif j >= 0 and not rede[j]: Lr[j] = max(Lr[j], Lr[i] + dd[i])
xy = lambda i: (float(i % W) + 0.5, float(H - i // W) - 0.5)   # coordenada local (m desde X0, Y0)

def chaikin(p, n=2):
    for _ in range(n):
        if len(p) < 3: break
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]): q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(p[-1]); p = q
    return p
PER_L = shape({'type': 'Polygon', 'coordinates': [[[x - X0, y - Y0] for x, y in poligono().exterior.coords]]})
trechos = []
for s in np.nonzero(rede & (up_n != 1))[0]:
    cel = [s]; j = dn[s]
    while j >= 0 and rede[j]:
        cel.append(j)
        if up_n[j] != 1: break
        j = dn[j]
    if len(cel) < 2: continue
    pts = [xy(i) for i in cel]; L = LineString(pts)
    zz = F.ravel()[cel]; decl = float(max(zz[0] - zz[-1], 0) / max(L.length, 1) * 100)
    sm = chaikin(list(LineString(pts).simplify(0.6).coords))
    trechos.append(dict(id=len(trechos), ordem=int(strah[s]), acc_ha=round(float(acc[cel[-1]]) / 1e4, 3), comp_m=round(L.length, 1), decl_pct=round(decl, 1),
                        dentro_m=round(L.intersection(PER_L).length, 1),
                        saida=int(cel[-1]), pts=[[round(a, 2), round(b, 2)] for a, b in sm], _geo=L))

# ---------- bacias: área de estudo e trechos principais ----------
INf = IN.ravel(); hit = np.zeros(N, bool)
for i in ordem[::-1]:                                  # de jusante para montante
    j = dn[i]; hit[i] = INf[i] or (j >= 0 and hit[j])
rev = [[] for _ in range(N)]
for i in np.nonzero(dn >= 0)[0]: rev[dn[i]].append(i)
def bacia(sai):
    m_ = np.zeros(N, bool); st = [sai]
    while st:
        i = st.pop()
        if m_[i]: continue
        m_[i] = True; st += rev[i]
    return m_.reshape(H, W)
def contorno(m2, tol=1.0):
    d_ = gdal.GetDriverByName('MEM').Create('', W, H, 1, gdal.GDT_Byte); d_.SetGeoTransform((0, R, 0, H, 0, -R)); d_.GetRasterBand(1).WriteArray(m2.astype(np.uint8))
    o_ = (ogr.GetDriverByName('MEM') or ogr.GetDriverByName('Memory')).CreateDataSource(''); ly = o_.CreateLayer('b'); ly.CreateField(ogr.FieldDefn('v', ogr.OFTInteger))
    gdal.Polygonize(d_.GetRasterBand(1), d_.GetRasterBand(1), ly, 0)
    g_ = unary_union([shape(json.loads(f.GetGeometryRef().ExportToJson())) for f in ly if f.GetField('v') == 1]).simplify(tol)
    g_ = max(g_.geoms, key=lambda q: q.area) if g_.geom_type == 'MultiPolygon' else g_
    return g_
BA = hit.reshape(H, W); g_ba = contorno(BA)
fora_ha = float((BA & ~IN).sum()) * R * R / 1e4
borda_rec = BA & ~ndi.binary_erosion(dom, border_value=0)
principais = sorted(trechos, key=lambda t: -t['acc_ha'])[:6]
for t in principais:
    g_ = contorno(bacia(t['saida'])); t['bacia_ha'] = round(g_.area / 1e4, 3); t['bacia'] = [[round(a, 1), round(b, 1)] for a, b in g_.exterior.coords]

# ---------- entradas, saídas e pontos de concentração ----------
def agrupa(cands, raio=6):
    out = []
    for c_ in sorted(cands, key=lambda q: -q['acc_m2']):
        if all(np.hypot(c_['x'] - o['x'], c_['y'] - o['y']) > raio for o in out): out.append(c_)
    return out
ent = agrupa([dict(zip(('x', 'y'), xy(i)), acc_m2=float(acc[i])) for i in np.nonzero(~INf & dom.ravel() & (dn >= 0))[0] if INf[dn[i]] and acc[i] >= 100])
sai = agrupa([dict(zip(('x', 'y'), xy(i)), acc_m2=float(acc[i])) for i in np.nonzero(INf)[0] if (dn[i] < 0 or not INf[dn[i]]) and acc[i] >= 100])
conc = []
for i in np.nonzero(INf & (acc >= LCON))[0]:
    if all(acc[u] < LCON for u in rev[i]): x_, y_ = xy(i); conc.append(dict(x=x_, y=y_, acc_m2=float(acc[i])))
conc = agrupa(conc, 3)
rampa = Lr.reshape(H, W)[IN & ~rede.reshape(H, W)]

# ---------- linhas de cultivo: cruzamentos, condução ao longo, trechos de risco ----------
FIL = np.where(np.isfinite(F), F, z)
gy, gx = np.gradient(FIL, R); gN = -gy                  # gradiente da superfície preenchida
amostra = lambda A_, x, y: float(ndi.map_coordinates(A_, [[H - y - 0.5], [x - 0.5]], order=1, mode='nearest')[0])
LIN = json.load(open(os.path.join(ROOT, 'fase1b', 'linhas_tratadas.geojson'), encoding='utf-8'))['features']
lin_res, cruz, cond_geo, risco_geo = [], [], [], []
for f_ in LIN:
    L = LineString([(x - X0, y - Y0) for x, y in f_['geometry']['coordinates']]); lid = f_['properties'].get('linha')
    for t in trechos:
        it = L.intersection(t['_geo'])
        for p in ([it] if it.geom_type == 'Point' else list(getattr(it, 'geoms', []))):
            if p.geom_type == 'Point': cruz.append(dict(linha=lid, x=round(p.x, 1), y=round(p.y, 1), ordem=t['ordem'], acc_ha=t['acc_ha'], trecho=t['id']))
    n_ = max(2, int(L.length)); run = []; runs = []; risco = []
    for k in range(n_ + 1):
        p = L.interpolate(k / n_, normalized=True); q = L.interpolate(min(1, (k + 0.5) / n_), normalized=True); p0 = L.interpolate(max(0, (k - 0.5) / n_), normalized=True)
        tx, ty = q.x - p0.x, q.y - p0.y; tn = np.hypot(tx, ty) or 1; tx, ty = tx / tn, ty / tn
        ge, gn_ = amostra(gx, p.x, p.y), amostra(gN, p.x, p.y); gs = np.hypot(ge, gn_)
        alin = abs(-(ge * tx + gn_ * ty)) / gs if gs > 1e-6 else 0; dl = abs(ge * tx + gn_ * ty) * 100
        a_ = amostra(ACC, p.x, p.y)
        if alin >= ALIN and dl >= COND_S: run.append((p.x, p.y))
        else:
            if len(run) > 1: runs.append(run)
            run = []
        if gs * 100 >= RISCO_D and a_ >= RISCO_A: risco.append((round(p.x, 1), round(p.y, 1)))
    if len(run) > 1: runs.append(run)
    runs = [r_ for r_ in runs if LineString(r_).length >= COND_L]
    for r_ in runs: cond_geo.append(dict(linha=lid, pts=[[round(a, 2), round(b, 2)] for a, b in r_], comp_m=round(LineString(r_).length, 1)))
    if risco: risco_geo.append(dict(linha=lid, pts=risco))
    lin_res.append(dict(linha=lid, comp_m=round(L.length, 1), cruzamentos=sum(1 for c_ in cruz if c_['linha'] == lid),
                        conduz_m=round(sum(LineString(r_).length for r_ in runs), 1), maior_trecho_m=round(max([LineString(r_).length for r_ in runs] or [0]), 1),
                        risco_m=len(risco)))

np.savez_compressed(os.path.join(WORK, 'agua_grades.npz'), ACC=ACC, F=FIL, gx=gx, gN=gN, z=z, IN=IN)   # para estradas e plantio

# ---------- mapa de acumulação (mesma moldura do terreno 3D) ----------
PX = float((CFG.get('terreno') or {}).get('textura_px_m', 2)); TW, TH = int(round((X1 - X0) * PX)), int(round((Y1 - Y0) * PX))
la = np.log10(np.maximum(ACC, 1)); t_ = np.clip((la - 0.5) / (np.log10(max(LIM * 10, 10)) - 0.5), 0, 1)[..., None]
rgb = (1 - t_) * np.array([238, 234, 214]) + t_ * np.array([20, 80, 220]); rgb[(ACC >= LIM)] = (10, 40, 170)
gy2, gx2 = np.gradient(z); hs = np.clip(0.8 + 0.3 * (-gx2 + gy2) / 1.4, 0.55, 1.1); rgb = rgb * hs[..., None]
rgb[~IN] = rgb[~IN] * 0.6 + np.array([120, 125, 110]) * 0.4
im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((TW, TH), Image.BILINEAR); buf = io.BytesIO(); im.save(buf, 'JPEG', quality=82, optimize=True)
json.dump({'acum': base64.b64encode(buf.getvalue()).decode()}, open(os.path.join(WORK, 'agua_tex.json'), 'w'))

# ---------- estatísticas e saídas ----------
A_ha = poligono().area / 1e4; Rec_ha = float(dom.sum()) * R * R / 1e4
comp_tot = sum(t['comp_m'] for t in trechos); comp_in = sum(t['dentro_m'] for t in trechos)
est = dict(resolucao_m=R, suavizacao_sigma_m=SIG, limiar_rede_m2=LIM, limiar_concentracao_m2=LCON, preenchimento_max_m=FMAX,
           risco_declividade_pct=RISCO_D, risco_acumulacao_m2=RISCO_A, conducao_alinhamento=ALIN, conducao_declive_pct=COND_S,
           recorte_ha=round(Rec_ha, 2), area_ha=round(A_ha, 3),
           rede_m_recorte=round(comp_tot), rede_m_area=round(comp_in), densidade_km_km2_recorte=round(comp_tot / 1000 / (Rec_ha / 100), 2),
           densidade_km_km2_area=round(comp_in / 1000 / (A_ha / 100), 2), trechos=len(trechos), ordem_max=max([t['ordem'] for t in trechos] or [0]),
           trechos_por_ordem={int(o): sum(1 for t in trechos if t['ordem'] == o) for o in sorted({t['ordem'] for t in trechos})},
           bacia_area_ha=round(float(BA.sum()) * R * R / 1e4, 3), contribuinte_de_fora_ha=round(fora_ha, 3),
           bacia_na_borda_do_recorte_m=int(borda_rec.sum()), entradas=len(ent), saidas=len(sai),
           maior_entrada_ha=round(max([e['acc_m2'] for e in ent] or [0]) / 1e4, 3), maior_saida_ha=round(max([e['acc_m2'] for e in sai] or [0]) / 1e4, 3),
           pontos_concentracao=len(conc), rampa_m=dict(p50=round(float(np.percentile(rampa, 50)), 1), p90=round(float(np.percentile(rampa, 90)), 1), max=round(float(rampa.max()), 1)) if rampa.size else None,
           cruzamentos=len(cruz), linhas_com_cruzamento=len({c_['linha'] for c_ in cruz}), linhas_que_conduzem=sum(1 for l_ in lin_res if l_['conduz_m'] > 0),
           conducao_total_m=round(sum(l_['conduz_m'] for l_ in lin_res)), pontos_risco=sum(l_['risco_m'] for l_ in lin_res),
           linhas_com_risco=sum(1 for l_ in lin_res if l_['risco_m'] > 0), depressoes_fundas=len(dep_real),
           preenchimento_medio_area_m=round(float(prof[IN].mean()), 3), preenchimento_max_area_m=round(float(prof[IN].max()), 2))
for t in trechos: t.pop('_geo'); t.pop('saida')
site = dict(est=est, trechos=trechos, divisor=[[round(a, 1), round(b, 1)] for a, b in g_ba.exterior.coords],
            principais=[dict(id=t['id'], ordem=t['ordem'], acc_ha=t['acc_ha'], bacia_ha=t['bacia_ha'], bacia=t['bacia']) for t in principais],
            entradas=[dict(x=round(e['x'], 1), y=round(e['y'], 1), ha=round(e['acc_m2'] / 1e4, 3)) for e in ent],
            saidas=[dict(x=round(e['x'], 1), y=round(e['y'], 1), ha=round(e['acc_m2'] / 1e4, 3)) for e in sai],
            concentracao=[dict(x=round(e['x'], 1), y=round(e['y'], 1), ha=round(e['acc_m2'] / 1e4, 3)) for e in conc],
            cruzamentos=cruz, conducao=cond_geo, risco=risco_geo, linhas=lin_res, depressoes=dep_real)
json.dump(site, open(os.path.join(WORK, 'agua.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
glob = lambda p: [[round(a + X0, 2), round(b + Y0, 2)] for a, b in p]
json.dump(geojson_pontos('drenagem', [{'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': glob(t['pts'])},
                                      'properties': {k: t[k] for k in ('id', 'ordem', 'acc_ha', 'comp_m', 'decl_pct', 'dentro_m')}} for t in trechos]),
          open(os.path.join(F1, 'drenagem.geojson'), 'w'))
json.dump(dict(est=est, linhas=lin_res, cruzamentos=cruz, entradas=site['entradas'], saidas=site['saidas'], depressoes=dep_real,
               principais=[{k: v for k, v in p.items() if k != 'bacia'} for p in site['principais']]),
          open(os.path.join(F1, 'agua_resumo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(est, ensure_ascii=False))
