# Etapa IMP 2e. Estradas: eixo, largura, perfil longitudinal, água ao longo da pista, cruzamentos com a drenagem simulada,
# linhas de cultivo que cruzam ou chegam na estrada, cabeceira de manobra e distância das linhas até a estrada (logística).
# Só diagnóstico: não redesenha estrada nem linha. Depende da etapa de água (work/agua_grades.npz, work/agua.json).
# Saídas: work/estradas.json (site e plantio), fase1/estradas_resumo.json, fase1/estradas_eixo.geojson
from saf_comum import *
from scipy import ndimage as ndi
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union

ES = CFG.get('estradas') or {}; PL = CFG['plantio']
LARG = float(ES.get('largura_m', 4.0)); LIVRE = float(ES.get('faixa_livre_m', 2.0)); TR = float(ES.get('trecho_perfil_m', 10))
GC = float(ES.get('greide_critico_pct', 8)); AC = float(ES.get('acumulacao_critica_m2', 100)); CMIN = float(ES.get('cruzamento_min_m2', 100))
CAB = float(PL.get('cabeceira_min_m', 3.0)); MEIA = LARG / 2 + LIVRE          # meia largura do corredor sem planta
arq = CFG['dados'].get('estradas')
if not arq or not os.path.exists(caminho(arq)):
    cand = [f for f in os.listdir(D) if f.lower().endswith('.geojson') and ('estrada' in f.lower() or 'via' in f.lower() or 'road' in f.lower())]
    arq = cand[0] if cand else None
G = np.load(os.path.join(WORK, 'agua_grades.npz')); ACC, Fz, zs = G['ACC'], G['F'], G['z']; Hh, Ww = ACC.shape
AG = json.load(open(os.path.join(WORK, 'agua.json'), encoding='utf-8'))
am = lambda A_, x, y, o=1: ndi.map_coordinates(A_, [Hh - np.asarray(y, float) - 0.5, np.asarray(x, float) - 0.5], order=o, mode='nearest')   # x, y locais
area = poligono(); areaL = shape({'type': 'Polygon', 'coordinates': [[[x - X0, y - Y0] for x, y in area.exterior.coords]]})

def eixo_de_poligono(pol):
    """Eixo de um polígono comprido: parte o anel nos dois vértices mais distantes e tira a média dos dois lados."""
    c = np.array(pol.exterior.coords)[:-1]; d = np.hypot(c[:, None, 0] - c[None, :, 0], c[:, None, 1] - c[None, :, 1])
    i, j = np.unravel_index(d.argmax(), d.shape); i, j = min(i, j), max(i, j)
    A = LineString(c[i:j + 1]); B = LineString(np.vstack([c[j:], c[:i + 1]])[::-1])
    n = max(8, int(A.length / 2))
    return LineString([((A.interpolate(k / n, normalized=True).x + B.interpolate(k / n, normalized=True).x) / 2,
                        (A.interpolate(k / n, normalized=True).y + B.interpolate(k / n, normalized=True).y) / 2) for k in range(n + 1)])

res = dict(arquivo=arq, largura_assumida_m=LARG, faixa_livre_m=LIVRE, corredor_sem_planta_m=2 * MEIA, estradas=[])
site = dict(largura=LARG, meia=MEIA, eixos=[], perfil=[], agua=[], cruz=[], linhas=[])
eixos = []
if arq:
    J = json.load(open(caminho(arq), encoding='utf-8'))
    res['crs'] = (J.get('crs') or {}).get('properties', {}).get('name'); gs = [shape(f['geometry']) for f in J['features']]
    res['extensao'] = [round(v, 2) for v in unary_union(gs).bounds]; res['tipo'] = sorted({g.geom_type for g in gs})
    for k, g in enumerate(gs):
        partes = list(g.geoms) if g.geom_type.startswith('Multi') else [g]
        for p in partes:
            if p.geom_type == 'Polygon': ex = eixo_de_poligono(p); larg_des = p.area / max(ex.length, 1)
            else: ex = LineString([c[:2] for c in p.coords]); larg_des = None
            eixos.append(dict(id=len(eixos) + 1, geo=ex, larg_des=larg_des))
