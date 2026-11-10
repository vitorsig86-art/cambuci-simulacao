# Etapa IMP 4. Modelo anual da implantação: ano 0 = plantio (mudas), 30 anos, três cenários.
# Crescimento Chapman-Richards por espécie; mortalidade e replantio; touceira e renovação da banana; recepa escalonada do café;
# sombra (copas mais altas sobre a copa do café), faixa protegida e faixa de competição do quebra-vento; produção por idade;
# carbono (alometria, raízes IPCC, linha de base pastagem, solo à parte). A economia roda no site e no relatório (economia.js).
# Dois desenhos no mesmo modelo: com quebra-vento (renque de grevílea) e sem quebra-vento (café e banana nas linhas inteiras, sem grevílea,
# sem faixa protegida nem de competição, todo o café com a perda de vento da premissa efeitos.perda_vento_sem_protecao).
# Saídas: work/modelo.json, tabelas/anual_<cenario>.csv, tabelas/anual_<cenario>_sem_qv.csv, tabelas/sensibilidade_producao.csv, tabelas/sensibilidade_producao_sem_qv.csv
import base64, csv
from saf_comum import *
from scipy.spatial import cKDTree
import imp_02_plantio as PLN

PAR = yaml.safe_load(open(os.path.join(ROOT, SAF['parametros']), encoding='utf-8'))
QV = CFG['quebra_vento']
SPP = ['grevilea', 'banana', 'cafe']
ANOS = SAF['anos']; NY = ANOS + 1; ANO0 = SAF['ano0']
pol = poligono(); AREA = pol.area / 1e4
TAB = os.path.join(ROOT, 'tabelas'); os.makedirs(TAB, exist_ok=True)
RC = 0.5; MC = mask(RC); NCEL = MC.sum()

def usar(pts):
    global PL, N, XY, G, LINHA, S_, DZ, DQ, PI, PJ, DIJ, COL, ROW
    PL = pts; N = len(PL); XY = np.array([[p['x'], p['y']] for p in PL]); G = np.array([SPP.index(p['esp']) for p in PL]); LINHA = np.array([p['linha'] for p in PL])
    S_ = np.array([p['s'] if p['s'] is not None else np.inf for p in PL]); DZ = np.array([p['dz'] for p in PL]); DQ = np.array([p['dq'] for p in PL])
    pares = cKDTree(XY).query_pairs(9.0, output_type='ndarray'); PI = np.concatenate([pares[:, 0], pares[:, 1]]); PJ = np.concatenate([pares[:, 1], pares[:, 0]])
    DIJ = np.hypot(*(XY[PI] - XY[PJ]).T); COL = XY[:, 0] / RC; ROW = (Y1 - Y0 - XY[:, 1]) / RC
PTS0, PRES = PLN.gerar(); PTS_SEM, PRES_SEM = PLN.gerar(sem_qv=True); usar(PTS0)
print('plantas com quebra-vento', PRES['plantas'], '| sem quebra-vento', PRES_SEM['plantas'])

def overlap(r1, r2, d):
    r1 = np.maximum(r1, 1e-3); r2 = np.maximum(r2, 1e-3); a = np.zeros_like(d)
    cheio = d <= np.abs(r1 - r2); a[cheio] = np.pi * np.minimum(r1, r2)[cheio] ** 2
    m = (d < r1 + r2) & ~cheio
    if m.any():
        d_, a_, b_ = d[m], r1[m], r2[m]
        c1 = np.clip((d_ ** 2 + a_ ** 2 - b_ ** 2) / (2 * d_ * a_), -1, 1); c2 = np.clip((d_ ** 2 + b_ ** 2 - a_ ** 2) / (2 * d_ * b_), -1, 1)
        a[m] = a_ ** 2 * np.arccos(c1) + b_ ** 2 * np.arccos(c2) - 0.5 * np.sqrt(np.clip((-d_ + a_ + b_) * (d_ + a_ - b_) * (d_ - a_ + b_) * (d_ + a_ + b_), 0, None))
    return a

