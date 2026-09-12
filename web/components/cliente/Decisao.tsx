'use client';

/**
 * Decisão do analista (`03-ux-e-telas.md` §8.3, bloco 12 de §4.10).
 *
 * O produto recomenda; **quem decide é uma pessoa**. Este bloco é o fecho da tese: registra a
 * escolha humana, exige justificativa, e marca com destaque quando ela diverge da recomendação
 * do motor — porque a divergência é justamente o que a trilha de auditoria precisa preservar.
 */

import { CheckCircle2, PenLine, TriangleAlert } from 'lucide-react';
import { useMemo, useState } from 'react';

import { PERSONA, useSessao } from '@/components/shell';
import { Button, Card, ErrorState, SectionHeader } from '@/components/ui';
import { ErroLastro, registrarDecisao, textoDeErro } from '@/lib/api';
import { formatarDataHora } from '@/lib/format';
import { decisoesDaSessao, registrarDecisaoNaSessao } from '@/lib/sessao';
import type {
  AvaliacaoDeRisco,
  Cliente,
  CodigoRecomendacao,
  DecisaoAnalista,
  RegistroAuditoria,
} from '@/types';

import { AvisoDeDecisaoHumana } from './Lateral';

const OPCOES: Array<{ valor: DecisaoAnalista; rotulo: string }> = [
  { valor: 'APROVAR', rotulo: 'Aprovar' },
  { valor: 'APROVAR_COM_RESTRICOES', rotulo: 'Aprovar com restrições' },
  { valor: 'REVISAR', rotulo: 'Revisar' },
  { valor: 'SUSPENDER', rotulo: 'Suspender' },
  { valor: 'RECUSAR', rotulo: 'Recusar' },
];

/**
 * Decisão humana equivalente a cada código de recomendação. Serve só para **antecipar** ao
 * analista que ele está divergindo antes de clicar; a marca oficial de divergência no registro é
 * a que o servidor carimba (R6).
 */
const EQUIVALENTE: Record<CodigoRecomendacao, DecisaoAnalista> = {
  APROVAR: 'APROVAR',
  APROVAR_COM_MONITORAMENTO_INTENSIVO: 'APROVAR',
  APROVAR_COM_REVISAO_DE_LIMITE: 'APROVAR_COM_RESTRICOES',
  APROVAR_COM_RESTRICOES: 'APROVAR_COM_RESTRICOES',
  SUSPENDER_NOVA_EXPOSICAO_A_PRAZO: 'SUSPENDER',
  SUSPENDER_EXPOSICAO: 'SUSPENDER',
};

const ROTULO_DECISAO: Record<DecisaoAnalista, string> = {
  APROVAR: 'Aprovar',
  APROVAR_COM_RESTRICOES: 'Aprovar com restrições',
  REVISAR: 'Revisar',
  SUSPENDER: 'Suspender',
  RECUSAR: 'Recusar',
};

export interface BlocoDecisaoProps {
  cliente: Cliente;
  avaliacao: AvaliacaoDeRisco;
}

