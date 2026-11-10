# Etapa IMP 1. Diagnóstico da implantação: rasters e vetores, terreno, clima provável e aptidão do arábica,
# árvores existentes (CHM), linhas de cultivo (comprimento, entrelinha, ângulo com a curva de nível, fora da área, cruzamentos).
# Não redesenha nada: só mede e aponta. Saídas: fase1/diagnostico.json, fase1b/linhas_tratadas.geojson (linhas cortadas na área,
# numeradas de baixo para cima), work/excl_arvores.npy (máscara 0,25 m das copas existentes com folga).
from saf_comum import *
from scipy import ndimage as ndi
from shapely.geometry import LineString, shape, box
from shapely.ops import unary_union

PL = CFG['plantio']; CL = CFG.get('clima') or {}
diag = {}
srs = osr.SpatialReference(); srs.ImportFromEPSG(EPSG)
ll = osr.SpatialReference(); ll.ImportFromEPSG(4326); ll.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
geo = poligono(); bb = poligono(RECORTE_GJ)

# ---------- 1. rasters e vetores ----------
ras = {}
for f in ['orto.tif', 'mdt.tif', 'mds.tif']:
    d = gdal.Open(caminho(f)); g = d.GetGeoTransform(); s = osr.SpatialReference(wkt=d.GetProjection())
    ras[f] = dict(epsg=s.GetAuthorityCode(None), res_m=round(g[1], 4), px=[d.RasterXSize, d.RasterYSize], bandas=d.RasterCount,
                  extensao=[round(g[0], 2), round(g[3] + g[5] * d.RasterYSize, 2), round(g[0] + g[1] * d.RasterXSize, 2), round(g[3], 2)],
                  origem=[round(g[0], 3), round(g[3], 3)], nodata=d.GetRasterBand(1).GetNoDataValue())
orig = {tuple(v['origem']) for v in ras.values()}
vet = {}
for k in ['area_estudo', 'recorte', 'linhas', 'estradas']:
    f = CFG['dados'].get(k)
    if not f or not os.path.exists(caminho(f)): continue
    j = json.load(open(caminho(f), encoding='utf-8')); gs = [shape(x['geometry']) for x in j['features']]; u = unary_union(gs)
    vet[f] = dict(crs=(j.get('crs') or {}).get('properties', {}).get('name', 'sem crs declarado'), feicoes=len(gs), tipo=sorted({g_.geom_type for g_ in gs}),
                  extensao=[round(v, 2) for v in u.bounds], dentro_do_recorte=bool(bb.buffer(0.5).contains(u)), tem_z=any(g_.has_z for g_ in gs))
diag['rasters'] = ras; diag['vetores'] = vet
diag['alinhamento'] = dict(mesmo_crs=len({v['epsg'] for v in ras.values()}) == 1 and all(str(EPSG) in v['crs'] for v in vet.values()),
                           mesma_origem=len(orig) == 1, resolucoes_m={k: v['res_m'] for k, v in ras.items()},
                           nota='resoluções diferentes: o pipeline reamostra tudo para uma moldura comum (0,25 a 1 m)',
                           moldura=[X0, Y0, X1, Y1])

