# Etapa SAF 4. Modelo anual da agrofloresta: ano 0 = estado medido pelo drone.
# Crescimento Chapman-Richards por espécie, calibrado para reproduzir a altura e a copa medidas no CHM;
# competição por luz (sobreposição de copas mais altas), mortalidade, retirada de bananeira sombreada,
# poda anual das árvores de serviço (fica no solo), alimento e carbono. Três cenários + sensibilidade.
# Saídas: work/modelo.json (site), tabelas/*.csv, tabelas/sensibilidade.csv
import base64, csv
from saf_comum import *
from scipy.spatial import cKDTree

PAR = yaml.safe_load(open(os.path.join(ROOT, SAF['parametros']), encoding='utf-8'))
SPP = ['servico', 'frutifera', 'banana', 'cafe']
ANOS = SAF['anos']; NY = ANOS + 1; ANO0 = SAF['ano0']
pol = poligono(); AREA = pol.area / 1e4
TAB = os.path.join(ROOT, 'tabelas'); os.makedirs(TAB, exist_ok=True)

# ---------------- plantas: pontos de plantio das linhas de cultivo (v2) ----------------
# ORIG 0 = medido (inclui árvores fora da linha), 1 = não detectado (coorte própria, porte inicial sorteado)
from saf_02b_plantio import gerar
RC = 0.5; MC = mask(RC); NCEL = MC.sum()          # grade 0,5 m da área para cobertura de copa
def usar(pts):
    """Carrega uma lista de pontos de plantio nos arrays globais do modelo."""
    global PL, N, XY, H0, C0, MEMBRO, ORIG, IDADE, GRP, PI, PJ, DIJ, COL, ROW
    PL = pts; N = len(PL)
    XY = np.array([[p['E'], p['N']] for p in PL]); H0 = np.array([float(p['h0']) for p in PL]); C0 = np.array([float(p['c0']) for p in PL])
    MEMBRO = np.array([p['membro'] for p in PL]); ORIG = np.array([0 if p['status'] != 'nao_detectado' else 1 for p in PL])
    IDADE = np.array([float(p['idade0']) for p in PL]); GRP = np.array([SPP.index(p['grupo']) for p in PL])
    pares = cKDTree(XY).query_pairs(14.0, output_type='ndarray'); PI = np.concatenate([pares[:, 0], pares[:, 1]]); PJ = np.concatenate([pares[:, 1], pares[:, 0]])
    DIJ = np.hypot(*(XY[PI] - XY[PJ]).T)
    COL = (XY[:, 0] - X0) / RC; ROW = (Y1 - XY[:, 1]) / RC
PTS0, PRES = gerar()
usar(PTS0)
gj, fonte = ler_individuos()
print('pontos', N, '| medidos', (ORIG == 0).sum(), '| não detectados', (ORIG == 1).sum(), '| por cenário', PRES['plantas_por_cenario'])

def grupos(ov):
    return GRP.copy()

def overlap(r1, r2, d):
    """Área de interseção de dois círculos (vetorizado)."""
    r1 = np.maximum(r1, 1e-3); r2 = np.maximum(r2, 1e-3)
    a = np.zeros_like(d)
    cheio = d <= np.abs(r1 - r2); a[cheio] = np.pi * np.minimum(r1, r2)[cheio] ** 2
    m = (d < r1 + r2) & ~cheio
    if m.any():
        d_, a_, b_ = d[m], r1[m], r2[m]
        c1 = np.clip((d_ ** 2 + a_ ** 2 - b_ ** 2) / (2 * d_ * a_), -1, 1); c2 = np.clip((d_ ** 2 + b_ ** 2 - a_ ** 2) / (2 * d_ * b_), -1, 1)
        a[m] = a_ ** 2 * np.arccos(c1) + b_ ** 2 * np.arccos(c2) - 0.5 * np.sqrt(np.clip((-d_ + a_ + b_) * (d_ + a_ - b_) * (d_ - a_ + b_) * (d_ + a_ + b_), 0, None))
    return a

def curva(a, ini, pico, decl):
    f = np.clip((a - ini) / max(pico - ini, 1e-6), 0, 1); f[a < ini] = 0
    return np.where(a > decl, np.maximum(0.3, 1 - 0.04 * (a - decl)), f)

