/**
 * Concatenador de classes do design system.
 *
 * A spec §6 pede `clsx`; ele não é dependência direta do projeto (só chega
 * transitivamente por `recharts`) e o `package.json` pertence a outro agente,
 * então a mesma semântica vive aqui em nove linhas. O `className` recebido por
 * prop é sempre o último argumento — fundido **depois** das classes internas.
 */
export type ValorClasse = string | number | null | undefined | false | ValorClasse[];

export function cn(...valores: ValorClasse[]): string {
  const saida: string[] = [];
  for (const valor of valores) {
    if (!valor && valor !== 0) continue;
    if (Array.isArray(valor)) {
      const aninhado = cn(...valor);
      if (aninhado) saida.push(aninhado);
    } else {
      saida.push(String(valor));
    }
  }
  return saida.join(' ');
}
