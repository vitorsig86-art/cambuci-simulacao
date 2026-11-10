> HIPÓTESE demonstrativa de café, banana e grevílea. Espécies, uso anterior, data, manejo, clima, carbono e economia pendentes de validação local. Não constitui diagnóstico de aptidão.

# Cambuci · implantação demonstrativa: com e sem quebra-vento

Área de 1,22 ha, plantio hipotético em 2026, 30 anos, R$ constantes de 2026, taxa real de 8,0% a.a., mão de obra própria valorizada pela diária. Estimativa de modelagem, sem validação de campo. Os mesmos números estão no site (seletor Desenho).

## Os dois desenhos

| | Com quebra-vento | Sem quebra-vento | Diferença |
|---|---:|---:|---:|
| Pés de café | 2.900 | 3.079 | +179 |
| Bananeiras | 325 | 346 | +21 |
| Grevíleas | 77 | 0 | −77 |

Sem o renque, café e banana ocupam as linhas inteiras, inclusive a faixa de 2 m junto às grevíleas. Não há faixa protegida, faixa de competição, sombra de grevílea nem custo de muda, plantio e desrama do renque.

## Resultado por cenário

| Cenário | Desenho | Café em 30 anos (sc) | Receita no ano 10 (2036) | Acumulado em 30 anos | Ano de retorno | VPL | VPL sem pró-labore | CO2e no ano 30 (t) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Conservador | com quebra-vento | 354 | R$ 18.853 | −R$ 1.090.072 | não retorna | −R$ 452.942 | −R$ 121.154 | 32 |
| Conservador | sem quebra-vento | 338 | R$ 18.215 | −R$ 1.123.468 | não retorna | −R$ 464.727 | −R$ 135.667 | 20 |
| Conservador | diferença (sem − com) | −16 | −R$ 638 | −R$ 33.396 | – | −R$ 11.786 | −R$ 14.513 | −12 |
| Provável | com quebra-vento | 604 | R$ 47.184 | −R$ 27.946 | não retorna | −R$ 61.731 | R$ 176.810 | 75 |
| Provável | sem quebra-vento | 594 | R$ 46.822 | −R$ 52.742 | não retorna | −R$ 71.208 | R$ 166.841 | 35 |
| Provável | diferença (sem − com) | −10 | −R$ 362 | −R$ 24.795 | – | −R$ 9.477 | −R$ 9.969 | −40 |
| Otimista | com quebra-vento | 983 | R$ 89.826 | R$ 1.407.932 | ano 4 | R$ 451.571 | R$ 639.651 | 172 |
| Otimista | sem quebra-vento | 1.009 | R$ 92.460 | R$ 1.455.723 | ano 4 | R$ 466.158 | R$ 657.727 | 61 |
| Otimista | diferença (sem − com) | +26 | +R$ 2.634 | +R$ 47.791 | 0 ano(s) | +R$ 14.587 | +R$ 18.076 | −111 |

## O que na diferença vem de premissa

Vem da geometria (dado do desenho):

- Contagem de pés: +179 cafés e +21 bananeiras sem o renque, 77 grevíleas a menos. Depende só do recuo de 2,0 m entre grevílea e café (projeto.yaml, premissa a validar) e da posição do renque.

Vem de premissa a validar (sem medição local):

- Perda de produção do café exposto ao vento: 15% · 10% · 5% (conservador · provável · otimista). No desenho sem quebra-vento vale para todo o café; no desenho com renque, só para o café fora da faixa protegida. Fonte: HIPÓTESE Cambuci, valor herdado da Jurema, sem calibração local. Referência histórica não revalidada: premissa a validar: perda de produção do café fora da faixa protegida. Base qualitativa: vento causa lesão nas folhas e favorece mancha aureolada (Embrapa); renques de grevílea são recomendação antiga do IBC para cafezais (Embrapa Florestas). Sem número medido para este lugar.
- Perda na faixa de competição junto ao renque: 40% · 30% · 20%. Só existe no desenho com quebra-vento.
- Alcance da proteção: 10,0 · 12,5 · 15,0 vezes a altura do renque, descontado o desnível. Direção do vento: 45°, sem rosa dos ventos local.
- Crescimento da grevílea (altura máxima 15 · 18 · 22 m): define quando a proteção começa e quanto carbono o renque estoca. A diferença de carbono entre os desenhos é quase toda biomassa de grevílea.
- Custos do renque: muda R$ 6,0 · 4,0 · 2,5, cova R$ 2,0 · 1,5 · 1,0, plantio 0,05 · 0,04 · 0,03 dia-homem por muda e desrama 0,07 · 0,05 · 0,03 dia-homem por árvore por ano.
- Produção por pé, preços e custos unitários são os mesmos nos dois desenhos; mudam junto com o cenário.

