/**
 * Valores dinâmicos do Canvas (spec 07 §0.3). Cada token já chega resolvido
 * como string pronta para renderização, inclusive o fallback textual, quando
 * o repositório não responde.
 */
export interface IndicadoresDaCarteira {
  /** `{{carteira.total}}`, fallback `18` */
  total: string;
  /** `{{carteira.emCouD}}`, fallback `-` */
  emCouD: string;
  /** `{{carteira.exposicaoEmRiscoEmRJ}}`, fallback `-` */
  exposicaoEmRiscoEmRJ: string;
  /** `{{carteira.comVeto}}`, fallback `-` */
  comVeto: string;
  /** `{{carteira.rjEmCurso}}`, fallback `-` */
  rjEmCurso: string;
  /** `{{data.hoje}}`, `dd/mm/aaaa` */
  hoje: string;
  /** true quando algum token caiu no fallback: alimenta o `title` de indisponibilidade. */
  degradado: boolean;
}

export const INDICADORES_FALLBACK: IndicadoresDaCarteira = {
  total: "18",
  emCouD: "-",
  exposicaoEmRiscoEmRJ: "-",
  comVeto: "-",
  rjEmCurso: "-",
  hoje: "",
  degradado: true,
};
