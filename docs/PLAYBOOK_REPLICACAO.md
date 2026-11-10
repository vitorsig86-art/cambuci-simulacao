# Playbook: nova propriedade

Tempo típico com o Claude: 30 a 60 min, a maior parte nas duas decisões manuais.

## 1. Preparar a pasta
```
<nova_area>/
  projeto.yaml            (cópia de pipeline/projeto.modelo.yaml)
  dados/orto.tif          RGBA
  dados/mdt.tif
  dados/mds.tif
  dados/perimetro.geojson 1 polígono
```
Todos no mesmo CRS projetado em metros (ex.: EPSG:31983). Resolução do MDT de 0,5 a 1 m basta.
- Orto precisa ser RGB(A) 8 bits. Multiespectral ou 16 bits: `python pipeline/scripts/00_orto_rgb.py
  entrada.tif dados/orto.tif 1 2 3 8`. ECW não é lido: exporte para TIF no QGIS/Global Mapper.
- Perímetro com Z, vários polígonos ou outro nome: renomeie para `perimetro.geojson`; o `rodar.py`
  converte para 1 polígono 2D e guarda o original.
- Áreas acima de ~10 ha: use `plantio.completar: true` e `mecanizacao.rota_por_manchas: true`.

## 2. Inspeção (antes de rodar)
Conferir CRS, resolução, extensão, % sem dado dentro do perímetro e área do perímetro.
Se CRS divergente, reprojetar antes (QGIS ou `gdalwarp`).

## 3. Preencher o básico do projeto.yaml
`nome`, `titulo_html`, `regiao`, `crs`, `blocos` provisório (`ids: [V]`), parâmetros de plantio,
mecanização e simulação se diferentes do padrão.

## 4. Rodar até a decisão 1
`python pipeline/rodar.py --raiz <nova_area>` roda 1 a 3 e para.
- Ler o perfil e a linha `SUGESTÃO de keypoint`.
- Se o eixo foi para o vale errado, definir `keyline.eixo_colunas` e repetir `--de 3`.
- Preencher `keyline.cota` e `keyline.keypoint`.

## 5. Decisão 2: espigões
`--de 4` roda 4 a 6 e para. Abrir `work/curv.png`; desenhar cada espigão como lista de
[linha, coluna] cruzando o perímetro. Preencher `blocos.espigoes`, `ids` (oeste → leste),
`nomes` e `vale`. Sem espigão relevante: `espigoes: []` e um único bloco.

## 5b. Exclusões
Cursos d'água com APP: `exclusoes.app_m: 30`. Sede, curral, estradas: polígonos em
`dados/exclusoes.geojson` e `exclusoes.arquivo: exclusoes.geojson`.

## 5c. Ocupação (quando o desenho já foi escolhido)
Desenhe as zonas de uso em `dados/ocupacao.geojson` (ou gere por regra, como em `projeto cruzilia/unidade_E/analise/ocupacao.py`)
e declare os desenhos no bloco `ocupacao` do yaml. Rasters recortados para o projeto precisam ter a mesma extensão
em metros inteiros (orto, MDT e MDS), senão as grades de 1 m saem com tamanhos diferentes.

## 6. Rodar o resto
`--de 7`. Conferir:
- `work/mapa_keyline.png`: linhas majoritariamente verdes (caimento < 2%).
- `work/diagnostico_terreno.png`: declividade, face, sol, umidade.
- Saída do `mec.py`: área mecanizável, nº de linhas, pés.
- Saída do `rota2.py`: "ligações sem caminho livre" deve ser 0.

## 7. Testar e publicar
- `node pipeline/teste/testar_site.js <nova_area>`: sem erros de JS, receita e horas plausíveis.
- Publicar: repositório novo com `site/index.html` como `index.html`, Vercel importa o repositório.

## 8. Checklist de aceitação
- [ ] Console sem erros; `__app.simular(i).ind.length === anos + 1`, sem NaN.
- [ ] Trator percorre todos os blocos; lista de trechos mostra os nomes do yaml.
- [ ] Texto de abertura com área e região corretas; latitude certa nas premissas.
- [ ] Desenho A com sombra só das árvores existentes.
- [ ] AREA_HA igual à área do perímetro.

## 9. Quando algo dá errado
| Sintoma | Causa provável | Ação |
|---|---|---|
| `espigões geram N blocos` | linha não cruza o perímetro ou nº de ids errado | estender a linha além do perímetro; ajustar ids |
| Muitas linhas vermelhas no mapa | guia ruim ou relevo muito irregular | baixar `caimento_max`, rever espigões |
| Ligações sem caminho livre > 0 | bloco isolado por declive | revisar carreadores ou aceitar trecho manual |
| Eixo do vale aos saltos | talvegue fraco ou vale errado | `eixo_colunas` ou `eixo_exutorio` |
| Poucas linhas na zona mecanizável | faixas não cobriram o bloco | `plantio.completar: true` |
| Deslocamento do trator maior que o trabalho | zona fragmentada | `rota_por_manchas: true` |
| Horas/semana muito altas nos desenhos B e D | área fora do café grande (bananal e SAF manual nela) | ler como alerta: esses desenhos não cabem na mão de obra |
| HTML acima de 15 MB | área grande | já reduzido (água ~600 trajetórias, rota em 0,1 m); se preciso, orto menor no prep2 |

## 10. Regressão do pipeline (após alterar scripts)
Rodar na área teste (`projeto_cafe_teste`) e comparar `work/*.json` com `pipeline/referencia/`.
Esperado: idênticos, exceto `tex.json` (sol) por latitude calculada.
