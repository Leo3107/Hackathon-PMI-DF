'use client';

/**
 * As treze seções do Parecer de Risco (`specs/07` §3.5), na ordem fixa.
 *
 * Cada seção declara de onde vem seu conteúdo: **motor** (determinístico, instantâneo) ou
 * **linguagem** (prosa, com fallback). Nenhuma mistura as duas origens sem dizer qual é qual -
 * é a promessa central do documento e a primeira coisa que a banca vai testar.
 */

import type { ReactNode } from 'react';

import {
  formatarData,
  formatarDelta,
  formatarDocumento,
  formatarMoeda,
  formatarNumero,
  formatarPercentual,
  formatarScore,
} from '@/lib/format';
import type {
  AvaliacaoDeRisco,
  Cliente,
  FatosDoCliente,
  Garantia,
  RedFlag,
  RegistroAuditoria,
} from '@/types';

import type { BlocoDeProsa } from './dados';

export const RED_FLAGS_POR_PAGINA = 8;
export const EVIDENCIAS_POR_PAGINA = 10;

const ESTADO: Record<string, string> = {
  ATIVO: 'Ativo',
  EM_OBSERVACAO: 'Em observação',
  SUSPENSO: 'Suspenso',
  RJ_EM_CURSO: 'Recuperação judicial em curso',
  FALENCIA: 'Falência',
};

const SEVERIDADE: Record<string, { rotulo: string; sigla: string }> = {
  CRITICA: { rotulo: 'Crítica', sigla: '▲' },
  ALTA: { rotulo: 'Alta', sigla: '!' },
  MEDIA: { rotulo: 'Média', sigla: '•' },
  BAIXA: { rotulo: 'Informativa', sigla: 'i' },
};

const TENDENCIA: Record<string, { rotulo: string; seta: string }> = {
  melhorando: { rotulo: 'Melhorando', seta: '↑' },
  estavel: { rotulo: 'Estável', seta: '→' },
  deteriorando: { rotulo: 'Deteriorando', seta: '↓' },
  deterioracao_acelerada: { rotulo: 'Deterioração acelerada', seta: '⇊' },
};

const TIPO_OPERACAO: Record<string, string> = {
  VENDA_A_PRAZO: 'Venda a prazo',
  BARTER: 'Barter',
  CPR: 'CPR',
};

const TIPO_GARANTIA: Record<string, string> = {
  ALIENACAO_FIDUCIARIA: 'Alienação fiduciária',
  CPR_FINANCEIRA: 'CPR financeira',
  CPR_FISICA: 'CPR física',
  PENHOR_SAFRA: 'Penhor de safra',
  PENHOR_MAQUINA: 'Penhor de máquina',
  HIPOTECA: 'Hipoteca',
  AVAL_FIANCA: 'Aval ou fiança',
};

const DECISAO: Record<string, string> = {
  APROVAR: 'Aprovar',
  APROVAR_COM_RESTRICOES: 'Aprovar com restrições',
  REVISAR: 'Revisar',
  SUSPENDER: 'Suspender',
  RECUSAR: 'Recusar',
};

/* ------------------------------------------------------------------ */
/* Peças reutilizadas                                                  */
/* ------------------------------------------------------------------ */

export function Secao({
  numero,
  titulo,
  origem,
  children,
}: {
  numero: number;
  titulo: string;
  origem: 'motor' | 'linguagem' | 'motor+linguagem' | 'fixo';
  children: ReactNode;
}) {
  return (
    <section className="pc-secao">
      <div className="pc-secao-cabeca">
        <h2>
          <span className="pc-secao-numero">{numero}</span> {titulo}
        </h2>
        <span className={`pc-origem pc-origem--${origem === 'linguagem' ? 'llm' : 'motor'}`}>
          {origem === 'motor'
            ? 'Motor determinístico'
            : origem === 'linguagem'
              ? 'Texto de IA'
              : origem === 'motor+linguagem'
                ? 'Motor, com leitura de IA'
                : 'Texto fixo'}
        </span>
      </div>
      {children}
    </section>
  );
}

