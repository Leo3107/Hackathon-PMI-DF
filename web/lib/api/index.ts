/**
 * Cliente de API do Lastro.
 *
 * ```ts
 * import { listarClientes, ErroLastro } from '@/lib/api';
 * ```
 *
 * ⚠️ `./proxy` **não** é reexportado aqui de propósito: é módulo de servidor e só pode ser
 * importado por route handlers em `web/app/api/**`. Reexportá-lo arrastaria código de servidor
 * para dentro de componentes de cliente.
 */

export * from './cliente';
export * from './erros';
export * from './narrativa';
export * from './disponibilidade';
