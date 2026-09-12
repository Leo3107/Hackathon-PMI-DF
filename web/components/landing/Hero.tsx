import { ArrowRight, Search } from 'lucide-react';
import Link from 'next/link';

import { CTA_PRIMARIO, CTA_SECUNDARIO } from './botoes';
import estilos from './landing.module.css';

/**
 * Hero centralizado, no molde da home da monday.com: headline display pesada, uma linha cinza
 * explicando o fluxo e dois CTAs pill. Nada mais: sem eyebrow, sem tagline, sem badges.
 *
 * Cabe na primeira dobra do desktop com `pt-24`; no mobile os CTAs empilham em largura total.
 *
 * Tamanhos de texto e altura dos CTAs em px, não em `rem`: o `html` do app usa base densa de
 * 13px (§4.2), e em `rem` a headline "7xl" sairia com 58px. A landing é a única tela que precisa
 * da escala grande da referência.
 */
export function Hero() {
  return (
    <section className="mx-auto w-full max-w-[1024px] px-4 pb-14 pt-14 text-center sm:px-6 sm:pt-20 lg:pb-20 lg:pt-24">
      {/* 72px só a partir de `xl`: em 1024px de largura ele forçaria a terceira linha. */}
      <h1
        className={`${estilos.entrada} text-balance font-display text-[36px] font-bold leading-[1.05] tracking-tight text-fg-primary sm:text-[48px] lg:text-[60px] xl:text-[72px]`}
      >
        Crédito rural com risco medido antes da assinatura.
      </h1>

      <p
        className={`${estilos.entrada} mx-auto mt-6 max-w-[640px] text-pretty text-[18px] leading-[1.5] text-fg-secondary sm:text-[20px]`}
        style={{ animationDelay: '90ms' }}
      >
        Consulte um CPF ou CNPJ, receba score, PD e risco de recuperação judicial e acompanhe a
        carteira em um só lugar.
      </p>

      <div
        className={`${estilos.entrada} mt-10 flex flex-col items-stretch gap-3 sm:flex-row sm:justify-center`}
        style={{ animationDelay: '180ms' }}
      >
        <Link href="/clientes" className={`${CTA_PRIMARIO} h-[56px] px-8 text-[16px] sm:min-w-[176px]`}>
          Entrar
          <ArrowRight className="size-[20px]" strokeWidth={2} aria-hidden="true" />
        </Link>
        <Link href="/nova-analise" className={`${CTA_SECUNDARIO} h-[56px] px-8 text-[16px]`}>
          <Search className="size-[20px]" strokeWidth={2} aria-hidden="true" />
          Nova análise
        </Link>
      </div>
    </section>
  );
}
