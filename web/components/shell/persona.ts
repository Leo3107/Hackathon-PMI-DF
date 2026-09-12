/**
 * Persona fixa de demonstração (`03-ux-e-telas.md` §1.3 · D11.1).
 *
 * O Lastro não tem autenticação: um gate de login atrasa o jurado sem agregar nada. A
 * identidade fica fixa na topbar e é o valor gravado em `RegistroAuditoria.analista`, para que
 * a trilha de auditoria tenha autor.
 */

export const PERSONA = {
  nome: 'Marina Rezende',
  iniciais: 'MR',
  cargo: 'Analista de Crédito Sênior',
  empresa: 'Krill Tech',
  /** String literal gravada na trilha de auditoria. */
  assinatura: 'Marina Rezende · Analista de Crédito Sênior · Krill Tech',
  aviso:
    'Perfil de demonstração. O Lastro não tem autenticação nesta versão (ver 00-decisoes.md D11.1).',
} as const;
