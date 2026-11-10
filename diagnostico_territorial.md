# Diagnóstico territorial gerado · Cambuci

Data da réplica: 10/11/2026. Calculado exclusivamente dos cinco insumos em `originais/`; hashes e metadados em `verificacao/entradas.json`. Auditoria local da referência de 30/10/2026 consultada; auditoria citada de 10/11 e diagnóstico territorial anterior não localizados. Critérios numéricos da solicitação conferidos diretamente.

## Medido nos arquivos

Polígono válido, sem furos: 1.2183 ha; área precisa 12183.366038 m² e perímetro 504.236169 m. Centroide {'E': 194222.6, 'N': 7616476.7, 'lat': -21.52842, 'lon': -41.95174}.

Rasters EPSG:31984, norte para cima, origem E 194130,082938933 / N 7616565,736833424 m. Orto 2002 × 1837 a 0,10 m, RGBA opaco, sem NoData numérico. MDT/MDS 334 × 306 a 0,60 m, NoData −32767; máscaras integralmente válidas. Coincidência espacial por transformações e coordenadas, sem confundir borda com centro de célula.

Moldura comum oeste/sul/leste/norte: 194130,082938933 / 7616382,736833424 / 194330,082938933 / 7616565,736833424 m. Cobertura integral validada antes de relevo/hidrologia/exportação. Grades 0,50 m: 400 × 366; 1 m: 200 × 183; 0,25 m: 800 × 732; textura 0,10 m: 2000 × 1830. Todas compartilham bordas.

Linhas: 30 LineString Z, ELEVATION textual, preservadas nos insumos. Bruto 2935.88221 m; fora 1.85651 m; dentro 2934.02569 m em 30 trechos; elegível 2930.63579 m em 27 trechos. Recorte feito uma vez no diagnóstico; etapas posteriores usam `fase1b/linhas_tratadas.geojson`.

Curtos excluídos por mínimo de 3 m: [{'origem': 3, 'trecho': 3, 'm': 1.6913122750055043}, {'origem': 23, 'trecho': 24, 'm': 1.161484818686366}, {'origem': 26, 'trecho': 26, 'm': 0.5371089890915598}]. Sobreposições: []; cruzamentos: []. Pontas a menos de 3 m da borda: 60 de 60, incluindo curtos. Não se infere capacidade de manobra desse indicador.

MDS − MDT nativo antes de filtro: -1.01947 a 22.65640 m; 29.82238% negativos; 5.52649% ≥ 2,50 m; 33837 células válidas no talhão. `fase1/chm_bruto_nativo.tif` preserva diferenças negativas.

## Inferido e operacional

Vetores sem declaração original: atribuição inferida de EPSG:31984 nas cópias normalizadas, sem reprojetar coordenadas. CRS explícito conferido via OGR e coordenadas conferidas com leitura JSON/Shapely. Procedência ainda pendente. Não foi necessário gerar GeoJSON RFC 7946. Z/ELEVATION não substituem o MDT na cena. Unidade vertical metro, datum vertical pendente.

CHM operacional: {'resolucao_m': 0.25, 'resolucao_fonte_m': 0.6, 'metodo': 'bilinear; máscaras validadas antes de subtrair; clip [0,30] m; mediana 3x3 (0,75 m); abaixo de 0,30 m = 0', 'copa': '>=2,50 m; abertura binária cruz 3x3; manchas >=1,5 m²; dilatação cruz 4 iterações, folga nominal 1 m', 'status': 'copas propostas para preservação, interpretação pendente de conferência em campo'}. Área proposta para preservação/exclusão: {'altura_min_m': 2.5, 'manchas_de_copa_na_area': 2, 'area_copa_m2': 687.9, 'area_descontada_m2': 802.9, 'folga_m': 1.0, 'pct_da_area': 6.59, 'copa_no_entorno_m2': 2792.0, 'nota': 'manchas de copa (CHM acima da altura mínima) dentro da área: ficam como estão e saem da área de plantio. A contagem de árvores individuais vem da etapa de entorno'}. Interferência por trecho em `fase1/diagnostico.json`, campo `interferencia_copas_linhas`.

