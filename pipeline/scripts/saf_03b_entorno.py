# Etapa SAF 3b. Árvores de contexto no entorno (fora da área de estudo), para a cena 3D.
# Copa é o padrão: todo CHM de porte arbóreo (>= entorno.altura_min_m) vira árvore, inclusive copa escura, sombra de copa e copa rugosa.
# Construção só com evidência forte e combinada: cor claramente não vegetal no orto (telhado cerâmico, claro/metálico ou azulado),
# superfície plana ou em águas no MDS (baixa rugosidade) e contorno retilíneo. Passou nas três = volume simples na cor do telhado.
# Cor não vegetal que falha na forma = dúvida: fica só no orto, sem volume e sem árvore.
# Maciço (copa contínua grande): não vira bloco nem copa única; é preenchido com árvores em grade irregular, com a altura do CHM local.
# Saídas: work/entorno.json (cena), fase1/entorno_arvores.geojson, fase1/entorno_filtrados.geojson, fase1/entorno_resumo.json,
#         fase1/conferencia_entorno.png
from saf_comum import *
from scipy import ndimage as ndi
from shapely.geometry import MultiPoint, Point

EN = CFG.get('entorno') or {}
r = 0.25
H_MIN = float(EN.get('altura_min_m', 2.5))
H_MAX = float(EN.get('altura_max_m', 30))
DIAM_MIN = float(EN.get('diametro_min_m', 1.5))
EST_AREA_MIN = float(EN.get('estrutura_area_min_m2', 6))
EST_RUG_MAX = float(EN.get('estrutura_rugosidade_max_m', 0.35))      # resíduo (m) do melhor ajuste de um plano ou de duas águas
EST_RET_MIN = float(EN.get('estrutura_retangularidade_min', 0.70))   # área da mancha / área do retângulo mínimo
MAC_DIAM = float(EN.get('macico_diametro_m', 7.0))                   # copa contínua acima disto é maciço
MAC_PASSO = float(EN.get('macico_passo_m', 3.5))                     # passo da grade irregular de árvores dentro do maciço
MAX_ARV = int(EN.get('max_arvores', 2500))
INCLUIR = bool(EN.get('incluir_area_estudo', False))   # implantação: árvores que já existem dentro da área ficam na cena

bruto, chm = chm_grade(r)
chm = np.clip(chm, 0, H_MAX)
M = mask(r)                                     # área de estudo
REC = mask(r, RECORTE_GJ)                        # recorte mostrado
FORA = REC if INCLUIR else REC & ~M
o, exg = exg_grade(r)
o = o[:3]
brilho = o.mean(0); sat = o.max(0) - o.min(0)

# ---------- construções: candidatos pela cor claramente não vegetal, confirmados por plano e contorno ----------
ceramico = (o[0] > 1.15 * o[1]) & (o[0] > 1.30 * o[2]) & (brilho > 85) & (exg < 0.0)
claro = (sat < 30) & (brilho > 140) & (exg < 0.03)                  # metálico, fibrocimento, laje
azulado = (o[2] - o[1] > 8) & (brilho > 90)
nv = (chm >= 2.0) & FORA & (ceramico | claro | azulado)
nv = ndi.binary_opening(nv, iterations=1); nv = ndi.binary_closing(nv, iterations=2)
lab_nv, n_nv = ndi.label(nv)

def rug_planos(xs, ys, zs, eixo):
    """Resíduo (m) do melhor ajuste: um plano ou duas águas com cumeeira ao longo de um dos eixos do retângulo."""
    def sq(m):
        if m.sum() < 6: return None
        A = np.c_[xs[m], ys[m], np.ones(m.sum())]; res = zs[m] - A @ np.linalg.lstsq(A, zs[m], rcond=None)[0]
        return float((res ** 2).sum())
    melhor = np.sqrt(sq(np.ones(len(zs), bool)) / len(zs))
    for ex, ey in (eixo, (-eixo[1], eixo[0])):
        t = (xs - xs.mean()) * ex + (ys - ys.mean()) * ey; a, b = sq(t < 0), sq(t >= 0)
        if a is not None and b is not None: melhor = min(melhor, np.sqrt((a + b) / len(zs)))
    return float(melhor)

