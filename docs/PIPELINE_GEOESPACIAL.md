# Pipeline geoespacial

Ordem e arquivos: `pipeline/README_PIPELINE.md`. Aqui ficam os métodos e as decisões.

## 1. Preparação (etapas 1, 2, 10)
- MDT reamostrado a 1 m (média), sem dado preenchido por vizinho mais próximo só para suavização.
- Acúmulo de fluxo com pysheds: preenchimento de depressões, resolução de planos, D8. `Ai` é o
  acúmulo no MDT invertido (marca espigões).
- Base 3D (`prep2.py`): terreno 1 m em cm, orto 4096 px JPEG q72, árvores existentes por máximos
  locais de MDS − MDT dentro do perímetro, altura limitada a 30 m, raio de copa estimado.

## 2. Keyline (etapas 3 a 8)
1. **Eixo do vale.** `eixo_modo: fluxo` (padrão): talvegue seguido rio acima pelo D8, a partir do
   exutório (maior acúmulo dentro de `eixo_colunas`, ou o ponto `eixo_exutorio`). `eixo_modo: sul`
   (área teste): ponto mais ao sul de cada curva de 0,5 m dentro da janela.
2. **Keypoint (DECISÃO 1).** Perfil de declividade ao longo do eixo; keypoint = base do trecho mais
   íngreme, onde o vale passa de côncavo íngreme a mais suave (Yeomans). Sugestão automática: menor
   cota com declividade ≥ 85% da máxima, e uma segunda pela maior quebra de declive (média dos 4 m
   acima menos a dos 4 m abaixo). Quando concordam, a escolha é segura. Confirmar no campo.
3. **Keyline global** (`keyline.py`): curva de nível da cota do keypoint que passa pelo keypoint;
   distância assinada a ela (positiva acima) define as linhas paralelas.
4. **Espigões (DECISÃO 2).** Linhas desenhadas sobre `work/curv.png` (vermelho = convexo) em
   [linha, coluna] da grade de 1 m, cruzando o perímetro. Viram carreadores e dividem os blocos
   (Doherty: keylines comuns por forma de relevo).
5. **Blocos e guias** (`zones.py`): no bloco do vale a guia é a keyline; nos demais testa-se a guia
   em várias cotas e fica a de menor p90 de caimento.
6. **Faixas** (`bands.py`): linhas paralelas à guia a cada `entrelinha`; quando o p90 do caimento ao
   longo da linha passa de `caimento_max`, abre-se nova linha-mestra. Pés a cada `entreplantas`.
   Com `plantio.completar: true`, as partes do bloco onde as faixas não chegam (comum em áreas
   grandes) ganham nova linha-mestra na cota mediana do pedaço, até restar menos de 0,15 ha.

Resultado na área teste: caimento mediano 0,4%; 0,2% dos trechos acima de 5%.

## 3. Terreno e clima (etapa 13)
- Declividade e face (para onde a encosta cai) do MDT suavizado.
- Radiação: 16 azimutes de horizonte, Sol pela latitude; `rel` anual e `relw` inverno em % de área plana.
- TWI de acúmulo e declividade. Ar frio: elevação relativa < −0,6 m e TWI > 5,5.

## 4. Mecanização (etapa 14)
- Zona mecanizável: declividade suavizada (σ 2,5) ≤ `declividade_max`, limpeza morfológica.
- Carreadores: espigões com buffer `carreador/2`. Cabeceiras de `cabeceira` m só nas pontas que não
  terminam em carreador. Linhas menores que `linha_min` saem. Raio mínimo de curvatura 24 m.
- Fora do café: encostas acima do limite e bolsões de ar frio (usos próprios em cada desenho).
- `exclusoes.app_m`: faixa de APP em volta dos cursos d'água (acúmulo ≥ `app_acumulo_ha`). Sai do café
  e recebe só restauração nativa, igual em todos os desenhos; o quebra-vento não entra nela.
- `exclusoes.arquivo`: polígonos (sede, curral, estradas) sem café e sem árvores novas.

## 5. Desenhos e simulação (etapa 15 e template)
- A: café + regeneração nas encostas; B: café + bananal; C: café arborizado + restauração produtiva;
  D: agroflorestal sucessional; E: café + pomar e quebra-vento.
- No navegador: crescimento Chapman-Richards, sombra em grade de 1 m, café 0,55 kg/pé com
  bienalidade ±18%, esqueletamento nos anos 12 e 24, carbono Chave et al. (2014), horas por
  coeficientes + horas-máquina da rota.

## 5b. Ocupação desenhada (opcional)
Com `ocupacao.arquivo`, a zona mecanizada vira só o polígono `cafe_mec`, e `15b_ocupacao.py` substitui os desenhos A a E:
café nas linhas keyline das zonas de café, sombra a cada três linhas no `cafe_saf`, oliveiras linha sim, linha não a
cada 5 m no `oliva`, nativas em quincôncio de 4 m na `restauracao`. Cada desenho do yaml troca usos (`trocar`), o que
permite comparar a proposta com variantes e com o uso atual no mesmo 3D. Primeiro caso: Cruzília, unidade E.

## 6. Água (etapa 12)
Partículas (~600, espaçamento mínimo 7 m) descem pelo gradiente; com APP configurada, a que chega ao
córrego conta como escoada; linhas retêm conforme o cenário (pasto sem linhas,
keyline, curvas em nível). Mede % retido e % que chega ao eixo do vale.

## 7. Rota do trator (etapa 17)
Entrelinhas por bloco no padrão alternado (com `rota_por_manchas`, mancha por mancha, na ordem da
mais próxima); ligações por A* em grade de 0,5 m evitando linhas
(buffer 1,25 m), árvores e declive; trânsito até 25% com custo 3. Reamostrada a 0,25 m com
inclinação lateral e rampa. Métricas: roçada 4 km/h, pulverização e adubação 5 km/h, apoio à
colheita 3 km/h; manobra 3 km/h; deslocamento 8 km/h; 25 s por virada.

## 8. Validação
1. Regressão na área teste contra `referencia/` (ver `PLAYBOOK_REPLICACAO.md` §5).
2. Área nova: conferir `mapa_keyline.png` (cores de caimento), `diagnostico_terreno.png` e a
   sugestão de keypoint antes de seguir.
