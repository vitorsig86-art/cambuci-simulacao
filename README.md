# Cambuci · réplica isolada de implantação

Pacote local em `C:\Users\Usuario\Desktop\TRABALHO CAMBUCI\SIMULACAO\cambuci_implantacao`.
Abra `site/index.html` servido por HTTP. Duplo clique (`file://`) bloqueia módulos ES locais nos navegadores comuns; agora a própria tela identifica essa situação e mostra o comando de inicialização. O pacote é estático: Three.js, OrbitControls e licença MIT estão em `site/vendor`; não requer CDN, fontes externas, conta ou publicação.

Esta é uma **hipótese demonstrativa de café, banana e grevílea**, com dois desenhos, três cenários e anos 0–30. Território medido; proposta produtiva, uso anterior de pastagem, implantação em 2026, espécies, manejo, clima, espaçamentos, vento, carbono, custos e preços pendentes de validação. Valores constantes em reais de 2026; taxa real padrão de 8% a.a. Nenhuma conclusão de aptidão climática foi emitida.

## Arquivos de entrada e referência

- `originais/`: somente os cinco arquivos fornecidos, intactos. `verificacao/entradas.json` registra SHA-256, dimensões, transformações e máscaras.
- `dados/`: cópias dos rasters, vetores com EPSG:31984 explícito e coordenadas originais, e `bbox.geojson` gerado. Atribuição vetorial inferida, sem transformação de valores. Não se trata de GeoJSON RFC 7946 para intercâmbio.
- Referência independente copiada de `C:\Users\Usuario\Desktop\projetos\simu_jurema`: `pipeline/`, documentação e três YAMLs. Nenhum intermediário ou resultado antigo foi reutilizado; nenhum insumo territorial da Jurema foi copiado.
- Jurema e o projeto `simulacao_cambuci` não foram alterados. Assinaturas dos 111 arquivos de conteúdo da referência antes/depois e comparação em `verificacao/referencia_*.json`. O inventário inicial omitiu `.git` oculto; os metadados Git ficam fora da comparação, conforme registro explícito.
- Foi consultada a implementação ativa e sua auditoria local de **30/10/2026**. A auditoria citada de **10/11/2026** e o diagnóstico territorial anterior de Cambuci não foram localizados nas pastas examinadas nem nas buscas do Drive por Jurema/diagnóstico Cambuci. Os números da solicitação foram tratados como critérios de aceite e conferidos nos arquivos. A consulta documental desses dois documentos fica pendente.

## Execução reproduzível

Ambiente validado: Python 3.12 do QGIS 3.44.13, GDAL 3.13.2, NumPy 2.4.6, SciPy 1.18.0, Shapely 2.1.2, Pillow, PyYAML e Matplotlib; Node.js v24.15.0. `qpy.bat` configura o ambiente do QGIS instalado nesta máquina. Em outro ambiente, ajuste somente o caminho do QGIS ou use Python com essas dependências. Assegure Node no PATH ou configure `NODE_EXE`.

Execute no diretório deste pacote, em PowerShell. A raiz aparece explicitamente em cada passagem:

```powershell
.\qpy.bat verificacao/preparar.py
.\qpy.bat pipeline/rodar.py --raiz 'C:\Users\Usuario\Desktop\TRABALHO CAMBUCI\SIMULACAO\cambuci_implantacao' --de 1 --ate 1
# Confira fase1/diagnostico.json, territorio_validado.json e mapa_conferencia.png antes de avançar.
.\qpy.bat pipeline/rodar.py --raiz 'C:\Users\Usuario\Desktop\TRABALHO CAMBUCI\SIMULACAO\cambuci_implantacao' --de 2 --ate 3
.\qpy.bat verificacao/verificar_territorio.py
# O verificador exporta os dois desenhos em coordenadas precisas e valida contagens/exclusões.
.\qpy.bat pipeline/rodar.py --raiz 'C:\Users\Usuario\Desktop\TRABALHO CAMBUCI\SIMULACAO\cambuci_implantacao' --de 4 --ate 6
.\qpy.bat verificacao/verificar_modelo.py
```

A ordem ativa é `ETAPAS_IMP` em `pipeline/rodar.py`. `--lista` continua legado e exibe a sequência histórica. Scripts `adaptar.py`, `adaptar_interface.py`, `ajustar_desempenho.py` e `dependencias_locais.py` registram a adaptação inicial **já incorporada nos fontes**; não os execute novamente.

Para servir localmente:

```powershell
.\qpy.bat -m http.server 8090 --bind 127.0.0.1 --directory site
# Abra http://127.0.0.1:8090 e encerre o servidor com Ctrl+C.
```

Teste atual de implantação (substitui o teste histórico de trator, que não se aplica):

```powershell
Push-Location verificacao
npm.cmd install
npx.cmd playwright install chromium
npm.cmd test
Pop-Location
.\qpy.bat verificacao/finalizar.py
```

