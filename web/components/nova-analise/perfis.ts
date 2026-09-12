/**
 * Perfis demonstrativos clicáveis (`03-ux-e-telas.md` §6.7).
 *
 * Existem para que o jurado não precise digitar 14 dígitos durante o pitch. A spec manda
 * alimentá-los com `Cliente.origem === 'PROSPECT'`; como nenhuma rota do motor **lista**
 * prospects (só `POST /api/due-diligence` os encontra por documento), a seleção é feita sobre
 * o que `GET /api/clientes` devolve e degrada de forma previsível:
 *
 * 1. havendo prospects na lista, são eles;
 * 2. não havendo, usa clientes da carteira como demonstração — e o card **diz** que são da
 *    carteira, porque a consulta cai no estado "documento já pertence a um cliente" (§6.2).
 *
 * Nenhum documento é escrito à mão aqui: um CNPJ inventado reprovaria no dígito verificador do
 * próprio motor. Todos vêm do dataset.
 */

import type { ClienteAvaliado, Rating } from '@/types';

export type PerfilDeCredito = 'aprovavel' | 'limitrofe' | 'recusavel';

export const ROTULO_PERFIL: Record<PerfilDeCredito, string> = {
  aprovavel: 'aprovável',
  limitrofe: 'limítrofe',
  recusavel: 'recusável',
};

export interface PerfilDemonstrativo {
  linha: ClienteAvaliado;
  perfil: PerfilDeCredito;
  /** `true` quando o documento pertence à carteira — a consulta cai em §6.2, não no pipeline. */
  naCarteira: boolean;
}

/** Faixa de crédito a partir do rating **final** do motor. A tela não reclassifica nada. */
export function perfilDoRating(rating: Rating): PerfilDeCredito {
  if (rating === 'A' || rating === 'B') return 'aprovavel';
  if (rating === 'C') return 'limitrofe';
  return 'recusavel';
}

const ORDEM: PerfilDeCredito[] = ['aprovavel', 'limitrofe', 'recusavel'];

/**
 * Um representante por faixa, na ordem aprovável → limítrofe → recusável. Quando falta alguma
 * faixa, completa com os demais candidatos por score decrescente, para o painel nunca ficar
 * com um card só.
 */
export function perfisDemonstrativos(
  linhas: ClienteAvaliado[],
  limite = 3,
): PerfilDemonstrativo[] {
  if (!Array.isArray(linhas) || linhas.length === 0) return [];

  const prospects = linhas.filter((linha) => linha.cliente.origem === 'PROSPECT');
  const naCarteira = prospects.length === 0;
  const candidatos = [...(naCarteira ? linhas : prospects)].sort(
    (a, b) => b.avaliacao.scoreCalculado - a.avaliacao.scoreCalculado,
  );

  const escolhidos: PerfilDemonstrativo[] = [];
  const usados = new Set<string>();

  for (const perfil of ORDEM) {
    const achado = candidatos.find(
      (linha) =>
        !usados.has(linha.cliente.id) && perfilDoRating(linha.avaliacao.ratingFinal) === perfil,
    );
    if (achado) {
      usados.add(achado.cliente.id);
      escolhidos.push({ linha: achado, perfil, naCarteira });
    }
  }

  for (const linha of candidatos) {
    if (escolhidos.length >= limite) break;
    if (usados.has(linha.cliente.id)) continue;
    usados.add(linha.cliente.id);
    escolhidos.push({
      linha,
      perfil: perfilDoRating(linha.avaliacao.ratingFinal),
      naCarteira,
    });
  }

  return escolhidos
    .sort((a, b) => ORDEM.indexOf(a.perfil) - ORDEM.indexOf(b.perfil))
    .slice(0, limite);
}
