/**
 * Validação e máscara de CPF/CNPJ (`03-ux-e-telas.md` §6.2).
 *
 * A conferência do dígito verificador é a **única** operação de cálculo permitida no frontend:
 * é validação de formulário, não de risco. Nenhum número de risco nasce aqui — score, PD,
 * rating e recomendação continuam vindo exclusivamente do motor (D4, I7).
 *
 * A spec aponta este módulo para `lib/validacao/documento.ts`. Ele vive aqui porque `web/lib/`
 * é território de outro agente nesta rodada; o conteúdo é o mesmo e não tem dependência de
 * React, então mover o arquivo depois é um `git mv` sem alteração de código.
 *
 * O algoritmo é o mesmo de `api/routes/due_diligence.py` — os dois lados precisam concordar,
 * ou a interface habilitaria o botão para um documento que o motor recusa com `CORPO_INVALIDO`.
 */

export type TipoDocumento = 'CPF' | 'CNPJ';

export const TAMANHO_CPF = 11;
export const TAMANHO_CNPJ = 14;

export type EstadoDocumento =
  | { situacao: 'vazio' }
  | { situacao: 'incompleto'; digitos: string }
  | { situacao: 'invalido'; digitos: string; tipo: TipoDocumento }
  | { situacao: 'valido'; digitos: string; tipo: TipoDocumento; formatado: string };

export function somenteDigitos(texto: string): string {
  return (texto ?? '').replace(/\D/g, '');
}

function juntar(partes: string[], separadores: string[]): string {
  const presentes = partes.filter((parte) => parte.length > 0);
  return presentes.reduce(
    (acumulado, parte, indice) =>
      indice === 0 ? parte : `${acumulado}${separadores[indice - 1]}${parte}`,
    '',
  );
}

/**
 * Máscara progressiva: CPF até 11 dígitos, CNPJ a partir do 12º (§6.2). Aceita texto já
 * pontuado — só os dígitos importam.
 */
export function mascararDocumento(texto: string): string {
  const digitos = somenteDigitos(texto).slice(0, TAMANHO_CNPJ);
  if (digitos.length <= TAMANHO_CPF) {
    return juntar(
      [digitos.slice(0, 3), digitos.slice(3, 6), digitos.slice(6, 9), digitos.slice(9, 11)],
      ['.', '.', '-'],
    );
  }
  return juntar(
    [
      digitos.slice(0, 2),
      digitos.slice(2, 5),
      digitos.slice(5, 8),
      digitos.slice(8, 12),
      digitos.slice(12, 14),
    ],
    ['.', '.', '/', '-'],
  );
}

function digitoVerificador(digitos: number[], pesos: number[]): number {
  const resto = digitos.reduce((soma, digito, i) => soma + digito * pesos[i], 0) % 11;
  return resto < 2 ? 0 : 11 - resto;
}

function comoNumeros(documento: string): number[] {
  return documento.split('').map((caractere) => Number(caractere));
}

/** Rejeita sequências repetidas (`111.111.111-11`), que passam na conta mas não existem. */
function repetido(digitos: number[]): boolean {
  return new Set(digitos).size === 1;
}

export function cpfValido(entrada: string): boolean {
  const digitos = comoNumeros(somenteDigitos(entrada));
  if (digitos.length !== TAMANHO_CPF || repetido(digitos)) return false;
  const primeiro = digitoVerificador(digitos.slice(0, 9), [10, 9, 8, 7, 6, 5, 4, 3, 2]);
  const segundo = digitoVerificador(digitos.slice(0, 10), [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]);
  return digitos[9] === primeiro && digitos[10] === segundo;
}

export function cnpjValido(entrada: string): boolean {
  const digitos = comoNumeros(somenteDigitos(entrada));
  if (digitos.length !== TAMANHO_CNPJ || repetido(digitos)) return false;
  const pesosPrimeiro = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const pesosSegundo = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const primeiro = digitoVerificador(digitos.slice(0, 12), pesosPrimeiro);
  const segundo = digitoVerificador(digitos.slice(0, 13), pesosSegundo);
  return digitos[12] === primeiro && digitos[13] === segundo;
}

export function documentoValido(entrada: string): boolean {
  const digitos = somenteDigitos(entrada);
  if (digitos.length === TAMANHO_CPF) return cpfValido(digitos);
  if (digitos.length === TAMANHO_CNPJ) return cnpjValido(digitos);
  return false;
}

/** Estado do campo, na ordem exata da tabela de §6.2. */
export function analisarDocumento(texto: string): EstadoDocumento {
  const digitos = somenteDigitos(texto);
  if (digitos.length === 0) return { situacao: 'vazio' };

  if (digitos.length !== TAMANHO_CPF && digitos.length !== TAMANHO_CNPJ) {
    return { situacao: 'incompleto', digitos };
  }

  const tipo: TipoDocumento = digitos.length === TAMANHO_CPF ? 'CPF' : 'CNPJ';
  const valido = tipo === 'CPF' ? cpfValido(digitos) : cnpjValido(digitos);
  if (!valido) return { situacao: 'invalido', digitos, tipo };
  return { situacao: 'valido', digitos, tipo, formatado: mascararDocumento(digitos) };
}

/** Microcópia do campo. Nunca só o ícone: o texto é o canal primário (R2/I8). */
export function mensagemDoDocumento(estado: EstadoDocumento): string | null {
  switch (estado.situacao) {
    case 'vazio':
      return null;
    case 'incompleto':
      return 'Continue digitando — 11 dígitos para CPF, 14 para CNPJ.';
    case 'invalido':
      return 'Dígito verificador inválido. Confira o número digitado.';
    case 'valido':
      return `${estado.tipo} válido`;
  }
}

export const PLACEHOLDER_DOCUMENTO = '000.000.000-00 ou 00.000.000/0000-00';
