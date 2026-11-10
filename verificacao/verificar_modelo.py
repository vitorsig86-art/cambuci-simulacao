import os,sys,json,base64,hashlib
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1]
os.environ['PROJETO']=str(R);sys.path.insert(0,str(R/'pipeline/scripts'))
from saf_comum import CFG
import imp_02_plantio as P
M=json.loads((R/'work/modelo.json').read_text(encoding='utf-8'))
species=['grevilea','banana','cafe'];out={}
for d in ('com','sem'):
    D=M if d=='com' else M['des']['sem'];pts,res=P.gerar(sem_qv=d=='sem');assert len(pts)==D['n']==len(D['plantas'])
    raw=np.array([[p['x'],p['y']] for p in pts]);quant=np.array([p[:2] for p in D['plantas']]);errors=np.abs(raw-quant)
    assert errors.max()<=.00500001
    assert [p[2] for p in D['plantas']]==[species.index(p['esp']) for p in pts]
    group=np.array([p[2] for p in D['plantas']]);cen={}
    for c,C in D['cen'].items():
        assert len(C['ind'])==31
        arrays={k:np.frombuffer(base64.b64decode(C[k]),dtype='u1').reshape(31,D['n']) for k in ('V','H','R','F')}
        assert np.isin(arrays['V'],[0,1]).all() and (arrays['F']<=3).all()
        assert not ((arrays['H']==255)|(arrays['R']==255)).any(), 'saturação da quantização'
        assert (arrays['F'][arrays['V']==0]==0).all()
        for y,I in enumerate(C['ind']):
            assert int(arrays['V'][y].sum())==I['vivas']
            for g,s in enumerate(species):assert int(arrays['V'][y,group==g].sum())==I['por_esp'][s]
        for g,h0 in enumerate([4,5,3]):assert (arrays['H'][0,group==g]==h0).all()
        cen[c]={'shape':[31,D['n']],'vivas_conferidas':True,'sem_saturacao':True,'H_passo_m':.1,'R_passo_m':.05,'F':'ordinal 0 a 3, não kg'}
    out[d]={'n':D['n'],'XY_passo_m':.01,'XY_erro_max_por_eixo_m':float(errors.max()),'XY_erro_max_radial_m':float(np.linalg.norm(raw-quant,axis=1).max()),'series':cen}
out['economia_sha256']=hashlib.sha256((R/'pipeline/site/economia.js').read_bytes()).hexdigest()
(R/'verificacao/modelo_quantizacao.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=1))