Peso da premissa de vento no provável: o VPL do desenho sem quebra-vento é −R$ 71.208 com perda de 10%, −R$ 45.384 com perda zero e −R$ 97.032 com perda de 20%. O desenho com quebra-vento dá −R$ 61.731. Com perda de 20% o desenho com renque passa à frente. O modelo não conta dano de vento além da produção (quebra de ramos, doença, geada de vento) nem a madeira da grevílea no fim do ciclo.

Tabelas anuais: `tabelas/anual_<cenario>.csv` (com quebra-vento) e `tabelas/anual_<cenario>_sem_qv.csv` (sem). Sensibilidades: `tabelas/sensibilidade_producao.csv` e `tabelas/sensibilidade_producao_sem_qv.csv`.

## Território e limites da demonstração

Polígono de 12.183,37 m² e 504,24 m de perímetro em EPSG:31984. Centroide: -21.52842°, -41.95174°. CRS dos vetores atribuído por inferência, sem transformar coordenadas; procedência e datum vertical pendentes.
Moldura única 200 × 183 m: oeste/sul/leste/norte 194130.082938933 / 7616382.736833424 / 194330.082938933 / 7616565.736833424. Grades de 0,50 m (400 × 366), 1 m (200 × 183) e 0,25 m (800 × 732) compartilham bordas. MDT é a única superfície de assentamento; textura de 2.000 × 1.830 px. A grade 0,25 m reamostra a fonte nativa 0,60 m.
Linhas: 2.935,88 m brutos, 1,86 m fora, 30 trechos e 2.934,03 m dentro; 27 trechos e 2.930,64 m elegíveis antes das exclusões. IDs de origem e trecho preservados. Os Z e ELEVATION textuais originais estão nos insumos; a cena usa o MDT.
CHM nativo, sem filtro: -1,02 a 22,66 m; 29,82% negativo e 5,53% ≥ 2,50 m. Negativos preservados em fase1/chm_bruto_nativo.tif. Camada operacional: máscaras validadas, bilinear, clip [0,30] m, mediana 3×3 a 0,25 m, abaixo de 0,30 m zerado. Copas ≥ 2,50 m, abertura morfológica, manchas ≥ 1,5 m² e folga nominal de 1 m: 802,9 m² excluídos.
Conferência visual em fase1/mapa_conferencia.png: a grande mancha alta a sudeste coincide com árvores visíveis; os negativos também ocorrem em solo e carreadores abertos e não representam alturas físicas negativas. O diagnóstico não corrige datum ou suposto viés vertical sem pontos de controle. As copas são propostas para preservação, sujeitas à confirmação em campo.
Vias indisponíveis: work/estradas.json preserva arrays vazios e métricas indisponíveis. Sem corredores ou indicadores de logística. Proximidade à borda calculada separadamente em fase1/diagnostico.json; não atesta cabeceira ou acessibilidade. Drenagem é indicação estática por MDT, limitada ao voo; vazão e contribuições além da moldura não estimadas.
Quebra-vento demonstrativo: vento assumido de 45.0°, bordas efetivamente usadas: leste, nordeste, norte. Comprimento 208,0 m, 7 trechos, 77 grevíleas. As exclusões por copa, drenagem e exposição constam de fase2/plantio_resumo.json.
Sombra visual: renderização 3D. Efeito produtivo: sobreposição de copas de plantas simuladas, sem calibração local; árvores existentes afetam exclusões e cena, não têm efeito produtivo calibrado. Insolação: céu limpo e horizonte do MDT, independente das copas. Drenagem: rede estática, independente dos anos. Carbono projetado de novas plantas, sem inventário ou crédito certificado; pastagem anterior é apenas linha de base hipotética.
Pendentes: espécies e cultivares, data de implantação, uso anterior, espaçamentos, manejo, clima local, direção do vento, carbono e solo, custos e preços, datum vertical, procedência CRS vetorial. Se a cultura ou condição inicial confirmada for incompatível, manter o pipeline territorial e adaptar modelo/interface antes de usar projeções. Detalhes de execução e testes em README.md e verificacao/aceite.json. O relatório usa padrões; edições econômicas ficam no navegador e não reescrevem este arquivo.
