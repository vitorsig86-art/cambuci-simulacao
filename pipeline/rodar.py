# Roda o pipeline de uma propriedade na ordem certa.
#
#   python pipeline/rodar.py                 # roda tudo a partir da pasta do projeto (onde está projeto.yaml)
#   python pipeline/rodar.py --de 7          # retoma da etapa 7
#   python pipeline/rodar.py --de 3 --ate 3  # só uma etapa
#   python pipeline/rodar.py --raiz D:/fazenda_x --lista
#
# Para sozinho nas duas decisões manuais (keypoint e espigões) quando elas ainda estão vazias no projeto.yaml.
import os, sys, subprocess, argparse, time, yaml

AQUI = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(AQUI, 'scripts')

# (nº, nome, scripts, obrigatória)
ETAPAS = [
    (1,  'MDT em grade de 1 m',                 ['01_dem1m.py'], True),
    (2,  'Hidrologia (acúmulo de fluxo)',       ['hydro.py'], True),
    (3,  'Eixo do vale e perfil (keypoint)',    ['03_eixo_vale.py'], True),
    (4,  'Keyline global e distância assinada', ['keyline.py'], True),
    (5,  'Linhas keyline e em nível',           ['rows.py'], True),
    (6,  'Curvatura (desenhar espigões)',       ['05_curvatura.py'], True),
    (7,  'Blocos e guias',                      ['zones.py'], True),
    (8,  'Linhas por faixas e pés',             ['bands.py'], True),
    (9,  'Diagnóstico: deriva e mapa',          ['drift.py', 'mapa.py'], False),
    (10, 'Base 3D: terreno, orto, árvores',     ['prep2.py'], True),
    (11, 'Cenários base (existentes, keyline)', ['cenarios.py'], True),
    (12, 'Água: escoamento por cenário',        ['agua.py'], True),
    (13, 'Terreno: declividade, face, sol, TWI',['terreno.py', 'painel.py'], True),
    (14, 'Zona mecanizável',                    ['mec.py'], True),
    (15, 'Os 5 desenhos',                       ['cen2.py'], True),
    (16, 'Texturas temáticas',                  ['16_texturas.py'], True),
    (17, 'Rota do trator e métricas',           ['rota2.py', '17b_metricas_rota.py'], True),
    (18, 'Montar site/index.html',              ['18_montar_html.py'], True),
]

# modo saf_existente: agrofloresta já implantada (detecção, posições, base 3D, modelo, site)
ETAPAS_SAF = [
    (1, 'Diagnóstico, CHM, linhas e copas',     ['saf_01_deteccao.py'], True),
    (2, 'Esqueleto de plantio pelas linhas',    ['saf_02b_plantio.py'], True),   # v1: saf_02_posicoes.py (grade 4 x 3)
    (3, 'Base 3D, entorno, terreno, análise e água', ['saf_03_base3d.py', 'saf_03b_entorno.py', 'saf_03c_terreno.py', 'saf_03d_agua.py'], True),
    (4, 'Modelo: crescimento, alimento, carbono', ['saf_04_modelo.py'], True),
    (5, 'Montar site/index.html',               ['saf_05_montar_html.py'], True),
    (6, 'Relatório (relatorio.md)',             ['saf_06_relatorio.py'], True),
]

# modo implantacao: plantio novo sobre pasto (diagnóstico, base e água, estradas, plantio, modelo, site)
ETAPAS_IMP = [
    (1, 'Diagnóstico: rasters, clima, CHM, linhas', ['imp_01_diagnostico.py'], True),
    (2, 'Base 3D, entorno, terreno, água e estradas', ['saf_03_base3d.py', 'saf_03b_entorno.py', 'saf_03c_terreno.py', 'saf_03d_agua.py', 'imp_03e_estradas.py'], True),
    (3, 'Plantio e quebra-vento', ['imp_02_plantio.py'], True),
    (4, 'Modelo de 30 anos', ['imp_04_modelo.py'], True),
    (5, 'Montar site/index.html', ['imp_05_montar_html.py'], True),
    (6, 'Relatório: com e sem quebra-vento (relatorio.md)', ['imp_06_relatorio.py'], True),
]

def vazio(v): return v is None or v == '' or v == []

def parada(n, cfg):
    kl = cfg['keyline']; bl = cfg['blocos']
    if n == 3 and (vazio(kl.get('keypoint')) or vazio(kl.get('cota'))):
        return ("DECISÃO 1 (keypoint). Leia o perfil e a SUGESTÃO impressos acima e preencha em projeto.yaml:\n"
                "  keyline.cota, keyline.keypoint [E, N] e, se quiser cortar a cabeceira plana, keyline.eixo_cota_max.\n"
                "  Se o eixo saiu no vale errado, defina keyline.eixo_colunas [c0, c1] (colunas da grade de 1 m) e rode --de 3.\n"
                "Depois: python pipeline/rodar.py --de 4")
    if n == 6 and bl.get('espigoes') is None:
        return ("DECISÃO 2 (espigões). Abra work/curv.png (vermelho = espigão, números = linha/coluna a cada 25 m) e preencha:\n"
                "  blocos.espigoes: lista de polilinhas [[linha, coluna], ...] cruzando o perímetro de ponta a ponta\n"
                "  blocos.ids (oeste -> leste, um a mais que o nº de espigões), blocos.nomes e blocos.vale.\n"
                "  Área sem espigão relevante: espigoes: [] e um único bloco.\n"
                "Depois: python pipeline/rodar.py --de 7")
    return None