# ---------- 2. terreno ----------
cx, cy = geo.centroid.x, geo.centroid.y
lon, lat, _ = osr.CoordinateTransformation(srs, ll).TransformPoint(cx, cy)
diag['area_estudo_ha'] = round(geo.area / 1e4, 4); diag['perimetro_m'] = round(geo.length, 1); diag['recorte_ha'] = round(bb.area / 1e4, 3)
diag['area_dentro_do_recorte'] = bool(bb.buffer(0.5).contains(geo))
diag['centro'] = {'E': round(cx, 1), 'N': round(cy, 1), 'lat': round(lat, 5), 'lon': round(lon, 5)}
z1 = warp('mdt.tif', 1.0, 'average').ReadAsArray().astype(float)
ok = np.isfinite(z1) & (z1 > -1000); idx = ndi.distance_transform_edt(~ok, return_distances=False, return_indices=True); z1 = z1[tuple(idx)]
zf = ndi.gaussian_filter(z1, 1.5); M1 = mask(1.0); H1, W1 = zf.shape
gy, gx = np.gradient(zf, 1.0); gN = -gy
decl = np.hypot(gx, gN) * 100; asp = (np.degrees(np.arctan2(-gx, -gN)) + 360) % 360
v = decl[M1]
diag['altitude_m'] = {k: round(float(f(zf[M1])), 1) for k, f in [('min', np.min), ('media', np.mean), ('max', np.max)]}
diag['declividade_pct'] = {'media': round(float(v.mean()), 1), 'p10': round(float(np.percentile(v, 10)), 1), 'mediana': round(float(np.median(v)), 1),
                           'p90': round(float(np.percentile(v, 90)), 1), 'max': round(float(v.max()), 1)}
ang = np.radians(asp[M1])
face = float((np.degrees(np.arctan2((np.sin(ang) * v).sum(), (np.cos(ang) * v).sum())) + 360) % 360)
ROSA = ['norte', 'nordeste', 'leste', 'sudeste', 'sul', 'sudoeste', 'oeste', 'noroeste']
diag['face_dominante'] = dict(graus=round(face), nome=ROSA[int(round(face / 45)) % 8])

# Clima local não fornecido: nenhuma temperatura ou aptidão é estimada.
diag['clima'] = dict(disponivel=False, alertas=['Clima local indisponível; aptidão não avaliada'],
                     metodo='Demonstração condicional de café e banana, sem diagnóstico de aptidão')

# ---------- 4. CHM: árvores existentes ----------
r = 0.25
bruto, chm = chm_grade(r); M = mask(r); REC = mask(r, RECORTE_GJ)
HA = float(PL.get('arvore_existente_min_m', 2.5)); FOLGA = float(PL.get('arvore_existente_folga_m', 1.0))
arv = ndi.binary_opening(chm >= HA, iterations=1)
lab, n = ndi.label(arv & M); tam = ndi.sum(arv & M, lab, range(1, n + 1)) * r * r if n else np.array([])
keep = np.isin(lab, 1 + np.nonzero(tam >= 1.5)[0])                      # mancha de copa com pelo menos 1,5 m²
excl = ndi.binary_dilation(keep, iterations=int(round(FOLGA / r))) & M
np.save(os.path.join(WORK, 'excl_arvores.npy'), excl)
vc = chm[M]
diag['chm'] = dict(p50=round(float(np.median(vc)), 2), p90=round(float(np.percentile(vc, 90)), 2), p99=round(float(np.percentile(vc, 99)), 2), max=round(float(vc.max()), 2),
                   cobertura_pct={f'>{t}m': round(float((vc > t).mean() * 100), 2) for t in [0.5, 1, 2.5, 5]})
diag['arvores_existentes'] = dict(altura_min_m=HA, manchas_de_copa_na_area=int((tam >= 1.5).sum()), area_copa_m2=round(float(keep.sum() * r * r), 1),
                                  area_descontada_m2=round(float(excl.sum() * r * r), 1), folga_m=FOLGA,
                                  pct_da_area=round(100 * float(excl.sum()) / M.sum(), 2),
                                  copa_no_entorno_m2=round(float((arv & REC & ~M).sum() * r * r), 0),
                                  nota='manchas de copa (CHM acima da altura mínima) dentro da área: ficam como estão e saem da área de plantio. A contagem de árvores individuais vem da etapa de entorno')

