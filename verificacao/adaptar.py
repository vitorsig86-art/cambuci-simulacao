"""Adapta a cópia; deve rodar uma vez, após preparar.py."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def edit(rel,fn):
    p=R/rel;s=p.read_text(encoding='utf-8');p.write_text(fn(s),encoding='utf-8')
def diag(s):
    a=s.index('# ---------- 3. clima');b=s.index('# ---------- 4. CHM')
    s=s[:a]+'''# Clima local não fornecido: nenhuma temperatura ou aptidão é estimada.
diag['clima'] = dict(disponivel=False, alertas=['Clima local indisponível; aptidão não avaliada'],
                     metodo='Demonstração condicional de café e banana, sem diagnóstico de aptidão')

'''+s[b:]
    s=s.replace("orig_l.append(dict(i=i, geo=L, cota=cota))","orig_l.append(dict(i=i, geo=L, cota=cota, id_origem=f['properties']['id_origem'], elevation_original=f['properties'].get('ELEVATION')))")
    s=s.replace("[round(x, 3), round(y, 3)]", "[x, y]")
    s=s.replace("'feicao_original': p['orig'] + 1", "'feicao_original': p['orig'] + 1, 'id_origem': orig_l[p['orig']]['id_origem'], 'id_trecho': p['linha'], 'ELEVATION_original': orig_l[p['orig']]['elevation_original'], 'z_cena': 'MDT, atributo original não usado para assentamento'")
    needle="json.dump(diag, open(os.path.join(F1, 'diagnostico.json')"
    idx=s.index(needle);s=s[:idx]+"from territorio_cambuci import complementar\ncomplementar(diag, pecas, orig_l, keep, excl)\n"+s[idx:]
    return s
edit('pipeline/scripts/imp_01_diagnostico.py',diag)
def roads(s):
    idx=s.index("json.dump(site, open(os.path.join(WORK, 'estradas.json')")
    s=s[:idx]+'''# Contrato sem vias: arrays preservados, métricas indisponíveis em vez de zeros observados.
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
''' +s[idx:]
    return s
edit('pipeline/scripts/imp_03e_estradas.py',roads)
def plants(s):
    s=s.replace("MEIA = EST['meia']","MEIA = EST['meia'] or 0.0")
    s=s.replace("abertura_estrada_m=2 * MEIA", "abertura_estrada_m=2 * MEIA if EIXOS else None")
    s=s.replace("corredor_estradas_na_area_m2=round(AREA.intersection(COR).area, 0)","corredor_estradas_na_area_m2=round(AREA.intersection(COR).area, 0) if EIXOS else None")
    # Registra orientação efetivamente usada, baseada na normal externa mais próxima.
    s=s.replace("res['quebra_vento'] =",'''qv['bordas_usadas'] = sorted({['norte','nordeste','leste','sudeste','sul','sudoeste','oeste','noroeste'][int(round((np.degrees(np.arctan2((PP.exterior.interpolate(PP.exterior.project(Point(x,y))).x-x),(PP.exterior.interpolate(PP.exterior.project(Point(x,y))).y-y)))+360)%360/45))%8] for x,y in QVT})
    qv['status'] = 'hipótese demonstrativa; vento de 45° não medido'
    res['quebra_vento'] =''')
    s=s.replace("f\"cortados no corredor da estrada: {ct['estrada']['cafe']} cafés e {ct['estrada']['banana']} bananas | junto ao quebra-vento:", "f\"vias indisponíveis; junto ao quebra-vento:")
    return s
edit('pipeline/scripts/imp_02_plantio.py',plants)
def base(s):
    s=s.replace("resampleAlg='average').ReadAsArray()", "dstSRS=CFG['crs'], resampleAlg='average').ReadAsArray()")
    s=s.replace("resampleAlg='near')", "dstSRS=CFG['crs'], resampleAlg='near')")
    s=s.replace("zmin = float(Z.min());", "assert np.isfinite(Z).all() and Z.max()-Z.min()<655.35\nzmin = float(Z.min());")
    return s
edit('pipeline/scripts/saf_03_base3d.py',base)
def html(s):
    s=s.replace("site = dict(W=", "site = dict(georreferencia=dict(id=CFG['id'], crs=CFG['crs'], origem_SW=[b['X0'],b['Y0']], extensao=[b['X0'],b['Y0'],b['X0']+b['W'],b['Y0']+b['H']], eixos='X leste; Y vertical; Z sul (norte negativo); centrado em W/2,H/2', pixel='centro: E=X0+(c+0.5)*passo, N=Y1-(r+0.5)*passo', passo_m=b['res'], unidade_vertical='m', datum_vertical=None,zmin=b['zmin'], entradas=json.load(open(os.path.join(ROOT,'verificacao','entradas.json'),encoding='utf-8'))['entradas']), W=")
    s=s.replace("cfg=dict(lat=", "cfg=dict(id=CFG['id'], fuso=CFG['fuso'], utc_offset_h=CFG['utc_offset_h'],base_monetaria=CFG['base_monetaria'],pendentes=CFG['pendentes'],lat=")
    return s
edit('pipeline/scripts/imp_05_montar_html.py',html)
print('Adaptações territoriais aplicadas na cópia')
