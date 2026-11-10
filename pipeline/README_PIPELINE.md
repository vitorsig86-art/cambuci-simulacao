# Pipeline Café Keyline 3D (v2, parametrizado)

Transforma ortomosaico + MDT + MDS + perímetro de drone em um site 3D estático (`site/index.html`)
com café keyline mecanizável, 5 desenhos agroflorestais, 30 anos de simulação e rota do trator.

v2 = mesmo código da v1 (que gerou o site publicado), com os valores da área movidos para
`projeto.yaml`. Regressão na área teste: todas as saídas intermediárias idênticas byte a byte à
`referencia/`, exceto a textura "sol" (latitude agora calculada do perímetro, −21,8937 em vez de
−21,894; diferença máxima de 4 níveis de cor). Receita e horas dos 5 desenhos iguais às publicadas.

## Uso
```
pip install -r pipeline/requirements.txt        # Python 3.11+
cd <pasta do projeto>                           # tem projeto.yaml e os 4 arquivos de dados
python <caminho>/pipeline/rodar.py              # roda tudo; para nas decisões manuais
python <caminho>/pipeline/rodar.py --de 7       # retoma
python <caminho>/pipeline/rodar.py --lista      # mostra as etapas
```
Saídas em `<projeto>/work/` (intermediárias, PNG de diagnóstico) e `<projeto>/site/index.html`.

## Dados de entrada (nomes fixos, todos no mesmo CRS projetado em metros)
`orto.tif` (RGBA), `mdt.tif`, `mds.tif`, `perimetro.geojson` (1 polígono). A pasta vem de
`dados.pasta` no `projeto.yaml`.

## Etapas
| # | Script | Grava em work/ | Observação |
|---|---|---|---|
| 1 | 01_dem1m.py | dem1m.npz, dem1m.tif | MDT reamostrado a 1 m |
| 2 | hydro.py | hydro.npz | acúmulo de fluxo (pysheds; `np.in1d=np.isin`) |
| 3 | 03_eixo_vale.py | axis.npy | perfil do eixo do vale + SUGESTÃO de keypoint. **Decisão 1** |
| 4 | keyline.py | sd.npz, base.json | keyline global pela cota do keypoint |
| 5 | rows.py | rows.json | linhas keyline globais e em nível (a água usa as de nível) |
| 6 | 05_curvatura.py | curv.png, kp.npy | curvatura em planta com grade. **Decisão 2: espigões** |
| 7 | zones.py | zoned.json | blocos separados pelos espigões, guia de cada bloco |
| 8 | bands.py | bands.json | linhas por faixas (nova linha-mestra quando p90 do caimento > limite) e pés |
| 9 | drift.py, mapa.py | mapa_keyline.png | diagnóstico (opcional) |
| 10 | prep2.py | base2.json, Tq.npy, T1.npy, orto2.jpg | terreno 3D, textura, árvores existentes (MDS−MDT) |
| 11 | cenarios.py | cenarios.json | existentes, keyline, carreadores |
| 12 | agua.py | agua.json | escoamento: pasto, keyline, em nível |
| 13 | terreno.py, painel.py | terreno.npz, diagnostico_terreno.png | declividade, face, sol, TWI, ar frio |
| 14 | mec.py | mec.json | zona mecanizável, cabeceiras, carreadores, linhas finais |
| 15 | cen2.py | cen2.json | os 5 desenhos |
| 16 | 16_texturas.py | tex.json | texturas temáticas do terreno |
| 17 | rota2.py, 17b_metricas_rota.py | rota2.json | rota A* do trator e horas-máquina |
| 18 | 18_montar_html.py | ../site/index.html | injeta dados no `site/template4.html` |
| 0 | 00_orto_rgb.py (manual) | dados/orto.tif | converte orto 16 bits ou multiespectral em RGBA 8 bits |

Teste: `teste/testar_site.js` (Playwright + three.js local), ver comentário no arquivo.

## Pastas
- `scripts/` pipeline; `scripts/config.py` lê o `projeto.yaml`.
- `site/template4.html` página com `__SITE__`, `__ORTO__`, `__NOME__`, `__TITULO__`.
- `projeto.yaml` da área teste; `projeto.modelo.yaml` para áreas novas.
- `referencia/` saídas da área teste para regressão.
- `historico/` como o template foi derivado e scripts substituídos (rota.py, t5.js). Não roda.
