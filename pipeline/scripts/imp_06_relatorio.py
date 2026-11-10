# Etapa IMP 6. Relatório curto (relatorio.md): os dois desenhos, com e sem quebra-vento, lado a lado, e o que na diferença vem de premissa.
# Usa o mesmo motor econômico do site (pipeline/site/economia.js, via node). Rodar depois da etapa 5.
import subprocess
from saf_comum import *

aqui = os.path.dirname(os.path.abspath(__file__))
MOJ = os.path.join(WORK, 'modelo.json'); PEJ = os.path.join(WORK, 'economia_parametros.json')
MO = json.load(open(MOJ, encoding='utf-8'))
import shutil
# o ambiente do QGIS (o4w_env) troca o PATH: procura o node também na pasta padrão e em NODE_EXE
NODE = os.environ.get('NODE_EXE') or shutil.which('node') or next((p for p in [r'C:\Program Files\nodejs\node.exe', r'C:\Program Files (x86)\nodejs\node.exe'] if os.path.exists(p)), None)
if not NODE: raise SystemExit('node não encontrado: instale o Node.js ou defina NODE_EXE com o caminho do node.exe')
r = subprocess.run([NODE, os.path.join(aqui, '..', 'site', 'economia_cli.js'), MOJ, PEJ], capture_output=True, text=True, encoding='utf-8')
if r.returncode != 0: raise SystemExit('node economia_cli.js falhou:\n' + r.stderr)
EC = json.loads(r.stdout)['des']
PAR = yaml.safe_load(open(os.path.join(ROOT, SAF['parametros']), encoding='utf-8'))
PE = json.load(open(PEJ, encoding='utf-8')); QV = CFG['quebra_vento']
ANOS = MO['anos']; ANO0 = MO['ano0']; A = MO['area_ha']

def n(v, d=0): return '–' if v is None else f'{v:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
def rs(v): return '–' if v is None else ('−' if v < 0 else '') + 'R$ ' + n(abs(v))
def sinal(v, f=n): return ('+' if v > 0 else '−' if v < 0 else '') + f(abs(v))
pct = lambda d: ' · '.join(n(100 * d[k]) + '%' for k in 'cpo')
tri = lambda d, dec=0: ' · '.join(n(d[k], dec) for k in 'cpo')
CEN = [('conservador', 'Conservador'), ('provavel', 'Provável'), ('otimista', 'Otimista')]
DES = [('com', 'com quebra-vento'), ('sem', 'sem quebra-vento')]
ind = lambda d, c: (MO['cen'] if d == 'com' else MO['des']['sem']['cen'])[c]['ind']
cont = {d: EC[d]['contagens'] for d, _ in DES}
YR = 10   # ano de referência da receita (lavoura formada, antes da primeira recepa)

L = ['> HIPÓTESE demonstrativa de café, banana e grevílea. Espécies, uso anterior, data, manejo, clima, carbono e economia pendentes de validação local. Não constitui diagnóstico de aptidão.\n']
L.append(f"# {CFG['nome']}: com e sem quebra-vento\n")
L.append(f"Área de {n(A, 2)} ha, plantio hipotético em {ANO0}, {ANOS} anos, R$ constantes de 2026, taxa real de {n(100 * EC['com']['padroes']['taxa'], 1)}% a.a., mão de obra própria valorizada pela diária. "
         "Estimativa de modelagem, sem validação de campo. Os mesmos números estão no site (seletor Desenho).\n")
L.append('## Os dois desenhos\n')
L.append('| | Com quebra-vento | Sem quebra-vento | Diferença |\n|---|---:|---:|---:|')
for k, nome in (('cafe', 'Pés de café'), ('banana', 'Bananeiras'), ('grevilea', 'Grevíleas')):
    L.append(f"| {nome} | {n(cont['com'][k])} | {n(cont['sem'][k])} | {sinal(cont['sem'][k] - cont['com'][k])} |")
L.append(f"\nSem o renque, café e banana ocupam as linhas inteiras, inclusive a faixa de {n(float(QV['recuo_cafe_m']), 0)} m junto às grevíleas. "
         'Não há faixa protegida, faixa de competição, sombra de grevílea nem custo de muda, plantio e desrama do renque.\n')