def rodar(nivel, dens_bit, ov=None, guardar=False):
    ov = ov or {}
    def P(*path):
        if path in ov: return ov[path]
        v = PAR
        for k in path: v = v[k]
        return v[nivel] if isinstance(v, dict) and nivel in v else v
    E = PAR['especies']
    idade0 = ov.get('idade0', ANO0 - SAF['ano_plantio'])
    poda = ov.get('poda', SAF['manejo']['poda_servico_frac_copa'])
    adub = ov.get('adub', P('manejo', 'fator_adubacao'))
    G = grupos(ov); ativo = (MEMBRO & dens_bit) > 0
    pf = P('crescimento', 'forma_p')
    Hmax = np.array([P('especies', s, 'Hmax_m') for s in SPP])[G]; Cmax = np.array([P('especies', s, 'copa_max_m') for s in SPP])[G]
    fpoda = np.where(G == 0, np.sqrt(1 - poda), 1.0)
    # calibração: k e kc de cada espécie reproduzem a mediana medida (detectadas) na idade de hoje
    kH = np.full(4, 0.3); kC = np.full(4, 0.3)
    for s in range(4):
        sel = (G == s) & (ORIG == 0)
        if sel.sum() == 0: continue
        Hm = Hmax[sel][0]; Cm = Cmax[sel][0]
        q = np.clip((np.median(H0[sel]) - 0.3) / (Hm - 0.3), 0.02, 0.9); kH[s] = -np.log(1 - q ** (1 / pf)) / idade0
        qc = np.clip((np.median(C0[sel]) / (fpoda[sel][0]) - 0.3) / (Cm - 0.3), 0.02, 0.9); kC[s] = -np.log(1 - qc) / idade0
    k = kH[G]; kc = kC[G]
    Hm_i = np.maximum(Hmax, H0 / 0.9)
    Hf = lambda t: 0.3 + (Hm_i - 0.3) * (1 - np.exp(-k * t)) ** pf
    Cf = lambda t: 0.3 + (Cmax - 0.3) * (1 - np.exp(-kc * t))
    q = np.clip((H0 - 0.3) / (Hm_i - 0.3), 1e-4, 0.999); t = -np.log(1 - q ** (1 / pf)) / k
    m = np.clip(C0 / (Cf(t) * fpoda), 0.5, 2.0); m[ORIG == 1] = 1.0              # não detectado segue a copa da espécie
    idade_pl = np.where(ORIG == 0, idade0, ov.get("idade_nd", IDADE)).astype(float)   # idade do plantio de cada planta
    rho = np.array([P('especies', SPP[s], 'densidade_madeira') if s < 2 else 0 for s in range(4)])[G]
    opac = np.array([P('especies', s, 'opacidade_copa') for s in SPP])[G]
    red = P('crescimento', 'reducao_sombra'); mort_s = P('crescimento', 'mortalidade_sombra_extra')
    RS = P('carbono', 'raiz_parte_aerea'); CF_ = P('carbono', 'fracao_carbono'); kdec = P('carbono', 'decomposicao_k_ano'); frc = P('carbono', 'poda_fracao_biomassa_copa')
    a_jk = P('carbono', 'dap_por_altura_copa')
    ali = {s: (E[s]['alimento'] and {kk: P('especies', s, 'alimento', kk) for kk in E[s]['alimento']}) for s in SPP}
    if ('frut_kcal',) in ov: ali['frutifera']['kcal_100g'] = ov[('frut_kcal',)]
    vivo = ativo.copy(); somb_ban = np.zeros(N, int); rng = np.random.default_rng(2026)
    serap = 0.0; ind = []; prev = None
    out = dict(V=np.zeros((NY, N), np.uint8), H=np.zeros((NY, N), np.uint8), R=np.zeros((NY, N), np.uint8), F=np.zeros((NY, N), np.uint8)) if guardar else None
    socref = P('solo', 'SOCref_tC_ha'); fb = ov.get('solo_fb', P('solo', 'fator_base_pastagem_degradada')); fs = P('solo', 'fator_saf'); Dt = P('solo', 'anos_transicao')
    for y in range(NY):
        H = Hf(t); CD = m * Cf(t) * fpoda; R = CD / 2
        # sombra: fração da copa coberta por copas mais altas, ponderada pela opacidade
        ok = vivo[PI] & vivo[PJ] & (H[PJ] > H[PI] + 0.3)
        ov_ = overlap(R[PI][ok], R[PJ][ok], DIJ[ok]) * opac[PJ][ok]
        s = np.clip(np.bincount(PI[ok], ov_, N) / (np.pi * np.maximum(R, 0.05) ** 2), 0, 1); s[~vivo] = 0
        # biomassa aérea seca (kg)
        D = a_jk * (H * CD) ** 0.809
        agb = np.where(G < 2, 0.0673 * (rho * D ** 2 * H) ** 0.976, 0.0)
        bmax = P('especies', 'banana', 'biomassa_seca_max_kg'); agb = np.where(G == 2, bmax * np.clip(H / Hm_i, 0, 1) ** 1.5, agb)
        agb = np.where(G == 3, P('especies', 'cafe', 'biomassa_coef') * H ** 1.8, agb)
        agb = np.where(vivo, agb, 0)
        # alimento (kg fresco por planta)
        kg = np.zeros(N); kcal = np.zeros(N); prot = np.zeros(N); cms = np.zeros(N)
        for si, sn in enumerate(SPP):
            A = ali[sn]
            if not A: continue
            sel = vivo & (G == si)
            f = curva(t[sel], A['inicio_idade'], A['pico_idade'], A['declinio_apos']) * A['kg_planta_pico'] * adub
            if sn == 'banana': f *= np.clip(1 - A['reducao_sombra'] * s[sel], 0, 1)
            else:
                tol = A['sombra_tolerada']; f *= np.where(s[sel] <= tol, 1, np.maximum(0.2, 1 - 1.2 * (s[sel] - tol)))
            kg[sel] = f; kcal[sel] = f * A['fracao_comestivel'] * A['kcal_100g'] * 10; prot[sel] = f * A['fracao_comestivel'] * A['proteina_100g'] / 100
            cms[sel] = f * A['materia_seca'] * CF_
        # poda (fica no solo) e serapilheira
        podado = float((poda * frc * agb[(G == 0) & vivo]).sum()) if poda > 0 else 0.0
        cbio = float(agb.sum() * (1 + RS) * CF_ / 1000)                       # t C
        csolo_ha = socref * (fb + (fs - fb) * min(1, (idade0 + y) / Dt))
        # cobertura de copa
        cob = np.zeros(MC.shape, bool)
        for i in (np.where(vivo & (R > 0.15))[0] if guardar else []):
            rr = R[i] / RC; r0, r1 = int(max(ROW[i] - rr, 0)), int(min(ROW[i] + rr + 1, MC.shape[0])); c0_, c1 = int(max(COL[i] - rr, 0)), int(min(COL[i] + rr + 1, MC.shape[1]))
            yy, xx = np.mgrid[r0:r1, c0_:c1]; cob[r0:r1, c0_:c1] |= (yy + 0.5 - ROW[i]) ** 2 + (xx + 0.5 - COL[i]) ** 2 <= rr * rr
        cobp = 100 * (cob & MC).sum() / NCEL
        clit = serap * CF_ / 1000
        tot = cbio + clit
        est = {'alto': int((vivo & (H >= 5)).sum()), 'medio': int((vivo & (H >= 2.5) & (H < 5)).sum()),
               'arbustivo': int((vivo & (H >= 0.8) & (H < 2.5)).sum()), 'pequena': int((vivo & (H < 0.8)).sum())}
        kcal_t = float(kcal.sum())
        I = dict(ano=y, cal=ANO0 + y, kg_alimento=float(kg[G != 3].sum()), kg_banana=float(kg[G == 2].sum()), kg_fruta=float(kg[G == 1].sum()),
                 kg_cafe=float(kg[G == 3].sum()), kcal=kcal_t, prot_kg=float(prot.sum()), pessoas=kcal_t / (SAF['kcal_pessoa_dia'] * 365),
                 c_bio=cbio, c_serap=clit, c_total=tot, co2e_total=tot * 44 / 12, c_solo=csolo_ha * AREA, c_solo_ganho=(csolo_ha - socref * fb) * AREA,
                 c_exportado=float(cms.sum() / 1000), cobertura=cobp, agb_t=float(agb.sum() / 1000), agb_lenhosa_t=float(agb[G < 2].sum() / 1000), vivas=int(vivo.sum()),
                 por_esp={sn: int((vivo & (G == si)).sum()) for si, sn in enumerate(SPP)}, estrato=est)
        I['seq_co2e'] = None if prev is None else (tot - prev) * 44 / 12
        I['seq_solo_co2e'] = None if y == 0 else (I['c_solo'] - ind[-1]['c_solo']) * 44 / 12
        ind.append(I); prev = tot
        if guardar:
            out['V'][y] = vivo; out['H'][y] = np.clip(np.round(H * 10), 0, 255); out['R'][y] = np.clip(np.round(R * 20), 0, 255)
            nivel_f = np.where(kg > 0, np.where(G == 3, kg / 0.1, np.where(G == 2, kg / 4, kg / 8)), 0)
            out['F'][y] = np.where(vivo, np.clip(np.ceil(nivel_f), 0, 3), 0)
        # ---- transição para o próximo ano ----
        mortos = []
        taxa = np.where(idade_pl + y < SAF['mortalidade']['anos_iniciais'], SAF['mortalidade']['inicial'], SAF['mortalidade']['depois'])
        taxa = taxa + np.where((G < 2) & (s > 0.7), mort_s, 0)
        u = rng.random(N)
        morre = vivo & (u < taxa)
        somb_ban = np.where(vivo & (G == 2) & (s > P('especies', 'banana', 'sombra_remove')), somb_ban + 1, 0)
        morre |= vivo & (G == 2) & (somb_ban >= 2)
        entrada = podado + float((agb[morre] * (1 + RS)).sum())             # poda e plantas mortas ficam no sistema
        serap = serap * np.exp(-kdec) + entrada
        vivo = vivo & ~morre
        t = t + np.where(vivo, 1 - red * s, 0)
    return ind, out, dict(kH=kH.round(3).tolist(), kC=kC.round(3).tolist())

