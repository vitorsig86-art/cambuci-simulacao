# Etapa SAF 6. Gera relatorio.md a partir de work/modelo.json e tabelas/ (regera junto com o modelo).
from saf_comum import *

mo = json.load(open(os.path.join(WORK, 'modelo.json'), encoding='utf-8'))
D = mo['diag']; I = D['individuos']; L = D['linhas']; A = mo['area_ha']; ANOS = mo['anos']; ANO0 = mo['ano0']
CEN = [('conservador', 'Conservador'), ('provavel', 'Provável'), ('otimista', 'Otimista')]
ind = {k: mo['cen'][k]['ind'] for k, _ in CEN}
f = lambda v, d=0: '–' if v is None else f"{v:,.{d}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
fx = lambda key, y, d=0, g=lambda v: v: f"{f(min(g(ind[k][y][key]) for k, _ in CEN), d)} a {f(max(g(ind[k][y][key]) for k, _ in CEN), d)}"
media = lambda k, key: sum(i[key] for i in ind[k][1:]) / ANOS
co2 = lambda v: v * 44 / 12
sb = mo['sens_base']; ch = mo['cheque']

L_ = []; w = L_.append
w('# Agrofloresta de Cambuci: rentabilidade, estado atual e projeção de 30 anos\n')
w('> **Estimativas de modelagem, sem validação de campo.** Os valores em R$ não são orçamento nem previsão de lucro: a maior parte dos custos '
  'é premissa a validar, e a produção vem de um modelo calibrado só pela altura das plantas no drone. Não equivalem a certificação de créditos de carbono. '
  'Espécies, idade, manejo, uso anterior e densidade são premissas a validar (ver seção 4).\n')

# ---------------- 1. rentabilidade (mesmo motor do site, pipeline/site/economia.js, via node) ----------------
import subprocess, shutil
PE = json.load(open(os.path.join(WORK, 'economia_parametros.json'), encoding='utf-8'))
node = shutil.which('node') or r'C:\Program Files\nodejs\node.exe'
cli = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site', 'economia_cli.js')
EC = json.loads(subprocess.run([node, cli, os.path.join(WORK, 'modelo.json'), os.path.join(WORK, 'economia_parametros.json')],
                               capture_output=True, text=True, encoding='utf-8', check=True).stdout)
R_ = lambda v: '–' if v is None else ('−' if v < 0 else '') + 'R$ ' + f(abs(v))
pb = lambda r: 'não retorna em 30 anos' if r['payback'] is None else f"{r['payback']} ({r['payback_anos']} anos)"
tx = lambda v: '–' if v is None else f(v * 100, 1) + '%'
UD = EC['padroes']; P0 = int(UD['ano_plantio']); FIM = ANO0 + ANOS
w('## 1. Rentabilidade do talhão (café e banana como eixo)\n')
w(f"Fluxo de caixa anual em **R$ constantes de 2026** (sem inflação), de **{P0} (plantio, premissa a validar) a {FIM}**, para a área de estudo ({f(A, 2)} ha). "
  f"Taxa de desconto real de {f(UD['taxa'] * 100, 1)}% a.a. **Com mão de obra própria** = todos os dias-homem pagos a R$ {f(UD['diaria'])}/dia (pró-labore); "
  "**sem pró-labore** = só o desembolso com insumos e serviços. Cenários variam produção, preço e custo juntos.\n")
w('### Resultado por cenário\n')
w('| Cenário | Modo | Implantação | Acumulado até ' + str(ANO0 - 1) + ' | Falta recuperar | Ano de retorno | VPL | TIR | Acumulado em ' + str(FIM) + ' |\n|---|---|---|---|---|---|---|---|---|')
for k, nome in CEN:
    for modo, rot in [('com', 'com mão de obra própria'), ('sem', 'sem pró-labore')]:
        r = EC['cen'][k][modo]
        w(f"| {nome} | {rot} | {R_(r['impl'])} ({R_(r['impl'] / A)}/ha) | {R_(r['acum_ate_hoje'])} | {R_(r['falta_recuperar'])} | {pb(r)} | {R_(r['vpl'])} | {tx(r['tir'])} | {R_(r['final'])} |")
rp = EC['cen']['provavel']
w(f"\nPior momento do acumulado no provável: {R_(-rp['com']['exposicao'])} em {rp['com']['ano_exposicao']} com mão de obra própria, "
  f"{R_(-rp['sem']['exposicao'])} em {rp['sem']['ano_exposicao']} sem pró-labore.\n")