export function BlocoDecisao({ cliente, avaliacao }: BlocoDecisaoProps) {
  const concessao = cliente.origem === 'PROSPECT';
  const [decisao, setDecisao] = useState<DecisaoAnalista | null>(null);
  const [justificativa, setJustificativa] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [registrado, setRegistrado] = useState<RegistroAuditoria | null>(null);

  // A trilha vem do store de sessão, não de um `useState` local: registrar uma decisão
  // notifica o store, e a lista se atualiza sozinha — inclusive em outra aba.
  const sessao = useSessao();
  const anteriores = useMemo(
    () =>
      decisoesDaSessao(sessao)
        .filter((registro) => registro.clienteId === cliente.id)
        .slice(-3)
        .reverse(),
    [cliente.id, sessao],
  );

  const divergente =
    decisao !== null && decisao !== EQUIVALENTE[avaliacao.recomendacao.codigo];
  const valido = decisao !== null && justificativa.trim().length >= 10;

  async function enviar() {
    if (!valido || decisao === null) return;
    setEnviando(true);
    setErro(null);
    try {
      const registro = await registrarDecisao({
        clienteId: cliente.id,
        clienteNome: cliente.razaoSocial,
        analista: PERSONA.nome,
        dataHora: new Date().toISOString(),
        scoreNoMomento: avaliacao.scoreCalculado,
        ratingNoMomento: avaliacao.ratingFinal,
        recomendacaoGerada: avaliacao.recomendacao.codigo,
        decisaoAnalista: decisao,
        justificativa: justificativa.trim(),
        divergiuDaRecomendacao: divergente,
      });
      registrarDecisaoNaSessao(registro);
      setRegistrado(registro);
      setJustificativa('');
      setDecisao(null);
    } catch (causa: unknown) {
      setErro(
        causa instanceof ErroLastro
          ? textoDeErro(causa)
          : 'Não foi possível registrar a decisão.',
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Card id="decisao" as="section" aria-labelledby="titulo-decisao" className="scroll-mt-[88px]">
      <SectionHeader
        nivel={2}
        titulo={concessao ? 'Decisão de concessão' : 'Decisão do analista'}
        descricao={`Registrada em nome de ${PERSONA.nome}. A trilha completa fica salva nesta sessão.`}
        meta={<PenLine size={14} strokeWidth={2} aria-hidden="true" />}
      />
      <h2 id="titulo-decisao" className="sr-only">
        Decisão do analista
      </h2>

      <form
        className="mt-3 flex flex-col gap-3"
        onSubmit={(evento) => {
          evento.preventDefault();
          void enviar();
        }}
        onKeyDown={(evento) => {
          if ((evento.metaKey || evento.ctrlKey) && evento.key === 'Enter') {
            evento.preventDefault();
            void enviar();
          }
        }}
      >
        <fieldset className="flex flex-col gap-2">
          <legend className="type-eyebrow text-fg-secondary">Decisão</legend>
          <div role="radiogroup" aria-label="Decisão do analista" className="flex flex-wrap gap-2">
            {OPCOES.map((opcao) => {
              const ativo = decisao === opcao.valor;
              return (
                <label
                  key={opcao.valor}
                  className={`transicao-controle type-body flex cursor-pointer items-center gap-2 rounded border px-3 py-1.5 ${
                    ativo
                      ? 'border-accent-line bg-accent-tint text-fg-primary'
                      : 'border-line-default text-fg-secondary hover:bg-surface-hover'
                  }`}
                >
                  <input
                    type="radio"
                    name="decisao-analista"
                    value={opcao.valor}
                    checked={ativo}
                    onChange={() => setDecisao(opcao.valor)}
                    className="accent-[var(--color-accent-400)]"
                  />
                  {opcao.rotulo}
                </label>
              );
            })}
          </div>
        </fieldset>

        <label className="flex flex-col gap-1">
          <span className="type-eyebrow text-fg-secondary">Justificativa (obrigatória)</span>
          <textarea
            value={justificativa}
            rows={3}
            onChange={(evento) => setJustificativa(evento.target.value)}
            placeholder="Descreva o que sustenta esta decisão — mínimo de 10 caracteres."
            className="transicao-controle type-body w-full resize-y rounded border border-line-default bg-surface-input px-3 py-2 text-fg-primary placeholder:text-fg-tertiary focus-visible:border-accent-line focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-400"
          />
        </label>

        <p
          className={`type-body flex items-start gap-2 rounded border px-3 py-2 ${
            divergente
              ? 'border-risk-c-line bg-risk-c-tint text-fg-primary'
              : 'border-line-default text-fg-secondary'
          }`}
          aria-live="polite"
        >
          {divergente ? (
            <TriangleAlert size={14} strokeWidth={2} className="mt-0.5 shrink-0 text-risk-c" aria-hidden="true" />
          ) : (
            <CheckCircle2 size={14} strokeWidth={2} className="mt-0.5 shrink-0" aria-hidden="true" />
          )}
          <span>
            {decisao === null
              ? `Recomendação do motor: ${avaliacao.recomendacao.rotulo}.`
              : divergente
                ? `Sua decisão diverge da recomendação do motor (${avaliacao.recomendacao.rotulo}). A divergência fica marcada na trilha de auditoria.`
                : `Sua decisão está alinhada à recomendação do motor (${avaliacao.recomendacao.rotulo}).`}
          </span>
        </p>

        <AvisoDeDecisaoHumana />

        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="submit"
            variante="primario"
            className="w-full sm:w-auto"
            carregando={enviando}
            disabled={!valido}
          >
            Registrar decisão
          </Button>
          {/* Atalho de teclado só faz sentido com teclado físico. */}
          <span className="type-caption hidden sm:inline">
            Ctrl/Cmd + Enter registra quando o formulário é válido.
          </span>
        </div>
      </form>

      {erro ? (
        <div className="mt-3">
          <ErrorState
            compacto
            titulo="A decisão não foi registrada"
            detalhe={erro}
            aoTentarNovamente={() => void enviar()}
          />
        </div>
      ) : null}

      {registrado ? (
        <p
          className="type-body mt-3 rounded border border-risk-a-line bg-risk-a-tint px-3 py-2 text-fg-primary"
          role="status"
        >
          Decisão registrada em {formatarDataHora(registrado.dataHora)} por {registrado.analista}.
        </p>
      ) : null}

      {anteriores.length > 0 ? (
        <section className="mt-4 border-t border-line-subtle pt-3">
          <h3 className="type-eyebrow mb-2 text-fg-secondary">
            Últimas decisões deste cliente nesta sessão
          </h3>
          <ul className="flex flex-col gap-2">
            {anteriores.map((registro) => (
              <li
                key={registro.id}
                className={`flex flex-col gap-0.5 rounded border px-3 py-2 ${
                  registro.divergiuDaRecomendacao
                    ? 'border-risk-c-line'
                    : 'border-line-default'
                }`}
              >
                <p className="type-body-strong text-fg-primary">
                  {ROTULO_DECISAO[registro.decisaoAnalista]}
                  {registro.divergiuDaRecomendacao ? ' · divergente da recomendação' : ''}
                </p>
                <p className="type-caption">
                  {formatarDataHora(registro.dataHora)} · {registro.analista} · score no momento{' '}
                  <span className="tnum">{registro.scoreNoMomento}</span> · rating{' '}
                  {registro.ratingNoMomento}
                </p>
                <p className="type-caption text-fg-secondary">{registro.justificativa}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </Card>
  );
}
