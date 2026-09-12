'use client';

/**
 * Cabeçalho, banda de veto e painel de Stay Period (`03-ux-e-telas.md` §4.3, §4.4 e §4.9).
 *
 * As duas faixas de largura total vêm **imediatamente abaixo do cabeçalho**, antes de qualquer
 * outro bloco, porque mudam o que a Krill Tech pode legalmente fazer hoje: o veto muda a
 * classificação e o Stay Period suspende execuções. Informação que altera a ação do analista
 * não pode depender de rolagem.
 */

import { FileText, Gavel, Hourglass, Lock, LockOpen, X } from 'lucide-react';
import { useRouter } from 'next/navigation';

import {
  Badge,
  Button,
  Card,
  CLASSES_RISCO,
  ProgressBar,
  Termo,
  Tooltip,
} from '@/components/ui';
import { formatarData, formatarDataHora, formatarDias, formatarDocumento, formatarLista } from '@/lib/format';
import type { Cliente, EstadoCliente, StayPeriod, VetoAtivo } from '@/types';

const ROTULO_ESTADO: Record<EstadoCliente, string> = {
  ATIVO: 'Ativo',
  EM_OBSERVACAO: 'Em observação',
  SUSPENSO: 'Suspenso',
  RJ_EM_CURSO: 'RJ em curso',
  FALENCIA: 'Falência',
};

const FAMILIA_ESTADO: Record<EstadoCliente, 'a' | 'b' | 'c' | 'd' | 'neutral'> = {
  ATIVO: 'a',
  EM_OBSERVACAO: 'b',
  SUSPENSO: 'c',
  RJ_EM_CURSO: 'd',
  FALENCIA: 'd',
};

export interface CabecalhoDoClienteProps {
  cliente: Cliente;
  /** ISO datetime da última varredura — a data de referência da avaliação, quando houver. */
  ultimaVarredura?: string | null;
  /** Desabilitado quando o fechamento de soma não bate (§4.6). */
  parecerBloqueado?: boolean;
}

export function CabecalhoDoCliente({
  cliente,
  ultimaVarredura,
  parecerBloqueado = false,
}: CabecalhoDoClienteProps) {
  const router = useRouter();
  const prospect = cliente.origem === 'PROSPECT';

  return (
    <header className="flex flex-col gap-2 border-b border-line-subtle pb-4">
      {/* Em tela estreita as ações descem para a linha de baixo e ocupam a largura toda. */}
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
        <h1 className="type-page-title min-w-0 break-words text-fg-primary">
          {cliente.razaoSocial}
        </h1>
        <div className="flex w-full min-w-0 flex-wrap items-center gap-2 sm:w-auto sm:shrink-0">
          <Button
            variante="primario"
            iconeEsquerda={FileText}
            className="w-full sm:w-auto"
            disabled={parecerBloqueado}
            title={
              parecerBloqueado
                ? 'Parecer bloqueado: o fechamento de soma da avaliação não confere.'
                : undefined
            }
            onClick={() => router.push(`/clientes/${cliente.id}/parecer`)}
          >
            Gerar parecer
          </Button>
        </div>
      </div>

      <p className="type-body flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-fg-secondary">
        <span className="type-mono break-all text-fg-primary">
          {formatarDocumento(cliente.documento, { mascarar: cliente.tipoPessoa === 'PF' })}
        </span>
        <Separador />
        <span>
          {cliente.municipio}/{cliente.uf}
        </span>
        <Separador />
        <span>{formatarLista(cliente.culturas)}</span>
        <Separador />
        <Tooltip conteudo={`${cliente.atividade} · CNAE ${cliente.cnaePrincipal}`}>
          <span tabIndex={0} className="rounded-sm">
            <Badge variante="neutro" tamanho="sm" icone={null}>
              {cliente.tipoPessoa}
            </Badge>
          </span>
        </Tooltip>
      </p>

      <p className="type-caption flex flex-wrap items-center gap-x-2 gap-y-1">
        {prospect ? (
          <>
            <Badge variante="severidade" severidade="MEDIA" tamanho="sm">
              PROSPECT — sem relacionamento comercial
            </Badge>
            {ultimaVarredura ? (
              <span>Consulta realizada em {formatarDataHora(ultimaVarredura)}</span>
            ) : null}
          </>
        ) : (
          <>
            <span>Cliente desde {formatarData(cliente.inicioRelacionamento, 'mes')}</span>
            <Separador />
            <span
              className={`type-body-strong ${CLASSES_RISCO[FAMILIA_ESTADO[cliente.estado]].texto}`}
              data-estado={cliente.estado}
            >
              {ROTULO_ESTADO[cliente.estado]}
            </span>
            {ultimaVarredura ? (
              <>
                <Separador />
                <span>Última varredura: {formatarDataHora(ultimaVarredura)}</span>
              </>
            ) : null}
          </>
        )}
      </p>
    </header>
  );
}

