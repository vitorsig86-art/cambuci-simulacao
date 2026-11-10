# Etapa SAF 2. Grade de plantio (entrelinha x entreplantas) sobre as linhas medidas, cruzada com os
# indivíduos detectados. Em cada posição vazia, testa evidência de planta pequena no orto e no CHM:
#   CHM (0,25 a 0,6 m acima do fundo da linha), cor (ExG acima do fundo), textura (variação de brilho)
#   e sombra (pixels escuros). Fundo = a própria linha de plantio a meia distância entre posições.
# Saídas: fase1/posicoes_estimadas.geojson, fase1/conferencia_posicoes.png, work/grade.json
from saf_comum import *
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

diag = json.load(open(os.path.join(F1, 'diagnostico.json'), encoding='utf-8'))
ESP_L = SAF['espacamento']['entrelinha']; ESP_P = SAF['espacamento']['entreplantas']
az = diag['linhas']['azimute_graus']; t = np.radians(az); ct, st_ = np.cos(t), np.sin(t)
d0, fase = diag['linhas']['grade']['d0'], diag['linhas']['grade']['fase']
perp = lambda E, N: E * ct - N * st_
long_ = lambda E, N: E * st_ + N * ct
volta = lambda dp, dl: (dp * ct + dl * st_, -dp * st_ + dl * ct)

gj, fonte = ler_individuos()
det = [(f['geometry']['coordinates'][0], f['geometry']['coordinates'][1], f['properties']) for f in gj['features']]
DE = np.array([[x, y] for x, y, _ in det])
print('indivíduos de', os.path.relpath(fonte, ROOT), len(det))

pol = poligono(); dentro = pol.buffer(-0.75)
xs, ys = np.array(pol.exterior.coords).T
dps = perp(xs, ys); kmin = int(np.floor((dps.min() - d0 - fase) / ESP_L)) + 1; kmax = int(np.ceil((dps.max() - d0 - fase) / ESP_L)) + 1
Dp, Dl = perp(DE[:, 0], DE[:, 1]), long_(DE[:, 0], DE[:, 1])

# ---------- grade ----------
fase_glob = np.angle(np.exp(2j * np.pi * (Dl % ESP_P) / ESP_P).mean()) / (2 * np.pi) * ESP_P % ESP_P
grade = []
for k in range(kmin, kmax + 1):
    c = d0 + fase + (k - 1) * ESP_L
    sel = np.abs(Dp - c) < 1.2
    if sel.sum() >= 3: c += float(np.clip(np.median(Dp[sel] - c), -0.8, 0.8))     # linha real pode ter leve desvio
    ph = np.angle(np.exp(2j * np.pi * (Dl[sel] % ESP_P) / ESP_P).mean()) / (2 * np.pi) * ESP_P % ESP_P if sel.sum() >= 2 else fase_glob
    L = 400; a = volta(c, Dl.mean() - L); b = volta(c, Dl.mean() + L)
    seg = LineString([a, b]).intersection(dentro)
    for s in getattr(seg, 'geoms', [seg]):
        if s.is_empty or s.length < 0.1: continue
        l0, l1 = sorted(long_(np.array(s.coords)[:, 0], np.array(s.coords)[:, 1]))
        j0 = int(np.ceil((l0 - ph) / ESP_P)); j1 = int(np.floor((l1 - ph) / ESP_P))
        for j in range(j0, j1 + 1):
            E, N = volta(c, ph + j * ESP_P); grade.append([E, N, k])
G = np.array(grade)
print('posições na grade', len(G), 'linhas', len(set(G[:, 2])))

# ---------- cruzamento: cada detectado ocupa no máximo uma posição (mais próxima, até 1,5 m) ----------
tr = cKDTree(G[:, :2]); dd, ii = tr.query(DE, k=3, distance_upper_bound=1.5)
pares = sorted([(dd[a, q], a, ii[a, q]) for a in range(len(DE)) for q in range(3) if np.isfinite(dd[a, q])])
ocup = np.full(len(G), -1); usado = set()
for d, a, g in pares:
    if a in usado or ocup[g] >= 0: continue
    ocup[g] = a; usado.add(a)
