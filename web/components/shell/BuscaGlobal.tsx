'use client';

/**
 * Busca global da topbar (`03-ux-e-telas.md` §1.3, slot 2).
 *
 * Atalhos `/` e `Ctrl/Cmd+K`. Busca por razão social, nome fantasia, documento e município,
 * sobre a lista já carregada — filtrar 18 clientes no cliente é instantâneo e não gasta uma
 * viagem ao motor por tecla digitada.
 *
 * Sem resultado, a mensagem nomeia o termo buscado e, quando o texto tem forma de CPF/CNPJ,
 * oferece a saída útil: analisar o documento em Nova análise (fluxo A).
 *
 * Abaixo de `md` não há 280px sobrando na topbar: o campo vira um ícone de lupa que, tocado,
 * expande a busca sobre a barra inteira (mesma altura de 48px), com os resultados logo
 * abaixo. É a mesma lista, o mesmo filtro e o mesmo estado de termo; só a moldura muda.
 */

import { Search, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useId, useMemo, useState } from 'react';

import { IconButton, RatingBadge, SearchInput } from '@/components/ui';
import { formatarDocumento } from '@/lib/format';
import type { ClienteAvaliado } from '@/types';

import { Popover } from './Popover';
import { useClientes } from './usar-clientes';

const LIMITE = 8;

function pareceDocumento(texto: string): boolean {
  const digitos = texto.replace(/\D/g, '');
  return digitos.length === 11 || digitos.length === 14;
}

function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase();
}

export function BuscaGlobal() {
  const router = useRouter();
  const [termo, setTermo] = useState('');
  // Busca expandida sobre a topbar, só abaixo de `md`.
  const [expandida, setExpandida] = useState(false);
  const idMovel = useId();
  // Cache compartilhado do shell: a busca não dispara uma viagem própria ao motor.
  const lista = useClientes();

  const resultados = useMemo(() => {
    const alvo = normalizar(termo.trim());
    if (alvo.length < 2) return [];
    const digitos = termo.replace(/\D/g, '');
    return lista
      .filter(({ cliente }) => {
        const campos = [
          cliente.razaoSocial,
          cliente.nomeFantasia ?? '',
          cliente.municipio,
          cliente.uf,
        ].map(normalizar);
        const docLimpo = cliente.documento.replace(/\D/g, '');
        return (
          campos.some((c) => c.includes(alvo)) ||
          (digitos.length >= 3 && docLimpo.includes(digitos))
        );
      })
      .slice(0, LIMITE);
  }, [termo, lista]);

  function fecharExpandida() {
    setExpandida(false);
    setTermo('');
  }

  function abrir(id: string) {
    setTermo('');
    setExpandida(false);
    router.push(`/clientes/${id}`);
  }

  function analisarDocumento() {
    setExpandida(false);
    router.push(`/nova-analise?documento=${encodeURIComponent(termo)}`);
  }

  const conteudo = (
    <Resultados
      termo={termo}
      resultados={resultados}
      aoAbrir={abrir}
      aoAnalisarDocumento={analisarDocumento}
    />
  );

  return (
    <>
      {/* `md`+: campo inline com popover de resultados, como sempre. */}
      <Popover
        rotulo="Busca global"
        largura={360}
        className="hidden w-70 shrink-0 md:block"
        gatilho={({ alternar, id, controla, aberto }) => (
          <div id={id} aria-controls={controla} aria-expanded={aberto}>
            <SearchInput
              valor={termo}
              aoMudar={(v) => {
                setTermo(v);
                if (!aberto && v) alternar();
              }}
              atalho="/"
              tamanho="sm"
              aria-label="Buscar cliente, documento ou município"
              placeholder="Buscar cliente, CNPJ ou município"
            />
          </div>
        )}
      >
        {conteudo}
      </Popover>

      {/* Abaixo de `md`: ícone que expande a busca sobre a barra inteira. */}
      <button
        type="button"
        aria-label="Abrir busca"
        aria-expanded={expandida}
        aria-controls={idMovel}
        onClick={() => setExpandida(true)}
        className="transicao-controle inline-flex size-[var(--height-control-sm)] shrink-0 items-center justify-center rounded-full border border-transparent text-fg-secondary hover:bg-surface-hover hover:text-fg-primary md:hidden"
      >
        <Search size={16} strokeWidth={2} aria-hidden="true" />
      </button>

      {expandida && (
        <div
          id={idMovel}
          role="search"
          className="absolute inset-0 z-20 flex items-center gap-2 bg-surface-card px-3 md:hidden"
          onKeyDown={(evento) => {
            if (evento.key !== 'Escape') return;
            evento.stopPropagation();
            fecharExpandida();
          }}
        >
          <SearchInput
            autoFocus
            valor={termo}
            aoMudar={setTermo}
            tamanho="sm"
            className="min-w-0 flex-1"
            aria-label="Buscar cliente, documento ou município"
            placeholder="Buscar cliente, CNPJ ou município"
          />
          <IconButton icone={X} rotulo="Fechar busca" tamanho="sm" onClick={fecharExpandida} />
          <div
            role="dialog"
            aria-label="Busca global"
            className="absolute inset-x-3 top-full z-50 mt-1.5 max-h-[70dvh] overflow-y-auto rounded-md border border-line-strong bg-surface-raised p-3 shadow-[var(--shadow-overlay)]"
          >
            {conteudo}
          </div>
        </div>
      )}
    </>
  );
}

/** Corpo do painel de resultados, compartilhado pelo popover e pela busca expandida. */
function Resultados({
  termo,
  resultados,
  aoAbrir,
  aoAnalisarDocumento,
}: {
  termo: string;
  resultados: ClienteAvaliado[];
  aoAbrir: (id: string) => void;
  aoAnalisarDocumento: () => void;
}) {
  const grupos = {
    Clientes: resultados.filter((r) => r.cliente.origem === 'CARTEIRA'),
    Prospects: resultados.filter((r) => r.cliente.origem === 'PROSPECT'),
  };

  if (termo.trim().length < 2) {
    return (
      <p className="type-caption text-fg-tertiary">
        Digite ao menos dois caracteres. Busca por razão social, documento ou município.
      </p>
    );
  }

  if (resultados.length === 0) {
    return (
      <div>
        <p className="type-body text-fg-secondary">
          Nenhum cliente ou prospect corresponde a «{termo}».
        </p>
        {pareceDocumento(termo) && (
          <button
            type="button"
            onClick={aoAnalisarDocumento}
            className="type-label mt-2 text-accent-400 hover:text-accent-300"
          >
            Analisar este documento em Nova análise →
          </button>
        )}
      </div>
    );
  }

  return Object.entries(grupos).map(([grupo, itens]) =>
    itens.length === 0 ? null : (
      <div key={grupo} className="mb-2 last:mb-0">
        <p className="type-eyebrow mb-1 text-fg-tertiary">{grupo}</p>
        <ul>
          {itens.map(({ cliente, avaliacao }) => (
            <li key={cliente.id}>
              <button
                type="button"
                onClick={() => aoAbrir(cliente.id)}
                className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-surface-hover"
              >
                <span className="min-w-0 flex-1">
                  <span className="type-body block truncate text-fg-primary">
                    {cliente.razaoSocial}
                  </span>
                  <span className="type-caption block truncate text-fg-tertiary">
                    {formatarDocumento(cliente.documento)} · {cliente.municipio}/{cliente.uf}
                  </span>
                </span>
                <RatingBadge rating={avaliacao.ratingFinal} tamanho="sm" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    ),
  );
}
