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
 */

import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

import { RatingBadge, SearchInput } from '@/components/ui';
import { formatarDocumento } from '@/lib/format';

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

  const grupos = useMemo(
    () => ({
      Clientes: resultados.filter((r) => r.cliente.origem === 'CARTEIRA'),
      Prospects: resultados.filter((r) => r.cliente.origem === 'PROSPECT'),
    }),
    [resultados],
  );

  function abrir(id: string) {
    setTermo('');
    router.push(`/clientes/${id}`);
  }

  return (
    <Popover
      rotulo="Busca global"
      largura={360}
      className="w-70 shrink-0"
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
      {termo.trim().length < 2 ? (
        <p className="type-caption text-fg-tertiary">
          Digite ao menos dois caracteres. Busca por razão social, documento ou município.
        </p>
      ) : resultados.length === 0 ? (
        <div>
          <p className="type-body text-fg-secondary">
            Nenhum cliente ou prospect corresponde a «{termo}».
          </p>
          {pareceDocumento(termo) && (
            <button
              type="button"
              onClick={() => router.push(`/nova-analise?documento=${encodeURIComponent(termo)}`)}
              className="type-label mt-2 text-accent-400 hover:text-accent-300"
            >
              Analisar este documento em Nova análise →
            </button>
          )}
        </div>
      ) : (
        Object.entries(grupos).map(([grupo, itens]) =>
          itens.length === 0 ? null : (
            <div key={grupo} className="mb-2 last:mb-0">
              <p className="type-eyebrow mb-1 text-fg-tertiary">{grupo}</p>
              <ul>
                {itens.map(({ cliente, avaliacao }) => (
                  <li key={cliente.id}>
                    <button
                      type="button"
                      onClick={() => abrir(cliente.id)}
                      className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-surface-hover"
                    >
                      <span className="min-w-0 flex-1">
                        <span className="type-body block truncate text-fg-primary">
                          {cliente.razaoSocial}
                        </span>
                        <span className="type-caption block truncate text-fg-tertiary">
                          {formatarDocumento(cliente.documento)} · {cliente.municipio}/
                          {cliente.uf}
                        </span>
                      </span>
                      <RatingBadge rating={avaliacao.ratingFinal} tamanho="sm" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ),
        )
      )}
    </Popover>
  );
}