w('### Fluxo do cenário provável (anos escolhidos)\n')
w('| Ano | Café (sc) | Banana (t cacho) | Receita café | Receita banana | Receita frutas | Receita total | Desembolso | Dias-homem | Resultado sem pró-labore | Resultado com MO própria | Acumulado com MO |\n|' + '---|' * 12)
acum_com = rp['com']['acum']
for i, r in enumerate(rp['rows']):
    if r['ano'] in (P0, P0 + 1, P0 + 2, ANO0, ANO0 + 1, ANO0 + 2, ANO0 + 3, ANO0 + 5, ANO0 + 10, ANO0 + 15, ANO0 + 20, FIM) or r['ano'] < ANO0:
        w(f"| {r['ano']}{' (hist.)' if r['hist'] else ''} | {f(r['sacas'], 1)} | {f(r['kg_banana'] / 1000, 1)} | {R_(r['rec']['cafe'])} | {R_(r['rec']['banana'])} | {R_(r['rec']['fruta'])} | "
          f"{R_(r['receita'])} | {R_(r['caixa'])} | {f(r['dias'])} | {R_(r['res_sem'])} | {R_(r['res_com'])} | {R_(acum_com[i])} |")
cs = [c for c in rp['custo_saca'] if ANO0 + 5 <= c['ano'] <= ANO0 + 10 and c['com']]
if cs: w(f"\nCusto por saca de café no provável, {ANO0 + 5} a {ANO0 + 10} (colheita do café + custos comuns rateados pela receita): "
         f"{R_(min(c['com'] for c in cs))} a {R_(max(c['com'] for c in cs))} com mão de obra própria, {R_(min(c['sem'] for c in cs))} a {R_(max(c['sem'] for c in cs))} sem pró-labore. "
         f"Preço provável do café: {R_(UD['preco_cafe'])}/saca.\n")
w('### Sensibilidade do ano de retorno\n')
w('Um fator por vez sobre o provável. Densidade: variações de desenho e sobrevivência já existentes no modelo (o custo de implantação acompanha o número de mudas).\n')
w('| Premissa | Variação | Retorno com MO própria | Retorno sem pró-labore | VPL com MO | VPL sem pró-labore |\n|---|---|---|---|---|---|')
for s in EC['sens']:
    w(f"| {s['grupo']} | {s['nome']} | {pb(s['com'])} | {pb(s['sem'])} | {R_(s['com']['vpl'])} | {R_(s['sem']['vpl'])} |")
w('\nLeitura rápida:')
w(f"- Com o trabalho da família pago a R$ {f(UD['diaria'])}/dia, o provável {('retorna em ' + str(rp['com']['payback'])) if rp['com']['payback'] else 'não retorna em 30 anos'}; "
  f"sem pró-labore, {('retorna em ' + str(rp['sem']['payback'])) if rp['sem']['payback'] else 'também não retorna'}. A mão de obra é o maior custo do sistema.")
w('- A faixa entre conservador e otimista é muito larga porque a produção de café varia de cerca de 2 a 16 sacas por ano no pico entre os cenários (clima marginal e sobrevivência incerta).')
w('- No VPL, a sobrevivência das plantas pesa mais, seguida do preço do café; o custo de implantação (±30%) pesa cerca de metade do preço do café (±30%).\n')
w('### Método do fluxo de caixa\n')
for t in [f"**Linha do tempo**: começa no ano do plantio ({P0}). Os anos antes de {ANO0} são **histórico estimado**: as plantas medidas pelo drone produzem pela curva de idade "
          f"da espécie, os custos seguem o desenho inteiro plantado e os {f(sum(mo['econ']['contagens']['provavel']['nao_detectadas'].values()))} pontos não detectados entram como replantio em {ANO0 - round(mo['econ']['idade_nd'])} (coorte mais nova do modelo).",
          f"**Do ano {ANO0} em diante**: produção do modelo de crescimento, ano a ano, por cenário.",
          '**Receita**: café beneficiado em sacas de 60 kg × preço; banana = peso do cacho × fração vendida em pencas × preço; frutíferas × fração vendida × preço; outras produções = 0 (nenhuma informada).',
          '**Implantação** (ano do plantio): preparo do solo, correção, mudas e adubação de cova de todo o desenho (café, banana, serviço, frutífera), cerca pelo perímetro da área, outros. Sem irrigação.',
          '**Custeio anual**: adubação orgânica por planta viva, fitossanitário e manutenção por ha, replantio das mortes do ano anterior (mudas e cova). O modelo de crescimento não repõe as plantas mortas: a receita não sobe com o replantio, o que deixa a conta do lado conservador.',
          '**Colheita e pós-colheita**: dias-homem e R$ por saca de café, por tonelada e por kg de banana e de frutas.',
          '**Mão de obra**: capina seletiva, poda e manejo das árvores de serviço, adubação, fitossanitário, plantio e colheita, em dias-homem.',
          '**Indicadores**: ano de retorno = primeiro ano em que o acumulado volta a zero e não fica mais negativo; VPL e TIR sobre o fluxo do plantio ao fim; "falta recuperar" = acumulado negativo até o fim do ano anterior a hoje.',
          'No site, os campos da aba Premissas editam o provável (preço do café e da banana, implantação e custeio por ha, diária, chave de mão de obra, taxa e ano do plantio). Conservador e otimista andam na mesma proporção. O ano do plantio muda só o caixa; o crescimento segue calibrado no drone.']:
    w(f'- {t}')
