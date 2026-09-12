import { CLASSES_RISCO } from './risco';
import type { FamiliaRisco } from './tipos-ui';

/** Id determinístico do padrão hachurado por família. */
export function idHachura(familia: FamiliaRisco, escopo = 'lastro'): string {
  return `${escopo}-hatch-${familia}`;
}

export interface PadraoHachuraProps {
  familia: FamiliaRisco;
  escopo?: string;
}

/**
 * Padrão hachurado do modo veto (spec §7.7) e do segmento "em risco" da
 * `StackedBar` (§6.16). Deve ser renderizado dentro de um `<defs>`.
 *
 * Leitura: "este era o valor calculado, mas está sobrestado".
 */
export function PadraoHachura({ familia, escopo }: PadraoHachuraProps) {
  const classes = CLASSES_RISCO[familia];
  return (
    <pattern
      id={idHachura(familia, escopo)}
      patternUnits="userSpaceOnUse"
      width="6"
      height="6"
      patternTransform="rotate(45)"
    >
      <rect width="6" height="6" fill={classes.varTint} />
      <rect width="2.5" height="6" fill={classes.varCor} />
    </pattern>
  );
}
