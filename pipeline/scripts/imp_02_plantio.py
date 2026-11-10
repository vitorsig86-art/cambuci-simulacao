# Etapa IMP 3. Desenho do plantio: café e banana sobre as linhas de cultivo, renque duplo de grevílea nas bordas expostas ao vento,
# corredor das estradas sem planta, faixa protegida e faixa de competição. Não redesenha linha nem estrada.
# Saídas (raiz): pontos_plantio.geojson, quebra_vento.geojson (linhas dos renques, para ajustar), quebra_vento_arvores.geojson
# Saídas: fase2/conferencia_plantio.png, fase2/plantio_resumo.json, work/plantio.json
# gerar(cafe_m, banana_m) é reutilizada pela sensibilidade de densidade do modelo.
from saf_comum import *
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point, shape, Polygon
from shapely.ops import unary_union

PL = CFG['plantio']; QV = CFG['quebra_vento']; VE = CFG['vento']; ES = CFG.get('estradas') or {}
EST = json.load(open(os.path.join(WORK, 'estradas.json'), encoding='utf-8'))
AG = json.load(open(os.path.join(WORK, 'agua.json'), encoding='utf-8'))
GR = np.load(os.path.join(WORK, 'agua_grades.npz')); ZS = GR['z']; HH_, WW_ = ZS.shape
zloc = lambda x, y: ndi.map_coordinates(ZS, [HH_ - np.asarray(y, float) - 0.5, np.asarray(x, float) - 0.5], order=1, mode='nearest')
AREA = shape({'type': 'Polygon', 'coordinates': [[[x - X0, y - Y0] for x, y in poligono().exterior.coords]]}); AREA_HA = AREA.area / 1e4
EIXOS = [LineString(e) for e in EST['eixos']]; MEIA = EST['meia'] or 0.0
COR = unary_union([e.buffer(MEIA) for e in EIXOS]) if EIXOS else Polygon()         # corredor das estradas: largura + faixa livre
PP = AREA.difference(COR); PP = max(PP.geoms, key=lambda g: g.area) if PP.geom_type == 'MultiPolygon' else PP   # área plantável
EXCL = np.load(os.path.join(WORK, 'excl_arvores.npy'))                              # copas existentes com folga (grade 0,25 m)
def em_arvore(x, y):
    r_, c_ = int((Y1 - Y0 - y) / 0.25), int(x / 0.25)
    return bool(EXCL[r_, c_]) if 0 <= r_ < EXCL.shape[0] and 0 <= c_ < EXCL.shape[1] else False
LIN = [f for f in json.load(open(os.path.join(ROOT, 'fase1b', 'linhas_tratadas.geojson'), encoding='utf-8'))['features'] if not f['properties'].get('curta')]
AZ = float(VE['azimute_de_graus']); U = np.array([np.sin(np.radians(AZ)), np.cos(np.radians(AZ))])    # aponta para de onde vem o vento
DREN = unary_union([LineString(t['pts']) for t in AG['trechos'] if len(t['pts']) > 1]) if AG['trechos'] else None

