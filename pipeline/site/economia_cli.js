// Roda o mesmo motor do site (economia.js) para o relatório: node economia_cli.js modelo.json parametros.json > saida.json
// Saída: os dois desenhos (com e sem quebra-vento) nos três cenários, com os valores padrão.
const fs = require('fs'), path = require('path');
const E = require(path.join(__dirname, 'economia.js'));
const MO0 = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')), PE = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = { des: {} };
for (const d of ['com', 'sem']) {
  const MO = E.desenho(MO0, d), U = E.padroes(MO, PE), o = { padroes: U, contagens: MO.econ.contagens, cen: {}, sens: E.sens(MO, PE, U) };
  for (const c of ['conservador', 'provavel', 'otimista']) {
    const rows = E.cenario(MO, PE, c, U);
    o.cen[c] = { rows, com: E.resumo(rows, true, U.taxa), sem: E.resumo(rows, false, U.taxa),
                 custo_saca: rows.map(r => ({ ano: r.ano, com: E.custoSaca(r, true), sem: E.custoSaca(r, false) })) };
  }
  out.des[d] = o;
}
Object.assign(out, out.des.com);   // compatibilidade: campos do desenho com quebra-vento na raiz
process.stdout.write(JSON.stringify(out));
