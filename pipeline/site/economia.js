// Fluxo de caixa anual da implantação de café com banana, com ou sem quebra-vento, em R$ constantes de 2026 (sem inflação).
// Sem quebra-vento: contagem de grevíleas zero, logo sem muda, cova, plantio e desrama do renque.
// O mesmo arquivo roda no site (injetado pela etapa 5) e no relatório (node, etapa 6).
// Linha do tempo: ano 0 = plantio (implantação), anos 1 a N = custeio, colheita e receita com a produção do modelo.
(function (root) {
  const NIV = { conservador: 'c', provavel: 'p', otimista: 'o' };
  const SPP = ['grevilea', 'banana', 'cafe'];
  const FORM = [0, 0.4, 0.7];   // adubação do café nos anos 0, 1 e 2 em relação ao ano de produção (premissa)

  function implCaixa(PE, n, C, A, per) {
    const I = PE.implantacao, g = o => o[n];
    let v = (g(I.preparo_solo_ha) + g(I.correcao_ha) + g(I.outros_ha)) * A + g(I.cerca_m) * per;
    for (const s of SPP) v += (g(I.muda[s]) + g(I.adubo_cova[s])) * C[s];
    return v;
  }
  function custeioCaixa(PE, n, viv, A, y) {
    const Cu = PE.custeio, g = o => o[n], f = y < FORM.length ? FORM[y] : 1;
    let v = (g(Cu.fitossanitario_ha) + g(Cu.manutencao_ha)) * A;
    for (const s of SPP) v += g(Cu.adubo_planta[s]) * viv[s] * (s === 'cafe' ? f : 1);
    return v;
  }
  const serieModelo = (MO, cenId) => MO.cen[cenId].ind;

  // desenho 'sem' (sem quebra-vento): a mesma área com as plantas, as séries e as contagens do segundo desenho (modelo.des.sem)
  function desenho(MO, id) {
    const d = id === 'sem' && MO.des && MO.des.sem; if (!d) return MO;
    return Object.assign({}, MO, { n: d.n, plantas: d.plantas, plantio: d.plantio, cen: d.cen, sens: d.sens, sens_base: d.sens_base, desenho: 'sem',
                                   econ: Object.assign({}, MO.econ, { contagens: d.contagens, sens: d.econ_sens || {} }) });
  }
  // os campos editáveis valem para um desenho; no outro, implantação e custeio por hectare andam na mesma proporção do padrão
  function uPara(U, Dde, Dpara) {
    return Object.assign({}, U, { impl_ha: U.impl_ha * Dpara.impl_ha / Dde.impl_ha, custeio_ha: U.custeio_ha * Dpara.custeio_ha / Dde.custeio_ha });
  }

  // valores padrão (provável) dos campos editáveis do site
  function padroes(MO, PE) {
    const E = MO.econ, A = MO.area_ha, p = o => o.p, ser = serieModelo(MO, 'provavel'), yr = Math.min(6, ser.length - 1);
    return { preco_cafe: p(PE.precos.cafe_saca), preco_banana: p(PE.precos.banana_kg),
             impl_ha: implCaixa(PE, 'p', E.contagens, A, E.perimetro_m) / A,
             custeio_ha: custeioCaixa(PE, 'p', ser[yr].por_esp, A, yr) / A,
             diaria: p(PE.mao_de_obra.diaria), mo_propria: !!PE.mao_de_obra.propria_valorizada, taxa: p(PE.geral.taxa_desconto) };
  }
  // os campos editam o provável; conservador e otimista andam na mesma proporção
  function mult(MO, PE, U) {
    const D = padroes(MO, PE), k = (x, d) => (x == null || !isFinite(x) || !d) ? 1 : x / d;
    return { cafe: k(U.preco_cafe, D.preco_cafe), banana: k(U.preco_banana, D.preco_banana), impl: k(U.impl_ha, D.impl_ha),
             custeio: k(U.custeio_ha, D.custeio_ha), diaria: k(U.diaria, D.diaria) };
  }

  // fluxo anual de um cenário. alt = {serie, contagens} para as variações de desenho (parâmetros prováveis)
  function cenario(MO, PE, cenId, U = {}, alt = null) {
    const E = MO.econ, A = MO.area_ha, n = alt ? 'p' : NIV[cenId], g = o => o[n], K = mult(MO, PE, U);
    const ANO0 = MO.ano0, C = alt ? alt.contagens : E.contagens, ser = alt ? alt.serie : serieModelo(MO, cenId);
    const pc = g(PE.precos.cafe_saca) * K.cafe, pb = g(PE.precos.banana_kg) * K.banana, fb = g(PE.precos.fracao_comercial_banana);
    const I = PE.implantacao, Cu = PE.custeio, Co = PE.colheita, diaria = g(PE.mao_de_obra.diaria) * K.diaria, rows = [];
    for (let y = 0; y < ser.length; y++) {
      const S = ser[y], viv = S.por_esp, kc = S.kg_cafe, kb = S.kg_banana, sc = kc / 60, vb = kb * fb;
      const rec = { cafe: sc * pc, banana: vb * pb };
      let ic = 0, id = 0, cc = 0, cd = 0, rc = 0, rd = 0;
      if (y === 0) {
        ic = implCaixa(PE, n, C, A, E.perimetro_m) * K.impl; id = g(I.dias_preparo_ha) * A;
        for (const s of SPP) id += g(I.dias_plantio_muda[s]) * C[s];
      } else {
        cc = custeioCaixa(PE, n, viv, A, y) * K.custeio;
        cd = (g(Cu.dias_capina_ha) + g(Cu.dias_adubacao_ha) + g(Cu.dias_fito_ha)) * A;
        for (const s of SPP) { cd += g(Cu.dias_manejo_planta[s]) * viv[s];
          const m = (S.replantio && S.replantio[s]) || 0;                 // replantio das mortes do ano anterior
          rc += (g(I.muda[s]) * (s === 'banana' ? 0 : 1) + g(I.adubo_cova[s])) * m; rd += g(I.dias_plantio_muda[s]) * m; }   // banana: filhote da própria área
        rc *= K.custeio;
      }
      // recepa do café e renovação da banana (feitas depois da colheita do ano)
      const md = (S.recepados || 0) * g(Cu.dias_recepa_planta) + (S.renov_banana || 0) * g(I.dias_plantio_muda.banana);
      const mc = (S.renov_banana || 0) * g(I.adubo_cova.banana) * K.custeio;
      const hcCafe = sc * g(Co.cafe_pos_saca), hdCafe = sc * g(Co.cafe_dias_saca);
      const hc = hcCafe + vb * g(Co.banana_pos_kg), hd = hdCafe + kb / 1000 * g(Co.banana_dias_t);
      const receita = rec.cafe + rec.banana, caixa = ic + cc + rc + mc + hc, dias = id + cd + rd + md + hd;
      rows.push({ ano: ANO0 + y, y, idade: y, sacas: sc, kg_banana: kb, rec, receita,
                  impl: ic, impl_dias: id, custeio: cc + rc + mc, custeio_dias: cd + rd + md, colheita: hc, colheita_dias: hd,
                  colheita_cafe: hcCafe, colheita_cafe_dias: hdCafe, caixa, dias, mo: dias * diaria, diaria,
                  res_sem: receita - caixa, res_com: receita - caixa - dias * diaria });
    }
    return rows;
  }

  function npv(f, r) { let v = 0; for (let i = 0; i < f.length; i++) v += f[i] / Math.pow(1 + r, i); return v; }
  function tir(f) {
    if (!(f.some(v => v < 0) && f.some(v => v > 0))) return null;
    let lo = -0.95, hi = 3, flo = npv(f, lo), fhi = npv(f, hi);
    if (flo * fhi > 0) return null;
    for (let k = 0; k < 120; k++) { const m = (lo + hi) / 2, fm = npv(f, m); if (flo * fm <= 0) { hi = m; fhi = fm; } else { lo = m; flo = fm; } }
    return (lo + hi) / 2;
  }
  // resumo de um fluxo: com = mão de obra própria valorizada
  function resumo(rows, com, taxa) {
    const f = rows.map(r => com ? r.res_com : r.res_sem), acum = []; let s = 0, min = 0, anoMin = rows[0].ano;
    f.forEach((v, i) => { s += v; acum.push(s); if (s < min) { min = s; anoMin = rows[i].ano; } });
    // ano de retorno: último cruzamento de negativo para positivo, se o acumulado termina positivo
    let pb = null; if (acum[acum.length - 1] >= 0) { for (let i = 1; i < acum.length; i++) if (acum[i - 1] < 0 && acum[i] >= 0) pb = rows[i].ano; if (pb == null && min >= 0) pb = rows[0].ano; }
    const impl = rows[0].impl + (com ? rows[0].impl_dias * rows[0].diaria : 0);
    return { fluxo: f, acum, payback: pb, payback_anos: pb == null ? null : pb - rows[0].ano, vpl: npv(f, taxa), tir: tir(f),
             exposicao: -min, ano_exposicao: anoMin, impl, final: acum[acum.length - 1] };
  }
  // custo por saca: colheita do café + parte dos demais custos na proporção da receita do café
  function custoSaca(r, com) {
    if (r.sacas < 0.05 || r.receita <= 0) return null;
    const tot = r.caixa + (com ? r.mo : 0), colhCafe = r.colheita_cafe + (com ? r.colheita_cafe_dias * r.diaria : 0);
    const colhTot = r.colheita + (com ? r.colheita_dias * r.diaria : 0);
    return (colhCafe + (tot - colhTot) * r.rec.cafe / r.receita) / r.sacas;
  }

  // sensibilidade do ano de retorno e do VPL (parâmetros prováveis, um fator por vez)
  function sens(MO, PE, U = {}) {
    const D = padroes(MO, PE), base = Object.assign({}, D, U), taxa = base.taxa, out = [];
    const um = (grupo, nome, u, alt = null, cen = 'provavel') => {
      const rows = cenario(MO, PE, cen, Object.assign({}, base, u), alt);
      out.push({ grupo, nome, com: resumo(rows, true, taxa), sem: resumo(rows, false, taxa), sacas: rows.reduce((s, r) => s + r.sacas, 0) });
    };
    um('Base', 'provável', {});
    um('Preço do café', '-30%', { preco_cafe: base.preco_cafe * 0.7 }); um('Preço do café', '+30%', { preco_cafe: base.preco_cafe * 1.3 });
    um('Custo de implantação', '-30%', { impl_ha: base.impl_ha * 0.7 }); um('Custo de implantação', '+30%', { impl_ha: base.impl_ha * 1.3 });
    um('Mão de obra (diária)', '-30%', { diaria: base.diaria * 0.7 }); um('Mão de obra (diária)', '+30%', { diaria: base.diaria * 1.3 });
    um('Custeio anual', '-30%', { custeio_ha: base.custeio_ha * 0.7 }); um('Custeio anual', '+30%', { custeio_ha: base.custeio_ha * 1.3 });
    for (const [nome, v] of Object.entries(MO.econ.sens || {})) um(v.premissa, nome, {}, { serie: v.serie, contagens: v.contagens });
    um('Cenário completo', 'conservador (produção, preço e custo)', {}, null, 'conservador');
    um('Cenário completo', 'otimista (produção, preço e custo)', {}, null, 'otimista');
    return out;
  }

  const API = { cenario, resumo, padroes, sens, custoSaca, desenho, uPara, NIV };
  if (typeof module !== 'undefined' && module.exports) module.exports = API; else root.ECON = API;
})(typeof window !== 'undefined' ? window : globalThis);
