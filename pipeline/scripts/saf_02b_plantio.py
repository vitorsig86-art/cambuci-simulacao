# Etapa SAF 2 (v2). Esqueleto de plantio a partir das LINHAS DE CULTIVO desenhadas pelo usuário.
# 1) linhas: não orientadas, recortadas pela área de estudo, espaçamento real, avisos (fora da área, cruzando)
# 2) pontos ao longo de cada linha: banana a cada B m, café a cada C m entre bananas, padrão alternado entre linhas
#    vizinhas; árvores (>= 2,5 m) nas posições detectadas; detectados associados ao ponto mais próximo (<= 1,5 m)
# 3) sobrevivência dos não detectados por cenário (ano 0)
# Saídas: fase1b/linhas_tratadas.geojson, fase1b/pontos_plantio.geojson, fase1b/plantio_resumo.json, fase1b/conferencia_plantio.png
from saf_comum import *
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, nearest_points
from scipy.spatial import cKDTree

PLA = SAF['plantio']
F1B = os.path.join(ROOT, 'fase1b'); os.makedirs(F1B, exist_ok=True)
SPP = ['servico', 'frutifera', 'banana', 'cafe']

def ler_linhas():
    gj = json.load(open(os.path.join(D, PLA['linhas']), encoding='utf-8'))
    pol = poligono(); out = []
    for i, f in enumerate(gj['features']):
        g = shape(f['geometry']); c = np.array(g.coords)[:, :2]
        az = np.degrees(np.arctan2(c[-1, 0] - c[0, 0], c[-1, 1] - c[0, 1])) % 360
        if not (90 <= az < 270): c = c[::-1]; az = (az + 180) % 360        # todas no mesmo sentido (~155°)
        g = LineString(c); dentro = g.intersection(pol)
        out.append(dict(fid=i, geom=g, dentro=dentro, az=az, L=g.length, L_in=dentro.length))
    return out, pol

def eixo(linhas):
    a = np.radians([l['az'] for l in linhas]) * 2; w = np.array([l['L'] for l in linhas])
    th = np.arctan2((np.sin(a) * w).sum(), (np.cos(a) * w).sum()) / 2
    return th % np.pi

