# CONTEXTO: Café Keyline 3D (Cardeal Map)
Leia isto antes de abrir qualquer arquivo. Não redescubra a arquitetura.

## O que é
Simulador 3D estático (1 HTML) de café keyline mecanizável + 5 desenhos agroflorestais em 30 anos,
gerado por um pipeline Python a partir de orto, MDT, MDS e perímetro de drone.
Área teste: projeto_cafe_teste, 3,09 ha, EPSG:31983, lat −21,89. Segundo caso: projeto ivan, 33,7 ha
(córrego com APP, sede, orto multiespectral convertido). Terceiro: Cruzília, 15,7 ha em 5 unidades;
unidade E (3,8 ha) em café agroflorestal com os 5 desenhos (a ocupação mista com olival foi descartada:
perdeu qualidade). Lição: recorte justo (múltiplos de 21 m), café até 30% com trator até 20%, APP só onde é obrigatória.
Site: repo vitorsig86-art/cafe-keyline-3d (privado) → Vercel.

## Onde está cada coisa
- `pipeline/rodar.py` orquestra; `pipeline/scripts/` 23 scripts; `scripts/config.py` lê `projeto.yaml`.
- `projeto.yaml` (raiz de cada projeto): CRS, keypoint, espigões, blocos, plantio, mecanização, preços.
- `pipeline/site/template4.html`: página. `18_montar_html.py` injeta dados e gera `site/index.html`.
- `pipeline/referencia/`: saídas da área teste para regressão.
- `docs/`: AUDITORIA, ARQUITETURA, PIPELINE_GEOESPACIAL, PLAYBOOK_REPLICACAO, PROMPT_MESTRE.

## REGRA Nº 1 DE TOKENS
No `index.html` gerado as linhas 203 e 204 são MB de dados. Nunca ler o arquivo inteiro.
- Código: ler `pipeline/site/template4.html` (632 linhas, sem dados).
- Dados: `python -c` com json sobre `work/*.json` ou extrair a linha 203.
- Não editar `site/index.html`: alterar template ou script e regenerar com `--de 18`.

## Rodar
```
cd <projeto>; python <...>/pipeline/rodar.py            # tudo
python <...>/pipeline/rodar.py --de N [--ate M]          # retomar
```
Para nas decisões: etapa 3 (keypoint) e 6 (espigões) se vazias no yaml.

## Etapas (detalhe no README_PIPELINE)
1 MDT 1 m · 2 fluxo · 3 eixo/keypoint · 4 keyline global · 5 linhas · 6 curvatura · 7 blocos ·
8 faixas e pés · 9 diagnóstico · 10 base 3D · 11 cenários base · 12 água · 13 terreno/clima ·
14 zona mecanizável · 15 desenhos A–E · 16 texturas · 17 rota do trator · 18 HTML.

## Opções do projeto.yaml além do básico
keyline.eixo_modo (fluxo|sul), eixo_colunas, eixo_exutorio, eixo_cota_max · plantio.completar, nivel ·
mecanizacao.rota_por_manchas · exclusoes.app_m, app_acumulo_ha, arquivo · ocupacao.arquivo, desenhos (15b_ocupacao.py) · mecanizacao.cafe_max · exclusoes.app_linhas, nascentes. Modelo comentado em
pipeline/projeto.modelo.yaml. Ausentes = comportamento da área teste (regressão idêntica).

## Coordenadas
Local x=E−origin[0], y=N−origin[1], z=cota−zmin. three: P(x,y,z)=(x−W/2, z, −(y−H/2)).
Terreno Uint16 cm, linha 0 = norte. Espigões no yaml em [linha, coluna] da grade de 1 m:
E = x0+col+0,5; N = y1−lin−0,5.

## Papéis dos dados
MDT: terreno, declividade, keyline, zonas, rota, água. MDS: só altura das árvores existentes
(MDS−MDT, máx. 30 m). Orto: textura e detecção de copas. Perímetro: recorte e área.

## Regras de domínio
Mecanizável ≤ 20%; linhas 3,7 × 0,6 m; raio mín. 24 m; cabeceira 6 m só nas pontas sem carreador;
carreador 7 m nos espigões; linha mín. 20 m. Fora do café: > 20% e ar frio.
Trator: entrelinhas alternadas, 25 s/virada, manobra 3 km/h, deslocamento 8 km/h, trânsito ≤ 25%.

## Natureza do modelo
Pedagógico, não calibrado. Geometria (sombra, rota, água) vem do MDT; produção, horas, receita e
carbono por coeficientes. Comparar desenhos, não prever safra.

## Estável: não reescrever
`zAt`, `dentro`, `P`, malha do terreno, pools + `poeR`, `sombraGrade`, `simular`, loop sob demanda,
`bands.py`, `rota2.py` (A*), `agua.py`.

## Ainda específico de café
`cen2.py` e `CEN`/`ESP` no template definem os 5 desenhos e espécies. Outra cultura: reescrever só isso.

## Erros já resolvidos (não repetir)
- pysheds com numpy 2: `np.in1d = np.isin`.
- Malha fora do perímetro: triângulos recortados e paredes no perímetro.
- `[hidden]{display:none!important}` para legendas com display grid.
- Playwright com animação: capturas com `clip` e `__app.pausa(true, pos)`.
- Commit para o PC do usuário: preparar arquivo com nome novo (cópia antiga em cache).

## Verificação rápida
`node pipeline/teste/testar_site.js <projeto>`: sem erros, 5 desenhos com receita e horas, trechos com
os nomes dos blocos. Regressão: área teste igual a `referencia/` (exceto textura sol).

## Ambiente
Windows do usuário sem Python instalado: o pipeline roda no ambiente de nuvem do Claude
(dados enviados da pasta, resultados devolvidos) ou após instalar Python 3.11 + requirements.
Preferências: português, direto, sem travessão, sem clichês.