CEN = {'conservador': ('c', 1), 'provavel': ('p', 2), 'otimista': ('o', 4)}
RES = {}
for nome, (nv, bit) in CEN.items():
    ind, out, cal = rodar(nv, bit, guardar=True); RES[nome] = (ind, out, cal)
    I0, I30 = ind[0], ind[-1]
    print(f"{nome:12s} ano0: vivas {I0['vivas']} cob {I0['cobertura']:.1f}% C {I0['c_bio']:.2f} tC | ano{ANOS}: vivas {I30['vivas']} cob {I30['cobertura']:.0f}% "
          f"C {I30['c_total']:.1f} tC ({I30['co2e_total']:.0f} tCO2e) | alimento médio {np.mean([i['kg_alimento'] for i in ind[1:]]):.0f} kg/ano "
          f"pessoas {np.mean([i['pessoas'] for i in ind[1:]]):.2f} | k {cal['kH']}")

# ---------------- checagem com o CHM (ordem de grandeza) ----------------
det = [f['properties'] for f in gj['features']]
h = np.array([p['altura_m'] for p in det]); cd = np.array([p['copa_m'] for p in det])
lnD = []   # Chave 2014 eq. 6a invertida, E = 0 (premissa): ln H = 0,893 + 0,760 ln D - 0,0340 (ln D)^2
for hh in h:
    a_, b_, c_ = -0.0340, 0.760, 0.893 - np.log(max(hh, 1.31))
    lnD.append((-b_ + np.sqrt(b_ * b_ - 4 * a_ * c_)) / (2 * a_) if b_ * b_ - 4 * a_ * c_ > 0 else np.log(1))