L.append('## Resultado por cenário\n')
L.append(f'| Cenário | Desenho | Café em {ANOS} anos (sc) | Receita no ano {YR} ({ANO0 + YR}) | Acumulado em {ANOS} anos | Ano de retorno | VPL | VPL sem pró-labore | CO2e no ano {ANOS} (t) |\n|---|---|---:|---:|---:|---:|---:|---:|---:|')
for c, cn in CEN:
    for d, dn in DES:
        e = EC[d]['cen'][c]; R = e['com']
        L.append(f"| {cn} | {dn} | {n(sum(x['sacas'] for x in e['rows']), 0)} | {rs(e['rows'][YR]['receita'])} | {rs(R['final'])} | {'não retorna' if R['payback_anos'] is None else 'ano ' + str(R['payback_anos'])} | {rs(R['vpl'])} | {rs(e['sem']['vpl'])} | {n(ind(d, c)[-1]['co2e_total'], 0)} |")
    a, b = EC['com']['cen'][c], EC['sem']['cen'][c]
    L.append(f"| {cn} | diferença (sem − com) | {sinal(sum(x['sacas'] for x in b['rows']) - sum(x['sacas'] for x in a['rows']))} | {sinal(b['rows'][YR]['receita'] - a['rows'][YR]['receita'], rs)} | {sinal(b['com']['final'] - a['com']['final'], rs)} | "
             f"{'–' if a['com']['payback_anos'] is None or b['com']['payback_anos'] is None else sinal(b['com']['payback_anos'] - a['com']['payback_anos']) + ' ano(s)'} | {sinal(b['com']['vpl'] - a['com']['vpl'], rs)} | {sinal(b['sem']['vpl'] - a['sem']['vpl'], rs)} | {sinal(ind('sem', c)[-1]['co2e_total'] - ind('com', c)[-1]['co2e_total'])} |")
L.append('')
# o peso da premissa de vento no desenho sem quebra-vento (sensibilidade do provável)
sv = {s['nome']: s for s in EC['sem']['sens']}; base_com = EC['com']['cen']['provavel']['com']['vpl']; base_sem = EC['sem']['cen']['provavel']['com']['vpl']
v0 = next((s for k, s in sv.items() if 'perda zero' in k), None); v20 = next((s for k, s in sv.items() if '20%' in k), None)
E = PAR['efeitos']; pv = E['perda_vento_sem_protecao']; pc = E['perda_faixa_competicao']; I = PE['implantacao']; Cu = PE['custeio']
L.append('## O que na diferença vem de premissa\n')
L.append('Vem da geometria (dado do desenho):\n')
L.append(f"- Contagem de pés: {sinal(cont['sem']['cafe'] - cont['com']['cafe'])} cafés e {sinal(cont['sem']['banana'] - cont['com']['banana'])} bananeiras sem o renque, {n(cont['com']['grevilea'])} grevíleas a menos. "
         f"Depende só do recuo de {n(float(QV['recuo_cafe_m']), 1)} m entre grevílea e café (projeto.yaml, premissa a validar) e da posição do renque.\n")
L.append('Vem de premissa a validar (sem medição local):\n')
L.append(f"- Perda de produção do café exposto ao vento: {pct(pv)} (conservador · provável · otimista). No desenho sem quebra-vento vale para todo o café; no desenho com renque, só para o café fora da faixa protegida. Fonte: {pv['fonte']}.")
L.append(f"- Perda na faixa de competição junto ao renque: {pct(pc)}. Só existe no desenho com quebra-vento.")
L.append(f"- Alcance da proteção: {tri(QV['protecao_alturas'], 1)} vezes a altura do renque, descontado o desnível. Direção do vento: {n(float(CFG['vento']['azimute_de_graus']))}°, sem rosa dos ventos local.")
L.append(f"- Crescimento da grevílea (altura máxima {tri(PAR['especies']['grevilea']['Hmax_m'])} m): define quando a proteção começa e quanto carbono o renque estoca. A diferença de carbono entre os desenhos é quase toda biomassa de grevílea.")
L.append(f"- Custos do renque: muda R$ {tri(I['muda']['grevilea'], 1)}, cova R$ {tri(I['adubo_cova']['grevilea'], 1)}, plantio {tri(I['dias_plantio_muda']['grevilea'], 2)} dia-homem por muda e desrama {tri(Cu['dias_manejo_planta']['grevilea'], 2)} dia-homem por árvore por ano.")
L.append(f"- Produção por pé, preços e custos unitários são os mesmos nos dois desenhos; mudam junto com o cenário.\n")
if v0 and v20:
    L.append(f"Peso da premissa de vento no provável: o VPL do desenho sem quebra-vento é {rs(base_sem)} com perda de {n(100 * pv['p'])}%, {rs(v0['com']['vpl'])} com perda zero e {rs(v20['com']['vpl'])} com perda de 20%. "
             f"O desenho com quebra-vento dá {rs(base_com)}. " + ('Mesmo com perda de 20% o desenho sem renque fica à frente.' if v20['com']['vpl'] > base_com else 'Com perda de 20% o desenho com renque passa à frente.') +
             ' O modelo não conta dano de vento além da produção (quebra de ramos, doença, geada de vento) nem a madeira da grevílea no fim do ciclo.\n')