w('\n### Preços e custos: fonte, data e confiança\n')
w('Valores conservador · provável · otimista. **Em negrito: premissa a validar (sem fonte verificável).**\n')
w('| Item | Valores | Unidade | Fonte | Data | Confiança |\n|---|---|---|---|---|---|')
def _flat(o, pre):
    for k, v in o.items():
        if isinstance(v, dict) and 'fonte' in v: yield pre + k, v
        elif isinstance(v, dict): yield from _flat(v, pre + k + ' · ')
nv_ = lambda v: f(v, 2 if abs(v) < 1 else 1 if abs(v) < 10 else 0) if isinstance(v, (int, float)) else str(v)
for sec in ['geral', 'precos', 'mao_de_obra', 'implantacao', 'custeio', 'colheita']:
    for k, v in _flat(PE[sec], sec + ' · '):
        prem = str(v['fonte']).startswith('premissa')
        nome = k.replace('_', ' ')
        w(f"| {'**' + nome + '**' if prem else nome} | {nv_(v['c'])} · {nv_(v['p'])} · {nv_(v['o'])} | {v.get('unidade', '')} | {v['fonte']} | {v['data']} | {v['confianca']} |")
w('\nReferências só para conferir a ordem de grandeza (não entram na conta):\n')
for r in PE.get('referencias', []): w(f"- {r['item']}: {r['valor']} ({r['fonte']}, {r['data']}).")
npremis = sum(1 for sec in ['geral', 'precos', 'mao_de_obra', 'implantacao', 'custeio', 'colheita'] for _, v in _flat(PE[sec], '') if str(v['fonte']).startswith('premissa'))
w(f"\n> **Premissas não confirmadas**: {npremis} dos itens acima não têm fonte verificável, entre eles todos os custos de implantação e de custeio, a diária rural, "
  "o preço das frutíferas (espécie não informada), o deságio regional do café, a produtividade do café em clima marginal e o ano do plantio. "
  "As planilhas de custo da Emater-DF (2025) e da Conab não puderam ser lidas (acesso por validação de documento); o preço regional do Noroeste Fluminense não foi encontrado. "
  "Antes de decidir, confira com orçamento local de mudas, diária praticada na região e a colheita real.\n")

# ---------------- 2. água (etapa 3d) ----------------
AGR = json.load(open(os.path.join(F1, 'agua_resumo.json'), encoding='utf-8')); AE = AGR['est']
w('## 2. Água: drenagem simulada\n')
w('> Diagnóstico derivado do MDT, sem proposta de obra. Indica por onde a água tende a correr e se concentrar; não diz quanto escoa.\n')
w('### Método e parâmetros\n')
for t_ in [f"MDT do **recorte inteiro** ({f(AE['recorte_ha'], 2)} ha, não só a área de estudo), reamostrado para {f(AE['resolucao_m'], 0)} m pela média e suavizado com gaussiana de σ {f(AE['suavizacao_sigma_m'], 1)} m para tirar o ruído fotogramétrico do MDT de 0,48 m.",
           f"Depressões preenchidas por *priority flood* (Barnes 2014) com declive mínimo. Depressões mais fundas que {f(AE['preenchimento_max_m'], 2)} m seriam listadas como possível microrelevo real; nesta área não houve nenhuma (preenchimento máximo dentro da área: {f(AE['preenchimento_max_area_m'], 2)} m).",
           f"Direção de fluxo **D8** e acumulação em área (m²). Rede onde a área contribuinte passa de **{f(AE['limiar_rede_m2'])} m²** (`projeto.yaml > agua.limiar_rede_m2`). Testado: 1.000 m² deixa só 73 m de rede na área; 300 m² gera rede densa demais para ler. Ordem de **Strahler** por trecho.",
           'Bacia da área de estudo = todas as células cujo caminho D8 passa pela área. Bacia de cada trecho principal (6 maiores) = células que drenam até o fim do trecho.',
           f"Pontos de concentração = onde, dentro da área, o fluxo passa de {f(AE['limiar_concentracao_m2'])} m². Comprimento de rampa = caminho D8 do divisor até a rede.",
           f"Linhas de cultivo (`fase1b/linhas_tratadas.geojson`) amostradas a cada 1 m: **cruzamento** = interseção com um trecho da rede; **conduz fluxo** = declive a menos de ~37° da linha (cosseno ≥ {f(AE['conducao_alinhamento'], 1)}) e declive ao longo da linha ≥ {f(AE['conducao_declive_pct'])}% por pelo menos 10 m contínuos; **risco de erosão indicativo** = declividade ≥ {f(AE['risco_declividade_pct'])}% e acumulação ≥ {f(AE['risco_acumulacao_m2'])} m² no mesmo ponto. **Os três critérios são premissas a validar.**"]:
    w(f'- {t_}')