Conferência visual no orto: a grande mancha alta a sudeste acompanha árvores visíveis; negativos se distribuem também em terreno e carreadores abertos, não são alturas físicas de vegetação. Sem pontos de controle não se corrige viés ou datum. Propostas de copa precisam de campo; as árvores instanciadas de contexto não são inventário botânico.

Sem vetor de vias: contrato `work/estradas.json` mantém arrays vazios, disponibilidade falsa e métricas nulas. Consumidores testados. Nenhuma exclusão por corredor ativada. Drenagem estática pelo MDT, contribuição externa possível por gradiente nas bordas: {'norte': {'celulas_1m': 0, 'comprimento_indicativo_m': 0}, 'sul': {'celulas_1m': 200, 'comprimento_indicativo_m': 200}, 'oeste': {'celulas_1m': 49, 'comprimento_indicativo_m': 49}, 'leste': {'celulas_1m': 106, 'comprimento_indicativo_m': 106}}. Esses comprimentos indicativos podem incluir cantos; não representam bacias externas medidas ou vazão.

## Hipóteses demonstrativas e contagens

Café a 0,80 m e banana a 8 m com alternância de 4 m; mínimo de linha 3 m; vento assumido de NE 45°; grevílea em dois renques, 3 m entre árvores e renques, primeiro recuo 1 m, afastamento café–grevílea 2 m e drenagem 2 m. São regras herdadas da Jurema para demonstração.

Quebra-vento efetivo: bordas ['leste', 'nordeste', 'norte'], 7 trechos, 208.0 m, 77 árvores. Cortes de candidatos do renque: {'drenagem': 12, 'arvore_existente': 6, 'nao_exposta': 221}. Textos do site usam essas bordas reais, não uma orientação fixa herdada.

Desenho com: {'plantas': {'cafe': 2900, 'banana': 325, 'grevilea': 77}, 'brutas': {'cafe': 3294, 'banana': 371}, 'cortes': {'estrada': {'cafe': 0, 'banana': 0}, 'quebra_vento': {'cafe': 181, 'banana': 21}, 'arvore_existente': {'cafe': 213, 'banana': 25}}, 'distancia_max_linha_m': 1.7187932156272677e-14, 'fora': 0, 'sobre_exclusoes': 0}. Pontos precisos em `fase2/plantas_com_precisas.geojson`. As contagens brutas de café/banana fecham com aceitas + exclusões por motivo, em ordem de prioridade.

Desenho sem: {'plantas': {'cafe': 3079, 'banana': 346, 'grevilea': 0}, 'brutas': {'cafe': 3294, 'banana': 371}, 'cortes': {'estrada': {'cafe': 0, 'banana': 0}, 'quebra_vento': {'cafe': 0, 'banana': 0}, 'arvore_existente': {'cafe': 215, 'banana': 25}}, 'distancia_max_linha_m': 1.7187932156272677e-14, 'fora': 0, 'sobre_exclusoes': 0}. Pontos precisos em `fase2/plantas_sem_precisas.geojson`. As contagens brutas de café/banana fecham com aceitas + exclusões por motivo, em ordem de prioridade.

Pendentes: espécies e cultivares, data de implantação, uso anterior, espaçamentos, manejo, clima local, direção do vento, carbono e solo, custos e preços, datum vertical, procedência CRS vetorial. Uso anterior de pastagem e ano 2026 são hipóteses, não fatos do talhão. Clima local indisponível; sem diagnóstico de aptidão.

## Cena, quantização e testes

Origem local SW (194130.082938933, 7616382.736833424); cena centrada, X leste, Y vertical acima de zmin=432.587463 m, Z sul (norte negativo). MDT sozinho, quantizado em 0,01 m, erro máximo 0.005000 m. Malha completa com 146400 vértices, 291270 triângulos e Uint32.

