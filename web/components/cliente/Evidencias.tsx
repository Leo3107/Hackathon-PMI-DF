'use client';

/**
 * Fontes e evidências, e os dois drawers de detalhe (`03-ux-e-telas.md` §4.11 e §4.5).
 *
 * O laço **evidência ↔ fator** funciona nos dois sentidos e é o que responde "onde está a
 * prova?": do fator se chega às evidências que o sustentam, e da evidência se chega aos fatores
 * que ela move. Sem esse laço, o produto volta a ser uma nota sem lastro.
 */

import { Link2, Link as LinkIcon } from 'lucide-react';
import { useMemo, useState } from 'react';

import {
  Badge,
  Button,
  CLASSES_RISCO,
  Card,
  Drawer,
  EmptyState,
  EvidenceCard,
  FilterChips,
  ICONE_EVIDENCIA,
  NOME_CURTO_FONTE,
  NOME_DIMENSAO,
  SectionHeader,
  Tooltip,
  type FatorRelacionado,
} from '@/components/ui';
import { formatarData, formatarDelta, formatarNumero, formatarPercentual } from '@/lib/format';
import type { AvaliacaoDeRisco, Evidencia, FatorCalculado, FonteId } from '@/types';

/* ------------------------------------------------------------------ */
/* Bloco 10 — fontes e evidências                                      */
/* ------------------------------------------------------------------ */

export interface BlocoEvidenciasProps {
  avaliacao: AvaliacaoDeRisco;
  indiceDeFatores: Map<string, { fator: FatorCalculado; peso: number }>;
  aoAbrirEvidencia: (evidenciaId: string) => void;
  aoSelecionarFator: (fatorId: string) => void;
}

