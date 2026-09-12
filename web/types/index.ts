/**
 * Ponto único de importação dos tipos do Lastro.
 *
 * ```ts
 * import type { Cliente, AvaliacaoDeRisco } from '@/types';
 * ```
 *
 * Os tipos vêm de `specs/01-modelo-de-dados.md` e são o contrato da API (D3). Nenhum
 * componente deve declarar uma forma paralela de dado de domínio; se faltar campo, ele se
 * acrescenta aqui **e** no modelo pydantic correspondente.
 */

export * from './dominio';
export * from './avaliacao';
export * from './eventos';
export * from './api';
