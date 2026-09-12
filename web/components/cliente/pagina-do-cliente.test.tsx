import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

// `next/font/google` é um plugin de build do Next e não existe no runtime do Vitest. Os
// componentes chegam aqui pelo barrel do design system, que carrega `fontes.ts`; o mock
// devolve só o que o barrel usa — as variáveis CSS.
vi.mock('next/font/google', () => ({
  Inter: () => ({ variable: '--font-inter', className: 'fonte-inter' }),
  JetBrains_Mono: () => ({ variable: '--font-jetbrains-mono', className: 'fonte-mono' }),
}));

import { AVISO_DECISAO_HUMANA } from '@/types';
import type {
  AvaliacaoDeRisco,
  ExposicaoCalculada,
  FatosDoCliente,
  ProbabilidadeDeDefault,
  Recomendacao,
  RiscoRJ,
  StayPeriod,
} from '@/types';

import { PainelStayPeriod } from './Cabecalho';
import { BlocoExposicao } from './Exposicao';
import {
  CardDePd,
  CardDeRecomendacao,
  CardDeRiscoRj,
  CardDeScore,
} from './Lateral';
import type { Narrativa } from './dados';

afterEach(cleanup);

/**
 * Texto renderizado com o espaço estreito insecável de `formatarMoeda` (`R$ 1.000`)
 * normalizado para espaço comum — do contrário toda asserção de moeda falharia por um
 * caractere invisível.
 */
function textoDe(no: Element | null): string {
  return (no?.textContent ?? '').replace(/ /g, ' ');
}

/* ------------------------------------------------------------------ */
/* Fixtures — números do motor, nunca inventados pela tela             */
/* ------------------------------------------------------------------ */

const PD: ProbabilidadeDeDefault = {
  pd6m: 0.102,
  pd12m: 0.171,
  pd24m: 0.339,
  metodo: 'Curva logística sobre o score, calibrada por faixa de rating.',
};

const RJ: RiscoRJ = {
  probabilidade12m: 0.225,
  eventoJaOcorrido: false,
  rjIndex: 55,
  rjIndexEfetivo: 55,
  elegivel: true,
  sinais: [{ rotulo: '4 credores distintos executando', pontos: 18 }],
};

const RECOMENDACAO: Recomendacao = {
  codigo: 'APROVAR_COM_RESTRICOES',
  rotulo: 'Aprovar com restrições',
  prazoReavaliacaoDias: 30,
  acoes: [
    { id: 'a1', rotulo: 'Reduzir limite de R$ 5,0 mi para R$ 3,5 mi', prioridade: 1 },
    { id: 'a2', rotulo: 'Exigir garantia adicional de R$ 1,48 mi', prioridade: 2 },
  ],
  aviso: AVISO_DECISAO_HUMANA,
};

const EXPOSICAO: ExposicaoCalculada = {
  exposicaoTotal: 14_200_000,
  limiteAprovado: 16_000_000,
  limiteUtilizadoPct: 0.8875,
  aVencer90d: 4_100_000,
  emAtraso: 230_000,
  porTipoOperacao: { VENDA_A_PRAZO: 9_000_000, BARTER: 4_200_000, CPR: 1_000_000 },
  valorExtraconcursal: 5_396_000,
  valorConcursal: 4_686_000,
  coberturaExtraconcursal: 0.38,
  coberturaTotal: 0.71,
  exposicaoProtegida: 10_082_000,
  exposicaoEmRisco: 4_118_000,
  exposicaoEmRiscoEmRJ: 8_804_000,
};

const AVALIACAO: AvaliacaoDeRisco = {
  clienteId: 'vale-do-araguaia',
  dataReferencia: '2026-09-12',
  scoreCalculado: 604,
  ratingCalculado: 'C',
  ratingFinal: 'D',
  vetosAtivos: [
    {
      id: 'VETO_EMBARGO_GARANTIA',
      rotulo: 'Embargo do IBAMA sobre imóvel oferecido em garantia',
      efeito: 'FORCA_D',
      justificativa:
        'Garantia juridicamente comprometida: bem embargado tem excussão inviabilizada.',
      evidenciaIds: ['ev-ibama-1'],
    },
  ],
  dimensoes: [],
  pd: PD,
  riscoRJ: RJ,
  stayPeriod: null,
  exposicao: EXPOSICAO,
  tendencia: 'deterioracao_acelerada',
  redFlags: [],
  recomendacao: RECOMENDACAO,
  evidencias: [],
  auditoria: { somaImpactos: 604, scoreReconstruido: 604, diferenca: 0 },
};

const NARRATIVA_AGUARDANDO: Narrativa = {
  texto: '',
  estado: 'aguardando',
  origem: 'deterministico',
  tentarNovamente: () => {},
};

/* ------------------------------------------------------------------ */

describe('Exigência 1 — veto nunca esconde o score calculado', () => {
  it('exibe Score calculado e Classificação final lado a lado, com o motivo nomeado', () => {
    const { container } = render(
      <CardDeScore avaliacao={AVALIACAO} variacao={null} aoVerEvidencia={() => {}} />,
    );
    const par = container.querySelector('[data-teste="par-veto"]');
    expect(par).not.toBeNull();

    const texto = textoDe(par);
    expect(texto).toContain('Score calculado');
    expect(texto).toContain('Classificação final');
    // O número calculado continua em tela mesmo com o veto forçando D.
    expect(texto).toContain('604');

    // O motivo é nomeado, não genérico.
    expect(container.textContent).toContain(
      'Embargo do IBAMA sobre imóvel oferecido em garantia',
    );
  });
});