feats = []
for e in eixos:
    L = LineString([(x - X0, y - Y0) for x, y in e['geo'].coords]); e['loc'] = L; n = max(2, int(round(L.length)))
    S = np.linspace(0, L.length, n + 1); P_ = [L.interpolate(s) for s in S]; x = np.array([p.x for p in P_]); y = np.array([p.y for p in P_])
    z = am(zs, x, y); tx = np.gradient(x, S); ty = np.gradient(y, S); tn = np.hypot(tx, ty) + 1e-9; tx /= tn; ty /= tn
    greide = np.abs(np.gradient(ndi.gaussian_filter1d(z, 2), S)) * 100
    # acumulação na pista: maior valor em 5 pontos atravessando a largura assumida
    acc = np.max([am(ACC, x - ty * o, y + tx * o, 0) for o in np.linspace(-LARG / 2, LARG / 2, 5)], axis=0)
    # declive transversal: se a pista cai para um lado, a água sai; se o greide domina, ela corre na pista
    zt = (am(zs, x - ty * LARG / 2, y + tx * LARG / 2) - am(zs, x + ty * LARG / 2, y - tx * LARG / 2)) / LARG * 100
    trechos = []
    for a in np.arange(0, L.length, TR):
        m = (S >= a) & (S <= min(a + TR, L.length))
        if m.sum() < 2: continue
        dz = float(z[m][-1] - z[m][0]); comp = float(S[m][-1] - S[m][0])
        trechos.append(dict(estrada=e['id'], de_m=round(float(a)), ate_m=round(float(S[m][-1])), decl_pct=round(dz / comp * 100, 1), cota_ini=round(float(z[m][0]), 1),
                            cota_fim=round(float(z[m][-1]), 1), acc_max_m2=round(float(acc[m].max())), transversal_pct=round(float(np.median(np.abs(zt[m]))), 1),
                            dentro_da_area=bool(areaL.buffer(MEIA).contains(Point(float(x[m].mean()), float(y[m].mean())))),
                            xy=[round(float(x[m].mean()), 1), round(float(y[m].mean()), 1)]))
    # água ao longo da pista: greide alto e acumulação alta juntos, em trecho contínuo de 5 m ou mais
    crit = (greide >= GC) & (acc >= AC); runs = []; lab, nl = ndi.label(crit)
    for q in range(1, nl + 1):
        ii = np.nonzero(lab == q)[0]
        if S[ii[-1]] - S[ii[0]] >= 5:
            runs.append(dict(estrada=e['id'], de_m=round(float(S[ii[0]])), ate_m=round(float(S[ii[-1]])), comp_m=round(float(S[ii[-1]] - S[ii[0]]), 1),
                             greide_pct=round(float(greide[ii].mean()), 1), acc_max_m2=round(float(acc[ii].max())), pts=[[round(float(x[i]), 2), round(float(y[i]), 2)] for i in ii]))
    # cruzamentos: caminhos de fluxo que atravessam a pista (máximos locais de acumulação ao longo do eixo) e trechos da rede
    cr = []
    pk = (acc >= CMIN) & (acc == ndi.maximum_filter1d(acc, 9))
    lab, nl = ndi.label(pk)
    for q in range(1, nl + 1):
        i = int(np.nonzero(lab == q)[0].mean())
        na_rede = any(LineString(t['pts']).distance(Point(float(x[i]), float(y[i]))) < LARG for t in AG['trechos'] if len(t['pts']) > 1)
        cr.append(dict(estrada=e['id'], dist_m=round(float(S[i])), x=round(float(x[i]), 1), y=round(float(y[i]), 1), E=round(float(x[i]) + X0, 1), N=round(float(y[i]) + Y0, 1),
                       area_contribuinte_m2=round(float(acc[i])), ha=round(float(acc[i]) / 1e4, 4), greide_pct=round(float(greide[i]), 1), na_rede=bool(na_rede)))
    e.update(S=S, x=x, y=y, z=z)
    decl = np.array([abs(t['decl_pct']) for t in trechos])
    res['estradas'].append(dict(id=e['id'], comprimento_m=round(L.length, 1), largura_desenhada_m=round(e['larg_des'], 2) if e['larg_des'] else None,
                                cota_min=round(float(z.min()), 1), cota_max=round(float(z.max()), 1), desnivel_m=round(float(z.max() - z.min()), 1),
                                decl_media_pct=round(float(decl.mean()), 1), decl_max_pct=round(float(decl.max()), 1), greide_max_pontual_pct=round(float(greide.max()), 1),
                                transversal_mediano_pct=round(float(np.median(np.abs(zt))), 1),
                                dentro_da_area_m=round(L.intersection(areaL).length, 1), no_corredor_da_area_m=round(L.intersection(areaL.buffer(MEIA)).length, 1),
                                trechos=trechos, agua_ao_longo=[{k: v for k, v in r_.items() if k != 'pts'} for r_ in runs], cruzamentos=cr))
    site['eixos'].append([[round(a, 2), round(b, 2)] for a, b in L.coords]); site['perfil'] += trechos; site['agua'] += runs; site['cruz'] += cr
    feats.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[round(a, 2), round(b, 2)] for a, b in e['geo'].coords]},
                  'properties': {'estrada': e['id'], 'comp_m': round(L.length, 1), 'largura_assumida_m': LARG, 'largura_desenhada_m': round(e['larg_des'], 2) if e['larg_des'] else None}})
