import Image from 'next/image';

import estilos from './landing.module.css';

/**
 * Faixa levemente tingida com o screenshot real da carteira, logo abaixo do hero.
 *
 * A captura é @2x (2880x1800), medida no arquivo. `h-auto` deixa a altura seguir a proporção
 * real, então uma recaptura em outra proporção não distorce. Com `src` string o Next não valida
 * o arquivo no build, por isso não há fallback: se a imagem faltar, o `alt` fala por ela.
 */
export function FaixaDoProduto() {
  return (
    <section className="flex-1 bg-surface-page px-4 py-12 sm:px-6 sm:py-16 lg:py-20" aria-label="O produto">
      <div className="mx-auto w-full max-w-[1152px]">
        <Image
          src="/landing/carteira.png"
          alt="Carteira de clientes do Lastro com scores e alertas"
          width={2880}
          height={1800}
          priority
          sizes="(min-width: 1200px) 1152px, calc(100vw - 32px)"
          className={`${estilos.entradaImagem} h-auto w-full rounded-lg border border-line-default bg-surface-card shadow-overlay`}
          style={{ animationDelay: '260ms' }}
        />
      </div>
    </section>
  );
}