D_ch = np.exp(lnD); lenhosa = h >= 2.5
agb_hd = float((0.0673 * (0.58 * D_ch ** 2 * h) ** 0.976)[lenhosa].sum() / 1000)
chm25 = chm_grade(0.25)[1]; M25 = mask(0.25)
vol = float((chm25 * (chm25 >= 2.5) * M25).sum() * 0.0625)
cheque = dict(agb_modelo_ano0_lenhosas_t={k: round(RES[k][0][0]['agb_lenhosa_t'], 2) for k in RES}, agb_modelo_ano0_total_t=round(RES['provavel'][0][0]['agb_t'], 2),
              agb_chave_altura_diametro_t=round(agb_hd, 2), volume_dossel_m3=round(vol, 0),
              agb_volume_dossel_t=[round(vol * 0.1 / 1000, 2), round(vol * 0.25 / 1000, 2), round(vol * 0.5 / 1000, 2)],
              nota='volume do dossel (CHM >= 2,5 m) x 0,1 a 0,5 kg/m3: densidade aparente de copa jovem, premissa a validar; Chave 2014 eq. 6a com E = 0 tende a subestimar o DAP de árvores abertas')
print('checagem CHM:', cheque)

# ---------------- sensibilidade (parâmetros prováveis, um fator por vez) ----------------
def metr(ind): return dict(pessoas=np.mean([i['pessoas'] for i in ind[1:]]), alimento_t=sum(i['kg_alimento'] for i in ind[1:]) / 1000,
                           co2e30=ind[-1]['co2e_total'], solo30=ind[-1]['c_solo_ganho'] * 44 / 12, cafe_t=sum(i['kg_cafe'] for i in ind[1:]) / 1000)