def rodar(nivel, ov=None, guardar=False):
    ov = ov or {}
    def P(*path):
        if path in ov: return ov[path]
        v = PAR
        for k in path: v = v[k]
        return v[nivel] if isinstance(v, dict) and nivel in v else v
    por = lambda chave: np.array([P('especies', s, chave) for s in SPP], float)[G]
    h0 = por('h0_m'); Hmax = por('Hmax_m'); kH = por('k_altura'); Cmax = por('copa_max_m'); kC = por('k_copa'); opac = por('opacidade_copa')
    m1 = por('mortalidade_ano1'); ma = por('mortalidade_anual'); pf = P('crescimento', 'forma_p')
    cafe = G == 2; ban = G == 1; grev = G == 0
    PC = {k: P('especies', 'cafe', 'producao', k) for k in ('inicio_idade', 'pico_idade', 'declinio_apos', 'kg_planta_pico', 'sombra_tolerada')}
    PC['kg_planta_pico'] *= ov.get('fator_densidade', 1.0)       # sensibilidade de densidade: planta mais apertada produz menos por pé
    PB = {k: P('especies', 'banana', 'producao', k) for k in ('inicio_idade', 'pico_idade', 'kg_planta_pico', 'reducao_sombra')}
    rec_n = int(P('especies', 'cafe', 'renovacao_anos')); ren_b = int(P('especies', 'banana', 'renovacao_anos')); rep_ate = int(P('especies', 'cafe', 'replantio_ate_ano'))
    pv = ov.get('perda_vento', P('efeitos', 'perda_vento_sem_protecao')); pfx = P('efeitos', 'perda_faixa_competicao')
    kprot = QV['protecao_alturas'][nivel]; fcomp = QV['competicao_alturas'][nivel]; capc = QV['competicao_max_m'][nivel]
    rho = P('especies', 'grevilea', 'densidade_madeira'); a_jk = P('carbono', 'dap_por_altura_copa'); RS = P('carbono', 'raiz_parte_aerea'); CF_ = P('carbono', 'fracao_carbono'); kdec = P('carbono', 'decomposicao_k_ano')
    base_c = P('carbono', 'pastagem_biomassa_tC_ha') * AREA
    socref = P('solo', 'SOCref_tC_ha'); fb = P('solo', 'fator_base_pastagem'); fs = P('solo', 'fator_sistema'); Dt = P('solo', 'anos_transicao')
    rng = np.random.default_rng(2026)
    t = np.zeros(N)                      # idade de crescimento (anos)
    ta = np.zeros(N)                     # idade de produção (zera no replantio; recepa volta para pico - 2)
    km = np.ones(N)                      # rebrota mais rápida depois da recepa
    rec_ult = np.zeros(N, int); rec_fase = np.full(N, 99)      # anos desde a última recepa
    ren_ult = np.zeros(N, int); ren_flag = np.zeros(N, bool)
    vivo = np.ones(N, bool)
    serap = 0.0; ind = []; prev = None; rep_prox = {s: 0 for s in SPP}
    out = dict(V=np.zeros((NY, N), np.uint8), H=np.zeros((NY, N), np.uint8), R=np.zeros((NY, N), np.uint8), F=np.zeros((NY, N), np.uint8)) if guardar else None
    par_linha = (LINHA % 2 == 0)
    for y in range(NY):
        H = h0 + (Hmax - h0) * (1 - np.exp(-kH * km * t)) ** pf; CD = 0.2 + (Cmax - 0.2) * (1 - np.exp(-kC * km * t)); R = CD / 2
        # sombra sobre cada planta: fração da copa coberta por copas mais altas, ponderada pela opacidade
        ok = vivo[PI] & vivo[PJ] & (H[PJ] > H[PI] + 0.3)
        s = np.clip(np.bincount(PI[ok], overlap(R[PI][ok], R[PJ][ok], DIJ[ok]) * opac[PJ][ok], N) / (np.pi * np.maximum(R, 0.05) ** 2), 0, 1); s[~vivo] = 0
        # quebra-vento: altura média do renque, proteção (com desnível) e faixa de competição
        hq = float(H[grev & vivo].mean()) if (grev & vivo).any() else 0.0
        prot = (S_ <= kprot * (hq - DZ)) & (hq >= 1.5)
        faixa = (DQ <= min(fcomp * hq, capc)) & (hq >= 1.5)
        # produção (kg por planta no ano)
        kg = np.zeros(N)
        fa = np.clip((ta - PC['inicio_idade']) / max(PC['pico_idade'] - PC['inicio_idade'], 1e-6), 0, 1)
        fa = np.where(ta > PC['declinio_apos'], np.maximum(0.4, 1 - 0.04 * (ta - PC['declinio_apos'])), fa)
        fa = np.where(rec_fase == 1, 0.0, np.where(rec_fase == 2, 0.7, fa))
        fsomb = np.where(s <= PC['sombra_tolerada'], 1, np.maximum(0.2, 1 - 1.2 * (s - PC['sombra_tolerada'])))
        fv = np.where(prot, 1.0, 1 - pv); ff = np.where(faixa, 1 - pfx, 1.0)
        kg[cafe & vivo] = (fa * PC['kg_planta_pico'] * fsomb * fv * ff)[cafe & vivo]
        fbn = np.clip((ta - PB['inicio_idade'] + 1) / max(PB['pico_idade'] - PB['inicio_idade'] + 1, 1e-6), 0, 1) * (ta >= PB['inicio_idade'])
        kg[ban & vivo] = (fbn * PB['kg_planta_pico'] * np.clip(1 - PB['reducao_sombra'] * s, 0, 1) * np.where(ren_flag, 0.5, 1.0))[ban & vivo]
        # biomassa aérea seca (kg)
        D = a_jk * (H * CD) ** 0.809
        agb = np.where(grev, 0.0673 * (rho * D ** 2 * H) ** 0.976, 0.0)
        agb = np.where(ban, P('especies', 'banana', 'biomassa_seca_max_kg') * np.clip(H / Hmax, 0, 1) ** 1.5, agb)
        agb = np.where(cafe, P('especies', 'cafe', 'biomassa_coef') * H ** 1.8, agb); agb = np.where(vivo, agb, 0)
        cbio = float(agb.sum() * (1 + RS) * CF_ / 1000); clit = serap * CF_ / 1000; tot = cbio + clit
        csolo_ha = socref * (fb + (fs - fb) * min(1, y / Dt))
        cob = np.zeros(MC.shape, bool)
        for i in (np.where(vivo & (R > 0.15))[0] if guardar else []):
            rr = R[i] / RC; r0, r1 = int(max(ROW[i] - rr, 0)), int(min(ROW[i] + rr + 1, MC.shape[0])); c0_, c1 = int(max(COL[i] - rr, 0)), int(min(COL[i] + rr + 1, MC.shape[1]))
            yy, xx = np.mgrid[r0:r1, c0_:c1]; cob[r0:r1, c0_:c1] |= (yy + 0.5 - ROW[i]) ** 2 + (xx + 0.5 - COL[i]) ** 2 <= rr * rr
        cv = cafe & vivo; ncv = max(int(cv.sum()), 1)
        # ---- eventos de manejo deste ano (depois da colheita): recepa do café e renovação da banana ----
        idade_ciclo = y - rec_ult
        rec = cv & (idade_ciclo >= np.where(par_linha, rec_n + 1, rec_n)) & (y < ANOS)
        ren = ban & vivo & (y - ren_ult >= ren_b) & (y < ANOS)
        I = dict(ano=y, cal=ANO0 + y, kg_cafe=float(kg[cafe].sum()), sacas=float(kg[cafe].sum() / 60), kg_banana=float(kg[ban].sum()), vivas=int(vivo.sum()),
                 por_esp={sn: int((vivo & (G == si)).sum()) for si, sn in enumerate(SPP)}, replantio=dict(rep_prox), recepados=int(rec.sum()), renov_banana=int(ren.sum()),
                 falhas_cafe=int((cafe & ~vivo).sum()), h_qv=hq, protegido_pct=100 * float(prot[cv].sum()) / ncv, faixa_pct=100 * float(faixa[cv].sum()) / ncv,
                 faixa_m=min(fcomp * hq, capc) if hq >= 1.5 else 0.0, sombra_cafe=float(s[cv].mean()) if cv.any() else 0.0,
                 cafe_sombra_acima_pct=100 * float((s[cv] > PC['sombra_tolerada']).sum()) / ncv,
                 c_bio=cbio, c_serap=clit, c_total=tot, co2e_total=tot * 44 / 12, c_base=base_c, co2e_liquido=(tot - base_c) * 44 / 12,
                 c_solo=csolo_ha * AREA, c_solo_ganho=(csolo_ha - socref * fb) * AREA, cobertura=100 * (cob & MC).sum() / NCEL, agb_t=float(agb.sum() / 1000),
                 estrato={'alto': int((vivo & (H >= 5)).sum()), 'medio': int((vivo & (H >= 2.5) & (H < 5)).sum()), 'arbustivo': int((vivo & (H >= 0.8) & (H < 2.5)).sum()), 'pequena': int((vivo & (H < 0.8)).sum())})
        I['seq_co2e'] = None if prev is None else (tot - prev) * 44 / 12
        I['seq_solo_co2e'] = None if y == 0 else (I['c_solo'] - ind[-1]['c_solo']) * 44 / 12
        ind.append(I); prev = tot
        if guardar:
            out['V'][y] = vivo; out['H'][y] = np.clip(np.round(H * 10), 0, 255); out['R'][y] = np.clip(np.round(R * 20), 0, 255)
            out['F'][y] = np.where(vivo, np.clip(np.ceil(np.where(cafe, kg / 0.2, kg / 4)), 0, 3), 0)
        # ---- transição para o próximo ano ----
        entrada = 0.0
        if rec.any():                    # recepa: copa cortada fica no solo; rebrota; falhas da linha são replantadas
            entrada += float(agb[rec].sum() * 0.8); t[rec] = 0.25; km[rec] = 1.6; ta[rec] = PC['pico_idade'] - 2; rec_fase[rec] = 0
            lin = np.isin(LINHA, np.unique(LINHA[rec])); rec_ult[cafe & lin] = y
            vazio = cafe & ~vivo & lin; rep_prox_c = int(vazio.sum()); vivo[vazio] = True; t[vazio] = 0; ta[vazio] = 0; km[vazio] = 1; rec_fase[vazio] = 99
        else: rep_prox_c = 0
        ren_flag = np.zeros(N, bool)
        if ren.any(): entrada += float(agb[ren].sum()); t[ren] = 0.5; ta[ren] = PB['inicio_idade'] - 0.001; ren_ult[ban] = y; ren_flag[ren] = True
        u = rng.random(N); morre = vivo & (u < np.where(t < 1, m1, ma)) & ~rec & ~ren
        entrada += float((agb[morre] * (1 + RS)).sum()); serap = serap * np.exp(-kdec) + entrada
        rep = morre & (ban | (y < rep_ate))                      # replantio: banana sempre (filhote); café e grevílea até o ano limite
        rep_prox = {sn: int((rep & (G == si)).sum()) for si, sn in enumerate(SPP)}; rep_prox['cafe'] += rep_prox_c
        vivo = vivo & (~morre | rep)
        t = t + 1; ta = ta + 1; rec_fase = np.where(rec_fase < 99, rec_fase + 1, 99)
        t[rep] = 0; ta[rep] = 0; km[rep] = 1
    return ind, out