# ---------- 5. linhas de cultivo ----------
LJ = json.load(open(caminho(CFG['dados']['linhas']), encoding='utf-8'))['features']
amostra = lambda A_, x, y: ndi.map_coordinates(A_, [(Y1 - np.asarray(y)) / 1.0 - 0.5, (np.asarray(x) - X0) / 1.0 - 0.5], order=1, mode='nearest')
orig_l = []
for i, f in enumerate(LJ):
    L = LineString([c[:2] for c in f['geometry']['coordinates']])
    cota = f['properties'].get('ELEVATION'); cota = float(str(cota).split()[0]) if cota else None
    orig_l.append(dict(i=i, geo=L, cota=cota, id_origem=f['properties']['id_origem'], elevation_original=f['properties'].get('ELEVATION')))
pecas = []
for o in orig_l:
    it = o['geo'].intersection(geo)
    gs = [it] if it.geom_type == 'LineString' else [g_ for g_ in getattr(it, 'geoms', []) if g_.geom_type == 'LineString']
    o['dentro_m'] = sum(g_.length for g_ in gs); o['fora_m'] = o['geo'].length - o['dentro_m']; o['pecas'] = len(gs)
    for g_ in gs:
        if g_.length > 0.05: pecas.append(dict(orig=o['i'], cota=o['cota'], geo=g_))
for p in pecas:
    n_ = max(2, int(p['geo'].length)); pts = [p['geo'].interpolate(k / n_, normalized=True) for k in range(n_ + 1)]
    p['x'] = np.array([q.x for q in pts]); p['y'] = np.array([q.y for q in pts]); p['z'] = float(amostra(zf, p['x'], p['y']).mean())
pecas.sort(key=lambda p: (p['z'], p['geo'].centroid.x))
for k, p in enumerate(pecas): p['linha'] = k + 1
MINL = float(PL.get('linha_min_m', 3.0))
esp, angs, decl_l, dz = [], [], [], []
for p in pecas:
    outras = unary_union([q['geo'] for q in pecas if q['orig'] != p['orig'] and (q['cota'] is None or q['cota'] != p['cota'])])
    L = p['geo']; x, y = p['x'], p['y']
    d = np.array([outras.distance(L.interpolate(k / (len(x) - 1), normalized=True)) for k in range(len(x))]) if not outras.is_empty else np.array([np.nan])
    tx = np.gradient(x); ty = np.gradient(y); tn = np.hypot(tx, ty) + 1e-9; tx /= tn; ty /= tn
    ge, gn_ = amostra(gx, x, y), amostra(gN, x, y); gs_ = np.hypot(ge, gn_) + 1e-9
    a = np.degrees(np.arcsin(np.clip(np.abs(tx * ge + ty * gn_) / gs_, 0, 1)))        # 0° = sobre a curva de nível
    dl = np.abs(tx * ge + ty * gn_) * 100                                                 # declive ao longo da linha (%)
    p.update(comp_m=round(L.length, 1), entrelinha_mediana_m=round(float(np.nanmedian(d)), 2), entrelinha_min_m=round(float(np.nanmin(d)), 2),
             angulo_mediano_graus=round(float(np.median(a)), 1), angulo_max_graus=round(float(a.max()), 1), declive_ao_longo_pct=round(float(np.median(dl)), 1),
             curta=bool(L.length < MINL))
    if L.length >= MINL: esp += list(d[np.isfinite(d)]); angs += list(a); decl_l += list(dl)
    if p['cota'] is not None: dz.append(p['z'] - p['cota'])
esp, angs, decl_l = np.array(esp), np.array(angs), np.array(decl_l)
cruz = []
for i in range(len(pecas)):
    for j in range(i + 1, len(pecas)):
        if pecas[i]['geo'].crosses(pecas[j]['geo']): cruz.append([pecas[i]['linha'], pecas[j]['linha']])
