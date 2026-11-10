# Auditoria técnica: Café Keyline 3D

Data: 30/10/2026. Base: auditoria em modo leitura feita pelo Claude Code na pasta do projeto,
conferida e corrigida com o código do pipeline que gerou o site (salvo em `pipeline/`).

## 1. Inventário
| Item | Valor |
|---|---|
| Entrega | `cafe-keyline-3d-site/index.html`, 1 arquivo estático, ~3,4 MB, sem build |
| Front | HTML + CSS + JS ES module; three.js 0.160 + OrbitControls via importmap (jsdelivr); Google Fonts |
| Dados embutidos | `<script id="site" type="application/json">` (~2,3 MB) e `<script id="orto" type="text/plain">` (JPEG base64, ~1 MB) |
| Hospedagem | GitHub `vitorsig86-art/cafe-keyline-3d` (privado) + Vercel (deploy no push da main) |
| Pipeline | Python, 23 scripts em `pipeline/scripts/`, orquestrado por `pipeline/rodar.py` |
| Parâmetros da área | `projeto.yaml` (raiz do projeto) |
| Dados brutos | `orto.tif`, `mdt.tif`, `mds.tif`, `perimetro.geojson` (EPSG:31983); `simulacao_contagem.geojson` só referência |
| Teste | `pipeline/teste/testar_site.js` (Playwright, three.js local, SwiftShader) |

## 2. Correções à auditoria do Claude Code
| Afirmação | Situação real |
|---|---|
| "Pipeline TIF→JSON ausente, risco nº 1" | Existe. Salvo em `pipeline/` com regressão: as saídas reproduzem as originais byte a byte e o `index.html` v1 saiu idêntico ao publicado. |
| Latitude −22,05 como fato | Era um erro do template (valor da primeira área). Correto −21,89. Agora calculada do perímetro. |
| "Árvores com ~33.900 m de altura" | Refutado. As árvores mais altas têm 28,8 a 37,6 m de MDS−MDT com MDT válido (limite de 30 m aplicado). As 180 células sem dado estão todas fora do perímetro. |
| "GitHub Pages" | É Vercel. |
| "Sem medição de desempenho" | Medido: ~2 M triângulos, 12 a 15 draw calls, reconstrução de ano em 17 a 47 ms. |
| Valores fixos espalhados no HTML | Corrigido na v2: latitude, ano inicial, preços, metas, blocos, limites, névoa e caixa de sombra vêm de `S.cfg` / `S.resumo`. |

Pontos da auditoria do Claude Code que continuam válidos: mapa do código do HTML, contrato do
`site.json`, papéis dos dados (MDT para geometria, MDS só para altura das árvores, orto só textura),
caráter pedagógico do modelo, regra de nunca ler as duas linhas de dados do HTML inteiras.

## 3. Números da área teste (3,09 ha, Mantiqueira)
- Declividade: 78% da área até 20%; 95% das faces para norte e nordeste; sol de inverno ~10% acima de área plana.
- Keypoint: 1.096 m (E 514536,5 N 7578950,5); sugestão automática da etapa 3 deu 1.096,2 m no mesmo ponto.
- Zona mecanizável 2,36 ha; 65 linhas; 7.407 pés de café; rota de 5,41 km por passada; 23,3 h-máquina/ano.
- Desenhos (média anos 6 a 15, mil R$/ha e h/semana): A 30,0/15; B 35,3/30; C 27,6/17; D 37,1/50; E 45,9/29.
- Água: pasto retém 0%; keyline 40%; em nível 43% (o ganho vem das bermas; a keyline acrescenta pouco).

## 4. Riscos e limitações
1. **Decisões manuais** (keypoint e espigões) ainda exigem leitura humana do perfil e da curvatura.
   O pipeline sugere o keypoint; os espigões são desenhados sobre `work/curv.png`.
2. **Heurística do eixo do vale.** O modo janela (v1) pega o ponto mais ao sul de cada curva: só vale
   para vales que drenam para o sul. Áreas novas usam o modo automático (maior acúmulo de fluxo).
3. **Desenhos A a E** estão no código (`cen2.py` e `CEN` no template), calibrados para café de
   montanha. Outra cultura exige reescrever essas duas peças.
4. **Coeficientes** de produção, horas, preços e carbono são estimativas, não calibradas.
5. **Tamanho**: áreas muito maiores que 3 ha aumentam o HTML (terreno em cm e texturas embutidas)
   e o custo do A*. Acima de ~20 ha, avaliar grade de 2 m e texturas menores.
6. **Python no Windows** não está instalado na máquina do usuário; o pipeline roda no ambiente de
   nuvem do Claude ou após instalar Python 3.11 + requirements.

## 5. Recomendações
- Rodar sempre por `rodar.py`; nunca editar o `index.html` gerado (alterar template ou pipeline).
- Manter `referencia/` e rodar a regressão após mexer em script compartilhado.
- Versionar `projeto.yaml` junto com o site de cada propriedade.