json.dump(geojson_pontos('estradas_eixo', feats), open(os.path.join(F1, 'estradas_eixo.geojson'), 'w'))

# ---------- linhas de cultivo x estradas ----------
LIN = [f for f in json.load(open(os.path.join(ROOT, 'fase1b', 'linhas_tratadas.geojson'), encoding='utf-8'))['features'] if not f['properties'].get('curta')]
EX = unary_union([e['loc'] for e in eixos]) if eixos else None
cruzam, pontas, logi = [], [], []
for f in LIN:
    L = LineString([(x - X0, y - Y0) for x, y in f['geometry']['coordinates']]); lid = f['properties']['linha']
    if EX is None: continue
    n = max(2, int(L.length / 2)); ds = np.array([EX.distance(L.interpolate(k / n, normalized=True)) for k in range(n + 1)])
    no_cor = L.intersection(EX.buffer(MEIA)).length
    if L.crosses(EX): cruzam.append(dict(linha=lid, tipo='cruza o eixo', no_corredor_m=round(no_cor, 1)))
    elif no_cor > 0.5: cruzam.append(dict(linha=lid, tipo='entra no corredor sem cruzar o eixo', no_corredor_m=round(no_cor, 1)))
    logi.append(dict(linha=lid, comp_m=round(L.length, 1), dist_media_m=round(float(ds.mean()), 1), dist_max_m=round(float(ds.max()), 1), no_corredor_m=round(no_cor, 1)))
    for nome, pt in (('oeste' if L.coords[0][0] < L.coords[-1][0] else 'leste', Point(L.coords[0])), ('leste' if L.coords[0][0] < L.coords[-1][0] else 'oeste', Point(L.coords[-1]))):
        d_e = EX.distance(pt); d_b = areaL.exterior.distance(pt)
        sit = 'sai na estrada' if d_e <= MEIA + 1 else ('sem cabeceira' if d_b < CAB else 'com cabeceira')
        pontas.append(dict(linha=lid, ponta=nome, x=round(pt.x, 1), y=round(pt.y, 1), dist_estrada_m=round(d_e, 1), dist_borda_m=round(d_b, 1), situacao=sit))