describe('Exigência 2 — risco de RJ é indicador separado da PD', () => {
  it('declara a escala própria e não repete os números da PD', () => {
    const { container } = render(<CardDeRiscoRj risco={RJ} />);
    const texto = textoDe(container);

    expect(texto).toContain('Escala própria');
    expect(texto).toContain('22,5%');
    expect(texto).toContain('55/100');

    // Nenhum valor de PD aparece no card de RJ: escalas diferentes, cards diferentes.
    expect(texto).not.toContain('10,2%');
    expect(texto).not.toContain('17,1%');
    expect(texto).not.toContain('33,9%');
  });

  it('o card de PD não menciona recuperação judicial', () => {
    const { container } = render(<CardDePd pd={PD} />);
    const texto = textoDe(container);
    expect(texto).toContain('17,1%');
    expect(texto).not.toContain('Risco de RJ');
  });

  it('inelegibilidade legal substitui a probabilidade, sem virar "risco baixo"', () => {
    const { container } = render(
      <CardDeRiscoRj
        risco={{
          ...RJ,
          elegivel: false,
          motivoInelegibilidade:
            'Produtor rural pessoa física sem comprovação de 2 anos de atividade (Lei 14.112/2020).',
        }}
      />,
    );
    const texto = textoDe(container);
    expect(texto).toContain('Não elegível a RJ');
    expect(texto).toContain('Lei 14.112/2020');
    expect(texto).toContain('inelegibilidade legal');
  });
});

describe('Exigência 3 — garantias separadas e exposição em risco em RJ', () => {
  const fatos = { garantias: [], operacoes: [] } as unknown as FatosDoCliente;

  it('separa extraconcursal de concursal, sem soma única', () => {
    const { container } = render(<BlocoExposicao exposicao={EXPOSICAO} fatos={fatos} />);
    const texto = textoDe(container);
    expect(texto).toContain('Extraconcursal');
    expect(texto).toContain('Concursal');
    expect(texto).toContain('R$ 5.396.000');
    expect(texto).toContain('R$ 4.686.000');
  });

  it('destaca em caixa própria o que se perde de proteção em cenário de RJ', () => {
    const { container } = render(<BlocoExposicao exposicao={EXPOSICAO} fatos={fatos} />);
    const caixa = container.querySelector('[data-teste="exposicao-em-risco-em-rj"]');
    expect(caixa).not.toBeNull();
    const texto = textoDe(caixa);
    expect(texto).toContain('R$ 8.804.000');
    expect(texto).toContain('62%');
    expect(texto).toContain(
      'O penhor entra no plano de recuperação com deságio; a alienação fiduciária, não.',
    );
  });
});

describe('Exigência 4 — aviso de decisão humana não dispensável', () => {
  it('acompanha toda recomendação e não tem controle de fechar', () => {
    const { container } = render(
      <CardDeRecomendacao recomendacao={RECOMENDACAO} narrativa={NARRATIVA_AGUARDANDO} />,
    );
    const aviso = container.querySelector('[data-teste="aviso-decisao-humana"]');
    expect(aviso).not.toBeNull();
    expect(aviso?.textContent).toContain(AVISO_DECISAO_HUMANA);
    expect(aviso?.querySelector('button')).toBeNull();
  });
});

describe('Exigência 5 — nenhum número espera o LLM', () => {
  it('as ações e o prazo aparecem enquanto a justificativa ainda está em skeleton', () => {
    render(
      <CardDeRecomendacao recomendacao={RECOMENDACAO} narrativa={NARRATIVA_AGUARDANDO} />,
    );
    expect(screen.getByText('Aprovar com restrições')).toBeTruthy();
    expect(screen.getByText(/Reduzir limite de R\$ 5,0 mi/)).toBeTruthy();
    expect(screen.getByText(/Reavaliar em 30 dias/)).toBeTruthy();
  });

  it('a falha total do stream degrada só a prosa, não os números', () => {
    const { container } = render(
      <CardDeRecomendacao
        recomendacao={RECOMENDACAO}
        narrativa={{ ...NARRATIVA_AGUARDANDO, estado: 'erro' }}
      />,
    );
    expect(container.textContent).toContain('Aprovar com restrições');
    expect(container.textContent).toContain('Exigir garantia adicional de R$ 1,48 mi');
  });
});

describe('Stay Period — o que a Krill Tech pode e não pode hoje', () => {
  const STAY: StayPeriod = {
    ativo: true,
    dataDeferimento: '2026-09-04',
    diasDecorridos: 8,
    diasRestantes: 172,
    bloqueios: ['Executar garantias concursais', 'Protestar títulos'],
    permitido: ['Excutir alienação fiduciária (extraconcursal)'],
  };

  it('renderiza literalmente as listas do motor, sem inventar item', () => {
    const { container } = render(<PainelStayPeriod stayPeriod={STAY} />);
    const texto = textoDe(container);
    expect(texto).toContain('A Krill Tech NÃO pode');
    expect(texto).toContain('Executar garantias concursais');
    expect(texto).toContain('A Krill Tech ainda pode');
    expect(texto).toContain('Excutir alienação fiduciária (extraconcursal)');
    expect(texto).toContain('172 dias restantes');
  });

  it('não renderiza nada quando o Stay Period não está ativo', () => {
    const { container } = render(
      <PainelStayPeriod stayPeriod={{ ...STAY, ativo: false }} />,
    );
    expect(container.textContent).toBe('');
  });
});
