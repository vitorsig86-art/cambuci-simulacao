import os,sys,json,base64
from pathlib import Path
R=Path(__file__).resolve().parents[1]
os.environ['PROJETO']=str(R);sys.path.insert(0,str(R/'pipeline/scripts'))
from saf_comum import *
import imp_02_plantio as P
from shapely.geometry import Point,LineString
result={}
B=json.loads((R/'work/base3d.json').read_text())
assert (B['nx'],B['ny'])==(400,366) and (B['W'],B['H'])==(200,183)
assert B['nx']*B['ny']==146400 and 2*(B['nx']-1)*(B['ny']-1)==291270
q=np.frombuffer(base64.b64decode(B['b64']),dtype='<u2').reshape(B['ny'],B['nx'])
z=warp('mdt.tif',.5,'average').ReadAsArray()
err=float(np.max(np.abs(q/100+B['zmin']-z)))
assert err<=.00501
result['terreno']=dict(vertices=146400,triangulos=291270,quantizacao_erro_max_m=err,indices='Uint32 explícito no template',invalidos=0)
result['desenhos']={}
for d in ('com','sem'):
    pts,res=P.gerar(sem_qv=d=='sem')
    byid={f['properties']['linha']:LineString([(x-X0,y-Y0) for x,y in f['geometry']['coordinates']]) for f in P.LIN}
    errs=[]; maxdist=0
    for p in pts:
        pt=Point(p['x'],p['y'])
        assert P.AREA.covers(pt), (d,'fora',p)
        assert not P.em_arvore(p['x'],p['y']), (d,'copa',p)
        if p['esp']!='grevilea':
            dist=byid[p['linha']].distance(pt);maxdist=max(maxdist,dist);assert dist<1e-7
            if d=='com': assert P.dist_renque([p['x']],[p['y']])[0]>=float(CFG['quebra_vento']['recuo_cafe_m'])-1e-7
        assert not P.COR.contains(pt)
    for esp in ('cafe','banana'):
        assert res['antes_dos_cortes'][esp]==res['plantas'][esp]+sum(v[esp] for v in res['cortes'].values())
    result['desenhos'][d]=dict(plantas=res['plantas'],brutas=res['antes_dos_cortes'],cortes=res['cortes'],distancia_max_linha_m=maxdist,fora=0,sobre_exclusoes=0)
    features=[{'type':'Feature','geometry':{'type':'Point','coordinates':[p['x']+X0,p['y']+Y0]},'properties':{k:v for k,v in p.items() if k not in ('x','y')}} for p in pts]
    (R/f'fase2/plantas_{d}_precisas.geojson').write_text(json.dumps(geojson_pontos('plantas_'+d,features),ensure_ascii=False,allow_nan=False),encoding='utf-8')
E=json.loads((R/'work/estradas.json').read_text(encoding='utf-8'))
assert E['disponivel'] is False and E['eixos']==[] and E['meia'] is None and E['logistica']['dist_media_ponderada_m'] is None
result['sem_vias']=dict(contrato_preservado=True,corredores_e_logistica='indisponíveis',consumidores=['imp_02_plantio.gerar com/sem','modelo usa mesmo gerador','template com camada desabilitada'])
# Identifica bordas com gradiente descendente para dentro do recorte: contribuição externa possível.
G=np.load(R/'work/agua_grades.npz');zs=G['z'];gy,gx=np.gradient(zs)
edges={'norte':gy[0,:]<0,'sul':gy[-1,:]>0,'oeste':gx[:,0]<0,'leste':gx[:,-1]>0}
result['contribuicao_externa_possivel']={k:dict(celulas_1m=int(v.sum()),comprimento_indicativo_m=int(v.sum())) for k,v in edges.items()}
result['nota_drenagem']='indicação estática por gradiente do MDT suavizado; área externa ao voo desconhecida, vazão não estimada'
(R/'verificacao/territorio_passagem2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=1))