CEN = {'conservador': 'c', 'provavel': 'p', 'otimista': 'o'}
RES_SEM = {}; usar(PTS_SEM); G_SEM = G.copy()
for nome, nv in CEN.items():
    RES_SEM[nome] = rodar(nv, guardar=True); i_ = RES_SEM[nome][0]
    print(f"sem quebra-vento {nome:12s} café pico {max(i['sacas'] for i in i_):.1f} sc | média anos 5-30 {np.mean([i['sacas'] for i in i_[5:]]):.1f} sc | CO2e ano 30: {i_[30]['co2e_total']:.0f} t")
usar(PTS0)
RES = {}
for nome, nv in CEN.items():
    ind, out = rodar(nv, guardar=True); RES[nome] = (ind, out)
    pk = max(ind, key=lambda i: i['sacas'])
    print(f"{nome:12s} café pico {pk['sacas']:.1f} sc no ano {pk['ano']} ({pk['sacas'] / AREA:.1f} sc/ha) | média anos 5-30 {np.mean([i['sacas'] for i in ind[5:]]):.1f} sc | banana pico {max(i['kg_banana'] for i in ind):.0f} kg"
          f" | renque ano 5/10/30: {ind[5]['h_qv']:.1f}/{ind[10]['h_qv']:.1f}/{ind[30]['h_qv']:.1f} m | café protegido ano 5/10/20: {ind[5]['protegido_pct']:.0f}/{ind[10]['protegido_pct']:.0f}/{ind[20]['protegido_pct']:.0f}%"
          f" | faixa ano 15: {ind[15]['faixa_pct']:.0f}% | CO2e ano 30: {ind[30]['co2e_total']:.0f} t (líquido {ind[30]['co2e_liquido']:.0f})")