export function BlocoEvidencias({
  avaliacao,
  indiceDeFatores,
  aoAbrirEvidencia,
  aoSelecionarFator,
}: BlocoEvidenciasProps) {
  const fontes = useMemo(() => {
    const presentes = new Set<FonteId>();
    for (const evidencia of avaliacao.evidencias) presentes.add(evidencia.fonte);
    return [...presentes].sort((a, b) =>
      NOME_CURTO_FONTE[a].localeCompare(NOME_CURTO_FONTE[b], 'pt-BR'),
    );
  }, [avaliacao.evidencias]);

  const [filtro, setFiltro] = useState<ReadonlySet<FonteId>>(new Set());

  const visiveis = useMemo(() => {
    const lista =
      filtro.size === 0
        ? avaliacao.evidencias
        : avaliacao.evidencias.filter((e) => filtro.has(e.fonte));
    return [...lista].sort((a, b) => b.dataConsulta.localeCompare(a.dataConsulta));
  }, [avaliacao.evidencias, filtro]);

  return (
    <Card
      id="evidencias"
      as="section"
      aria-labelledby="titulo-evidencias"
      className="scroll-mt-[88px]"
    >
      <SectionHeader
        nivel={2}
        titulo="Fontes e evidências"
        descricao={`${fontes.length} fontes consultadas · ${avaliacao.evidencias.length} documentos. Toda consulta desta demonstração é simulada.`}
        meta={<Link2 size={14} strokeWidth={2} aria-hidden="true" />}
      />
      <h2 id="titulo-evidencias" className="sr-only">
        Fontes e evidências
      </h2>

      {fontes.length > 0 ? (
        <div className="mt-3">
          <FilterChips<FonteId>
            rotulo="Filtrar evidências por fonte"
            limparRotulo="Todas as fontes"
            selecionados={filtro}
            aoMudar={setFiltro}
            opcoes={fontes.map((fonte) => ({
              valor: fonte,
              rotulo: NOME_CURTO_FONTE[fonte],
              contagem: avaliacao.evidencias.filter((e) => e.fonte === fonte).length,
            }))}
          />
        </div>
      ) : null}

      {visiveis.length === 0 ? (
        <div className="mt-3">
          <EmptyState
            compacto
            titulo="Nenhuma evidência nesta seleção"
            descricao={
              avaliacao.evidencias.length === 0
                ? 'O motor não devolveu documentos para esta avaliação.'
                : 'Nenhum documento da fonte selecionada. Limpe o filtro para ver todos.'
            }
          />
        </div>
      ) : (
        <ul className="mt-3 flex flex-col gap-2">
          {visiveis.map((evidencia) => (
            <li key={evidencia.id}>
              <EvidenceCard
                evidencia={paraEvidenciaUi(evidencia)}
                fatoresRelacionados={fatoresDe(evidencia, indiceDeFatores)}
                aoClicarFator={aoSelecionarFator}
                aoAlternar={() => aoAbrirEvidencia(evidencia.id)}
              />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/**
 * `types/dominio.Evidencia` usa `null` onde o tipo estrutural do design system usa `undefined`
 * (campo ausente). A conversão é aqui, uma vez, em vez de espalhar `?? undefined` por cada uso.
 */
function paraEvidenciaUi(evidencia: Evidencia) {
  return {
    ...evidencia,
    dataDocumento: evidencia.dataDocumento ?? undefined,
    urlFicticia: evidencia.urlFicticia ?? undefined,
  };
}

function fatoresDe(
  evidencia: Evidencia,
  indice: Map<string, { fator: FatorCalculado; peso: number }>,
): FatorRelacionado[] {
  return evidencia.fatoresRelacionados
    .map((id) => indice.get(id))
    .filter((entrada): entrada is { fator: FatorCalculado; peso: number } => Boolean(entrada))
    .map(({ fator }) => ({
      id: fator.id,
      rotulo: fator.rotulo,
      impacto: fator.impactoGlobalAjustado,
    }));
}

/* ------------------------------------------------------------------ */
/* Drawer de evidência                                                 */
/* ------------------------------------------------------------------ */

export interface DrawerDeEvidenciaProps {
  evidencia: Evidencia | null;
  indiceDeFatores: Map<string, { fator: FatorCalculado; peso: number }>;
  aoFechar: () => void;
  aoSelecionarFator: (fatorId: string) => void;
}

export function DrawerDeEvidencia({
  evidencia,
  indiceDeFatores,
  aoFechar,
  aoSelecionarFator,
}: DrawerDeEvidenciaProps) {
  const Icone = evidencia ? ICONE_EVIDENCIA[evidencia.tipo] : null;

  return (
    <Drawer
      aberto={evidencia !== null}
      aoFechar={aoFechar}
      titulo={evidencia?.titulo ?? 'Evidência'}
      subtitulo={evidencia ? NOME_CURTO_FONTE[evidencia.fonte] : undefined}
      cabecalhoExtra={<Badge variante="simulado" tamanho="sm" />}
    >
      {evidencia ? (
        <div className="flex flex-col gap-4">
          <dl className="grid grid-cols-2 gap-3">
            <Linha rotulo="Fonte" valor={evidencia.nomeFonte} />
            <Linha
              rotulo="Tipo"
              valor={
                <span className="inline-flex items-center gap-1.5">
                  {Icone ? <Icone size={13} strokeWidth={2} aria-hidden="true" /> : null}
                  {evidencia.tipo}
                </span>
              }
            />
            <Linha
              rotulo="Data do documento"
              valor={evidencia.dataDocumento ? formatarData(evidencia.dataDocumento) : '—'}
            />
            <Linha rotulo="Data da consulta" valor={formatarData(evidencia.dataConsulta)} />
          </dl>

          <section className="flex flex-col gap-1">
            <h3 className="type-eyebrow text-fg-secondary">Resumo</h3>
            <p className="type-body text-fg-secondary">{evidencia.resumo}</p>
          </section>

          {evidencia.urlFicticia ? (
            <Tooltip conteudo="Endereço ilustrativo — nenhuma consulta real foi realizada.">
              <p
                tabIndex={0}
                className="type-mono flex cursor-not-allowed items-center gap-1.5 rounded border border-line-default bg-surface-sunken px-2 py-1.5 text-fg-disabled"
              >
                <LinkIcon size={12} strokeWidth={2} aria-hidden="true" />
                {evidencia.urlFicticia}
              </p>
            </Tooltip>
          ) : null}

          <section className="flex flex-col gap-2 border-t border-line-subtle pt-3">
            <h3 className="type-eyebrow text-fg-secondary">Sustenta os fatores</h3>
            {evidencia.fatoresRelacionados.length === 0 ? (
              <p className="type-caption">
                Esta evidência documenta o cadastro, mas não sustenta nenhum fator pontuado.
              </p>
            ) : (
              <ul className="flex flex-col gap-1">
                {evidencia.fatoresRelacionados.map((fatorId) => {
                  const entrada = indiceDeFatores.get(fatorId);
                  return (
                    <li key={fatorId}>
                      <button
                        type="button"
                        onClick={() => {
                          aoSelecionarFator(fatorId);
                          aoFechar();
                        }}
                        className="transicao-controle type-body flex w-full items-baseline justify-between gap-3 rounded px-2 py-1 text-left text-fg-primary hover:bg-surface-hover"
                      >
                        <span className="min-w-0">{entrada?.fator.rotulo ?? fatorId}</span>
                        {entrada ? (
                          <span className="tnum shrink-0 text-fg-secondary">
                            {formatarDelta(entrada.fator.impactoGlobalAjustado, 'pts')}
                          </span>
                        ) : null}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <p className="type-caption border-t border-line-subtle pt-2">
            consulta simulada — protótipo demonstrativo, nenhuma consulta real a órgão público.
          </p>
        </div>
      ) : null}
    </Drawer>
  );
}

/* ------------------------------------------------------------------ */
/* Drawer de fator                                                     */
/* ------------------------------------------------------------------ */

export interface DrawerDeFatorProps {
  entrada: { fator: FatorCalculado; peso: number } | null;
  evidencias: Map<string, Evidencia>;
  aoFechar: () => void;
  aoAbrirEvidencia: (evidenciaId: string) => void;
}

export function DrawerDeFator({
  entrada,
  evidencias,
  aoFechar,
  aoAbrirEvidencia,
}: DrawerDeFatorProps) {
  const fator = entrada?.fator ?? null;
  const familia = fator?.direcao === 'protecao' ? 'a' : 'c';

  return (
    <Drawer
      aberto={entrada !== null}
      aoFechar={aoFechar}
      titulo={fator?.rotulo ?? 'Fator'}
      subtitulo={fator ? NOME_DIMENSAO[fator.dimensao] : undefined}
    >
      {fator && entrada ? (
        <div className="flex flex-col gap-4">
          {fator.detalhe ? (
            <p className="type-body text-fg-secondary">{fator.detalhe}</p>
          ) : null}

          <dl className="grid grid-cols-2 gap-3">
            <Linha
              rotulo="Direção"
              valor={fator.direcao === 'protecao' ? 'Proteção' : 'Risco'}
              familia={familia}
            />
            <Linha rotulo="Pontos brutos" valor={formatarNumero(fator.pontos, 1)} />
            <Linha rotulo="Peso da dimensão" valor={formatarPercentual(entrada.peso, 0)} />
            <Linha
              rotulo="Impacto no score"
              valor={formatarDelta(fator.impactoGlobal, 'pts')}
            />
            <Linha
              rotulo="Impacto após saturação"
              valor={formatarDelta(fator.impactoGlobalAjustado, 'pts')}
              familia={familia}
            />
            <Linha rotulo="Fonte" valor={NOME_CURTO_FONTE[fator.fonte]} />
          </dl>

          <p className="type-caption rounded border border-line-default bg-surface-sunken px-3 py-2">
            Impacto no score = pontos × peso da dimensão × sinal da direção. A soma dos impactos
            ajustados de todos os fatores reconstrói o score exibido — é a conferência que aparece
            ao pé da decomposição por dimensão.
          </p>

          <section className="flex flex-col gap-2 border-t border-line-subtle pt-3">
            <h3 className="type-eyebrow text-fg-secondary">Evidências que sustentam</h3>
            {fator.evidenciaIds.length === 0 ? (
              <p className="type-caption">
                Fator derivado do histórico interno da Krill Tech, sem documento externo
                associado.
              </p>
            ) : (
              <ul className="flex flex-col gap-1">
                {fator.evidenciaIds.map((id) => {
                  const evidencia = evidencias.get(id);
                  return (
                    <li key={id}>
                      <Button
                        variante="fantasma"
                        tamanho="sm"
                        larguraTotal
                        onClick={() => aoAbrirEvidencia(id)}
                      >
                        {evidencia ? `${evidencia.titulo} · ${evidencia.nomeFonte}` : id}
                      </Button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </Drawer>
  );
}

function Linha({
  rotulo,
  valor,
  familia,
}: {
  rotulo: string;
  valor: React.ReactNode;
  familia?: 'a' | 'c';
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="type-eyebrow text-fg-tertiary">{rotulo}</dt>
      <dd
        className={`type-body-strong tnum ${
          familia ? CLASSES_RISCO[familia].texto : 'text-fg-primary'
        }`}
      >
        {valor}
      </dd>
    </div>
  );
}
