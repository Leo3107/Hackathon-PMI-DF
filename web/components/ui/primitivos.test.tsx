import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { DataTable, type Coluna } from './DataTable';
import { RatingBadge } from './RatingBadge';
import { ScoreGauge } from './ScoreGauge';
import { TrendIndicator } from './TrendIndicator';

afterEach(cleanup);

describe('RatingBadge — veto', () => {
  it('mostra o rating calculado e o final lado a lado, sem esconder nenhum', () => {
    const { container } = render(<RatingBadge rating="D" calculado="B" />);
    const texto = container.textContent ?? '';
    expect(texto).toContain('B');
    expect(texto).toContain('D');
    expect(
      container.querySelector('[aria-label*="Rating calculado B"]'),
    ).not.toBeNull();
  });
});

describe('ScoreGauge — modo veto', () => {
  it('exibe o score calculado e as duas classificações', () => {
    const { container } = render(
      <ScoreGauge
        score={520}
        ratingCalculado="C"
        ratingFinal="D"
        animar={false}
        vetos={[
          {
            id: 'v1',
            rotulo: 'RJ deferida',
            efeito: 'FORCA_D',
            justificativa: 'Recuperação judicial deferida.',
            evidenciaIds: [],
          },
        ]}
      />,
    );

    const texto = container.textContent ?? '';
    // O número calculado nunca é escondido.
    expect(texto).toContain('520');
    // O rótulo do veto é textual, não apenas cor.
    expect(texto).toContain('VETO · RJ DEFERIDA');

    const rotulo = screen.getByRole('img').getAttribute('aria-label') ?? '';
    expect(rotulo).toContain('Score calculado 520');
    expect(rotulo).toContain('rating calculado C');
    expect(rotulo).toContain('Classificação final D');
  });

  it('sem veto, o aria-label traz score, rating e variação', () => {
    render(
      <ScoreGauge
        score={604}
        ratingCalculado="B"
        ratingFinal="B"
        scoreAnterior={712}
        periodoDelta="90d"
        tendencia="deterioracao_acelerada"
        animar={false}
      />,
    );
    const rotulo = screen.getByRole('img').getAttribute('aria-label') ?? '';
    expect(rotulo).toContain('604 de 1000');
    expect(rotulo).toContain('rating B');
    expect(rotulo).toContain('108 pontos');
  });
});

describe('TrendIndicator — redundância de canal', () => {
  it('renderiza cor, rótulo textual e ícone', () => {
    const { container } = render(
      <TrendIndicator tendencia="deteriorando" delta={-42} periodo="90d" />,
    );
    const raiz = container.firstElementChild as HTMLElement;
    expect(raiz.className).toContain('text-risk-c');
    expect(raiz.textContent).toContain('Deteriorando');
    expect(raiz.textContent).toContain('−42');
    expect(raiz.querySelector('svg')).not.toBeNull();
  });
});

interface Linha {
  id: string;
  nome: string;
  exposicao: number;
}

const COLUNAS: Coluna<Linha>[] = [
  { id: 'nome', cabecalho: 'Cliente', celula: (l) => l.nome },
  {
    id: 'exposicao',
    cabecalho: 'Exposição',
    numerica: true,
    ordenavel: true,
    valorOrdenacao: (l) => l.exposicao,
    celula: (l) => l.exposicao,
  },
];

const LINHAS: Linha[] = [
  { id: 'a', nome: 'Alfa', exposicao: 300 },
  { id: 'b', nome: 'Beta', exposicao: 100 },
  { id: 'c', nome: 'Gama', exposicao: 200 },
];

describe('DataTable', () => {
  it('aplica tabular-nums e alinhamento à direita em coluna numérica', () => {
    const { container } = render(
      <DataTable
        aria-label="Clientes"
        colunas={COLUNAS}
        linhas={LINHAS}
        obterId={(l) => l.id}
      />,
    );
    const celula = container.querySelectorAll('tbody tr')[0].querySelectorAll('td')[1];
    expect(celula.className).toContain('tnum');
    expect(celula.className).toContain('text-right');
  });

  it('ordena pela coluna pedida e expõe aria-sort', () => {
    render(
      <DataTable
        aria-label="Clientes"
        colunas={COLUNAS}
        linhas={LINHAS}
        obterId={(l) => l.id}
        ordenacaoInicial={{ colunaId: 'exposicao', direcao: 'asc' }}
      />,
    );
    const primeira = screen.getAllByRole('row')[1];
    expect(primeira.textContent).toContain('Beta');
    expect(screen.getByRole('columnheader', { name: /Exposição/ }).getAttribute('aria-sort')).toBe(
      'ascending',
    );
  });

  it('linhas clicáveis são focáveis pelo teclado', () => {
    const { container } = render(
      <DataTable
        aria-label="Clientes"
        colunas={COLUNAS}
        linhas={LINHAS}
        obterId={(l) => l.id}
        aoClicarLinha={() => undefined}
      />,
    );
    const linhas = container.querySelectorAll('tbody tr[role="button"]');
    expect(linhas.length).toBe(LINHAS.length);
    expect(linhas[0].getAttribute('tabindex')).toBe('0');
  });
});