# ---------------- quebra-vento ----------------
DT = float(QV['entre_arvores_m']); DR = float(QV['entre_renques_m']); REC0 = float(QV['recuo_borda_m']); NR = int(QV['renques'])
def arvores_da_linha(L, renque):
    n = int((L.length - (DT / 2 if renque % 2 == 0 else 0)) // DT) + 1; s0 = DT / 2 if renque % 2 == 0 else 0      # filas desencontradas
    return [L.interpolate(s0 + k * DT) for k in range(max(n, 0)) if s0 + k * DT <= L.length + 1e-6]
aj = os.path.join(ROOT, QV.get('ajustado', 'quebra_vento_ajustado.geojson'))
QV_ORIGEM = 'proposta do pipeline'
renques = []          # [{renque, trecho, geo (LineString local), pts [(x, y)]}]
cortes_qv = dict(drenagem=0, arvore_existente=0, nao_exposta=0)
if os.path.exists(aj):
    QV_ORIGEM = os.path.basename(aj) + ' (ajustado pelo usuário)'
    for k, f in enumerate(json.load(open(aj, encoding='utf-8'))['features']):
        if f['geometry']['type'] != 'LineString': continue
        L = LineString([(c[0] - X0, c[1] - Y0) for c in f['geometry']['coordinates']]); rq = int(f['properties'].get('renque', 1))
        pts = [(p.x, p.y) for p in arvores_da_linha(L, rq) if not COR.contains(p)]
        renques.append(dict(renque=rq, trecho=k + 1, geo=L, pts=pts))
else:
    ext = PP.exterior
    for j in range(NR):
        anel = PP.buffer(-(REC0 + j * DR)); anel = max(anel.geoms, key=lambda g: g.area) if anel.geom_type == 'MultiPolygon' else anel
        ring = LineString(anel.exterior.coords); atual = []; grupos = []
        for p in arvores_da_linha(ring, j + 1):
            q = ext.interpolate(ext.project(p)); n = np.array([q.x - p.x, q.y - p.y]); n /= (np.hypot(*n) + 1e-9)
            ok = True
            if float(n @ U) < float(QV['exposicao_cos_min']): ok = False; cortes_qv['nao_exposta'] += 1
            elif DREN is not None and DREN.distance(p) < float(QV['folga_drenagem_m']): ok = False; cortes_qv['drenagem'] += 1
            elif em_arvore(p.x, p.y): ok = False; cortes_qv['arvore_existente'] += 1
            if ok: atual.append((p.x, p.y))
            elif atual: grupos.append(atual); atual = []
        if atual: grupos.append(atual)
        if len(grupos) > 1 and np.hypot(grupos[0][0][0] - grupos[-1][-1][0], grupos[0][0][1] - grupos[-1][-1][1]) < DT * 1.2: grupos[0] = grupos.pop() + grupos[0]   # anel fechado
        for g in grupos:
            if len(g) >= 2: renques.append(dict(renque=j + 1, trecho=len(renques) + 1, geo=LineString(g), pts=g))
QVT = np.array([p for r_ in renques for p in r_['pts']]).reshape(-1, 2)              # árvores do quebra-vento (local)
QVR = np.array([r_['renque'] for r_ in renques for _ in r_['pts']], int)
SEG = np.array([[*a, *b] for r_ in renques for a, b in zip(r_['pts'][:-1], r_['pts'][1:])]).reshape(-1, 4)   # barreira = segmentos entre árvores vizinhas
QV_GEO = unary_union([r_['geo'] for r_ in renques]) if renques else None

def protecao(x, y):
    """Para cada ponto: distância s (m) contra o vento até o renque e desnível dz = cota do ponto − cota do renque (m).
    Protegido quando s <= k × (H − dz): renque morro abaixo protege menos. s = inf se não há renque a barlavento."""
    x = np.asarray(x, float); y = np.asarray(y, float); s_min = np.full(x.shape, np.inf); dz = np.zeros(x.shape)
    if not len(SEG): return s_min, dz
    zp = zloc(x, y)
    for ax, ay, bx, by in SEG:
        ex, ey = bx - ax, by - ay; den = U[0] * ey - U[1] * ex
        if abs(den) < 1e-9: continue
        s = ((ax - x) * ey - (ay - y) * ex) / den; t = ((ax - x) * U[1] - (ay - y) * U[0]) / den
        m = (s > 0) & (t >= 0) & (t <= 1) & (s < s_min)
        if m.any(): s_min[m] = s[m]; dz[m] = zp[m] - zloc(ax + t[m] * ex, ay + t[m] * ey)
    return s_min, dz
def dist_renque(x, y):
    return cKDTree(QVT).query(np.c_[x, y])[0] if len(QVT) else np.full(np.shape(x), np.inf)

# ---------------- pontos de plantio ----------------
def gerar(cafe_m=None, banana_m=None, sem_qv=False):
    cm = float(cafe_m or PL['cafe_m']); bm = float(banana_m or PL['banana_m']) if banana_m != 0 else 0
    nb = max(2, int(round(bm / cm))) if bm else 0; alt = int(round(float(PL.get('alterna_m', bm / 2)) / cm)) if bm else 0
    pts = []; cort = dict(estrada=dict(cafe=0, banana=0), quebra_vento=dict(cafe=0, banana=0), arvore_existente=dict(cafe=0, banana=0)); bruto = dict(cafe=0, banana=0)
    recuo = float(QV['recuo_cafe_m'])
    for ordem, f in enumerate(sorted(LIN, key=lambda f: f['properties']['linha'])):
        co = [(x - X0, y - Y0) for x, y in f['geometry']['coordinates']]
        if co[0][0] > co[-1][0]: co = co[::-1]                                       # todas de oeste para leste: a alternância fica alinhada
        L = LineString(co); lid = f['properties']['linha']; k = 0; pos = 0
        while cm / 2 + k * cm <= L.length:
            s = cm / 2 + k * cm; p = L.interpolate(s); esp = 'banana' if nb and (k + (alt if ordem % 2 else 0)) % nb == 0 else 'cafe'; k += 1
            bruto[esp] += 1
            if COR.contains(p): cort['estrada'][esp] += 1; continue
            if not sem_qv and len(QVT) and np.hypot(QVT[:, 0] - p.x, QVT[:, 1] - p.y).min() < recuo: cort['quebra_vento'][esp] += 1; continue
            if em_arvore(p.x, p.y): cort['arvore_existente'][esp] += 1; continue
            pos += 1; pts.append(dict(x=p.x, y=p.y, esp=esp, linha=lid, pos=pos, dist_m=round(s, 2)))
    x = np.array([p['x'] for p in pts]); y = np.array([p['y'] for p in pts]); s, dz = protecao(x, y); dq = dist_renque(x, y)
    for p, a, b, c in zip(pts, s, dz, dq): p['s'] = float(a) if np.isfinite(a) and not sem_qv else None; p['dz'] = float(b); p['dq'] = 999.0 if sem_qv else float(min(c, 999))
    for k, (qx, qy) in enumerate([] if sem_qv else QVT): pts.append(dict(x=float(qx), y=float(qy), esp='grevilea', linha=0, renque=int(QVR[k]), pos=k + 1, dist_m=None, s=None, dz=0.0, dq=0.0))
    n = {e: sum(p['esp'] == e for p in pts) for e in ('cafe', 'banana', 'grevilea')}
    res = dict(cafe_m=cm, banana_m=bm, alterna_m=alt * cm, area_ha=round(AREA_HA, 4), area_plantavel_ha=round(PP.area / 1e4, 4), corredor_estradas_na_area_m2=round(AREA.intersection(COR).area, 0) if EIXOS else None,
               linhas=len(LIN), comprimento_linhas_m=round(sum(LineString(f['geometry']['coordinates']).length for f in LIN), 1),
               antes_dos_cortes=bruto, cortes=cort, plantas=n, por_ha={e: round(v / AREA_HA) for e, v in n.items()},
               por_ha_plantavel={e: round(v / (PP.area / 1e4)) for e, v in n.items()})
    return pts, res

if __name__ == '__main__':
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    F2 = os.path.join(ROOT, 'fase2'); os.makedirs(F2, exist_ok=True)
    pts, res = gerar()
    # grades de 1 m para o site: altura mínima do renque que protege cada célula (por cenário) e distância ao renque
    Wg, Hg = int(round(X1 - X0)), int(round(Y1 - Y0)); gx_, gy_ = np.meshgrid(np.arange(Wg) + 0.5, Hg - np.arange(Hg) - 0.5)
    IN = mask(1.0); s, dz = protecao(gx_.ravel(), gy_.ravel()); s = s.reshape(Hg, Wg); dz = dz.reshape(Hg, Wg)
    dq = dist_renque(gx_.ravel(), gy_.ravel()).reshape(Hg, Wg)
    b64 = lambda a: __import__('base64').b64encode(np.ascontiguousarray(a).tobytes()).decode()
    grades = {}
    for nv, k in QV['protecao_alturas'].items():
        hmin = np.where(np.isfinite(s) & IN, np.maximum(s / k + dz, 0), 99); grades[nv] = b64(np.clip(np.round(hmin * 10), 0, 255).astype(np.uint8))
    grades['dq'] = b64(np.where(IN, np.clip(np.round(dq * 4), 0, 255), 255).astype(np.uint8)); grades['nx'] = Wg; grades['ny'] = Hg
    # faixa protegida e de competição por altura do renque (tabela de conferência)
    cafe = [p for p in pts if p['esp'] == 'cafe']; S_ = np.array([p['s'] if p['s'] is not None else np.inf for p in cafe]); DZ = np.array([p['dz'] for p in cafe]); DQ = np.array([p['dq'] for p in cafe])
    tab = []
    for Hq in (2, 4, 6, 8, 10, 12, 15, 18):
        lin = dict(altura_m=Hq)
        for nv in 'cpo':
            k = QV['protecao_alturas'][nv]; fc = QV['competicao_alturas'][nv]; cap = QV['competicao_max_m'][nv]
            lin[nv] = dict(cafe_protegido_pct=round(100 * float((S_ <= k * (Hq - DZ)).mean()), 1), area_protegida_pct=round(100 * float(((s <= k * (Hq - dz)) & IN).sum() / IN.sum()), 1),
                           faixa_competicao_m=round(min(fc * Hq, cap), 1), cafe_na_competicao_pct=round(100 * float((DQ <= min(fc * Hq, cap)).mean()), 1))
        tab.append(lin)
    qv = dict(origem=QV_ORIGEM, especie=QV['especie'], azimute_vento_graus=AZ, fonte_vento=VE['fonte'], renques=NR if QV_ORIGEM.startswith('proposta') else len({r_['renque'] for r_ in renques}),
              trechos=len(renques), arvores=int(len(QVT)), comprimento_m=round(sum(r_['geo'].length for r_ in renques), 1),
              comprimento_por_renque_m={str(j): round(sum(r_['geo'].length for r_ in renques if r_['renque'] == j), 1) for j in sorted({r_['renque'] for r_ in renques})},
              entre_arvores_m=DT, entre_renques_m=DR, cortes=cortes_qv, abertura_estrada_m=2 * MEIA if EIXOS else None,
              perimetro_exposto_pct=round(100 * sum(r_['geo'].length for r_ in renques if r_['renque'] == 1) / AREA.length, 0),
              angulo_com_o_vento='renque ideal fica a 90° do vento; aqui segue a borda, a até 60° da perpendicular',
              tabela=tab, nota='proteção = n × (altura do renque − desnível do ponto acima do pé do renque). Em encosta, renque morro abaixo protege menos')
    qv['bordas_usadas'] = sorted({['norte','nordeste','leste','sudeste','sul','sudoeste','oeste','noroeste'][int(round((np.degrees(np.arctan2((PP.exterior.interpolate(PP.exterior.project(Point(x,y))).x-x),(PP.exterior.interpolate(PP.exterior.project(Point(x,y))).y-y)))+360)%360/45))%8] for x,y in QVT})
    qv['status'] = 'hipótese demonstrativa; vento de 45° não medido'
    res['quebra_vento'] = {k: v for k, v in qv.items() if k != 'tabela'}; res['quebra_vento_tabela'] = tab
    res['sem_quebra_vento'] = gerar(sem_qv=True)[1]      # segundo desenho: café e banana nas linhas inteiras, sem renque
    glob = lambda x, y: [round(x + X0, 2), round(y + Y0, 2)]
    json.dump(geojson_pontos('pontos_plantio', [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': glob(p['x'], p['y'])},
              'properties': {'linha': p['linha'], 'especie': p['esp'], 'posicao': p['pos'], 'dist_na_linha_m': p['dist_m'], **({'renque': p['renque']} if p['esp'] == 'grevilea' else {})}} for p in pts]),
              open(os.path.join(ROOT, 'pontos_plantio.geojson'), 'w', encoding='utf-8'))
    json.dump(geojson_pontos('quebra_vento', [{'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [glob(*c) for c in r_['geo'].coords]},
              'properties': {'renque': r_['renque'], 'trecho': r_['trecho'], 'arvores': len(r_['pts']), 'comp_m': round(r_['geo'].length, 1), 'especie': QV['especie'], 'entre_arvores_m': DT,
                             'obs': 'ajuste os vértices e salve como quebra_vento_ajustado.geojson; as árvores são recolocadas a cada entre_arvores_m'}} for r_ in renques]),
              open(os.path.join(ROOT, 'quebra_vento.geojson'), 'w', encoding='utf-8'))
    json.dump(geojson_pontos('quebra_vento_arvores', [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': glob(x, y)}, 'properties': {'renque': int(rq)}} for (x, y), rq in zip(QVT, QVR)]),
              open(os.path.join(ROOT, 'quebra_vento_arvores.geojson'), 'w', encoding='utf-8'))
    json.dump(dict(resumo=res, grades=grades, renques=[dict(renque=r_['renque'], pts=[[round(a, 2), round(b, 2)] for a, b in r_['pts']]) for r_ in renques],
                   vento=dict(az=AZ, ux=float(U[0]), uy=float(U[1])), corredor=[[[round(a, 2), round(b, 2)] for a, b in g.exterior.coords] for g in (COR.geoms if COR.geom_type == 'MultiPolygon' else [COR]) if not g.is_empty]),
              open(os.path.join(WORK, 'plantio.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(res, open(os.path.join(F2, 'plantio_resumo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'quebra_vento_tabela'}, ensure_ascii=False, indent=1))
    print('sem quebra-vento:', res['sem_quebra_vento']['plantas'], '| com:', res['plantas'])
    for l in tab: print(l['altura_m'], 'm:', {nv: (l[nv]['cafe_protegido_pct'], l[nv]['faixa_competicao_m'], l[nv]['cafe_na_competicao_pct']) for nv in 'cpo'})

    # ---------- imagem de conferência ----------
    ro = 0.1; oo = warp('orto.tif', ro, 'average').ReadAsArray()[:3].transpose(1, 2, 0)
    fig, ax = plt.subplots(figsize=(15, 15 * (Y1 - Y0) / (X1 - X0) + 1.2)); ax.imshow(oo, extent=(0, X1 - X0, 0, Y1 - Y0))
    ax.plot(*AREA.exterior.xy, color='yellow', lw=1.6, label=f'área de estudo ({AREA_HA:.2f} ha)'.replace('.', ','))
    for g in (COR.geoms if COR.geom_type == 'MultiPolygon' else [COR]): ax.fill(*g.exterior.xy, color='#ff7043', alpha=0.25)
    for k, e in enumerate(EIXOS): ax.plot(*e.xy, color='#ff7043', lw=1.5, label=f'estrada: eixo e corredor sem planta ({2 * MEIA:.0f} m)' if k == 0 else None)
    for k, f in enumerate(LIN): c = np.array(f['geometry']['coordinates']); ax.plot(c[:, 0] - X0, c[:, 1] - Y0, color='white', lw=0.5, alpha=0.7, label=f'linhas de cultivo ({len(LIN)})' if k == 0 else None)
    for k, t in enumerate(AG['trechos']): c = np.array(t['pts']); ax.plot(c[:, 0], c[:, 1], color='#29b6f6', lw=2, label='drenagem simulada' if k == 0 else None)
    if EST['cruz']: ax.scatter([c['x'] for c in EST['cruz']], [c['y'] for c in EST['cruz']], marker='X', s=120, c='#01579b', edgecolors='white', label=f"fluxo cruza a estrada ({len(EST['cruz'])})", zorder=6)
    sem = [p for p in EST['pontas'] if p['situacao'] == 'sem cabeceira']
    if sem: ax.scatter([p['x'] for p in sem], [p['y'] for p in sem], marker='|', s=90, c='magenta', label=f'ponta de linha sem cabeceira ({len(sem)})', zorder=6)
    n = res['plantas']; h = res['por_ha']; sel = lambda e: np.array([[p['x'], p['y']] for p in pts if p['esp'] == e]).reshape(-1, 2)
    c_ = sel('cafe'); ax.scatter(c_[:, 0], c_[:, 1], s=3, c='#b71c1c', label=f"café: {n['cafe']} ({h['cafe']}/ha)")
    b_ = sel('banana'); ax.scatter(b_[:, 0], b_[:, 1], s=34, c='#ffeb3b', edgecolors='black', linewidths=0.5, label=f"banana: {n['banana']} ({h['banana']}/ha)", zorder=5)
    g_ = sel('grevilea'); ax.scatter(g_[:, 0], g_[:, 1], s=46, c='#00e676', marker='^', edgecolors='black', linewidths=0.5, label=f"grevílea: {n['grevilea']} ({h['grevilea']}/ha)", zorder=5)
    cxy = (X1 - X0 - 12, Y1 - Y0 - 12); ax.annotate('', xy=(cxy[0] - U[0] * 9, cxy[1] - U[1] * 9), xytext=cxy, arrowprops=dict(color='cyan', width=3, headwidth=11))
    ax.text(cxy[0] - 1, cxy[1] + 1.5, f'vento dominante\n(premissa, de {AZ:.0f}°)', color='cyan', fontsize=9, ha='center')
    ct = res['cortes']
    ax.set_title(f"Conferência do plantio | café a cada {res['cafe_m']} m, banana a cada {res['banana_m']:.0f} m alternada, grevílea em renque duplo a cada {DT:.0f} m\n"
                 f"vias indisponíveis; junto ao quebra-vento: {ct['quebra_vento']['cafe']} cafés e {ct['quebra_vento']['banana']} bananas"
                 f" | coordenadas locais em m (E − {X0:.1f}, N − {Y0:.1f})".replace('.', ','), fontsize=10)
    ax.set_xlim(0, X1 - X0); ax.set_ylim(0, Y1 - Y0); ax.legend(loc='lower left', fontsize=9, framealpha=0.9); ax.tick_params(labelsize=7)
    plt.tight_layout(); plt.savefig(os.path.join(F2, 'conferencia_plantio.png'), dpi=120)