comp = np.array([l['comp_m'] for l in logi]); dm = np.array([l['dist_media_m'] for l in logi])
res['linhas_x_estrada'] = dict(linhas_que_cruzam_ou_entram_no_corredor=cruzam, comprimento_de_linha_no_corredor_m=round(sum(l['no_corredor_m'] for l in logi), 1),
                               pontas=dict(total=len(pontas), sai_na_estrada=sum(p['situacao'] == 'sai na estrada' for p in pontas),
                                           sem_cabeceira=sum(p['situacao'] == 'sem cabeceira' for p in pontas), com_cabeceira=sum(p['situacao'] == 'com cabeceira' for p in pontas),
                                           cabeceira_min_m=CAB, lista_sem_cabeceira=[dict(linha=p['linha'], ponta=p['ponta'], dist_borda_m=p['dist_borda_m'], dist_estrada_m=p['dist_estrada_m']) for p in pontas if p['situacao'] == 'sem cabeceira']))
res['logistica'] = dict(dist_media_ponderada_m=round(float((dm * comp).sum() / comp.sum()), 1) if len(comp) else None, dist_max_m=max([l['dist_max_m'] for l in logi] or [0]),
                        linha_mais_distante=max(logi, key=lambda l: l['dist_media_m'])['linha'] if logi else None, por_linha=logi,
                        nota='distância horizontal média de cada linha ao eixo da estrada mais próxima. Indicador de logística da colheita, sem custo associado')
res['resumo'] = dict(estradas=len(eixos), comprimento_total_m=round(sum(e['loc'].length for e in eixos), 1),
                     trechos_agua_ao_longo=len(site['agua']), agua_ao_longo_m=round(sum(r_['comp_m'] for r_ in site['agua']), 1), cruzamentos_de_drenagem=len(site['cruz']),
                     maior_cruzamento_m2=max([c['area_contribuinte_m2'] for c in site['cruz']] or [0]), greide_critico_pct=GC, acumulacao_critica_m2=AC, cruzamento_min_m2=CMIN)
site['pontas'] = pontas; site['linhas'] = logi; site['resumo'] = res['resumo']; site['logistica'] = {k: v for k, v in res['logistica'].items() if k != 'por_linha'}
site['pontas_resumo'] = {k: v for k, v in res['linhas_x_estrada']['pontas'].items() if k != 'lista_sem_cabeceira'}; site['cruzam'] = cruzam
site['estradas'] = [{k: v for k, v in e.items() if k not in ('trechos',)} for e in res['estradas']]; site['arquivo'] = arq
# Contrato sem vias: arrays preservados, métricas indisponíveis em vez de zeros observados.
site['disponivel'] = bool(eixos)
site['proximidade_borda'] = json.load(open(os.path.join(F1,'diagnostico.json'),encoding='utf-8'))['proximidade_borda']
if not eixos:
    for k in ('largura','meia'): site[k]=None
    site['logistica'] = dict(dist_media_ponderada_m=None,dist_max_m=None,linha_mais_distante=None,disponivel=False)
    site['resumo'] = {k: (0 if k=='estradas' else None) for k in site['resumo']}
    res['logistica'] = site['logistica']; res['resumo']=site['resumo']
    for k in ('largura_assumida_m','faixa_livre_m','corredor_sem_planta_m'):res[k]=None
    res['linhas_x_estrada']=None
    res['status']='indisponível: nenhum vetor de vias fornecido; corredores e logística não calculados'
json.dump(site, open(os.path.join(WORK, 'estradas.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(res, open(os.path.join(F1, 'estradas_resumo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ('logistica',)}, ensure_ascii=False)[:6000])
print('logística:', {k: v for k, v in res['logistica'].items() if k != 'por_linha'})
