# Prompt mestre: nova propriedade

Copie e cole, trocando os campos entre < >.

---
Vou gerar o simulador Café Keyline 3D para uma nova propriedade.

Pasta do projeto: <caminho>. Dados em <caminho>/dados: orto.tif, mdt.tif, mds.tif, perimetro.geojson.
Pipeline: <caminho do pipeline>. Leia primeiro docs/CONTEXTO_AGENTE.md e docs/PLAYBOOK_REPLICACAO.md.
Não leia index.html gerado inteiro.

1. Inspecione os dados e responda só com números: CRS, resolução, extensão, % sem dado no
   perímetro, área em ha. Pare se o CRS não for métrico ou se os arquivos divergirem.
2. Crie projeto.yaml a partir de pipeline/projeto.modelo.yaml com: nome <nome>, região <região>,
   CRS dos dados. Demais parâmetros padrão, salvo: <ajustes, ex.: declividade_max 25>.
3. Rode rodar.py até a primeira parada. Mostre o perfil resumido e a sugestão de keypoint, com sua
   leitura. Aguarde minha confirmação.
4. Com o keypoint confirmado, rode até a curvatura. Proponha os espigões em [linha, coluna] com a
   imagem curv.png anotada e os blocos resultantes. Aguarde confirmação.
5. Rode o restante. Entregue: mapa_keyline.png, diagnostico_terreno.png, área mecanizável, nº de pés,
   rota (km, h-máquina/ano, ligações sem caminho) e a tabela dos 5 desenhos (mil R$/ha, h/semana).
6. Rode o teste do site e publique como artifact. Não altere scripts compartilhados sem me avisar;
   se alterar, rode a regressão da área teste.

Respostas curtas, com números, em português, sem travessão.
---
