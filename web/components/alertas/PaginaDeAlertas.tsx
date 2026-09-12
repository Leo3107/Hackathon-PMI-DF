'use client';

/**
 * `/alertas` — central de alertas (`03-ux-e-telas.md` §7).
 *
 * Responde "o que mudou na carteira e o que eu faço a respeito?". Agrupamento padrão **por
 * data**, porque a pergunta que traz o analista aqui é temporal, não nominal.
 *
 * O estado de leitura é da sessão (`localStorage`), nunca do servidor (D3): o motor devolve
 * `lido: false` sempre, e `aplicarLeitura` projeta o que esta sessão já viu.
 */

import { CheckCheck, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { useSessao } from '@/components/shell';
import {
  AlertRow,
  Badge,
  Button,
  Card,
  EmptyState,
  FilterChips,
  KpiTile,
  Modal,
  SEVERIDADE,
  SectionHeader,
  Termo,
  cn,
  type OpcaoChip,
} from '@/components/ui';
import { listarAlertas } from '@/lib/api';
import { formatarData } from '@/lib/format';
import { marcarAlertaComoLido, marcarAlertasComoLidos, sessaoParaApi } from '@/lib/sessao';
import type { Alerta, Severidade } from '@/types';

import { FalhaDoMotor } from './FalhaDoMotor';
import {
  ROTULO_AGRUPAMENTO,
  ROTULO_FILTRO,
  ROTULO_SEVERIDADE,
  SEVERIDADES,
  agrupar,
  aplicarLeitura,
  contarNaoLidos,
  contarPorSeveridade,
  filtrarAlertas,
  paraAlertRow,
  temCriticoNaoLido,
  textoDoVazio,
  type Agrupamento,
  type FiltroAlerta,
} from './agrupamento';

const FILTROS: FiltroAlerta[] = ['nao_lidos', 'ultimos_7d', 'ultimos_30d', 'acao_pendente'];

const OPCOES_FILTRO: OpcaoChip<FiltroAlerta>[] = FILTROS.map((valor) => ({
  valor,
  rotulo: ROTULO_FILTRO[valor],
}));

export function PaginaDeAlertas() {
  const router = useRouter();
  const sessao = useSessao();

  const [doMotor, setDoMotor] = useState<Alerta[] | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  const [tentativa, setTentativa] = useState(0);

  const [severidades, setSeveridades] = useState<ReadonlySet<Severidade>>(new Set());
  const [filtros, setFiltros] = useState<ReadonlySet<FiltroAlerta>>(new Set());
  const [agrupamento, setAgrupamento] = useState<Agrupamento>('data');
  const [confirmando, setConfirmando] = useState(false);

  // A data de referência dos buckets ("Hoje", "Ontem") é o relógio do navegador no momento da
  // montagem, fixado em estado para não mudar durante a sessão e para as funções puras de
  // agrupamento continuarem determinísticas.
  const [referencia] = useState(() => new Date().toISOString());

  useEffect(() => {
    let vivo = true;
    listarAlertas(sessaoParaApi())
      .then((dados) => {
        if (!vivo) return;
        setDoMotor(dados);
        setErro(null);
      })
      .catch((causa: unknown) => {
        if (!vivo) return;
        setDoMotor(null);
        setErro(causa);
      });
    return () => {
      vivo = false;
    };
  }, [tentativa]);

  const alertas = useMemo(
    () => (doMotor ? aplicarLeitura(doMotor, sessao.alertasLidos) : []),
    [doMotor, sessao.alertasLidos],
  );

  const criterios = useMemo(
    () => ({ severidades, filtros, referencia }),
    [severidades, filtros, referencia],
  );
  const visiveis = useMemo(() => filtrarAlertas(alertas, criterios), [alertas, criterios]);
  const grupos = useMemo(
    () => agrupar(visiveis, agrupamento, referencia),
    [visiveis, agrupamento, referencia],
  );

  const porSeveridade = useMemo(() => contarPorSeveridade(alertas), [alertas]);
  const naoLidos = contarNaoLidos(alertas);

  const abrirCliente = useCallback(
    (clienteId: string) => router.push(`/clientes/${clienteId}#red-flags`),
    [router],
  );

  const alternarSeveridade = useCallback((severidade: Severidade) => {
    setSeveridades((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(severidade)) proximo.delete(severidade);
      else proximo.add(severidade);
      return proximo;
    });
  }, []);

  const marcarTodos = useCallback(() => {
    marcarAlertasComoLidos(visiveis.map((alerta) => alerta.id));
    setConfirmando(false);
  }, [visiveis]);

  if (erro) {
    return (
      <FalhaDoMotor
        erro={erro}
        contexto="a central de alertas"
        aoTentarNovamente={() => setTentativa((n) => n + 1)}
      />
    );
  }

  const carregando = doMotor === null;
  const vazio = textoDoVazio(alertas.length, criterios, naoLidos === 0);

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-4">
        <SectionHeader
          titulo="Central de alertas"
          descricao="O que mudou na carteira desde a última varredura do motor, e o que fazer a respeito."
          meta={<Badge variante="simulado" tamanho="sm" />}
          acoes={
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variante="secundario"
                iconeEsquerda={CheckCheck}
                disabled={carregando || naoLidos === 0}
                onClick={() => {
                  if (temCriticoNaoLido(visiveis)) setConfirmando(true);
                  else marcarTodos();
                }}
              >
                Marcar todos como lidos
              </Button>
              <Button
                variante="fantasma"
                iconeEsquerda={Users}
                onClick={() => router.push('/clientes?filtro=com-alerta')}
              >
                Ver clientes afetados
              </Button>
            </div>
          }
        />

        <p className="type-caption" aria-live="polite">
          {carregando
            ? 'Carregando alertas…'
            : `${alertas.length} ${alertas.length === 1 ? 'alerta' : 'alertas'} · ${naoLidos} não ${naoLidos === 1 ? 'lido' : 'lidos'} · referência ${formatarData(referencia, 'curta')}`}
        </p>

        <p className="type-caption max-w-[92ch]">
          Severidade crítica cobre deferimento de <Termo sigla="RJ" /> e ativação do{' '}
          <Termo sigla="STAY_PERIOD" />, que suspende execuções e deixa exposto tudo o que não for{' '}
          <Termo sigla="EXTRACONCURSAL" />. Severidade alta cobre quebra de{' '}
          <Termo sigla="COVENANT" />, <Termo sigla="CNDT" /> positiva e inscrição em dívida ativa
          na <Termo sigla="PGFN" />.
        </p>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {SEVERIDADES.map((severidade) => {
            const apresentacao = SEVERIDADE[severidade];
            const ativo = severidades.has(severidade);
            return (
              <KpiTile
                key={severidade}
                tamanho="sm"
                rotulo={ROTULO_SEVERIDADE[severidade]}
                valor={carregando ? '—' : String(porSeveridade[severidade])}
                familia={apresentacao.familia}
                carregando={carregando}
                aoClicar={() => alternarSeveridade(severidade)}
                className={cn(ativo && 'border-accent-line ring-1 ring-accent-400')}
                rodape={
                  <span className="type-caption inline-flex items-center gap-1.5">
                    <apresentacao.Icone size={14} strokeWidth={2} aria-hidden="true" />
                    {ativo ? 'Filtro ativo — clique para remover' : 'Clique para filtrar'}
                  </span>
                }
              />
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <FilterChips
            rotulo="Filtros de alertas"
            opcoes={OPCOES_FILTRO}
            selecionados={filtros}
            aoMudar={(proximos) => setFiltros(proximos)}
            limparRotulo="Limpar"
          />
          <label className="type-caption flex items-center gap-2 text-fg-secondary">
            Agrupar
            <select
              aria-label="Agrupamento da lista de alertas"
              value={agrupamento}
              onChange={(evento) => setAgrupamento(evento.target.value as Agrupamento)}
              className="type-body h-8 rounded border border-line-default bg-surface-input px-2 text-fg-primary"
            >
              {(Object.keys(ROTULO_AGRUPAMENTO) as Agrupamento[]).map((valor) => (
                <option key={valor} value={valor}>
                  {ROTULO_AGRUPAMENTO[valor]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      {carregando ? (
        <Card semPadding aria-hidden="true">
          <div className="flex flex-col gap-2 p-4">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="esqueleto h-14 rounded-md" />
            ))}
          </div>
        </Card>
      ) : grupos.length === 0 ? (
        <Card>
          <EmptyState
            titulo={vazio.titulo}
            descricao={vazio.descricao}
            acao={
              vazio.acao === 'limpar'
                ? {
                    rotulo: 'Limpar filtros',
                    aoClicar: () => {
                      setSeveridades(new Set());
                      setFiltros(new Set());
                    },
                  }
                : vazio.acao === 'ver_todos'
                  ? {
                      rotulo: 'Ver todos',
                      aoClicar: () =>
                        setFiltros((atual) => {
                          const proximo = new Set(atual);
                          proximo.delete('nao_lidos');
                          return proximo;
                        }),
                    }
                  : undefined
            }
          />
        </Card>
      ) : (
        <Card semPadding>
          <ul className="flex flex-col">
            {grupos.map((grupo) => (
              <li key={grupo.chave}>
                <h2 className="type-eyebrow sticky top-0 z-10 border-y border-line-subtle bg-surface-raised px-4 py-1.5 text-fg-secondary">
                  {grupo.titulo}
                  <span className="tnum ml-2 text-fg-tertiary">{grupo.alertas.length}</span>
                </h2>
                <ul className="flex flex-col">
                  {grupo.alertas.map((alerta) => (
                    <li key={alerta.id} className="flex flex-col">
                      <AlertRow
                        alerta={paraAlertRow(alerta)}
                        referencia={referencia}
                        aoAbrirCliente={abrirCliente}
                        aoMarcarLido={marcarAlertaComoLido}
                      />
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line-subtle px-4 pb-2">
                        <p className="type-caption min-w-0 flex-1 text-fg-secondary">
                          {alerta.descricao}
                        </p>
                        <Button
                          tamanho="sm"
                          variante="fantasma"
                          onClick={() => marcarAlertaComoLido(alerta.id)}
                          disabled={alerta.lido}
                        >
                          {alerta.lido ? 'Lido' : 'Marcar como lido'}
                        </Button>
                        <Button
                          tamanho="sm"
                          variante="fantasma"
                          onClick={() => {
                            marcarAlertaComoLido(alerta.id);
                            abrirCliente(alerta.clienteId);
                          }}
                        >
                          Abrir cliente
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Modal
        aberto={confirmando}
        aoFechar={() => setConfirmando(false)}
        titulo="Marcar todos como lidos"
        descricao="Há alerta de severidade crítica ainda não lido na seleção atual."
        acoes={
          <>
            <Button variante="secundario" onClick={() => setConfirmando(false)}>
              Cancelar
            </Button>
            <Button variante="primario" onClick={marcarTodos}>
              Marcar todos mesmo assim
            </Button>
          </>
        }
      >
        <p className="type-body text-fg-secondary">
          Alertas lidos continuam na lista, apenas sem o realce de não lido. A marcação vale só
          para esta sessão e pode ser revertida em &quot;Restaurar dados da demonstração&quot;.
        </p>
      </Modal>
    </div>
  );
}