# ---------------- sensibilidade de produção e entradas da economia (parâmetros prováveis, um fator por vez) ----------------
lite = lambda ind: [dict(kg_cafe=round(i['kg_cafe'], 2), kg_banana=round(i['kg_banana'], 1), por_esp=i['por_esp'], replantio=i['replantio'], recepados=i['recepados'], renov_banana=i['renov_banana']) for i in ind]
def contagens(): return {s: int((G == i).sum()) for i, s in enumerate(SPP)}
CONT0 = contagens()
metr = lambda ind: dict(cafe_sc=float(sum(i['sacas'] for i in ind)), banana_t=float(sum(i['kg_banana'] for i in ind) / 1000), co2e30=float(ind[-1]['co2e_total']), solo30=float(ind[-1]['c_solo_ganho'] * 44 / 12))
EXPD = 0.5   # PREMISSA A VALIDAR: produção por pé proporcional a (espaçamento / espaçamento do projeto)^0,5
fd = lambda cm: (cm / float(CFG['plantio']['cafe_m'])) ** EXPD
base_m = metr(RES['provavel'][0])
VAR = [('Densidade de café', 'café a cada 0,6 m', dict(pts=(0.6, None), fator_densidade=fd(0.6))), ('Densidade de café', 'café a cada 1,0 m', dict(pts=(1.0, None), fator_densidade=fd(1.0))),
       ('Densidade de café', 'café a cada 1,2 m', dict(pts=(1.2, None), fator_densidade=fd(1.2))),
       ('Banana', 'banana a cada 4 m', dict(pts=(None, 4.0))), ('Banana', 'banana a cada 12 m', dict(pts=(None, 12.0))), ('Banana', 'sem banana', dict(pts=(None, 0))),
       ('Quebra-vento', 'sem quebra-vento (café e banana também na faixa do renque)', dict(pts=(None, None), sem_qv=True)),
       ('Quebra-vento', 'vento sem efeito sobre o café (perda zero)', {'perda_vento': 0.0}),
       ('Quebra-vento', 'vento forte (perda de 20% sem proteção)', {'perda_vento': 0.20}),
       ('Produtividade do café', '-30% no pico por planta', {('especies', 'cafe', 'producao', 'kg_planta_pico'): PAR['especies']['cafe']['producao']['kg_planta_pico']['p'] * 0.7}),
       ('Produtividade do café', '+30% no pico por planta', {('especies', 'cafe', 'producao', 'kg_planta_pico'): PAR['especies']['cafe']['producao']['kg_planta_pico']['p'] * 1.3}),
       ('Recepa do café', 'a cada 10 anos', {('especies', 'cafe', 'renovacao_anos'): 10}), ('Recepa do café', 'a cada 18 anos', {('especies', 'cafe', 'renovacao_anos'): 18})]