w('\n### Estatísticas\n')
w('| Indicador | Valor |\n|---|---|')
for a_, b_ in [('Rede na área de estudo', f"{f(AE['rede_m_area'])} m"), ('Rede no recorte', f"{f(AE['rede_m_recorte'])} m, {AE['trechos']} trechos, ordem máxima {AE['ordem_max']} ({', '.join(f'ordem {k}: {v}' for k, v in AE['trechos_por_ordem'].items())})"),
               ('Densidade de drenagem', f"{f(AE['densidade_km_km2_area'], 1)} km/km² na área, {f(AE['densidade_km_km2_recorte'], 1)} km/km² no recorte"),
               ('Bacia da área de estudo', f"{f(AE['bacia_area_ha'], 2)} ha, dos quais {f(AE['contribuinte_de_fora_ha'], 2)} ha vêm de fora da área"),
               ('Entradas concentradas', f"{AE['entradas']} (maior {f(AE['maior_entrada_ha'], 2)} ha); o restante entra difuso pela borda alta"),
               ('Saídas', f"{AE['saidas']} (maior {f(AE['maior_saida_ha'], 2)} ha)"), ('Pontos de concentração na área', str(AE['pontos_concentracao'])),
               ('Comprimento de rampa na área', f"mediana {f(AE['rampa_m']['p50'])} m, p90 {f(AE['rampa_m']['p90'])} m, máximo {f(AE['rampa_m']['max'])} m" if AE.get('rampa_m') else '–'),
               ('Cruzamentos rede × linhas de cultivo', f"{AE['cruzamentos']} em {AE['linhas_com_cruzamento']} linhas"),
               ('Linhas que conduzem fluxo', f"{AE['linhas_que_conduzem']} linhas, {f(AE['conducao_total_m'])} m"),
               ('Risco de erosão indicativo', f"{AE['pontos_risco']} pontos em {AE['linhas_com_risco']} linhas"),
               ('Bacia na borda do voo', f"{f(AE['bacia_na_borda_do_recorte_m'])} m de contato: a área contribuinte real pode ser maior" if AE['bacia_na_borda_do_recorte_m'] else 'não toca a borda')]:
    w(f'| {a_} | {b_} |')
w('\n### Trechos principais\n')
w('| Trecho | Ordem | Área contribuinte (ha) | Bacia do trecho (ha) |\n|---|---|---|---|')
for p_ in AGR['principais']: w(f"| {p_['id'] + 1} | {p_['ordem']} | {f(p_['acc_ha'], 2)} | {f(p_['bacia_ha'], 2)} |")
w('\n### Cruzamentos e condução nas linhas de cultivo\n')
LL = [l_ for l_ in AGR['linhas'] if l_['cruzamentos'] or l_['conduz_m'] or l_['risco_m']]
w('| Linha | Comprimento (m) | Cruzamentos com a rede | Conduz fluxo (m) | Maior trecho conduzindo (m) | Pontos de risco |\n|---|---|---|---|---|---|')
for l_ in sorted(LL, key=lambda q: q['linha']): w(f"| {l_['linha']} | {f(l_['comp_m'])} | {l_['cruzamentos']} | {f(l_['conduz_m'])} | {f(l_['maior_trecho_m'])} | {l_['risco_m']} |")
w(f"\nAs outras {len(AGR['linhas']) - len(LL)} linhas não cruzam a rede nem conduzem fluxo pelos critérios acima. As linhas correm a cerca de 155°, quase em nível na parte voltada para oeste; "
  'onde a encosta vira para noroeste, o declive fica perto de 40° da linha e a água tende a correr ao longo dela.\n')
w('### Limitações\n')
for t_ in ['Derivado do MDT fotogramétrico: sob copa densa o MDT é interpolado e pode errar o relevo fino (sulcos, camalhões, terraços).',
           'Sem calibração com chuva, infiltração ou vazão: mostra direções e concentração, não volume nem frequência de enxurrada.',
           'A área contribuinte vai só até a borda do recorte do voo; o que vem de mais longe não entra na conta.',
           'D8 concentra o fluxo numa direção por célula: em encosta plana gera caminhos paralelos e subestima o espalhamento (o TWI do mapa usa MFD).',
           'Os critérios de condução e de risco são indicativos e não substituem vistoria de campo.']:
    w(f'- {t_}')