vol, duv = [], []
CONSTR = np.zeros(chm.shape, bool); DUV = np.zeros(chm.shape, bool)
for k, sl in enumerate(ndi.find_objects(lab_nv)):
    if sl is None: continue
    m_ = lab_nv[sl] == k + 1; a = float(m_.sum()) * r * r
    if a < EST_AREA_MIN: continue
    yy, xx = np.nonzero(m_)
    E = X0 + (xx + sl[1].start + 0.5) * r; N = Y1 - (yy + sl[0].start + 0.5) * r
    ret = MultiPoint(list(zip(E, N))).buffer(r / 2, cap_style=3).minimum_rotated_rectangle
    co = list(ret.exterior.coords)[:4]
    l1 = np.hypot(co[1][0] - co[0][0], co[1][1] - co[0][1]); l2 = np.hypot(co[2][0] - co[1][0], co[2][1] - co[1][1])
    eixo = ((co[1][0] - co[0][0]) / (l1 + 1e-9), (co[1][1] - co[0][1]) / (l1 + 1e-9))
    retang = a / max(ret.area, 1e-6)
    mi = ndi.binary_erosion(m_, iterations=2)                       # miolo: a borda mistura telhado e chão no MDS
    if mi.sum() < 12: mi = m_
    yi, xi = np.nonzero(mi); hv = chm[sl][mi]
    rug = rug_planos((xi + sl[1].start) * r, -(yi + sl[0].start) * r, hv, eixo)
    h = float(np.percentile(hv, 60)); rgb = np.median(o[:, sl[0], sl[1]][:, mi], axis=1)
    tipo = 'telhado cerâmico' if ceramico[sl][m_].mean() > 0.5 else ('cobertura azulada' if azulado[sl][m_].mean() > 0.5 else 'cobertura clara (metálica, fibrocimento ou laje)')
    falhas = ([f'rugosidade {rug:.2f} m > {EST_RUG_MAX}'] if rug > EST_RUG_MAX else []) + ([f'retangularidade {retang:.2f} < {EST_RET_MIN}'] if retang < EST_RET_MIN else []) + ([f'altura {h:.1f} m < 2'] if h < 2.0 else [])
    d = dict(E=round(ret.centroid.x, 1), N=round(ret.centroid.y, 1), h=round(h, 2), area=round(a, 1), lados_m=[round(float(l1), 1), round(float(l2), 1)], cor=tipo,
             rugosidade_m=round(rug, 2), retangularidade=round(retang, 2), pol=[[round(x - X0, 2), round(y - Y0, 2)] for x, y in co], rgb=[int(v) for v in rgb])
    if falhas: d['motivo'] = 'dúvida, só no orto: cor não vegetal, mas ' + ' e '.join(falhas); duv.append(d); DUV[sl] |= m_
    else: vol.append(d); CONSTR[sl] |= m_
CONSTR_B = ndi.binary_dilation(CONSTR, iterations=int(round(1.0 / r))) if CONSTR.any() else CONSTR      # beiral: 1 m sem copa em volta

# ---------- copas: tudo que não é construção confirmada ----------
chm_a = np.where(CONSTR_B, 0, chm)
chs = ndi.gaussian_filter(chm_a, 1.0)
topo = np.zeros_like(chs, bool)
for h0, h1, rad in [(H_MIN, 5, 1.25), (5, 10, 1.75), (10, 99, 2.5)]:
    k = int(round(rad / r)); fp = np.hypot(*np.mgrid[-k:k + 1, -k:k + 1]) <= k
    mx = ndi.maximum_filter(chs, footprint=fp)
    topo |= (chs == mx) & (chs >= h0) & (chs < h1)
topo &= REC                                       # picos dentro da área também disputam a bacia, mas são descartados
lab_top, ntop = ndi.label(topo)
cen = ndi.center_of_mass(topo, lab_top, range(1, ntop + 1))
markers = np.zeros(chs.shape, np.int32); pts = []
for i, (cy_, cx_) in enumerate(cen):
    iy, ix = int(round(cy_)), int(round(cx_)); markers[iy, ix] = i + 1; pts.append((iy, ix))