Quantização de plantas/consistência: {'com': {'n': 3302, 'XY_passo_m': 0.01, 'XY_erro_max_por_eixo_m': 0.0049990357851470435, 'XY_erro_max_radial_m': 0.007007498066848267, 'series': {'conservador': {'shape': [31, 3302], 'vivas_conferidas': True, 'sem_saturacao': True, 'H_passo_m': 0.1, 'R_passo_m': 0.05, 'F': 'ordinal 0 a 3, não kg'}, 'provavel': {'shape': [31, 3302], 'vivas_conferidas': True, 'sem_saturacao': True, 'H_passo_m': 0.1, 'R_passo_m': 0.05, 'F': 'ordinal 0 a 3, não kg'}, 'otimista': {'shape': [31, 3302], 'vivas_conferidas': True, 'sem_saturacao': True, 'H_passo_m': 0.1, 'R_passo_m': 0.05, 'F': 'ordinal 0 a 3, não kg'}}}, 'sem': {'n': 3425, 'XY_passo_m': 0.01, 'XY_erro_max_por_eixo_m': 0.0049990357851470435, 'XY_erro_max_radial_m': 0.007007498066848267, 'series': {'conservador': {'shape': [31, 3425], 'vivas_conferidas': True, 'sem_saturacao': True, 'H_passo_m': 0.1, 'R_passo_m': 0.05, 'F': 'ordinal 0 a 3, não kg'}, 'provavel': {'shape': [31, 3425], 'vivas_conferidas': True, 'sem_saturacao': True, 'H_passo_m': 0.1, 'R_passo_m': 0.05, 'F': 'ordinal 0 a 3, não kg'}, 'otimista': {'shape': [31, 3425], 'vivas_conferidas': True, 'sem_saturacao': True, 'H_passo_m': 0.1, 'R_passo_m': 0.05, 'F': 'ordinal 0 a 3, não kg'}}}, 'economia_sha256': '4c58d3da0e2ffc3f80ee8f0894c25e13ece02383a1345138d3955df39f040bfa'}. São 31 estados por desenho/cenário, V/H/R/F têm 31 × n bytes; sobrevivência confrontada com contagens anuais, sem saturação H/R.

Sombra visual, efeito produtivo de copas simuladas, insolação do relevo e drenagem estática aparecem separados. Árvores existentes geram exclusões e sombra visual; efeito produtivo adicional não calibrado. Carbono é projeção de novas plantas e solo hipotético, sem crédito certificado.

Navegador: PASSOU; HTML 6064696 bytes; carregamento 905 ms; animação {'ano': 2.819879999999993, 'frames': 3, 'duracao_ms': 1350, 'fps': 1.4814814814814814}; reconstrução de plantas [{'ano': 0, 'ms': 16.700000047683716}, {'ano': 5, 'ms': 24.19999998807907}, {'ano': 15, 'ms': 29.69999998807907}, {'ano': 30, 'ms': 33.60000002384186}]. Software SwiftShader, detalhe móvel adaptativo, malha e contagem de plantas preservadas. Viewport móvel {'width': 390, 'scrollWidth': 390, 'canvasWidth': 368}; GPU física e telefone real não medidos.

Paridade site/relatório nos seis pares de desenho/cenário, em todos os anos e nos dois modos de mão de obra: diferença numérica máxima 2.91038304567e-11, abaixo de 1e-7 e idêntica ao centavo. Mesmo motor econômico embutido, com teste de conteúdo normalizado para LF. Sem erros JS ou requisições falhas/externas; câmeras, camadas, anos 0/30, reprodução, edição, persistência isolada e viewport móvel testados.

Referência preservada: True; 111 arquivos antes/depois, zero alterações. Arquivos adaptados na cópia: `parametros_economicos.yaml`, `parametros_especies.yaml`, `projeto.yaml`, `pipeline\scripts\imp_01_diagnostico.py`, `pipeline\scripts\imp_02_plantio.py`, `pipeline\scripts\imp_03e_estradas.py`, `pipeline\scripts\imp_05_montar_html.py`, `pipeline\scripts\imp_06_relatorio.py`, `pipeline\scripts\saf_03_base3d.py`, `pipeline\scripts\saf_comum.py`, `pipeline\site\template_imp.html`.

Publicação externa não realizada. Comandos reproduzíveis em README.md; resultados integrais em verificacao/ e logs/.