function Campos({ itens }: { itens: Array<[string, ReactNode]> }) {
  return (
    <dl className="pc-campos">
      {itens.map(([rotulo, valor]) => (
        <div key={rotulo}>
          <dt>{rotulo}</dt>
          <dd>{valor}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Prosa da camada de linguagem, sempre etiquetada com sua origem real. */
export function Prosa({ bloco, rotulo }: { bloco: BlocoDeProsa; rotulo?: string }) {
  if (!bloco.concluido && bloco.origem !== 'llm') {
    return (
      <div className="pc-prosa pc-prosa--gerando">
        {rotulo ? <span className="pc-prosa-rotulo">{rotulo}</span> : null}
        <p className="pc-esqueleto" aria-live="polite">
          gerando texto...
        </p>
      </div>
    );
  }
  return (
    <div className="pc-prosa">
      {rotulo ? <span className="pc-prosa-rotulo">{rotulo}</span> : null}
      <p>{bloco.texto}</p>
      <p className="pc-etiqueta">
        {bloco.origem === 'llm'
          ? 'Texto gerado por IA a partir dos dados deste parecer'
          : 'Texto padrão (sem IA)'}
      </p>
    </div>
  );
}

/** Gauge simplificado: arco de 180°, desenhado à mão. Nenhuma biblioteca. */
function Gauge({ score }: { score: number }) {
  const fracao = Math.min(1, Math.max(0, score / 1000));
  const raio = 40;
  const comprimento = Math.PI * raio;
  return (
    <svg className="pc-gauge" viewBox="0 0 100 54" role="img" aria-label={`Score ${score} de 1000`}>
      <path
        d={`M 10 50 A ${raio} ${raio} 0 0 1 90 50`}
        fill="none"
        stroke="#d7dbe0"
        strokeWidth="8"
        strokeLinecap="round"
      />
      <path
        d={`M 10 50 A ${raio} ${raio} 0 0 1 90 50`}
        fill="none"
        stroke="#111"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={`${comprimento * fracao} ${comprimento}`}
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* 1 e 2, identificação, data e responsável                           */
/* ------------------------------------------------------------------ */

export function SecaoIdentificacao({
  cliente,
  fatos,
}: {
  cliente: Cliente;
  fatos: FatosDoCliente | null;
}) {
  return (
    <Secao numero={1} titulo="Identificação do cliente" origem="motor">
      <p className="pc-cliente-nome">{cliente.razaoSocial}</p>
      <Campos
        itens={[
          ['Nome fantasia', cliente.nomeFantasia ?? 'Não informado'],
          [
            cliente.tipoPessoa === 'PF' ? 'CPF' : 'CNPJ',
            <span className="pc-num" key="doc">
              {formatarDocumento(cliente.documento)} (simulado)
            </span>,
          ],
          ['Tipo de pessoa', cliente.tipoPessoa === 'PF' ? 'Pessoa física' : 'Pessoa jurídica'],
          ['Município e UF', `${cliente.municipio}, ${cliente.uf}`],
          ['Atividade', cliente.atividade],
          ['CNAE principal', cliente.cnaePrincipal],
          ['Culturas', cliente.culturas.join(', ') || 'Não informadas'],
          ['Início do relacionamento', formatarData(cliente.inicioRelacionamento)],
          ['Estado atual', ESTADO[cliente.estado] ?? cliente.estado],
          ['Origem', cliente.origem === 'CARTEIRA' ? 'Carteira' : 'Prospect'],
          ['Safra de referência', fatos?.agro.safraReferencia ?? 'Não informada'],
        ]}
      />
    </Secao>
  );
}

export function SecaoResponsavel({
  avaliacao,
  identificador,
  geradoEm,
  analista,
}: {
  avaliacao: AvaliacaoDeRisco;
  identificador: string;
  geradoEm: string;
  analista: string;
}) {
  return (
    <Secao numero={2} titulo="Data e responsável" origem="motor">
      <Campos
        itens={[
          ['Data de referência dos fatos', formatarData(avaliacao.dataReferencia)],
          ['Geração deste documento', geradoEm],
          ['Analista responsável', analista],
          [
            'Identificador',
            <span className="pc-num" key="id">
              {identificador}
            </span>,
          ],
        ]}
      />
    </Secao>
  );
}

/* ------------------------------------------------------------------ */
/* 3, 4 e 5, os números                                               */
/* ------------------------------------------------------------------ */

export function SecaoScore({ avaliacao }: { avaliacao: AvaliacaoDeRisco }) {
  const forcaD = avaliacao.vetosAtivos.find((v) => v.efeito === 'FORCA_D');
  const tetoC = avaliacao.vetosAtivos.find((v) => v.efeito === 'TETO_C');
  const tendencia = TENDENCIA[avaliacao.tendencia] ?? TENDENCIA.estavel;

  return (
    <Secao numero={3} titulo="Score, rating e classificação final" origem="motor">
      <div className="pc-destaque">
        <div className="pc-destaque-score">
          <Gauge score={avaliacao.scoreCalculado} />
          <p className="pc-numero-grande pc-num">{formatarScore(avaliacao.scoreCalculado)}</p>
          <p className="pc-destaque-rotulo">Score calculado, de 0 a 1000</p>
        </div>
        <div className="pc-destaque-colunas">
          <div>
            <p className="pc-destaque-rotulo">Rating calculado</p>
            <p className="pc-numero-medio">{avaliacao.ratingCalculado}</p>
          </div>
          <div>
            <p className="pc-destaque-rotulo">Classificação final após regras de negócio</p>
            <p className="pc-numero-medio">{avaliacao.ratingFinal}</p>
          </div>
          <div>
            <p className="pc-destaque-rotulo">Tendência em 90 dias</p>
            <p className="pc-tendencia">
              <span aria-hidden="true">{tendencia.seta}</span> {tendencia.rotulo}
            </p>
          </div>
        </div>
      </div>

      {forcaD ? (
        <div className="pc-caixa pc-caixa--veto">
          <strong>Veto ativo, {forcaD.rotulo}</strong>
          <p>{forcaD.justificativa}</p>
        </div>
      ) : null}
      {tetoC ? (
        <div className="pc-caixa pc-caixa--teto">
          <strong>Teto aplicado, {tetoC.rotulo}</strong>
          <p>{tetoC.justificativa}</p>
        </div>
      ) : null}

      <p className="pc-nota">
        O score calculado permanece exibido mesmo quando a classificação final é rebaixada por
        regra de negócio.
      </p>
    </Secao>
  );
}

export function SecaoPd({ avaliacao }: { avaliacao: AvaliacaoDeRisco }) {
  const colunas: Array<[string, number]> = [
    ['6 meses', avaliacao.pd.pd6m],
    ['12 meses', avaliacao.pd.pd12m],
    ['24 meses', avaliacao.pd.pd24m],
  ];
  return (
    <Secao numero={4} titulo="Probabilidade de inadimplência" origem="motor">
      <div className="pc-pd">
        {colunas.map(([rotulo, valor]) => (
          <div key={rotulo}>
            <p className="pc-destaque-rotulo">{rotulo}</p>
            <p className="pc-numero-medio pc-num">{formatarPercentual(valor, 1)}</p>
            <span className="pc-minibarra">
              <span style={{ width: `${Math.min(100, valor * 100)}%` }} />
            </span>
          </div>
        ))}
      </div>
      <p className="pc-nota pc-nota--metodo">{avaliacao.pd.metodo}</p>
    </Secao>
  );
}

export function SecaoRiscoRJ({ avaliacao }: { avaliacao: AvaliacaoDeRisco }) {
  const rj = avaliacao.riscoRJ;
  const stay = avaliacao.stayPeriod;

  return (
    <Secao numero={5} titulo="Risco de recuperação judicial" origem="motor">
      {rj.eventoJaOcorrido ? (
        <>
          <div className="pc-caixa pc-caixa--veto">
            <strong>RJ em curso, evento ocorrido</strong>
            {stay ? (
              <p>
                Deferimento em {formatarData(stay.dataDeferimento)}. Stay Period com{' '}
                {stay.diasDecorridos} dias decorridos e {stay.diasRestantes} dias restantes.
              </p>
            ) : null}
          </div>
          {stay ? (
            <div className="pc-duas-colunas">
              <div>
                <p className="pc-destaque-rotulo">Impedido durante o Stay Period</p>
                <ul className="pc-lista">
                  {stay.bloqueios.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="pc-destaque-rotulo">Permanece possível</p>
                <ul className="pc-lista">
                  {stay.permitido.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : null}
        </>
      ) : (
        <>
          <div className="pc-pd">
            <div>
              <p className="pc-destaque-rotulo">Probabilidade em 12 meses</p>
              <p className="pc-numero-medio pc-num">
                {formatarPercentual(rj.probabilidade12m, 1)}
              </p>
            </div>
            <div>
              <p className="pc-destaque-rotulo">Índice de RJ, efetivo e bruto</p>
              <p className="pc-numero-medio pc-num">
                {Math.round(rj.rjIndexEfetivo)} de {Math.round(rj.rjIndex)}
              </p>
            </div>
            <div>
              <p className="pc-destaque-rotulo">Elegibilidade, Lei 14.112/2020</p>
              <p className="pc-tendencia">{rj.elegivel ? 'Elegível' : 'Não elegível'}</p>
              {rj.motivoInelegibilidade ? (
                <p className="pc-nota">{rj.motivoInelegibilidade}</p>
              ) : null}
            </div>
          </div>
          {rj.sinais.length ? (
            <table className="pc-tabela">
              <thead>
                <tr>
                  <th scope="col">Sinal de insolvência coletiva</th>
                  <th scope="col" className="pc-direita">
                    Pontos
                  </th>
                </tr>
              </thead>
              <tbody>
                {rj.sinais.map((s) => (
                  <tr key={s.rotulo}>
                    <td>{s.rotulo}</td>
                    <td className="pc-direita pc-num">{formatarNumero(s.pontos, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </>
      )}
      <p className="pc-nota">
        Inadimplência e recuperação judicial são eventos distintos e medidos separadamente.
      </p>
    </Secao>
  );
}

/* ------------------------------------------------------------------ */
/* 6, 7 e 8, leitura                                                  */
/* ------------------------------------------------------------------ */

export function SecaoResumo({ bloco }: { bloco: BlocoDeProsa }) {
  return (
    <Secao numero={6} titulo="Resumo executivo" origem="linguagem">
      <Prosa bloco={bloco} />
    </Secao>
  );
}

export function SecaoRiscos({
  redFlags,
  bloco,
  parte,
  total,
}: {
  redFlags: RedFlag[];
  bloco: BlocoDeProsa | null;
  parte: number;
  total: number;
}) {
  return (
    <Secao
      numero={7}
      titulo={total > 1 ? `Principais riscos (${parte} de ${total})` : 'Principais riscos'}
      origem={bloco ? 'motor+linguagem' : 'motor'}
    >
      {redFlags.length === 0 ? (
        <p className="pc-nota">Nenhuma red flag identificada na data de referência.</p>
      ) : (
        <ul className="pc-flags">
          {redFlags.map((flag) => {
            const s = SEVERIDADE[flag.severidade] ?? SEVERIDADE.BAIXA;
            return (
              <li key={flag.id} className={`pc-flag pc-flag--${flag.severidade.toLowerCase()}`}>
                <span className="pc-flag-sev">
                  <span aria-hidden="true">{s.sigla}</span> {s.rotulo}
                </span>
                <span className="pc-flag-titulo">{flag.titulo}</span>
                <span className="pc-flag-meta">
                  {formatarData(flag.data)} · {flag.fonte} (simulado) ·{' '}
                  <span className="pc-num">{formatarDelta(flag.impactoEmPontos, 'pts')}</span> ·{' '}
                  {flag.status}
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {bloco ? <Prosa bloco={bloco} rotulo="Leitura dos riscos" /> : null}
    </Secao>
  );
}

export function SecaoMitigadores({
  avaliacao,
  bloco,
}: {
  avaliacao: AvaliacaoDeRisco;
  bloco: BlocoDeProsa;
}) {
  const protecoes = avaliacao.dimensoes
    .flatMap((d) => d.fatores)
    .filter((f) => f.direcao === 'protecao')
    .sort((a, b) => b.pontos - a.pontos);

  return (
    <Secao numero={8} titulo="Fatores mitigadores" origem="motor+linguagem">
      {protecoes.length === 0 ? (
        <p className="pc-nota">Nenhum fator de proteção materializado na data de referência.</p>
      ) : (
        <table className="pc-tabela">
          <thead>
            <tr>
              <th scope="col">Fator de proteção</th>
              <th scope="col">Fonte</th>
              <th scope="col" className="pc-direita">
                Pontos
              </th>
            </tr>
          </thead>
          <tbody>
            {protecoes.map((f) => (
              <tr key={f.id}>
                <td>{f.rotulo}</td>
                <td>{f.fonte} (simulado)</td>
                <td className="pc-direita pc-num">{formatarNumero(f.pontos, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Prosa bloco={bloco} rotulo="Leitura dos mitigadores" />
    </Secao>
  );
}

/* ------------------------------------------------------------------ */
/* 9, exposição e garantias                                           */
/* ------------------------------------------------------------------ */

function TabelaDeGarantias({ titulo, garantias }: { titulo: string; garantias: Garantia[] }) {
  return (
    <div className="pc-garantias-bloco">
      <p className="pc-destaque-rotulo">{titulo}</p>
      {garantias.length === 0 ? (
        <p className="pc-nota">Nenhuma garantia desta natureza.</p>
      ) : (
        <table className="pc-tabela">
          <thead>
            <tr>
              <th scope="col">Garantia</th>
              <th scope="col" className="pc-direita">
                Declarado
              </th>
              <th scope="col" className="pc-direita">
                Haircut
              </th>
              <th scope="col" className="pc-direita">
                Atualizado
              </th>
              <th scope="col">Situação</th>
            </tr>
          </thead>
          <tbody>
            {garantias.map((g) => (
              <tr key={g.id}>
                <td>
                  {TIPO_GARANTIA[g.tipo] ?? g.tipo}
                  <br />
                  <span className="pc-sub">{g.descricao}</span>
                </td>
                <td className="pc-direita pc-num">{formatarMoeda(g.valorDeclarado)}</td>
                <td className="pc-direita pc-num">
                  {formatarPercentual(1 - g.valorAtualizado / (g.valorDeclarado || 1), 0)}
                </td>
                <td className="pc-direita pc-num">{formatarMoeda(g.valorAtualizado)}</td>
                <td>
                  {g.registrada ? 'Registrada' : 'Não registrada'}
                  {g.bemEmbargado ? ', bem embargado' : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function SecaoExposicao({
  avaliacao,
  fatos,
}: {
  avaliacao: AvaliacaoDeRisco;
  fatos: FatosDoCliente | null;
}) {
  const e = avaliacao.exposicao;
  const garantias = fatos?.garantias ?? [];
  const extraconcursais = garantias.filter((g) => g.natureza === 'EXTRACONCURSAL');
  const concursais = garantias.filter((g) => g.natureza === 'CONCURSAL');
  const barterSemCpr = (fatos?.operacoes ?? []).filter(
    (o) => o.tipo === 'BARTER' && !o.barter?.cprVinculadaId,
  );

  return (
    <Secao numero={9} titulo="Análise de exposição e garantias" origem="motor">
      <table className="pc-tabela">
        <thead>
          <tr>
            <th scope="col">Tipo de operação</th>
            <th scope="col" className="pc-direita">
              Saldo devedor
            </th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(e.porTipoOperacao).map(([tipo, valor]) => (
            <tr key={tipo}>
              <td>{TIPO_OPERACAO[tipo] ?? tipo}</td>
              <td className="pc-direita pc-num">{formatarMoeda(valor)}</td>
            </tr>
          ))}
          <tr className="pc-total">
            <td>Exposição total</td>
            <td className="pc-direita pc-num">{formatarMoeda(e.exposicaoTotal)}</td>
          </tr>
          <tr>
            <td>Em atraso</td>
            <td className="pc-direita pc-num">{formatarMoeda(e.emAtraso)}</td>
          </tr>
          <tr>
            <td>Limite aprovado e utilização</td>
            <td className="pc-direita pc-num">
              {formatarMoeda(e.limiteAprovado)} · {formatarPercentual(e.limiteUtilizadoPct, 0)}
            </td>
          </tr>
        </tbody>
      </table>

      <TabelaDeGarantias
        titulo="Garantias extraconcursais, que sobrevivem a uma recuperação judicial"
        garantias={extraconcursais}
      />
      <TabelaDeGarantias
        titulo="Garantias concursais, que entram no plano de recuperação"
        garantias={concursais}
      />

      <div className="pc-indicadores">
        <div>
          <p className="pc-destaque-rotulo">Valor extraconcursal</p>
          <p className="pc-num">{formatarMoeda(e.valorExtraconcursal)}</p>
        </div>
        <div>
          <p className="pc-destaque-rotulo">Valor concursal</p>
          <p className="pc-num">{formatarMoeda(e.valorConcursal)}</p>
        </div>
        <div>
          <p className="pc-destaque-rotulo">Cobertura extraconcursal</p>
          <p className="pc-num">{formatarPercentual(e.coberturaExtraconcursal, 0)}</p>
        </div>
        <div>
          <p className="pc-destaque-rotulo">Cobertura total</p>
          <p className="pc-num">{formatarPercentual(e.coberturaTotal, 0)}</p>
        </div>
        <div>
          <p className="pc-destaque-rotulo">Exposição protegida</p>
          <p className="pc-num">{formatarMoeda(e.exposicaoProtegida)}</p>
        </div>
        <div>
          <p className="pc-destaque-rotulo">Exposição em risco</p>
          <p className="pc-num">{formatarMoeda(e.exposicaoEmRisco)}</p>
        </div>
      </div>

      <div className="pc-caixa pc-caixa--destaque">
        <p className="pc-destaque-rotulo">Exposição em risco em cenário de RJ</p>
        <p className="pc-numero-grande pc-num">{formatarMoeda(e.exposicaoEmRiscoEmRJ)}</p>
        <p>
          Quanto a Krill Tech perde de proteção efetiva se este cliente pedir RJ: garantias
          concursais entram no plano; apenas as extraconcursais permanecem executáveis.
        </p>
      </div>

      {barterSemCpr.length ? (
        <p className="pc-nota">
          Operações de barter sem CPR vinculada:{' '}
          {barterSemCpr.map((o) => o.descricao).join('; ')}.
        </p>
      ) : null}
    </Secao>
  );
}

/* ------------------------------------------------------------------ */
/* 10, recomendação e decisão                                         */
/* ------------------------------------------------------------------ */

export function SecaoRecomendacao({
  avaliacao,
  bloco,
  registro,
}: {
  avaliacao: AvaliacaoDeRisco;
  bloco: BlocoDeProsa;
  registro: RegistroAuditoria | null;
}) {
  const r = avaliacao.recomendacao;
  return (
    <Secao numero={10} titulo="Recomendação operacional" origem="motor+linguagem">
      <div className="pc-recomendacao">
        <p className="pc-numero-medio">{r.rotulo}</p>
        <p className="pc-destaque-rotulo">
          Reavaliar em <span className="pc-num">{r.prazoReavaliacaoDias}</span> dias
        </p>
      </div>

      <ol className="pc-acoes">
        {r.acoes.map((a) => (
          <li key={a.id}>
            <span className="pc-acao-prio">Prioridade {a.prioridade}</span>
            <span>
              {a.rotulo}
              {a.detalhe ? <span className="pc-sub"> {a.detalhe}</span> : null}
            </span>
          </li>
        ))}
      </ol>

      <Prosa bloco={bloco} rotulo="Justificativa" />

      <p className="pc-aviso-decisao">{r.aviso}</p>

      {registro ? (
        <div className="pc-decisao">
          <p className="pc-destaque-rotulo">Decisão registrada</p>
          <p>
            <strong>{DECISAO[registro.decisaoAnalista] ?? registro.decisaoAnalista}</strong> em{' '}
            {formatarData(registro.dataHora)}, por {registro.analista}.
            {registro.divergiuDaRecomendacao ? ' Divergiu da recomendação.' : ''}
          </p>
          <p>{registro.justificativa}</p>
        </div>
      ) : (
        <div className="pc-decisao pc-decisao--assinatura">
          <p>
            Decisão do analista
            <span className="pc-linha" />
          </p>
          <p>
            Justificativa
            <span className="pc-linha" />
          </p>
          <p>
            Data e assinatura
            <span className="pc-linha" />
          </p>
        </div>
      )}
    </Secao>
  );
}

/* ------------------------------------------------------------------ */
/* 11, 12 e 13, evidências, auditoria, aviso                          */
/* ------------------------------------------------------------------ */

export function SecaoEvidencias({
  avaliacao,
  inicio,
  parte,
  total,
}: {
  avaliacao: AvaliacaoDeRisco;
  inicio: number;
  parte: number;
  total: number;
}) {
  const fatia = avaliacao.evidencias.slice(inicio, inicio + EVIDENCIAS_POR_PAGINA);
  return (
    <Secao
      numero={11}
      titulo={
        total > 1 ? `Evidências consultadas (${parte} de ${total})` : 'Evidências consultadas'
      }
      origem="motor"
    >
      <table className="pc-tabela pc-tabela--evidencias">
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Fonte</th>
            <th scope="col">Tipo</th>
            <th scope="col">Título</th>
            <th scope="col">Documento</th>
            <th scope="col">Consulta</th>
            <th scope="col">Fatores</th>
          </tr>
        </thead>
        <tbody>
          {fatia.map((ev, i) => (
            <tr key={ev.id}>
              <td className="pc-num">{inicio + i + 1}</td>
              <td>{ev.nomeFonte} (simulado)</td>
              <td>{ev.tipo}</td>
              <td>{ev.titulo}</td>
              <td className="pc-num">{ev.dataDocumento ? formatarData(ev.dataDocumento) : '-'}</td>
              <td className="pc-num">{formatarData(ev.dataConsulta)}</td>
              <td className="pc-mono">{ev.fatoresRelacionados.join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Secao>
  );
}

export function SecaoAuditoria({ avaliacao }: { avaliacao: AvaliacaoDeRisco }) {
  const a = avaliacao.auditoria;
  return (
    <Secao numero={12} titulo="Metodologia e auditoria de fechamento" origem="motor">
      <table className="pc-tabela">
        <thead>
          <tr>
            <th scope="col">Dimensão</th>
            <th scope="col" className="pc-direita">
              Peso
            </th>
            <th scope="col" className="pc-direita">
              Score da dimensão
            </th>
            <th scope="col" className="pc-direita">
              Contribuição
            </th>
          </tr>
        </thead>
        <tbody>
          {avaliacao.dimensoes.map((d) => (
            <tr key={d.id}>
              <td>{d.rotulo}</td>
              <td className="pc-direita pc-num">{formatarPercentual(d.peso, 0)}</td>
              <td className="pc-direita pc-num">{formatarScore(d.score)}</td>
              <td className="pc-direita pc-num">{formatarNumero(d.contribuicao, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="pc-fechamento pc-num">
        Σ impactos = {formatarNumero(a.somaImpactos, 1)} · score reconstruído ={' '}
        {formatarNumero(a.scoreReconstruido, 1)} · diferença = {formatarNumero(a.diferenca, 2)}
      </p>
      <p className="pc-nota">
        A soma das contribuições dos fatores reconstrói exatamente o score. Detalhe completo na
        aba Metodologia da aplicação.
      </p>
    </Secao>
  );
}

export function SecaoAviso({ identificador }: { identificador: string }) {
  return (
    <Secao numero={13} titulo="Aviso" origem="fixo">
      <div className="pc-caixa pc-caixa--aviso">
        <p>
          <strong>Aviso.</strong> Este relatório foi gerado de forma automatizada pela plataforma
          Lastro e constitui <strong>instrumento de apoio à decisão</strong>. Os valores de score,
          rating, probabilidade de inadimplência e risco de recuperação judicial resultam de
          modelo quantitativo determinístico aplicado a evidências com fonte e data
          identificadas; os textos assinalados como gerados por IA foram redigidos por modelo de
          linguagem exclusivamente a partir desses valores e evidências, sem produzir ou alterar
          qualquer número. <strong>A avaliação final e a decisão de crédito são de
          responsabilidade do analista responsável</strong>, que deve considerar informações
          adicionais não capturadas por este instrumento. Nesta versão, todos os dados são{' '}
          <strong>simulados</strong> e nenhuma base pública foi consultada para esta carteira;
          nomes, documentos e valores são fictícios. Documento{' '}
          <span className="pc-num">{identificador}</span>.
        </p>
      </div>
    </Secao>
  );
}