Na execução entregue, usou-se a instalação local existente do Playwright por `PLAYWRIGHT_PATH`; a versão efetiva é registrada em `aceite.json`. Nenhum navegador ou pacote foi instalado fora da réplica por esta tarefa. O teste cria servidor HTTP temporário em loopback e encerra servidor/navegador ao terminar.

## Entregas e critérios

- `site/index.html` e `site/vendor/`: cena métrica, textura, instâncias, câmeras, desenho/cenário, anos, reprodução, camadas e economia editável. Chave isolada `cambuci_implantacao.premissas.v1`.
- `relatorio.md`: projeções condicionais e síntese territorial. Usa **o mesmo `pipeline/site/economia.js`**, por Node. O HTML embute esse motor, sem duplicar regras econômicas. O relatório usa padrões; edições ficam no navegador e não reescrevem o relatório.
- `diagnostico_territorial.md`, `fase1/diagnostico.json`, `fase1/territorio_validado.json`, `fase1/chm_bruto_nativo.tif`: evidências territoriais, inclusive diferenças negativas.
- `fase1/mapa_conferencia.png`: orto, limite, linhas, CHM nativo e exclusões propostas. `fase1/conferencia_entorno.png` e `fase2/conferencia_plantio.png` detalham as propostas.
- `fase1b/linhas_tratadas.geojson`: recorte XY realizado uma vez, com ID de origem e trecho; Z e ELEVATION textuais preservados nas entradas normalizadas e originais. Cotas da cena vêm do MDT.
- `fase2/plantas_com_precisas.geojson` e `plantas_sem_precisas.geojson`: todos os pontos antes da quantização visual de 0,01 m, apropriados para conferir a geometria; não são locação de campo.
- `verificacao/aceite.json`, `territorio_passagem2.json`, `modelo_quantizacao.json`, capturas e `logs/`: resultados dos testes e desempenho.

## Convenções e limites

CRS EPSG:31984. Origem oeste/norte E 194130,082938933 / N 7616565,736833424 m; moldura 200 × 183 m, origem local sudoeste N 7616382,736833424 m. Grades com bordas comuns: 0,50 m → 400 × 366; 1 m → 200 × 183; 0,25 m → 800 × 732. Textura 0,10 m → 2000 × 1830. Meia célula GDAL: centro em `E=X0+(col+0.5)*passo`, `N=Y1-(lin+0.5)*passo`. Cena centrada: X leste, Y altura acima de zmin, Z sul (norte negativo). `georreferencia` no HTML registra o contrato e hashes. Vertical em metros; datum pendente.

Terreno exclusivamente MDT a 0,50 m, 146.400 vértices, 291.270 triângulos, índices Uint32, quantização 0,01 m. Plantas XY 0,01 m, altura 0,10 m, raio 0,05 m e fruto ordinal 0–3; os pontos precisos mantêm a verificação geométrica independente. A grade 0,25 m **reamostra** a fonte nativa 0,60 m.

O CHM nativo preserva negativos. Camada operacional valida máscaras antes de subtrair, limita a [0,30] m, usa mediana 3×3 a 0,25 m, zera abaixo de 0,30 m, aplica abertura binária, manchas ≥1,5 m² e folga nominal de 1 m por dilatação cruz (não um buffer euclidiano exato). O limiar de copa é 2,50 m. Copas são **propostas de preservação**, ainda sem conferência de campo. A mancha alta sudeste corresponde a árvores visíveis; negativos também ocorrem em carreadores e terreno aberto. Não se inferiu correção de datum a partir disso.

Vias indisponíveis: arrays vazios mantêm o contrato; corredores e logística são nulos/omitidos na interface. Contagens de cortes por via iguais a zero significam regra inativa. Proximidade à borda das pontas é separada e não certifica cabeceira. Drenagem é indicação estática do MDT; bordas com gradiente para dentro sugerem contribuições externas desconhecidas. Não calcula vazão, erosão calibrada ou capacidade hidráulica.

Sombra 3D é visual e pode ser ativada no painel solar; efeito produtivo usa sobreposição das copas simuladas. Árvores existentes ficam na cena e nas exclusões, sem efeito produtivo calibrado. Insolação do relevo usa céu limpo e horizonte limitado ao MDT, independente das copas; drenagem não muda ao passar os anos. Relógio solar usa centroide, calendário e meridiano UTC−3 (America/Sao_Paulo, sem ajuste dinâmico de horário de verão).

O teste preliminar saturou a GPU de software. O pacote mantém a malha de 0,50 m e todas as plantas, aplica o detalhe visual móvel quando detecta SwiftShader/llvmpipe e ativa sombras apenas pelo painel solar. As medições finais estão em `verificacao/aceite.json`; desempenho de GPU física e dispositivo móvel real não foi medido. O teste móvel é viewport 390 × 844.

Se espécie ou condição inicial confirmada for incompatível, preserve o pipeline territorial e delimite a adaptação do modelo e da interface antes de usar projeções. Nenhuma implantação ou publicação externa foi realizada.