w('')

w('## 3. Produção e carbono\n')
w(f'Área de estudo {f(A, 2)} ha. Faixa = conservador a otimista; entre parênteses, o provável.\n')
w('| Indicador | Ano 0 (hoje) | Ano 10 | Ano 30 |\n|---|---|---|---|')
for nome, key, d, g in [('Alimento colhido (kg/ano, fresco)', 'kg_alimento', 0, lambda v: v), ('Alimento (kg/ha/ano)', 'kg_alimento', 0, lambda v: v / A),
                        ('Café beneficiado (sacas/ano)', 'kg_cafe', 1, lambda v: v / 60),
                        ('C na biomassa e serapilheira (t)', 'c_total', 1, lambda v: v), ('CO2e estocado (t)', 'co2e_total', 0, lambda v: v),
                        ('CO2e estocado (t/ha)', 'co2e_total', 1, lambda v: v / A), ('Solo acima da linha de base (t CO2e, baixa confiança)', 'c_solo_ganho', 0, co2),
                        ('Cobertura de copa (%)', 'cobertura', 0, lambda v: v), ('Plantas vivas', 'vivas', 0, lambda v: v)]:
    w(f"| {nome} | " + ' | '.join(f"{fx(key, y, d, g)} ({f(g(ind['provavel'][y][key]), d)})" for y in [0, 10, ANOS]) + ' |')
w(f"\nMédia dos anos 1 a {ANOS}: café {f(media('conservador', 'kg_cafe') / 60, 1)} a {f(media('otimista', 'kg_cafe') / 60, 1)} sacas/ano "
  f"(provável {f(media('provavel', 'kg_cafe') / 60, 1)}); alimento {f(media('conservador', 'kg_alimento'))} a {f(media('otimista', 'kg_alimento'))} kg/ano "
  f"(provável {f(media('provavel', 'kg_alimento'))}).\n")

Pl = mo['plantio']; SV = Pl['sobrevivencia']; PD = Pl['padrao']
sens = {s['variacao']: s for s in mo['sens']}
pc = lambda v: '–' if v is None else (f"+{f(v)}%" if v > 0 else f"{f(v)}%")
w('## 4. Desenho de plantio assumido (premissa a validar)\n')
w(f"> **As plantas nascem das {Pl['linhas_de_cultivo']} linhas de cultivo desenhadas**, não só das árvores detectadas. Em cada linha: "
  f"**banana a cada {f(PD['banana_m'], 0)} m e café a cada {f(PD['cafe_m'], 1)} m entre as bananas** ({len([j for j in range(1, 50) if PD['cafe_m'] and j * PD['cafe_m'] < PD['banana_m'] - 0.5 * PD['cafe_m']])} cafés a cada {f(PD['banana_m'], 0)} m). O padrão é deslocado {f(PD['alterna_m'], 0)} m entre linhas vizinhas, "
  "para alternar. Árvores detectadas com 2,5 m ou mais ocupam o ponto mais próximo (serviço ≥ 5 m, frutífera de 2,5 a 5 m). Nenhuma espécie foi informada.\n")
w(f"- Linhas: {Pl['linhas_feicoes']} feições, tratadas como não orientadas (155° e 335° viram uma só direção, azimute médio {f(Pl['azimute_medio'], 1)}°). "
  f"Somam {f(Pl['comprimento_total_m'])} m, com {f(Pl['comprimento_dentro_m'])} m dentro da área e {f(Pl['comprimento_fora_m'])} m fora. "
  f"{'Nenhuma linha fora da área.' if not Pl['linhas_com_trecho_fora'] else 'Há linhas com trecho fora: ' + str(Pl['linhas_com_trecho_fora'])} "
  f"{'Nenhuma linha cruzando outra.' if not Pl['linhas_cruzando'] else 'Linhas cruzando: ' + str(Pl['linhas_cruzando'])}")
w(f"- Entrelinha real: mínimo {f(Pl['entrelinha_m']['min'], 2)} m, mediana {f(Pl['entrelinha_m']['mediana'], 2)} m, máximo {f(Pl['entrelinha_m']['max'], 2)} m. "
  "O valor medido antes pelo orto era 4,0 m: a mediana confere, mas o espaçamento entre linhas varia mais do que uma grade regular supõe.")
w(f"- **Pontos de plantio: {f(Pl['pontos'])}**, sendo {f(Pl['por_tipo']['banana'])} bananas, {f(Pl['por_tipo']['cafe'])} cafés e {f(Pl['por_tipo']['arvore'])} árvores.")
w(f"  - **Medidos**: {f(Pl['por_status']['medido'])}. Detectado a até 1,5 m de um ponto herda a altura e a copa medidas. "
  f"{Pl['medidos_extra_sem_ponto_livre']} detectados estavam na linha mas sem ponto livre e entraram como pontos extras.")