# azimute médio (axial) para a vista entre linhas
allx = np.concatenate([np.diff(p['x']) for p in pecas]); ally = np.concatenate([np.diff(p['y']) for p in pecas]); th = np.arctan2(allx, ally)
az = float((np.degrees(0.5 * np.arctan2(np.sin(2 * th).sum(), np.cos(2 * th).sum())) + 360) % 180)
validas = [p for p in pecas if not p['curta']]
diag['linhas'] = dict(
    feicoes_no_arquivo=len(orig_l), trechos_dentro_da_area=len(pecas), trechos_validos=len(validas), trechos_curtos=[p['linha'] for p in pecas if p['curta']],
    comprimento_total_m=round(sum(o['geo'].length for o in orig_l), 1), comprimento_dentro_m=round(sum(p['geo'].length for p in pecas), 1),
    comprimento_valido_m=round(sum(p['geo'].length for p in validas), 1), comprimento_fora_m=round(sum(o['fora_m'] for o in orig_l), 1),
    feicoes_com_trecho_fora=[dict(feicao=o['i'] + 1, cota=o['cota'], fora_m=round(o['fora_m'], 1)) for o in orig_l if o['fora_m'] > 0.3],
    feicoes_partidas_pela_borda=[o['i'] + 1 for o in orig_l if o['pecas'] > 1], cruzamentos_entre_linhas=cruz,
    entrelinha_m=dict(min=round(float(esp.min()), 2), p5=round(float(np.percentile(esp, 5)), 2), mediana=round(float(np.median(esp)), 2),
                      p95=round(float(np.percentile(esp, 95)), 2), max=round(float(esp.max()), 2)),
    pct_comprimento_entrelinha_menor_2_5m=round(float((esp < 2.5).mean() * 100), 1), pct_comprimento_entrelinha_maior_5m=round(float((esp > 5).mean() * 100), 1),
    angulo_com_curva_de_nivel_graus=dict(mediana=round(float(np.median(angs)), 1), p90=round(float(np.percentile(angs, 90)), 1), max=round(float(angs.max()), 1)),
    declive_ao_longo_pct=dict(mediana=round(float(np.median(decl_l)), 1), p90=round(float(np.percentile(decl_l, 90)), 1), max=round(float(decl_l.max()), 1)),
    pct_comprimento_declive_maior_3pct=round(float((decl_l > 3).mean() * 100), 1),
    cota_atributo_menos_mdt_m=round(float(np.median(dz)), 2) if dz else None,
    azimute_graus=round(az, 1), entrelinha_m_mediana=round(float(np.median(esp)), 2),
    densidade_linear_m_ha=round(sum(p['geo'].length for p in validas) / (geo.area / 1e4)),
    por_linha=[{k: p[k] for k in ('linha', 'cota', 'comp_m', 'entrelinha_mediana_m', 'entrelinha_min_m', 'angulo_mediano_graus', 'angulo_max_graus', 'declive_ao_longo_pct', 'curta')} for p in pecas])
os.makedirs(os.path.join(ROOT, 'fase1b'), exist_ok=True)
json.dump(geojson_pontos('linhas_tratadas', [{'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[x, y] for x, y in p['geo'].coords]},
                                              'properties': {'linha': p['linha'], 'cota': p['cota'], 'comp_m': p['comp_m'], 'curta': p['curta'], 'feicao_original': p['orig'] + 1, 'id_origem': orig_l[p['orig']]['id_origem'], 'id_trecho': p['linha'], 'ELEVATION_original': orig_l[p['orig']]['elevation_original'], 'z_cena': 'MDT, atributo original não usado para assentamento'}} for p in pecas]),
          open(os.path.join(ROOT, 'fase1b', 'linhas_tratadas.geojson'), 'w', encoding='utf-8'))
from territorio_cambuci import complementar
complementar(diag, pecas, orig_l, keep, excl)
json.dump(diag, open(os.path.join(F1, 'diagnostico.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
resumo = {k: v for k, v in diag.items() if k not in ('rasters', 'vetores')}; resumo['linhas'] = {k: v for k, v in diag['linhas'].items() if k != 'por_linha'}
print(json.dumps(resumo, ensure_ascii=False, indent=1))
print('vetores:', json.dumps(vet, ensure_ascii=False))