fundo = chs < 0.5 * H_MIN
markers[fundo] = ntop + 1
inv = (np.clip(chs.max() - chs, 0, None) / max(chs.max(), 1e-6) * 65000).astype(np.uint16)
ws = ndi.watershed_ift(inv, markers); ws[fundo] = 0
obj = ndi.find_objects(ws)

def local(iy, ix, raio_m):
    k = max(1, int(round(raio_m / r))); return slice(max(0, iy - k), iy + k + 1), slice(max(0, ix - k), ix + k + 1)
arv, filt, dentro, macicos = [], [], 0, []
rng = np.random.default_rng(303)
for i, (iy, ix) in enumerate(pts):
    lab = i + 1
    if M[iy, ix]:
        dentro += 1
        if not INCLUIR: continue
    if not FORA[iy, ix] or i >= len(obj) or obj[i] is None: continue
    sl = obj[i]; w_ = ws[sl] == lab; c_ = chs[sl]; ch_ = chm_a[sl]
    h = float(chm_a[local(iy, ix, 0.5)].max())
    if h < H_MIN: continue
    reg = w_ & (c_ >= 0.5 * h)
    rl, nl = ndi.label(reg)
    py, px = iy - sl[0].start, ix - sl[1].start
    if nl > 1: reg = rl == (rl[py, px] if rl[py, px] else np.bincount(rl.ravel())[1:].argmax() + 1)
    a = float(reg.sum()) * r * r
    diam = 2 * np.sqrt(max(a, r * r) / np.pi)
    E_, N_ = X0 + (ix + 0.5) * r, Y1 - (iy + 0.5) * r
    hv = ch_[reg]; rug = float(np.std(hv - np.median(hv))) if hv.size else 0
    sub = (slice(sl[0].start, sl[0].stop), slice(sl[1].start, sl[1].stop))
    g = float(exg[sub][reg].mean()) if reg.any() else 0.0; fduv = float(DUV[sub][reg].mean()) if reg.any() else 0.0
    motivo = None
    if fduv > 0.5: motivo = 'dúvida, só no orto: copa sobre mancha de cor não vegetal não confirmada como construção'
    elif diam < DIAM_MIN: motivo = 'fragmento de copa (< diametro_min_m, borda do recorte ou lasca entre copas)'
    if motivo:
        filt.append(dict(E=round(E_, 1), N=round(N_, 1), h=round(h, 2), copa=round(diam, 2), exg=round(g, 3), motivo=motivo)); continue
    um = lambda: dict(dentro=bool(M[iy, ix]), E=E_, N=N_, h=round(h, 2), copa=round(min(diam, MAC_DIAM), 2), exg=round(g, 3), rug=round(rug, 2),
                      rgb=[int(v) for v in o[:, sub[0], sub[1]][:, reg].mean(1)], macico=0)
    if diam <= MAC_DIAM: arv.append(um()); continue
    # maciço: grade irregular (fileiras desencontradas, deslocamento aleatório) sobre a bacia da copa, altura do CHM local
    corpo = w_ & (ch_ >= H_MIN) & ~DUV[sub]; mid = len(macicos) + 1; n0 = len(arv)
    for jy, y_ in enumerate(np.arange(MAC_PASSO / 2, corpo.shape[0] * r + MAC_PASSO, MAC_PASSO * 0.87)):
        for x_ in np.arange(MAC_PASSO / 2 - (MAC_PASSO / 2 if jy % 2 else 0), corpo.shape[1] * r + MAC_PASSO, MAC_PASSO):
            qy = int((y_ + rng.uniform(-0.28, 0.28) * MAC_PASSO) / r); qx = int((x_ + rng.uniform(-0.28, 0.28) * MAC_PASSO) / r)
            if not (0 <= qy < corpo.shape[0] and 0 <= qx < corpo.shape[1]) or not corpo[qy, qx]: continue
            gy, gx = qy + sl[0].start, qx + sl[1].start; jan = local(gy, gx, MAC_PASSO * 0.35)
            hl = float(np.percentile(chm_a[jan], 90))
            if hl < H_MIN: continue
            arv.append(dict(dentro=bool(M[gy, gx]), E=X0 + (gx + 0.5) * r, N=Y1 - (gy + 0.5) * r, h=round(hl, 2), copa=round(MAC_PASSO * rng.uniform(1.1, 1.4), 2),
                            exg=round(float(exg[jan].mean()), 3), rug=round(rug, 2), rgb=[int(v) for v in o[:, jan[0], jan[1]].reshape(3, -1).mean(1)], macico=mid))
    if len(arv) == n0: f = um(); f['macico'] = mid; arv.append(f)
    macicos.append(dict(id=mid, E=round(E_, 1), N=round(N_, 1), h_max=round(h, 1), copa_continua_m=round(diam, 1), arvores=len(arv) - n0))