base_m = metr(RES['provavel'][0])
VAR = [('Densidade de café', 'sem café', {'pts': (0, None)}, 2), ('Densidade de café', 'café a cada 2 m (1 entre bananas)', {'pts': (2.0, None)}, 2),
       ('Densidade de café', 'café a cada 0,5 m (7 entre bananas)', {'pts': (0.5, None)}, 2),
       ('Desenho de plantio', 'desenho anterior: banana 6 m, café 1,5 m', {'pts': (1.5, 6.0)}, 2), ('Desenho de plantio', 'banana a cada 3 m', {'pts': (None, 3.0)}, 2),
       ('Desenho de plantio', 'banana a cada 6 m', {'pts': (None, 6.0)}, 2),
       ('Sobrevivência', 'não detectados 50% (conservador)', {}, 1), ('Sobrevivência', 'não detectados 95% (otimista)', {}, 4),
       ('Espécies', 'frutífera tipo citros (40 kcal/100 g)', {('frut_kcal',): 40}, 2), ('Espécies', 'frutífera tipo abacate (96 kcal/100 g)', {('frut_kcal',): 96}, 2),
       ('Espécies', 'árvore de serviço densidade 0,45', {('especies', 'servico', 'densidade_madeira'): 0.45}, 2),
       ('Espécies', 'árvore de serviço densidade 0,65', {('especies', 'servico', 'densidade_madeira'): 0.65}, 2),
       ('Espécies', 'árvore de serviço porte 12 m', {('especies', 'servico', 'Hmax_m'): 12}, 2),
       ('Espécies', 'árvore de serviço porte 20 m', {('especies', 'servico', 'Hmax_m'): 20}, 2),
       ('Ano de plantio', 'medidos plantados em 2021 (5 anos)', {'idade0': 5}, 2), ('Ano de plantio', 'medidos plantados em 2024 (2 anos)', {'idade0': 2}, 2),
       ('Idade dos não detectados', '0 ano (recém-plantados)', {'idade_nd': 0.0}, 2), ('Idade dos não detectados', '3 anos (mesma coorte de 2023)', {'idade_nd': 3.0}, 2),
       ('Uso anterior', 'pastagem pouco degradada (fator 0,97)', {'solo_fb': 0.97}, 2), ('Uso anterior', 'pastagem muito degradada (fator 0,70)', {'solo_fb': 0.70}, 2),
       ('Manejo', 'sem poda das árvores de serviço', {'poda': 0.0}, 2), ('Manejo', 'poda de 50% da copa', {'poda': 0.5}, 2),
       ('Manejo', 'sem adubação (produção x 0,85)', {'adub': 0.85}, 2), ('Manejo', 'adubação forte (produção x 1,15)', {'adub': 1.15}, 2)]
# ---------------- entradas da economia (etapa 5, pipeline/site/economia.js) ----------------
def contagens(bit=None):
    sel = np.ones(N, bool) if bit is None else (MEMBRO & bit) > 0
    return dict(plantadas={s: int(((GRP == i)).sum()) for i, s in enumerate(SPP)},          # desenho inteiro plantado no ano do plantio
                nao_detectadas={s: int(((GRP == i) & (ORIG == 1)).sum()) for i, s in enumerate(SPP)},   # replantio (coorte mais nova)
                medidas={s: int(((GRP == i) & (ORIG == 0) & sel).sum()) for i, s in enumerate(SPP)})    # produzem no histórico
serie = lambda ind: dict(cafe=[round(i['kg_cafe'], 2) for i in ind], banana=[round(i['kg_banana'], 1) for i in ind],
                         fruta=[round(i['kg_fruta'], 1) for i in ind], vivas={s: [i['por_esp'][s] for i in ind] for s in SPP})