w(f"  - **Não detectados**: {f(Pl['por_status']['nao_detectado'])}. Entram pequenos e visíveis desde o ano 0: café de 0,3 a 0,6 m, banana de 0,5 a 1,2 m.")
w(f"  - **Fora da linha**: {Pl['fora_da_linha_arvores_incluidas']} árvores a mais de 1,5 m de qualquer linha (possível remanescente ou espontânea), incluídas. "
  f"{Pl['fora_da_linha_pequenos_excluidos']} detectados pequenos fora da linha ficaram de fora.")
w(f"- **Inconsistência de idade**: {f(Pl['bananas_nao_detectadas_pct'])}% das bananeiras e {f(Pl['cafes_nao_detectados_pct'])}% dos cafés previstos não aparecem no CHM. "
  f"Plantio em {mo['ano_plantio']} não explica isso: uma bananeira de 3 anos teria 2,5 m ou mais e seria detectada. "
  f"Por isso os não detectados são tratados como **coorte mais nova (replantio), com {Pl['idade_nao_detectados']} ano no ano 0**. Premissa a validar. "
  "Outra explicação possível é que essas posições nunca foram plantadas ou tiveram perda alta.\n")
w('### Sobrevivência dos não detectados por cenário (ano 0)\n')
w('| Cenário | Não detectados vivos no ano 0 | Plantas no ano 0 |\n|---|---|---|')
for k, nome in CEN:
    w(f"| {nome} | {f(SV[k] * 100)}% | {f(Pl['plantas_por_cenario'][k])} |")
w('\nOs medidos valem para os três cenários. Depois do ano 0, todos seguem a mortalidade anual (3%/ano até 5 anos de idade, 1%/ano depois). O cenário provável é o padrão do site.\n')
w('### Quanto a densidade de café muda o resultado\n')
w(f"Base provável: café a cada {f(PD['cafe_m'], 1)} m, {f(sb['cafe_t'], 1)} t de café beneficiado em 30 anos, {f(sb['co2e30'], 0)} t CO2e no ano 30.\n")
w('| Variação | Alimento (30 anos) | Café (30 anos) | CO2e ano 30 |\n|---|---|---|---|')
for v in ['sem café', 'café a cada 2 m (1 entre bananas)', 'café a cada 0,5 m (7 entre bananas)', 'desenho anterior: banana 6 m, café 1,5 m', 'banana a cada 3 m', 'banana a cada 6 m']:
    s = sens.get(v)
    if s: w(f"| {v} | {pc(s['d_alimento_t_pct'])} | {pc(s['d_cafe_t_pct'])} | {pc(s['d_co2e30_pct'])} |")
w('\nMais café quase não muda o alimento: a pequena queda vem da sombra que o café faz sobre a banana nova. '
  'Mais café aumenta o carbono, porque é biomassa lenhosa a mais. A banana é que define o alimento.\n')

w('## 5. Premissas não confirmadas e quanto mudam o resultado\n')
w('Cada linha muda uma premissa e mantém o resto no provável. Base: '
  f"{f(sb['alimento_t'], 1)} t de alimento em 30 anos, {f(sb['co2e30'], 0)} t CO2e na biomassa e serapilheira no ano {ANOS}, {f(sb['solo30'], 0)} t CO2e no solo.\n")
w('| Premissa não confirmada | Variação testada | Alimento | Café | CO2e ano 30 | Solo |\n|---|---|---|---|---|---|')
for s in [s for s in mo['sens'] if 'kcal' not in s['variacao']]:
    w(f"| **{s['premissa']}** | {s['variacao']} | {pc(s['d_alimento_t_pct'])} | {pc(s['d_cafe_t_pct'])} | {pc(s['d_co2e30_pct'])} | {pc(s['d_solo30_pct'])} |")
w('\nLeitura rápida:')
w('- **Desenho de plantio** e **sobrevivência** são as premissas de maior efeito no alimento, porque definem quantas bananeiras existem.')
w('- No carbono, o que manda é o porte e a densidade da madeira das árvores de serviço, seguidos da densidade de café.')
w('- **Café arábica a 454 m e 23 a 24 °C** está acima da faixa térmica ótima (cerca de 18 a 22 °C). Por isso a produtividade usada é baixa: 0,10 a 0,45 kg de café beneficiado por planta no pico.')
w('- **Uso anterior** só muda o solo, e o solo é o componente de menor confiança.')
w('- **Ano de plantio** e **idade dos não detectados** mudam pouco: as alturas iniciais ancoram o estado de hoje. **Manejo** muda até 15%.\n')