def sensibilidade(variacoes, pts_base, base, sem_qv, arquivo):
    econ, sens = {}, []
    for grp, nome, ov in variacoes:
        usar(PLN.gerar(cafe_m=ov['pts'][0], banana_m=ov['pts'][1], sem_qv=sem_qv or bool(ov.get('sem_qv')))[0] if 'pts' in ov else pts_base)
        ind_v = rodar('p', ov)[0]; mm = metr(ind_v); cont = contagens()
        econ[nome] = dict(premissa=grp, serie=lite(ind_v), contagens=cont)
        sens.append(dict(premissa=grp, variacao=nome, cafes=cont['cafe'], bananas=cont['banana'], **{k: round(v, 2) for k, v in mm.items()},
                         **{f'd_{k}_pct': round(100 * (mm[k] / base[k] - 1), 0) if base[k] else None for k in mm}))
    usar(PTS0)
    with open(os.path.join(TAB, arquivo), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(sens[0].keys())); w.writeheader(); w.writerows(sens)
    print(arquivo, 'base provável:', {k: round(v, 1) for k, v in base.items()})
    for s_ in sens: print(f"  {s_['premissa']:22s} {s_['variacao']:50s} cafés {s_['cafes']:5d} café {s_['d_cafe_sc_pct']:+.0f}%  banana {s_['d_banana_t_pct']:+.0f}%  CO2e30 {s_['d_co2e30_pct']:+.0f}%")
    return econ, sens
ECON_SENS, SENS = sensibilidade(VAR, PTS0, base_m, False, 'sensibilidade_producao.csv')
# desenho sem quebra-vento: as mesmas variações, menos a que tira o renque; o vento pesa sobre todo o café
base_sem = metr(RES_SEM['provavel'][0])
VAR_SEM = [(('Vento (sem quebra-vento)' if g_ == 'Quebra-vento' else g_), n_, o_) for g_, n_, o_ in VAR if not o_.get('sem_qv')]
ECON_SENS_SEM, SENS_SEM = sensibilidade(VAR_SEM, PTS_SEM, base_sem, True, 'sensibilidade_producao_sem_qv.csv')