ECON_SENS = {}
SENS = []
for grp, nome, ov, bit in VAR:
    if 'pts' in ov: usar(gerar(cafe_m=ov['pts'][0], banana_m=ov['pts'][1])[0])
    ind_v = rodar('p', bit, ov)[0]; mm = metr(ind_v)
    if grp in ('Densidade de café', 'Desenho de plantio', 'Sobrevivência'):
        ECON_SENS[nome] = dict(premissa=grp, bit=bit, serie=serie(ind_v), contagens=contagens(bit))
    if 'pts' in ov: usar(PTS0)
    SENS.append(dict(premissa=grp, variacao=nome, **{k: round(v, 2) for k, v in mm.items()},
                     **{f'd_{k}_pct': round(100 * (mm[k] / base_m[k] - 1), 0) if base_m[k] else None for k in mm}))
with open(os.path.join(TAB, 'sensibilidade.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(SENS[0].keys())); w.writeheader(); w.writerows(SENS)
print('sensibilidade: base', {k: round(v, 2) for k, v in base_m.items()})
for s_ in SENS: print(f"  {s_['premissa']:15s} {s_['variacao']:42s} pessoas {s_['d_pessoas_pct']:+.0f}%  CO2e30 {s_['d_co2e30_pct']:+.0f}%  solo {s_['d_solo30_pct']:+.0f}%")

# ---------------- tabelas por ano ----------------
CAMPOS = ['ano', 'cal', 'vivas', 'cobertura', 'kg_alimento', 'kg_banana', 'kg_fruta', 'kg_cafe', 'kcal', 'prot_kg', 'pessoas',
          'c_bio', 'c_serap', 'c_total', 'co2e_total', 'seq_co2e', 'c_solo', 'c_solo_ganho', 'seq_solo_co2e', 'c_exportado']
for nome, (ind, _, _) in RES.items():
    with open(os.path.join(TAB, f'anual_{nome}.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(CAMPOS + ['alto', 'medio', 'arbustivo', 'pequena'] + SPP)
        for I in ind: w.writerow([round(I[c], 3) if isinstance(I[c], float) else I[c] for c in CAMPOS] + list(I['estrato'].values()) + list(I['por_esp'].values()))

# ---------------- json para o site ----------------
b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
G_site = grupos({})
def flat(d, pre=''):
    for k, v in d.items():
        if isinstance(v, dict) and 'fonte' in v: yield pre + k, v
        elif isinstance(v, dict): yield from flat(v, pre + k + ' · ')
PREM = [dict(param=k, c=v.get('c'), p=v.get('p'), o=v.get('o'), fonte=v['fonte'], conf=v['confianca']) for k, v in flat(PAR)]
modelo = dict(area_ha=AREA, n=N, anos=ANOS, ano0=ANO0, ano_plantio=SAF['ano_plantio'],
              plantas=[[round(p['E'] - X0, 2), round(p['N'] - Y0, 2), int(g), int(p['membro']), {'medido': 0, 'nao_detectado': 1, 'fora_da_linha': 2}[p['status']]] for p, g in zip(PL, G_site)],
              linhas=[[[round(x - X0, 2), round(y - Y0, 2)] for x, y in f['geometry']['coordinates']] for f in json.load(open(os.path.join(ROOT, 'fase1b', 'linhas_tratadas.geojson'), encoding='utf-8'))['features']],
              plantio=PRES,
              especies=[dict(id=s, nome=PAR['especies'][s]['nome']) for s in SPP],
              cen={nome: dict(ind=ind, V=b64(out['V']), H=b64(out['H']), R=b64(out['R']), F=b64(out['F']), cal=cal) for nome, (ind, out, cal) in RES.items()},
              sens=SENS, sens_base={k: round(v, 2) for k, v in base_m.items()}, premissas=PREM, cheque=cheque,
              econ=dict(contagens={nome: contagens(bit) for nome, (nv, bit) in CEN.items()}, perimetro_m=round(pol.length, 1),
                        idade_nd=float(SAF['plantio'].get('idade_nao_detectados', 1)), mort_inicial=SAF['mortalidade']['inicial'],
                        curvas={nv: dict(adub=PAR['manejo']['fator_adubacao'][nv], **{s: {k: PAR['especies'][s]['alimento'][k][nv] for k in ('inicio_idade', 'pico_idade', 'declinio_apos', 'kg_planta_pico')}
                                for s in ('frutifera', 'banana', 'cafe')}) for nv in 'cpo'},
                        sens=ECON_SENS),
              diag=json.load(open(os.path.join(F1, 'diagnostico.json'), encoding='utf-8')), fonte_individuos=os.path.relpath(fonte, ROOT))
json.dump(modelo, open(os.path.join(WORK, 'modelo.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('modelo.json KB', os.path.getsize(os.path.join(WORK, 'modelo.json')) // 1024)