# limite de instâncias: guarda as maiores copas
if len(arv) > MAX_ARV:
    arv.sort(key=lambda f: -f['h'] * f['copa']); cortadas = len(arv) - MAX_ARV; arv = arv[:MAX_ARV]
else: cortadas = 0

# ---------- tom: o mesmo esmaecimento do orto no entorno (etapa 3); o telhado guarda mais da cor ----------
def tom(rgb, k_b=0.82, k_s=0.6):
    c = np.array(rgb, float); l = c @ [0.299, 0.587, 0.114]
    c = (l + (c - l) * k_s) * k_b
    return [int(v) for v in np.clip(c * 1.12, 0, 255)]   # +12 %: a copa 3D recebe sombra própria
def tom_copa(rgb, piso=62.0):
    """Copa escura ou em sombra no orto: sobe a luminosidade até o piso e puxa para verde escuro, para não virar volume preto."""
    c = np.array(tom(rgb), float); l = float(c @ [0.299, 0.587, 0.114])
    if l >= piso: return [int(v) for v in c]
    k = 1 - l / piso; c = c * (piso / max(l, 1.0)) * (1 - 0.5 * k) + np.array([48.0, 78.0, 44.0]) * 0.5 * k
    return [int(v) for v in np.clip(c, 0, 255)]

cena = dict(arvores=[[round(f['E'] - X0, 2), round(f['N'] - Y0, 2), round(f['h'], 1), round(f['copa'] / 2, 2), *tom_copa(f['rgb'])] for f in arv],
            volumes=[dict(p=v['pol'], h=v['h'], c=tom(v['rgb'], 0.9, 0.9)) for v in vol])
json.dump(cena, open(os.path.join(WORK, 'entorno.json'), 'w'), separators=(',', ':'))
pt = lambda fs, props: [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [f['E'], f['N']]},
                         'properties': {k: f[k] for k in props}} for f in fs]
json.dump(geojson_pontos('entorno_arvores', pt(arv, ['h', 'copa', 'exg', 'dentro', 'macico'])), open(os.path.join(F1, 'entorno_arvores.geojson'), 'w'))
json.dump(geojson_pontos('entorno_filtrados', pt(filt, ['h', 'copa', 'exg', 'motivo']) + pt(duv, ['h', 'area', 'cor', 'rugosidade_m', 'retangularidade', 'motivo']) +
                         pt([dict(v, motivo='construção confirmada (volume)') for v in vol], ['h', 'area', 'cor', 'rugosidade_m', 'retangularidade', 'motivo'])),
          open(os.path.join(F1, 'entorno_filtrados.geojson'), 'w', encoding='utf-8'), ensure_ascii=False)