CAMPOS = ['ano', 'cal', 'vivas', 'sacas', 'kg_cafe', 'kg_banana', 'recepados', 'renov_banana', 'falhas_cafe', 'h_qv', 'protegido_pct', 'faixa_pct', 'sombra_cafe', 'cobertura',
          'c_bio', 'c_serap', 'c_total', 'co2e_total', 'co2e_liquido', 'seq_co2e', 'c_solo', 'c_solo_ganho']
for nome, suf, ind in [(n_, '', r_[0]) for n_, r_ in RES.items()] + [(n_, '_sem_qv', r_[0]) for n_, r_ in RES_SEM.items()]:
    with open(os.path.join(TAB, f'anual_{nome}{suf}.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(CAMPOS + SPP + ['replantio_' + s for s in SPP])
        for I in ind: w.writerow([round(I[c], 3) if isinstance(I[c], float) else I[c] for c in CAMPOS] + [I['por_esp'][s] for s in SPP] + [I['replantio'][s] for s in SPP])

# ---------------- json para o site ----------------
b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
def flat(d, pre=''):
    for k, v in d.items():
        if isinstance(v, dict) and 'fonte' in v: yield pre + k, v
        elif isinstance(v, dict): yield from flat(v, pre + k + ' · ')
PREM = [dict(param=k, c=v.get('c'), p=v.get('p'), o=v.get('o'), fonte=v['fonte'], conf=v['confianca']) for k, v in flat(PAR)]
PLJ = json.load(open(os.path.join(WORK, 'plantio.json'), encoding='utf-8'))
modelo = dict(area_ha=AREA, n=N, anos=ANOS, ano0=ANO0,
              plantas=[[round(p['x'], 2), round(p['y'], 2), int(g), 7, int(p['linha'])] for p, g in zip(PTS0, G)],
              linhas=[[[round(x - X0, 2), round(y - Y0, 2)] for x, y in f['geometry']['coordinates']] for f in json.load(open(os.path.join(ROOT, 'fase1b', 'linhas_tratadas.geojson'), encoding='utf-8'))['features']],
              plantio=PLJ['resumo'], qv=dict(renques=PLJ['renques'], grades=PLJ['grades'], vento=PLJ['vento'], corredor=PLJ['corredor'],
                                             protecao=QV['protecao_alturas'], competicao=QV['competicao_alturas'], competicao_max=QV['competicao_max_m']),
              especies=[dict(id=s, nome=PAR['especies'][s]['nome']) for s in SPP],
              cen={nome: dict(ind=ind, V=b64(out['V']), H=b64(out['H']), R=b64(out['R']), F=b64(out['F'])) for nome, (ind, out) in RES.items()},
              sens=SENS, sens_base={k: round(v, 2) for k, v in base_m.items()}, premissas=PREM,
              econ=dict(contagens=CONT0, perimetro_m=round(pol.length, 1), sens=ECON_SENS, expoente_densidade=EXPD),
              vento=dict(perda=PAR['efeitos']['perda_vento_sem_protecao'], competicao=PAR['efeitos']['perda_faixa_competicao']),
              des=dict(sem=dict(n=len(PTS_SEM), plantas=[[round(p['x'], 2), round(p['y'], 2), int(g), 7, int(p['linha'])] for p, g in zip(PTS_SEM, G_SEM)], plantio=PRES_SEM,
                                cen={nome: dict(ind=ind, V=b64(out['V']), H=b64(out['H']), R=b64(out['R']), F=b64(out['F'])) for nome, (ind, out) in RES_SEM.items()},
                                contagens={s: int((G_SEM == i).sum()) for i, s in enumerate(SPP)}, sens=SENS_SEM, sens_base={k: round(v, 2) for k, v in base_sem.items()}, econ_sens=ECON_SENS_SEM)),
              diag=json.load(open(os.path.join(F1, 'diagnostico.json'), encoding='utf-8')))
modelo['diag']['linhas'].pop('por_linha', None)
json.dump(modelo, open(os.path.join(WORK, 'modelo.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('modelo.json KB', os.path.getsize(os.path.join(WORK, 'modelo.json')) // 1024)