function Separador() {
  return (
    <span aria-hidden="true" className="text-fg-tertiary">
      ·
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Banda de veto — largura total, logo abaixo do cabeçalho             */
/* ------------------------------------------------------------------ */

export interface BandaDeVetoProps {
  vetos: VetoAtivo[];
  scoreCalculado: string;
  ratingCalculado: string;
  ratingFinal: string;
  aoVerEvidencia: (evidenciaId: string) => void;
}

/** Efeito declarado em texto — nunca só pela cor da borda (I8). */
const ROTULO_EFEITO: Record<VetoAtivo['efeito'], string> = {
  FORCA_D: 'força a classificação final para D',
  TETO_C: 'limita a classificação final a C',
};

export function BandaDeVeto({
  vetos,
  scoreCalculado,
  ratingCalculado,
  ratingFinal,
  aoVerEvidencia,
}: BandaDeVetoProps) {
  if (vetos.length === 0) return null;

  return (
    <Card destaque="d" className="flex flex-col gap-3" as="section" aria-labelledby="titulo-veto">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2
          id="titulo-veto"
          className="type-section-title inline-flex items-center gap-2 text-risk-d"
        >
          <Gavel size={16} strokeWidth={2} aria-hidden="true" />
          {vetos.length === 1 ? 'Veto ativo' : `${vetos.length} vetos ativos`}
        </h2>
        <p className="type-body min-w-0 text-fg-secondary">
          O motor calculou <strong className="text-fg-primary">{scoreCalculado}</strong> (rating{' '}
          {ratingCalculado}); a classificação final é{' '}
          <strong className="text-fg-primary">{ratingFinal}</strong> por regra de negócio. O score
          calculado continua exibido — o veto não o apaga.
        </p>
      </div>

      <ul className="flex flex-col gap-2">
        {vetos.map((veto) => (
          <li
            key={veto.id}
            className="flex flex-col gap-1 rounded border border-risk-d-line bg-risk-d-tint px-3 py-2"
          >
            <p className="type-body-strong text-fg-primary">{veto.rotulo}</p>
            <p className="type-body text-fg-secondary">{veto.justificativa}</p>
            <p className="type-caption flex flex-wrap items-center gap-2">
              <span>Efeito: {ROTULO_EFEITO[veto.efeito]}.</span>
              {veto.evidenciaIds.length > 0 ? (
                <Button
                  variante="fantasma"
                  tamanho="sm"
                  onClick={() => aoVerEvidencia(veto.evidenciaIds[0])}
                >
                  Ver evidência
                </Button>
              ) : null}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Stay Period                                                         */
/* ------------------------------------------------------------------ */

export interface PainelStayPeriodProps {
  stayPeriod: StayPeriod;
}

/** Janela legal do art. 6º da Lei 11.101/2005, prorrogável uma vez. */
const DIAS_STAY = 180;

export function PainelStayPeriod({ stayPeriod }: PainelStayPeriodProps) {
  if (!stayPeriod.ativo) return null;
  const total = stayPeriod.diasDecorridos + stayPeriod.diasRestantes || DIAS_STAY;

  return (
    <Card
      id="stay-period"
      destaque="d"
      as="section"
      aria-labelledby="titulo-stay"
      className="scroll-mt-[88px] flex flex-col gap-3"
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2
          id="titulo-stay"
          className="type-section-title inline-flex items-center gap-2 text-risk-d"
        >
          <Hourglass size={16} strokeWidth={2} aria-hidden="true" />
          <Termo sigla="STAY_PERIOD">Stay Period</Termo> ativo
        </h2>
        <p className="type-body min-w-0 text-fg-secondary">
          <Termo sigla="RJ" /> deferida em {formatarData(stayPeriod.dataDeferimento)} · decorridos{' '}
          <span className="tnum text-fg-primary">{stayPeriod.diasDecorridos}</span> de{' '}
          <span className="tnum text-fg-primary">{total}</span> dias
        </p>
      </div>

      <ProgressBar
        valor={stayPeriod.diasDecorridos}
        maximo={total}
        familia="d"
        rotulo="Decorrido do Stay Period"
        valorFormatado={`${formatarDias(stayPeriod.diasRestantes)} restantes`}
        altura={8}
      />
      <p className="type-caption">
        Prorrogável uma única vez, por igual período (art. 6º, § 4º, Lei 11.101/2005). Contagem
        calculada pelo motor a partir da data de deferimento — não é um cronômetro da interface.
      </p>

      <div className="grid gap-3 md:grid-cols-2">
        <ListaJuridica
          titulo="A Krill Tech NÃO pode"
          itens={stayPeriod.bloqueios}
          Icone={X}
          familia="d"
          vazio="O motor não declarou bloqueios para este Stay Period."
        />
        <ListaJuridica
          titulo="A Krill Tech ainda pode"
          itens={stayPeriod.permitido}
          Icone={Lock}
          familia="a"
          vazio="O motor não declarou atos permitidos para este Stay Period."
        />
      </div>

      <p className="type-caption">
        Crédito com garantia <Termo sigla="EXTRACONCURSAL" /> escapa do plano; crédito{' '}
        <Termo sigla="CONCURSAL" /> entra e é pago com deságio.{' '}
        <LockOpen size={12} className="inline align-[-2px]" aria-hidden="true" />
      </p>
    </Card>
  );
}

function ListaJuridica({
  titulo,
  itens,
  Icone,
  familia,
  vazio,
}: {
  titulo: string;
  itens: string[];
  Icone: typeof X;
  familia: 'a' | 'd';
  vazio: string;
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded border border-line-default bg-surface-sunken p-3">
      <h3 className="type-eyebrow text-fg-secondary">{titulo}</h3>
      {itens.length === 0 ? (
        <p className="type-caption">{vazio}</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {itens.map((item) => (
            <li key={item} className="type-body flex items-start gap-2 text-fg-secondary">
              <Icone
                size={14}
                strokeWidth={2.5}
                className={`mt-0.5 shrink-0 ${CLASSES_RISCO[familia].texto}`}
                aria-hidden="true"
              />
              <span>
                <span className="sr-only">
                  {familia === 'd' ? 'Vedado: ' : 'Permitido: '}
                </span>
                {item}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