L.append('Tabelas anuais: `tabelas/anual_<cenario>.csv` (com quebra-vento) e `tabelas/anual_<cenario>_sem_qv.csv` (sem). Sensibilidades: `tabelas/sensibilidade_producao.csv` e `tabelas/sensibilidade_producao_sem_qv.csv`.')
L.append('\n## Território e limites da demonstração\n')
Dg=MO['diag']; Ln=Dg['linhas']['comprimentos_precisos_m']; Ch=Dg['chm_nativo']
L.append(f"Polígono de {n(poligono().area,2)} m² e {n(poligono().length,2)} m de perímetro em EPSG:31984. Centroide: {Dg['centro']['lat']}°, {Dg['centro']['lon']}°. CRS dos vetores atribuído por inferência, sem transformar coordenadas; procedência e datum vertical pendentes.")
L.append(f"Moldura única 200 × 183 m: oeste/sul/leste/norte {X0} / {Y0} / {X1} / {Y1}. Grades de 0,50 m (400 × 366), 1 m (200 × 183) e 0,25 m (800 × 732) compartilham bordas. MDT é a única superfície de assentamento; textura de 2.000 × 1.830 px. A grade 0,25 m reamostra a fonte nativa 0,60 m.")
L.append(f"Linhas: {n(Ln['bruto'],2)} m brutos, {n(Ln['fora'],2)} m fora, 30 trechos e {n(Ln['dentro'],2)} m dentro; 27 trechos e {n(Ln['elegivel'],2)} m elegíveis antes das exclusões. IDs de origem e trecho preservados. Os Z e ELEVATION textuais originais estão nos insumos; a cena usa o MDT.")
L.append(f"CHM nativo, sem filtro: {n(Ch['min'],2)} a {n(Ch['max'],2)} m; {n(Ch['negativos_pct'],2)}% negativo e {n(Ch['maior_igual_2_5_pct'],2)}% ≥ 2,50 m. Negativos preservados em fase1/chm_bruto_nativo.tif. Camada operacional: máscaras validadas, bilinear, clip [0,30] m, mediana 3×3 a 0,25 m, abaixo de 0,30 m zerado. Copas ≥ 2,50 m, abertura morfológica, manchas ≥ 1,5 m² e folga nominal de 1 m: {n(Dg['arvores_existentes']['area_descontada_m2'],1)} m² excluídos.")
L.append('Conferência visual em fase1/mapa_conferencia.png: a grande mancha alta a sudeste coincide com árvores visíveis; os negativos também ocorrem em solo e carreadores abertos e não representam alturas físicas negativas. O diagnóstico não corrige datum ou suposto viés vertical sem pontos de controle. As copas são propostas para preservação, sujeitas à confirmação em campo.')
L.append('Vias indisponíveis: work/estradas.json preserva arrays vazios e métricas indisponíveis. Sem corredores ou indicadores de logística. Proximidade à borda calculada separadamente em fase1/diagnostico.json; não atesta cabeceira ou acessibilidade. Drenagem é indicação estática por MDT, limitada ao voo; vazão e contribuições além da moldura não estimadas.')
Qv=MO['plantio']['quebra_vento']
L.append(f"Quebra-vento demonstrativo: vento assumido de {Qv['azimute_vento_graus']}°, bordas efetivamente usadas: {', '.join(Qv['bordas_usadas'])}. Comprimento {n(Qv['comprimento_m'],1)} m, {Qv['trechos']} trechos, {Qv['arvores']} grevíleas. As exclusões por copa, drenagem e exposição constam de fase2/plantio_resumo.json.")
L.append('Sombra visual: renderização 3D. Efeito produtivo: sobreposição de copas de plantas simuladas, sem calibração local; árvores existentes afetam exclusões e cena, não têm efeito produtivo calibrado. Insolação: céu limpo e horizonte do MDT, independente das copas. Drenagem: rede estática, independente dos anos. Carbono projetado de novas plantas, sem inventário ou crédito certificado; pastagem anterior é apenas linha de base hipotética.')
L.append('Pendentes: '+', '.join(CFG['pendentes'])+'. Se a cultura ou condição inicial confirmada for incompatível, manter o pipeline territorial e adaptar modelo/interface antes de usar projeções. Detalhes de execução e testes em README.md e verificacao/aceite.json. O relatório usa padrões; edições econômicas ficam no navegador e não reescrevem este arquivo.')
json.dump(EC,open(os.path.join(WORK,'economia_relatorio.json'),'w',encoding='utf-8'),ensure_ascii=False,allow_nan=False)
open(os.path.join(ROOT, 'relatorio.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L))