from collections import Counter
H = np.array([f['h'] for f in arv]); Dm = np.array([f['copa'] for f in arv])
sem_pol = lambda v: {k: x for k, x in v.items() if k not in ('pol', 'rgb')}
res = dict(arvores=len(arv), arvores_isoladas=sum(1 for f in arv if not f['macico']), arvores_em_macico=sum(1 for f in arv if f['macico']), macicos=macicos,
           cortadas_pelo_limite=cortadas, picos_dentro_da_area=dentro, arvores_dentro_da_area=sum(1 for f in arv if f['dentro']),
           filtrados=dict(Counter(f['motivo'] for f in filt)), construcoes_volume=len(vol), construcoes=[sem_pol(v) for v in vol], duvidas_so_no_orto=[sem_pol(v) for v in duv],
           criterio=dict(cor='cerâmico, claro (metálico) ou azulado no orto', rugosidade_max_m=EST_RUG_MAX, retangularidade_min=EST_RET_MIN, area_min_m2=EST_AREA_MIN,
                         macico_diametro_m=MAC_DIAM, macico_passo_m=MAC_PASSO),
           altura_m=dict(p10=round(float(np.percentile(H, 10)), 1), mediana=round(float(np.median(H)), 1), p90=round(float(np.percentile(H, 90)), 1), max=round(float(H.max()), 1)) if len(H) else None,
           copa_m=dict(p10=round(float(np.percentile(Dm, 10)), 1), mediana=round(float(np.median(Dm)), 1), p90=round(float(np.percentile(Dm, 90)), 1)) if len(Dm) else None)
json.dump(res, open(os.path.join(F1, 'entorno_resumo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))

# ---------- imagem de conferência ----------
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
Wm, Hm = X1 - X0, Y1 - Y0
oo = warp('orto.tif', 0.1, 'average').ReadAsArray()[:3].transpose(1, 2, 0)
fig, ax = plt.subplots(figsize=(16, 16 * Hm / Wm + 1.0)); ax.imshow(oo, extent=(0, Wm, 0, Hm))
ax.contour(np.flipud(chm), levels=[H_MIN], colors='cyan', linewidths=0.7, extent=(0, Wm, 0, Hm))
ax.plot([], [], color='cyan', lw=0.8, label=f'CHM ≥ {H_MIN:.1f} m (MDS − MDT)'.replace('.', ','))
pa = np.array(poligono().exterior.coords); ax.plot(pa[:, 0] - X0, pa[:, 1] - Y0, color='yellow', lw=1.2, label='área de estudo')
for f in arv: ax.add_patch(plt.Circle((f['E'] - X0, f['N'] - Y0), f['copa'] / 2, fill=False, lw=1.1, color='#ff9100' if f['macico'] else '#76ff03'))
ax.plot([], [], 'o', mfc='none', mec='#76ff03', label=f"árvore isolada ({res['arvores_isoladas']})"); ax.plot([], [], 'o', mfc='none', mec='#ff9100', label=f"árvore de maciço ({res['arvores_em_macico']} em {len(macicos)} maciços)")
for k, v in enumerate(vol):
    p = np.array(v['pol'] + [v['pol'][0]]); ax.plot(p[:, 0], p[:, 1], color='red', lw=2, label=f'construção confirmada, volume ({len(vol)})' if k == 0 else None)
    ax.text(p[:, 0].mean(), p[:, 1].min() - 1.2, f"{v['cor']}, {v['h']:.1f} m\nrug. {v['rugosidade_m']:.2f} m, ret. {v['retangularidade']:.2f}".replace('.', ','), color='red', fontsize=8, ha='center', va='top')
for k, v in enumerate(duv):
    p = np.array(v['pol'] + [v['pol'][0]]); ax.plot(p[:, 0], p[:, 1], color='magenta', lw=1.3, ls='--', label=f'dúvida: só no orto, sem volume ({len(duv)})' if k == 0 else None)
    ax.text(p[:, 0].mean(), p[:, 1].min() - 1.0, f"rug. {v['rugosidade_m']:.2f} m, ret. {v['retangularidade']:.2f}".replace('.', ','), color='magenta', fontsize=7, ha='center', va='top')
ax.set_title(f"Conferência do entorno | copa é o padrão; construção só com cor não vegetal + plano ou águas (resíduo ≤ {EST_RUG_MAX} m) + contorno retilíneo (≥ {EST_RET_MIN})".replace('.', ','), fontsize=10)
ax.set_xlim(0, Wm); ax.set_ylim(0, Hm); ax.legend(loc='lower left', fontsize=9, framealpha=0.9); ax.tick_params(labelsize=7)
plt.tight_layout(); plt.savefig(os.path.join(F1, 'conferencia_entorno.png'), dpi=110)
