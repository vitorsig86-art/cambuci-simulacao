# Arquitetura

```
dados (TIF + GeoJSON, CRS métrico)
   │  pipeline/rodar.py  →  scripts 01..18 (Python)  →  work/*.json|npz|png
   │                                   │
   │            projeto.yaml ──────────┘ (parâmetros da área)
   ▼
18_montar_html.py: site.json + orto2.jpg  →  template4.html  →  site/index.html
   ▼
git push → Vercel (estático)  /  publicação como artifact
```

## Página (site/template4.html, 632 linhas)
| Linhas | Bloco |
|---|---|
| 1–100 | head, CSS (claro/escuro, 2 colunas) |
| 101–201 | HTML: cena, tempo, metas, operação do trator, indicadores, gráfico, comparação, água, espécies, premissas |
| 203–204 | `__SITE__` (JSON) e `__ORTO__` (JPEG base64). No HTML gerado são MB de dados: nunca ler inteiras |
| 211–241 | `CFG`, `PRECO`, `KG_PE`, `ESP` (espécies), `CEN` (desenhos A–E) |
| 243–251 | geo: `zAt` (bilinear no terreno), `dentro`, `AREA_HA`, máscara 1 m |
| 253–294 | Sol em `CFG.lat`, `sombraGrade` (grade 1 m, 13 posições do Sol) |
| 295–362 | `simular(ci)`: motor anual, cache, indicadores `st.ind[ano]` |
| 364–424 | cena three.js: terreno recortado ao perímetro, paredes, desenho, água, zonas, texturas temáticas |
| 425–466 | trator: modelo, `trecho(k)`, animação, HUD |
| 467–534 | pools `InstancedMesh` + `poeR` (matriz direta), `construir()` por ano/desenho |
| 535–555 | câmeras `vue()` |
| 556–618 | UI, `operacao()`, `metas()`, `maj()`, `dessiner()`, loop com render sob demanda (`sujo`) |
| 619–628 | `textos()`: lede, premissas, metas e listas de blocos a partir de `S.cfg` e `S.resumo` |
| 629 | `window.__app` (gancho de teste: `simular`, `CEN`, `construir`, `pausa`) |

Módulos estáveis (não reescrever): `zAt`, `dentro`, `P`, malha do terreno, pools/`poeR`,
`sombraGrade`, `simular`, loop sob demanda.

## Coordenadas
- Local: x = E − origin[0], y = N − origin[1], z = cota − zmin (m). Sem exagero vertical.
- three.js: `P(x,y,z) = (x − W/2, z, −(y − H/2))`.
- Grade do terreno: Uint16 em cm, linha 0 = norte, centro de célula em +0,5.

## Contrato site.json
| Campo | Conteúdo | Origem |
|---|---|---|
| W, H, zmin, origin | extensão local | base2.json |
| terrain{nx,ny,res,b64} | Uint16 cm | Tq.npy |
| perimetro | polígono local | base2.json |
| cafe_b64, ncafe | Float32 [x,y,z] dos pés | cen2.json |
| cen.A..E | trees, banana, ban_perm, rem, rem_ban | cen2.json |
| existentes | [x,y,z,H0,R0] | cenarios.json (de MDS−MDT) |
| keyline, keypoint, carreadores | linhas locais | cenarios.json, zoned.json |
| agua{pasto,keyline,nivel} | paths, eixo, retido, perc | agua.json |
| zonas, areas | steep, cold; áreas em m² | cen2.json |
| rota | xy a 0,25 m, tilt, pitch, kind (0 trabalho, 1 manobra, 2 deslocamento), blk, rng, met | rota2.json |
| tex{decl,face,sol,agua} | JPEG base64 2048 px | tex.json |
| resumo | area_ha, pct_mec, faces, faces_pct, sol_inv | terreno.npz (v2) |
| cfg | lat, ano0, anos, precos, kg_pe, metas, regiao, decl_max, cabeceira, carreador, entrelinha, entreplantas, blocos{ids,nomes} | projeto.yaml (v2) |

## Desempenho medido
~2 M triângulos, 12 a 15 draw calls, troca de ano 17 a 47 ms, render só quando algo muda.