def gerar(cafe_m=None, banana_m=None, salvar=False):
    """Gera os pontos de plantio. Devolve (pontos, resumo). cafe_m=0 = sem café."""
    cafe_m = PLA['cafe_m'] if cafe_m is None else cafe_m
    banana_m = PLA['banana_m'] if banana_m is None else banana_m
    linhas, pol = ler_linhas()
    th = eixo(linhas); ct, st = np.cos(th), np.sin(th)
    perp = lambda x, y: x * ct - y * st
    lon = lambda x, y: x * st + y * ct
    for l in linhas:
        m = l['geom'].interpolate(0.5, normalized=True); l['dp'] = perp(m.x, m.y)
    linhas.sort(key=lambda l: l['dp'])
    # linhas colineares (diferença < 1 m) = mesma linha de cultivo
    r = 0; prev = None
    for l in linhas:
        if prev is not None and l['dp'] - prev > 1.0: r += 1
        l['linha'] = r + 1; prev = l['dp']
    nlin = r + 1
    # ---------- pontos ao longo das linhas ----------
    pts = []
    for l in linhas:
        ph = (l['linha'] % 2) * banana_m / 2                                   # alterna entre vizinhas
        pecas = [p for p in getattr(l['dentro'], 'geoms', [l['dentro']]) if not p.is_empty and p.length > 0.3]
        for pc in pecas:
            a = pc.coords[0]; dl0 = lon(*a); comp = pc.length
            s0 = (ph - dl0) % banana_m
            k = 0
            while s0 + k * banana_m <= comp + 1e-6:
                sb = s0 + k * banana_m
                pts.append(dict(s=sb, tipo='banana', peca=pc, linha=l['linha']))
                j = 1
                while cafe_m and j * cafe_m < banana_m - 0.5 * cafe_m:
                    sc = sb + j * cafe_m
                    if sc <= comp: pts.append(dict(s=sc, tipo='cafe', peca=pc, linha=l['linha']))
                    j += 1
                k += 1
            # café antes da primeira banana da peça
            j = 1
            while cafe_m and s0 - j * cafe_m >= 0 and j * cafe_m < banana_m - 0.5 * cafe_m:
                pts.append(dict(s=s0 - j * cafe_m, tipo='cafe', peca=pc, linha=l['linha'])); j += 1
    for p in pts:
        q = p['peca'].interpolate(p['s']); p.update(E=q.x, N=q.y, grupo=p['tipo'], status='nao_detectado', det=None)
    # ---------- detectados ----------
    gjd, fonte = ler_individuos()
    det = []
    for i, f in enumerate(gjd['features']):
        pr = f['properties']; x, y = f['geometry']['coordinates']
        det.append(dict(i=i, E=x, N=y, h=float(pr['altura_m']), c=float(pr['copa_m']), estrato=pr['estrato'], esp=(pr.get('especie') or '').strip()))
    uni = unary_union([l['dentro'] for l in linhas if not l['dentro'].is_empty])
    for d in det: d['dlin'] = uni.distance(Point(d['E'], d['N']))
    PXY = np.array([[p['E'], p['N']] for p in pts]); tr = cKDTree(PXY)
    tol = PLA['tolerancia_m']; hmin = PLA['arvore_min_m']
    def grupo_arvore(d):
        if d['esp']:
            for k, v in PAR_ESP.items():
                if d['esp'].lower() == k or d['esp'].lower() in [a.lower() for a in v['aliases']]: return k
        return 'servico' if d['h'] >= SAF['estratos_m']['alto'] else 'frutifera'
    pares = []
    for d in det:
        if d['dlin'] > tol: continue
        dd, ii = tr.query([d['E'], d['N']], k=6, distance_upper_bound=tol)
        for a, b in zip(np.atleast_1d(dd), np.atleast_1d(ii)):
            if np.isfinite(a): pares.append((0 if d['h'] >= hmin else 1, a, d['i'], b))   # árvores primeiro
    pares.sort(); usado_d = set(); usado_p = set()
    for _, a, di, pi in pares:
        if di in usado_d or pi in usado_p: continue
        d = det[di]; p = pts[pi]
        p.update(status='medido', det=di, h0=d['h'], c0=d['c'], dist=round(a, 2))
        if d['h'] >= hmin: p.update(tipo='arvore', grupo=grupo_arvore(d))
        elif d['esp']:
            g = grupo_arvore(d); p['grupo'] = g if g in ('banana', 'cafe') else p['grupo']
        usado_d.add(di); usado_p.add(pi)
    extras, fora, fora_exc, sem_ponto = [], [], [], []
    for d in det:
        if d['i'] in usado_d: continue
        if d['dlin'] > tol:
            (fora if d['h'] >= hmin else fora_exc).append(d['i'])
            if d['h'] >= hmin: extras.append(dict(E=d['E'], N=d['N'], tipo='arvore', grupo=grupo_arvore(d), status='fora_da_linha', det=d['i'], h0=d['h'], c0=d['c'], linha=None))
        else:
            # na linha, mas sem ponto livre a 1,5 m: entra como medido extra (planta certa), grupo pela altura
            sem_ponto.append(d['i'])
            q = nearest_points(uni, Point(d['E'], d['N']))[0]
            g = grupo_arvore(d) if d['h'] >= hmin else ('banana' if d['h'] >= 1.5 else 'cafe')
            extras.append(dict(E=d['E'], N=d['N'], tipo='arvore' if d['h'] >= hmin else g, grupo=g, status='medido', det=d['i'], h0=d['h'], c0=d['c'],
                               linha=min(linhas, key=lambda l: l['geom'].distance(q))['linha'], extra=True))
    pts += extras
    # ---------- porte inicial e sobrevivência dos não detectados ----------
    rng = np.random.default_rng(31)
    ini = PLA['porte_inicial']; surv = PLA['sobrevivencia_nao_detectados']
    for p in pts:
        u = rng.random(); hu = rng.random()
        if p['status'] == 'nao_detectado':
            lo, hi = ini[p['grupo']]; p['h0'] = round(lo + (hi - lo) * hu, 2)
            p['c0'] = round(p['h0'] * (0.9 if p['grupo'] == 'cafe' else 1.2), 2)
            p['idade0'] = PLA['idade_nao_detectados']
            p['membro'] = (1 if u < surv['conservador'] else 0) | (2 if u < surv['provavel'] else 0) | (4 if u < surv['otimista'] else 0)
        else:
            p['idade0'] = SAF['ano0'] - SAF['ano_plantio']; p['membro'] = 7
    for i, p in enumerate(pts): p['id'] = i + 1
    # ---------- resumo ----------
    dps = np.array([l['dp'] for l in linhas]); dif = np.diff(dps); esp = dif[dif > 1.0]
    cruz = [(linhas[a]['fid'], linhas[b]['fid']) for a in range(len(linhas)) for b in range(a + 1, len(linhas)) if linhas[a]['geom'].crosses(linhas[b]['geom'])]
    cnt = lambda **kw: sum(all(p.get(k) == v for k, v in kw.items()) for p in pts)
    nd_ban = [p for p in pts if p['tipo'] == 'banana']
    res = dict(linhas_feicoes=len(linhas), linhas_de_cultivo=nlin, azimute_medio=round(float(np.degrees(th)), 1),
               comprimento_total_m=round(sum(l['L'] for l in linhas), 1), comprimento_dentro_m=round(sum(l['L_in'] for l in linhas), 1),
               comprimento_fora_m=round(sum(l['L'] - l['L_in'] for l in linhas), 1),
               linhas_com_trecho_fora=[dict(feicao=l['fid'], fora_m=round(l['L'] - l['L_in'], 1)) for l in linhas if l['L'] - l['L_in'] > 0.5],
               linhas_cruzando=cruz, colineares=int(len(dif) - len(esp)),
               entrelinha_m=dict(min=round(float(esp.min()), 2), mediana=round(float(np.median(esp)), 2), max=round(float(esp.max()), 2), antes_medido=4.0),
               padrao=dict(banana_m=banana_m, cafe_m=cafe_m, alterna_m=banana_m / 2),
               pontos=len(pts), por_tipo={t: cnt(tipo=t) for t in ['banana', 'cafe', 'arvore']},
               por_status={s: cnt(status=s) for s in ['medido', 'nao_detectado', 'fora_da_linha']},
               medidos_extra_sem_ponto_livre=len(sem_ponto), detectados_total=len(det),
               fora_da_linha_arvores_incluidas=len(fora), fora_da_linha_pequenos_excluidos=len(fora_exc),
               bananas_nao_detectadas_pct=round(100 * sum(p['status'] == 'nao_detectado' for p in nd_ban) / max(1, len(nd_ban)), 1),
               cafes_nao_detectados_pct=round(100 * cnt(tipo='cafe', status='nao_detectado') / max(1, cnt(tipo='cafe')), 1),
               sobrevivencia=surv, idade_nao_detectados=PLA['idade_nao_detectados'], fonte_individuos=os.path.relpath(fonte, ROOT),
               plantas_por_cenario={k: sum(1 for p in pts if p['membro'] & b) for k, b in [('conservador', 1), ('provavel', 2), ('otimista', 4)]})
    if salvar:
        feats = [{'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[round(x, 2), round(y, 2)] for x, y in (pc.coords)]},
                  'properties': dict(feicao=l['fid'], linha=l['linha'], azimute=round(l['az'] % 180, 1), comprimento_m=round(l['L'], 2),
                                     dentro_m=round(l['L_in'], 2), fora_m=round(l['L'] - l['L_in'], 2))}
                 for l in linhas for pc in getattr(l['dentro'], 'geoms', [l['dentro']]) if not pc.is_empty]
        json.dump(geojson_pontos('linhas_tratadas', feats), open(os.path.join(F1B, 'linhas_tratadas.geojson'), 'w', encoding='utf-8'), ensure_ascii=False)
        nomes = {s: PAR_ESP[s]['nome'] for s in SPP}
        fp = [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(p['E'], 2), round(p['N'], 2)]},
               'properties': dict(id=p['id'], linha=p['linha'], tipo=p['tipo'], grupo=p['grupo'],
                                  especie=(det[p['det']]['esp'] if p.get('det') is not None and det[p['det']]['esp'] else 'espécie não informada'),
                                  status=p['status'], altura_ini_m=p['h0'], copa_ini_m=p['c0'], idade_ini=p['idade0'],
                                  vivo_ano0_conservador=bool(p['membro'] & 1), vivo_ano0_provavel=bool(p['membro'] & 2), vivo_ano0_otimista=bool(p['membro'] & 4),
                                  id_detectado=(p['det'] + 1 if p.get('det') is not None else None), grupo_nome=nomes[p['grupo']])} for p in pts]
        json.dump(geojson_pontos('pontos_plantio', fp), open(os.path.join(F1B, 'pontos_plantio.geojson'), 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump(res, open(os.path.join(F1B, 'plantio_resumo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        conferencia(linhas, pts, det, pol, res)
    return pts, res

PAR_ESP = yaml.safe_load(open(os.path.join(ROOT, SAF['parametros']), encoding='utf-8'))['especies']

def conferencia(linhas, pts, det, pol, res):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    ro = 0.1; O = warp('orto.tif', ro, 'average').ReadAsArray()[:3]
    Mo = mask(ro); yy, xx = np.nonzero(Mo)
    y0, y1, x0, x1 = max(yy.min() - 40, 0), yy.max() + 40, max(xx.min() - 40, 0), xx.max() + 40
    fig, ax = plt.subplots(figsize=(13, 13 * (y1 - y0) / (x1 - x0)))
    ax.imshow(np.moveaxis(O[:, y0:y1, x0:x1], 0, -1), extent=(X0 + x0 * ro, X0 + x1 * ro, Y1 - y1 * ro, Y1 - y0 * ro))
    ax.plot(*pol.exterior.xy, color='yellow', lw=1.5)
    for l in linhas:
        ax.plot(*l['geom'].xy, color='white', lw=0.6, alpha=0.8)
    est = {'medido': '#00e5ff', 'nao_detectado': '#ff3b30', 'fora_da_linha': '#ff00ff'}
    mk = {'banana': 's', 'cafe': 'o', 'arvore': '^'}
    for st, cor in est.items():
        for t, m in mk.items():
            sel = [p for p in pts if p['status'] == st and p['tipo'] == t]
            if sel: ax.scatter([p['E'] for p in sel], [p['N'] for p in sel], s={'banana': 16, 'cafe': 5, 'arvore': 40}[t], c=cor, marker=m,
                               linewidths=0.3, edgecolors='black' if t != 'cafe' else 'none', label=f'{st.replace("_", " ")} · {t} ({len(sel)})')
    ax.set_xlim(X0 + x0 * ro, X0 + x1 * ro); ax.set_ylim(Y1 - y1 * ro, Y1 - y0 * ro)
    ax.legend(loc='lower right', fontsize=8, framealpha=0.85); ax.tick_params(labelsize=7)
    ax.set_title(f"{res['pontos']} pontos de plantio em {res['linhas_de_cultivo']} linhas | banana a cada {res['padrao']['banana_m']:g} m, "
                 f"café a cada {res['padrao']['cafe_m']:g} m | medidos {res['por_status']['medido']} · não detectados {res['por_status']['nao_detectado']} · "
                 f"fora da linha {res['por_status']['fora_da_linha']}", fontsize=9)
    plt.tight_layout(); plt.savefig(os.path.join(F1B, 'conferencia_plantio.png'), dpi=110)

if __name__ == '__main__':
    pts, res = gerar(salvar=True)
    print(json.dumps(res, ensure_ascii=False, indent=1))
