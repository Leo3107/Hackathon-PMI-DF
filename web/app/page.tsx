import type { Metadata } from 'next';

import { FaixaDoProduto, Hero, Nav, Rodape } from '@/components/landing';

/**
 * Landing pública do Lastro em `/`.
 *
 * Renderiza sem o shell da aplicação (`rotaSemShell` em `components/shell/rotas.ts`), então
 * esta é a página inteira: nav, hero, screenshot do produto e rodapé de uma linha. Nada de
 * features, depoimentos ou pricing, por decisão do dono do produto.
 *
 * `title.absolute` ignora o template `%s · Lastro` do layout; a aba mostra só "Lastro".
 */
export const metadata: Metadata = {
  title: { absolute: 'Lastro' },
};

export default function PaginaInicial() {
  return (
    <div className="flex min-h-[100dvh] flex-col bg-surface-card text-fg-primary">
      <Nav />
      {/* `flex-1` aqui e na faixa: em viewport alto o fundo tingido cresce até o rodapé, sem sobra branca. */}
      <main id="conteudo" className="flex flex-1 flex-col">
        <Hero />
        <FaixaDoProduto />
      </main>
      <Rodape />
    </div>
  );
}