fora_grade = [a for a in range(len(DE)) if a not in usado]
print('posições ocupadas por detectados', (ocup >= 0).sum(), '| detectados fora da grade', len(fora_grade))

# ---------- evidência ----------
ro = 0.1; rc = 0.25
O = warp('orto.tif', ro, 'average').ReadAsArray()[:3].astype(float)
S = O.sum(0) + 1e-6; EXG = 2 * O[1] / S - O[0] / S - O[2] / S; BR = O.mean(0)
CHMb, _ = chm_grade(rc)
def disco(E, N, r, res, arr):
    cx, cy = (E - X0) / res, (Y1 - N) / res; R = r / res
    i0, i1 = int(max(cy - R, 0)), int(min(cy + R + 1, arr.shape[-2])); j0, j1 = int(max(cx - R, 0)), int(min(cx + R + 1, arr.shape[-1]))
    yy, xx = np.mgrid[i0:i1, j0:j1]; m = (yy + 0.5 - cy) ** 2 + (xx + 0.5 - cx) ** 2 <= R * R
    return arr[i0:i1, j0:j1][m]
def evidencia(E, N):
    dl = np.array([ESP_P / 2 * st_, ESP_P / 2 * ct])                 # meio caminho ao longo da linha
    fundos = [(E + s * dl[0], N + s * dl[1]) for s in (-1, 1)]
    ch = disco(E, N, 0.8, rc, CHMb); chb = np.median(np.concatenate([disco(x, y, 0.6, rc, CHMb) for x, y in fundos]))
    g = disco(E, N, 0.8, ro, EXG); gb = np.concatenate([disco(x, y, 0.6, ro, EXG) for x, y in fundos])
    b = disco(E, N, 0.8, ro, BR); bb = np.concatenate([disco(x, y, 0.6, ro, BR) for x, y in fundos])
    alt = ch.max() - max(chb, 0)
    e_chm = 1.0 if ch.max() >= 0.6 else float(np.clip((alt - 0.15) / 0.3, 0, 1))
    e_cor = float(np.clip((g.mean() - gb.mean() - 0.02) / 0.06, 0, 1))
    e_tex = float(np.clip((b.std() / (bb.std() + 1e-6) - 1.1) / 0.6, 0, 1))
    e_som = float(np.clip(((b < 0.65 * np.median(bb)).mean() - 0.05) / 0.15, 0, 1))
    sc = 0.35 * e_chm + 0.30 * e_cor + 0.15 * e_tex + 0.20 * e_som
    return round(sc, 3), dict(chm=round(e_chm, 2), cor=round(e_cor, 2), textura=round(e_tex, 2), sombra=round(e_som, 2), chm_max_m=round(float(ch.max()), 2))

# controle negativo primeiro: meio da entrelinha (sem plantio). Limiares = p90 (média) e p97 (alta) desse controle
rng = np.random.default_rng(1); neg_ctrl = []
for g in rng.choice(len(G), 400, replace=False):
    E, N = G[g, 0] + ESP_L / 2 * ct, G[g, 1] - ESP_L / 2 * st_
    if pol.buffer(-1).contains(Point(E, N)): neg_ctrl.append(evidencia(E, N)[0])
LIM_M, LIM_A = float(np.percentile(neg_ctrl, 90)), float(np.percentile(neg_ctrl, 97))
print("limiares de evidência: média", round(LIM_M, 3), "alta", round(LIM_A, 3))
classe = lambda s: "alta" if s >= LIM_A else ("media" if s >= LIM_M else "sem_evidencia")
vazias = np.where(ocup < 0)[0]
est = []
for n, g in enumerate(vazias):
    s, comp = evidencia(G[g, 0], G[g, 1])
    est.append(dict(id=n + 1, E=G[g, 0], N=G[g, 1], linha=int(G[g, 2]), evidencia=s, confianca=classe(s), **comp))