w('## 6. Dados e estado medido (ano 0)\n')
w(f"- CRS EPSG:31984 (SIRGAS 2000 / UTM 24S). Orto 0,10 m, MDS 0,24 m, MDT 0,48 m, alinhados e sem nodata. Recorte de {f(D['recorte_ha'], 2)} ha; área de estudo dentro dele.")
w(f"- Centro em {f(abs(D['centro']['lat']), 4)}° S e {f(abs(D['centro']['lon']), 4)}° O (Cambuci, RJ). Altitude de {f(D['altitude_m']['min'])} a {f(D['altitude_m']['max'])} m; declividade média de {f(D['declividade_pct']['media'])}%, com a encosta virada para oeste.")
w('- Clima provável: Köppen Aw (inverno seco), cerca de 1.100 a 1.300 mm/ano e 23 a 24 °C. Bioma Mata Atlântica, floresta estacional semidecidual.')
w(f"- CHM (MDS − MDT, filtro de mediana, < 0,3 m = 0): p90 {f(D['chm_m']['p90'], 1)} m, máximo {f(D['chm_m']['max'], 1)} m.")
w(f"- Linhas de plantio: azimute {f(L['azimute_graus'], 1)}°, entrelinha {f(L['entrelinha_m'], 1)} m (FFT e autocorrelação do ExG), {L['n_linhas_com_plantas']} linhas com plantas. "
  f"O espaçamento mais frequente entre plantas detectadas é {f(L['entre_plantas_detectadas_m']['moda_aprox'], 1)} m.")
w(f"- Indivíduos (máximos locais e watershed no CHM): {I['total']} no total. São {I['por_estrato'].get('arboreo_alto', 0)} arbóreos altos (≥ 5 m), "
  f"{I['por_estrato'].get('arboreo_medio', 0)} médios (2,5 a 5 m) e {I['por_estrato'].get('arbustivo', 0)} arbustivos (0,6 a 2,5 m). Cobertura de copa: {f(I['cobertura_copas_detectadas_pct'], 1)}%.")

w('\n## 7. Método\n')
w('- **Grupos**: nenhuma espécie foi informada. Árvores: arbóreo alto detectado = serviço/madeira, médio = frutífera. Banana e café vêm do desenho de plantio das linhas (seção 2). Todos marcados "espécie não informada".')
w('- **Crescimento**: Chapman-Richards H(t) = 0,3 + (Hmax − 0,3)(1 − e^(−kt))^1,3, e copa com curva própria. O k de cada grupo reproduz a mediana medida na idade de hoje (3 anos). '
  'Cada planta medida recebe uma idade fisiológica que reproduz a sua altura e um fator de copa que reproduz a sua copa. Assim, o ano 0 é o CHM. '
  'Os não detectados seguem a curva da espécie a partir do porte inicial.')
w('- **Competição por luz**: a fração da copa coberta por copas mais altas, ponderada pela opacidade, reduz o crescimento e a produção. A bananeira é retirada após 2 anos com mais de 80% de sombra. '
  'Árvores com mais de 70% de sombra têm mortalidade extra (autodesbaste).')
w('- **Mortalidade**: 3%/ano até 5 anos de idade e 1%/ano depois (os não detectados contam a idade da coorte de replantio). Plantas mortas e bananeiras retiradas viram serapilheira.')
w('- **Poda**: 30% da copa das árvores de serviço por ano. O material (25% da biomassa aérea é copa leve) fica no solo e decai como serapilheira.')
w('- **Alimento**: curva por idade (início, pico, platô, declínio) × kg/planta no pico × redução por sombra × fator de adubação. Preço e custo por cultura na seção 1.')
w('- **Carbono**: DAP = 0,557 (H × copa)^0,809 (Jucker et al. 2017); biomassa aérea = 0,0673 (ρ D² H)^0,976 (Chave et al. 2014), com ρ na faixa do Global Wood Density Database. '
  'Banana e café usam equações próprias (premissas). Raízes: razão IPCC de 0,20 (0,15 a 0,25). Fração de carbono 0,47; CO2e = C × 44/12. '
  'O sequestro líquido do ano é a variação do estoque de biomassa e serapilheira: a colheita sai do sistema e não conta, a poda deixada no solo conta.')
w('- **Solo**: IPCC Tier 1, 0 a 30 cm, SOCref de 47 a 65 t C/ha. Fator da pastagem degradada de 0,97 a 0,70; fator do SAF de 1,00 a 1,17 (por analogia, premissa). '
  'Transição linear em 20 anos desde 2023. **Baixa confiança**: mostrado à parte e não somado ao estoque principal.')
