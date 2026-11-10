"""Evidências territoriais nativas e conferência, antes de qualquer projeção."""
from saf_comum import *
from shapely.geometry import LineString, Point, mapping
from scipy import ndimage as ndi

def complementar(diag, pecas, orig_l, keep, excl):
    geo=poligono(); ds=gdal.Open(caminho('mdt.tif')); ms=gdal.Open(caminho('mds.tif'))
    gt=ds.GetGeoTransform(); z=ds.ReadAsArray().astype(float); s=ms.ReadAsArray().astype(float)
    valid=(ds.GetRasterBand(1).GetMaskBand().ReadAsArray()!=0)&(ms.GetRasterBand(1).GetMaskBand().ReadAsArray()!=0)&np.isfinite(z)&np.isfinite(s)
    diff=np.full(z.shape,np.nan); diff[valid]=s[valid]-z[valid]
    mem=gdal.GetDriverByName('MEM').Create('',ds.RasterXSize,ds.RasterYSize,1,gdal.GDT_Byte)
    mem.SetGeoTransform(gt); mem.SetProjection(ds.GetProjection()); v=ogr.Open(AREA_GJ)
    gdal.RasterizeLayer(mem,[1],v.GetLayer(),burn_values=[1]); M=mem.ReadAsArray()!=0
    a=diff[M&valid]
    native=dict(resolucao_m=.6,celulas_talhao=int(M.sum()),validas=int((M&valid).sum()),min=float(a.min()),max=float(a.max()),
                negativos_pct=float((a<0).mean()*100),maior_igual_2_5_pct=float((a>=2.5).mean()*100),
                unidade='m',datum_vertical='pendente',nota='MDS − MDT nativo, antes de limitar negativos ou filtrar')
    assert abs(native['min']+1.02)<.03 and abs(native['max']-22.66)<.03
    assert abs(native['negativos_pct']-29.82)<.05 and abs(native['maior_igual_2_5_pct']-5.53)<.05
    out=gdal.GetDriverByName('GTiff').Create(os.path.join(F1,'chm_bruto_nativo.tif'),ds.RasterXSize,ds.RasterYSize,1,gdal.GDT_Float32,options=['COMPRESS=DEFLATE'])
    out.SetGeoTransform(gt); out.SetProjection(ds.GetProjection()); out.GetRasterBand(1).SetNoDataValue(-32767)
    out.GetRasterBand(1).WriteArray(np.where(valid,diff,-32767)); out=None
    diag['chm_nativo']=native
    diag['chm_operacional']=dict(resolucao_m=.25,resolucao_fonte_m=.6,metodo='bilinear; máscaras validadas antes de subtrair; clip [0,30] m; mediana 3x3 (0,75 m); abaixo de 0,30 m = 0',
                               copa='>=2,50 m; abertura binária cruz 3x3; manchas >=1,5 m²; dilatação cruz 4 iterações, folga nominal 1 m',
                               status='copas propostas para preservação, interpretação pendente de conferência em campo')
    raw=sum(o['geo'].length for o in orig_l); inside=sum(p['geo'].length for p in pecas)
    eligible=[p for p in pecas if not p['curta']]
    assert len(orig_l)==30 and len(pecas)==30 and len(eligible)==27
    assert abs(raw-2935.88)<.02 and abs(inside-2934.03)<.02 and abs(sum(p['geo'].length for p in eligible)-2930.64)<.02
    diag['linhas']['comprimentos_precisos_m']=dict(bruto=raw,dentro=inside,fora=raw-inside,elegivel=sum(p['geo'].length for p in eligible))
    diag['linhas']['curtos_detalhes']=[{'origem':p['orig']+1,'trecho':p['linha'],'m':p['geo'].length} for p in pecas if p['curta']]
    overlaps=[]
    for i,p in enumerate(pecas):
        for q in pecas[i+1:]:
            length=p['geo'].intersection(q['geo']).length
            if length>1e-8: overlaps.append(dict(a=p['linha'],b=q['linha'],m=length))
    diag['linhas']['sobreposicoes']=overlaps
    pontas=[]
    for p in pecas:
        for lado,co in [('inicio',p['geo'].coords[0]),('fim',p['geo'].coords[-1])]:
            pontas.append(dict(origem=p['orig']+1,trecho=p['linha'],ponta=lado,dist_borda_m=geo.boundary.distance(Point(co)),curta=p['curta']))
    diag['proximidade_borda']=dict(limiar_m=3,pontas=pontas,pontas_abaixo_3m=sum(p['dist_borda_m']<3 for p in pontas),
                                  nota='distância geométrica até a borda; não atesta cabeceira operacional nem acesso viário; não exclui plantas')
    grades={}
    for r in (.5,1,.25,.1):
        d=warp('mdt.tif',r,'average'); a_=d.ReadAsArray()
        grades[str(r)]=dict(nx=d.RasterXSize,ny=d.RasterYSize,geotransform=d.GetGeoTransform(),invalidos=0)
    diag['grades']=grades
    diag['crs_atribuicao']='GeoJSON original sem CRS; EPSG:31984 inferido, coordenadas XY/Z preservadas nas cópias normalizadas; OGR e Shapely conferidos'
    diag['premissas']=dict(medidos=['rasters e geometria','MDT e MDS − MDT','comprimentos, declividade e centroide'],
                           inferidos=['CRS vetorial EPSG:31984','copas pelo CHM','drenagem estática limitada à moldura'],
                           assumidos=CFG['pendentes'])
    # Máscaras para mapa de interferência e camadas auditáveis.
    def vetor_mask(a_,nome):
        d_=gdal.GetDriverByName('MEM').Create('',a_.shape[1],a_.shape[0],1,gdal.GDT_Byte)
        d_.SetGeoTransform((X0,.25,0,Y1,0,-.25)); sr=osr.SpatialReference();sr.ImportFromEPSG(EPSG);d_.SetProjection(sr.ExportToWkt())
        d_.GetRasterBand(1).WriteArray(a_.astype(np.uint8)); drv=ogr.GetDriverByName('GeoJSON'); path=os.path.join(F1,nome+'.geojson')
        if os.path.exists(path): drv.DeleteDataSource(path)
        v_=drv.CreateDataSource(path); ly=v_.CreateLayer(nome,srs=sr);ly.CreateField(ogr.FieldDefn('valor',ogr.OFTInteger))
        gdal.Polygonize(d_.GetRasterBand(1),d_.GetRasterBand(1),ly,0);v_=None
    vetor_mask(keep,'copas_preservacao');vetor_mask(excl,'exclusao_copas')
    from shapely.ops import unary_union
    copas=unary_union([shape(f['geometry']) for f in json.load(open(os.path.join(F1,'exclusao_copas.geojson'),encoding='utf-8'))['features']])
    diag['interferencia_copas_linhas']=[dict(trecho=p['linha'],origem=p['orig']+1,comprimento_excluido_m=p['geo'].intersection(copas).length) for p in pecas]
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    oo=warp('orto.tif',.1,'average').ReadAsArray()[:3].transpose(1,2,0)
    fig,axs=plt.subplots(1,2,figsize=(17,8))
    for ax in axs:
        ax.imshow(oo,extent=(X0,X1,Y0,Y1));ax.plot(*geo.exterior.xy,color='yellow',lw=1.5)
        for p in pecas:
            ax.plot(*p['geo'].xy,color='red' if p['curta'] else 'cyan',lw=.8)
        ax.set_xlim(X0,X1);ax.set_ylim(Y0,Y1);ax.set_aspect('equal');ax.ticklabel_format(useOffset=False,style='plain')
    axs[0].set_title('Orto + limite de plantio + linhas (curtos em vermelho)')
    extent=(gt[0],gt[0]+gt[1]*ds.RasterXSize,gt[3]+gt[5]*ds.RasterYSize,gt[3])
    overlay=np.ma.masked_where(~valid|((diff>=0)&(diff<2.5)),diff)
    im=axs[1].imshow(overlay,extent=extent,cmap='coolwarm',vmin=-1.1,vmax=8,alpha=.8)
    axs[1].contour(excl.astype(float),levels=[.5],extent=(X0+.125,X1-.125,Y0+.125,Y1-.125),origin='upper',colors='lime',linewidths=.6)
    axs[1].set_title('CHM nativo: negativos e >= 2,50 m; exclusões em verde')
    fig.colorbar(im,ax=axs[1],label='MDS − MDT (m)');fig.suptitle('Cambuci · EPSG:31984 · alturas e copas a conferir no orto/campo')
    fig.savefig(os.path.join(F1,'mapa_conferencia.png'),dpi=150,bbox_inches='tight');plt.close(fig)
    json.dump(diag,open(os.path.join(F1,'territorio_validado.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=2,allow_nan=False)