# controles: positivo = posições ocupadas por detectados; negativo = meio da entrelinha (sem plantio)
pos_ctrl = [evidencia(G[g, 0], G[g, 1])[0] for g in np.where(ocup >= 0)[0]]
cnt = {c: sum(e['confianca'] == c for e in est) for c in ['alta', 'media', 'sem_evidencia']}
res = dict(posicoes_grade=int(len(G)), linhas=int(len(set(G[:, 2]))), ocupadas_por_detectados=int((ocup >= 0).sum()),
           detectados_total=len(det), detectados_fora_da_grade=len(fora_grade), vazias=int(len(vazias)),
           estimadas_com_evidencia=cnt['alta'] + cnt['media'], estimadas_alta=cnt['alta'], estimadas_media=cnt['media'],
           sem_evidencia=cnt['sem_evidencia'],
           controle_positivo_pct_com_evidencia=round(100 * np.mean(np.array(pos_ctrl) >= LIM_M), 1), limiar_media=round(LIM_M, 3), limiar_alta=round(LIM_A, 3),
           controle_negativo_pct_com_evidencia=round(100 * np.mean(np.array(neg_ctrl) >= LIM_M), 1), n_controle_negativo=len(neg_ctrl),
           densidade_por_ha={'conservador': round(len(det) / (pol.area / 1e4)), 'provavel': round((len(det) + cnt['alta'] + cnt['media']) / (pol.area / 1e4)),
                             'otimista': round((len(det) + len(vazias)) / (pol.area / 1e4))})
print(json.dumps(res, ensure_ascii=False, indent=1))

feats = [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(e['E'], 2), round(e['N'], 2)]},
          'properties': {k: e[k] for k in ['id', 'linha', 'evidencia', 'confianca', 'chm', 'cor', 'textura', 'sombra', 'chm_max_m']}} for e in est]
json.dump(geojson_pontos('posicoes_estimadas', feats), open(os.path.join(F1, 'posicoes_estimadas.geojson'), 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(dict(resumo=res, az=az, grade=[[round(x, 2), round(y, 2), int(k), int(o)] for (x, y, k), o in zip(G, ocup)],
               estimadas=[[round(e['E'], 2), round(e['N'], 2), e['evidencia'], e['confianca']] for e in est], fora_grade=fora_grade),
          open(os.path.join(WORK, 'grade.json'), 'w', encoding='utf-8'))
d = json.load(open(os.path.join(F1, 'diagnostico.json'), encoding='utf-8')); d['posicoes'] = res
json.dump(d, open(os.path.join(F1, 'diagnostico.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- imagem de conferência ----------
Mo = mask(ro); yy_, xx_ = np.nonzero(Mo)
y0, y1_, x0, x1_ = max(yy_.min() - 40, 0), yy_.max() + 40, max(xx_.min() - 40, 0), xx_.max() + 40
fig, ax = plt.subplots(figsize=(13, 13 * (y1_ - y0) / (x1_ - x0)))
ax.imshow(np.clip(O[:, y0:y1_, x0:x1_].transpose(1, 2, 0) / 255, 0, 1), extent=(X0 + x0 * ro, X0 + x1_ * ro, Y1 - y1_ * ro, Y1 - y0 * ro))
ax.plot(*pol.exterior.xy, color='yellow', lw=1.5)
ax.scatter(DE[:, 0], DE[:, 1], s=14, facecolors='none', edgecolors='white', linewidths=0.9, label=f'detectadas ({len(det)})')
for c, cor, mk, lab in [('alta', '#00e5ff', 'o', 'estimada, evidência alta'), ('media', '#ffb000', 'o', 'estimada, evidência média'),
                        ('sem_evidencia', '#ff3b30', 'x', 'posição vazia, sem evidência')]:
    sel = [e for e in est if e['confianca'] == c]
    ax.scatter([e['E'] for e in sel], [e['N'] for e in sel], s=12 if mk == 'o' else 10, c=cor, marker=mk, linewidths=0.8, label=f'{lab} ({len(sel)})')
ax.set_xlim(X0 + x0 * ro, X0 + x1_ * ro); ax.set_ylim(Y1 - y1_ * ro, Y1 - y0 * ro)
ax.legend(loc='lower right', fontsize=9, framealpha=0.85); ax.tick_params(labelsize=7)
ax.set_title(f"Grade {ESP_L:g} x {ESP_P:g} m: {len(G)} posições | {(ocup >= 0).sum()} ocupadas por detectadas | "
             f"{cnt['alta'] + cnt['media']} estimadas com evidência | {cnt['sem_evidencia']} sem evidência", fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(F1, 'conferencia_posicoes.png'), dpi=110)