w(f"- **Checagem com o CHM (ordem de grandeza)**: lenhosas ≥ 2,5 m no ano 0 têm {f(ch['agb_modelo_ano0_lenhosas_t']['provavel'], 2)} t de biomassa aérea pelo modelo. "
  f"Chave 2014 só pela altura (eq. 6a, E = 0) dá {f(ch['agb_chave_altura_diametro_t'], 2)} t; essa equação subestima o DAP de árvores crescidas a céu aberto. "
  f"O volume do dossel ({f(ch['volume_dossel_m3'])} m³) × 0,1 a 0,5 kg/m³ dá {f(ch['agb_volume_dossel_t'][0], 1)} a {f(ch['agb_volume_dossel_t'][2], 1)} t. "
  'O modelo fica dentro da faixa: é o estoque de um sistema jovem, com cerca de 1 t de biomassa lenhosa.\n')

w('## 8. Tabelas por ano\n')
CAM = [('kg_alimento', 'Alimento kg', 0, lambda v: v), ('kg_alimento', 'kg/ha', 0, lambda v: v / A),
       ('kg_cafe', 'Café kg', 0, lambda v: v), ('c_total', 't C', 1, lambda v: v), ('co2e_total', 't CO2e', 1, lambda v: v),
       ('co2e_total', 't CO2e/ha', 1, lambda v: v / A), ('seq_co2e', 'Seq. t CO2e', 1, lambda v: v), ('c_solo_ganho', 'Solo t CO2e', 1, co2),
       ('cobertura', 'Cobertura %', 0, lambda v: v), ('vivas', 'Vivas', 0, lambda v: v)]
for k, nome in CEN:
    w(f'### {nome}\n')
    w('| Ano | ' + ' | '.join(c[1] for c in CAM) + ' |\n|' + '---|' * (len(CAM) + 1))
    for y in [0, 1, 2, 3, 5, 10, 15, 20, 25, 30]:
        if y > ANOS: continue
        I_ = ind[k][y]
        w(f"| {y} ({ANO0 + y}) | " + ' | '.join(f(None if I_[c[0]] is None else c[3](I_[c[0]]), c[2]) for c in CAM) + ' |')
    w('')
w('Séries completas, ano a ano: `tabelas/anual_*.csv`. Sensibilidade: `tabelas/sensibilidade.csv`.\n')

w('## 9. Limitações\n')
for t in ['Nenhum número tem validação de campo: nem contagem de plantas, nem espécie, nem DAP, nem colheita, nem solo.',
          'Espécie não se distingue pelo orto. As árvores vêm do estrato; banana e café vêm de um desenho de plantio assumido (6 m e 1,5 m), sem conferência de campo.',
          'Plantas abaixo de cerca de 0,6 m não aparecem no CHM. A existência dos não detectados é suposta pelo desenho das linhas, não observada; a sobrevivência de 50 a 95% é premissa.',
          'O MDT de 0,48 m e o filtro do CHM suavizam plantas finas: bananeira e café jovens tendem a sair mais baixos do que são.',
          'Renques densos de árvores altas podem ter sido divididos em menos indivíduos do que existem.',
          'A sombra é vertical (sobreposição de copas), sem trajetória do sol. Pasto e capim do sub-bosque não são simulados nem no estoque nem na linha de base.',
          'Plantas mortas não são repostas, então depois de cerca de 15 anos o estoque fica estável ou cai devagar. O café não tem recepa.',
          'Clima constante, sem seca extrema, pragas, fogo ou mudança de manejo ao longo dos 30 anos.',
          'O solo segue o IPCC Tier 1 com fator do SAF por analogia. A ordem de grandeza é plausível; o valor não é.',
          'Carbono aqui não é crédito: falta adicionalidade, permanência, linha de base aprovada, medição de campo e verificação por terceiro.']:
    w(f'- {t}')
w('\n## 10. Como corrigir e regerar\n')
w('1. Corrija `fase1/individuos_detectados.geojson` (preencha `especie`, apague falsos, acrescente plantas) e salve como `fase1/individuos_corrigidos.geojson`.')
w('2. Ajuste `projeto.yaml` (ano de plantio, manejo, grupos) e `parametros_especies.yaml` (valores, fontes e confiança).')
w('3. Linhas ou desenho de plantio novos: edite `linhas_cultivo.geojson` ou o bloco `saf.plantio` do `projeto.yaml`.')
w('4. Rode `analise\\qpy.bat pipeline\\rodar.py --de 2`. Isso refaz os pontos de plantio, o modelo, o site e este relatório. Só com parâmetros novos, use `--de 4`.\n')
w('Arquivos: `fase1/` (diagnóstico e indivíduos detectados), `fase1b/` (linhas tratadas, pontos de plantio e imagem de conferência), `parametros_especies.yaml`, '
  '`tabelas/`, `site/index.html`. A versão anterior (grade 4 × 3 m) está em `v1/`.')
open(os.path.join(ROOT, 'relatorio.md'), 'w', encoding='utf-8').write('\n'.join(L_) + '\n')
print('relatorio.md gerado')