def normaliza_perimetro(f):
    # os scripts esperam 1 Polygon 2D em features[0]; KML/QGIS costumam gravar Z ou MultiPolygon
    import json
    g = json.load(open(f, encoding='utf-8')); geo = g['features'][0]['geometry']
    co = geo['coordinates'][0] if geo['type'] == 'Polygon' else max(geo['coordinates'], key=lambda p: len(p[0]))[0]
    if geo['type'] == 'Polygon' and all(len(p) == 2 for p in co) and len(g['features']) == 1: return
    os.replace(f, f.replace('.geojson', '_original.geojson'))
    feat = dict(type='Feature', properties={}, geometry=dict(type='Polygon', coordinates=[[p[:2] for p in co]]))
    json.dump(dict(type='FeatureCollection', features=[feat]), open(f, 'w', encoding='utf-8'))
    print('perímetro normalizado para 1 polígono 2D (original guardado como perimetro_original.geojson)')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raiz', default=os.getcwd(), help='pasta do projeto (tem projeto.yaml e dados/)')
    ap.add_argument('--de', type=int, default=1); ap.add_argument('--ate', type=int, default=18)
    ap.add_argument('--sem-diagnostico', action='store_true', help='pula a etapa 9')
    ap.add_argument('--lista', action='store_true')
    a = ap.parse_args()
    raiz = os.path.abspath(a.raiz)
    if a.lista:
        for n, nome, ss, ob in ETAPAS: print(f'{n:>2}  {nome:<38} {" + ".join(ss)}{"" if ob else "  (opcional)"}')
        return
    yml = os.path.join(raiz, 'projeto.yaml')
    if not os.path.exists(yml): sys.exit(f'Não achei {yml}. Copie pipeline/projeto.modelo.yaml para a raiz do projeto.')
    cfg = yaml.safe_load(open(yml, encoding='utf-8'))
    dados = os.path.join(raiz, cfg['dados']['pasta'])
    if cfg.get('modo') in ('saf_existente', 'implantacao'): return main_saf(a, raiz, cfg, dados)
    falta = [f for f in ['orto.tif', 'mdt.tif', 'mds.tif', 'perimetro.geojson'] if not os.path.exists(os.path.join(dados, f))]
    if falta: sys.exit(f'Faltam em {dados}: {", ".join(falta)}')
    normaliza_perimetro(os.path.join(dados, 'perimetro.geojson'))
    env = dict(os.environ, PROJETO=raiz, PYTHONPATH=SC + os.pathsep + os.environ.get('PYTHONPATH', ''), PYTHONIOENCODING='utf-8', MPLBACKEND='Agg')
    os.makedirs(os.path.join(raiz, 'work'), exist_ok=True)
    for n, nome, ss, ob in ETAPAS:
        if n < a.de or n > a.ate: continue
        if n == 9 and a.sem_diagnostico: continue
        for s in ss:
            t = time.time(); print(f'\n=== {n}. {nome}: {s}', flush=True)
            r = subprocess.run([sys.executable, os.path.join(SC, s)], cwd=raiz, env=env)
            if r.returncode != 0:
                if ob: sys.exit(f'Etapa {n} ({s}) falhou. Corrija e rode: python pipeline/rodar.py --de {n}')
                print(f'(etapa opcional {s} falhou, seguindo)')
            print(f'--- {s} ok em {time.time()-t:.0f} s')
        msg = parada(n, cfg)
        if msg and n < a.ate: print('\n' + '=' * 70 + '\n' + msg + '\n' + '=' * 70); return
    if a.ate >= 18: print('\nPronto: ' + os.path.join(raiz, 'site', 'index.html'))

def main_saf(a, raiz, cfg, dados):
    D = cfg['dados']
    falta = [f for f in ['orto.tif', 'mdt.tif', 'mds.tif', D.get('area_estudo', 'area_estudo.geojson'), D.get('recorte', 'bbox.geojson')]
             if not os.path.exists(os.path.join(dados, f))]
    if falta: sys.exit(f'Faltam em {dados}: {", ".join(falta)}')
    env = dict(os.environ, PROJETO=raiz, PYTHONPATH=SC + os.pathsep + os.environ.get('PYTHONPATH', ''), PYTHONIOENCODING='utf-8', MPLBACKEND='Agg')
    LISTA = ETAPAS_IMP if cfg.get('modo') == 'implantacao' else ETAPAS_SAF
    ate = min(a.ate, len(LISTA))
    for n, nome, ss, ob in LISTA:
        if n < a.de or n > ate: continue
        for s in ss:
            t = time.time(); print(f'\n=== {n}. {nome}: {s}', flush=True)
            r = subprocess.run([sys.executable, os.path.join(SC, s)], cwd=raiz, env=env)
            if r.returncode != 0: sys.exit(f'Etapa {n} ({s}) falhou. Corrija e rode: python pipeline/rodar.py --de {n}')
            print(f'--- {s} ok em {time.time()-t:.0f} s')
    if ate >= len(LISTA): print('\nPronto: ' + os.path.join(raiz, 'site', 'index.html'))

if __name__ == '__main__': main()
