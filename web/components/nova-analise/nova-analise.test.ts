import { describe, expect, it } from 'vitest';

import type { AvaliacaoDeRisco, ClienteAvaliado, RespostaDueDiligence } from '@/types';

import {
  analisarDocumento,
  cnpjValido,
  cpfValido,
  mascararDocumento,
  mensagemDoDocumento,
} from './documento';
import { perfilDoRating, perfisDemonstrativos } from './perfis';
import {
  ESTAGIOS,
  INDICE_SCORE,
  PISO_ESTAGIO_MS,
  TETO_ESTAGIO_MS,
  contadorDoEstagio,
  contarEvidencias,
  dadoDisponivel,
  duracaoDeExibicao,
  linhasDoRegistro,
  statusAposRevelar,
} from './pipeline';

/* ------------------------------------------------------------------ */
/* Dígito verificador — a única conta permitida no frontend (§6.2)     */
/* ------------------------------------------------------------------ */

describe('validação de documento', () => {
  it('aceita CPF e CNPJ com dígito verificador correto', () => {
    expect(cpfValido('529.982.247-25')).toBe(true);
    expect(cnpjValido('11.444.777/0001-61')).toBe(true);
  });

  it('recusa dígito verificador incorreto e sequência repetida', () => {
    expect(cpfValido('529.982.247-24')).toBe(false);
    expect(cnpjValido('11.222.333/0001-44')).toBe(false);
    expect(cpfValido('111.111.111-11')).toBe(false);
    expect(cnpjValido('11.111.111/1111-11')).toBe(false);
  });

  it('aplica máscara de CPF até 11 dígitos e de CNPJ a partir do 12º', () => {
    expect(mascararDocumento('5299')).toBe('529.9');
    expect(mascararDocumento('52998224725')).toBe('529.982.247-25');
    expect(mascararDocumento('114447770')).toBe('114.447.770');
    expect(mascararDocumento('114447770000')).toBe('11.444.777/0000');
    expect(mascararDocumento('11444777000161')).toBe('11.444.777/0001-61');
    expect(mascararDocumento('114447770001612222')).toBe('11.444.777/0001-61');
  });

  it('percorre os estados da tabela de §6.2', () => {
    expect(analisarDocumento('')).toEqual({ situacao: 'vazio' });
    expect(analisarDocumento('529.982').situacao).toBe('incompleto');
    expect(analisarDocumento('529.982.247-24').situacao).toBe('invalido');

    const valido = analisarDocumento('11.444.777/0001-61');
    expect(valido.situacao).toBe('valido');
    expect(mensagemDoDocumento(valido)).toBe('CNPJ válido');
    expect(mensagemDoDocumento(analisarDocumento('529.982.247-24'))).toContain(
      'Dígito verificador inválido',
    );
  });
});

/* ------------------------------------------------------------------ */
/* Honestidade do pipeline (§6.4)                                      */
/* ------------------------------------------------------------------ */

const AVALIACAO = {
  clienteId: 'prospect-1',
  dataReferencia: '2026-09-12',
  scoreCalculado: 712,
  ratingCalculado: 'A',
  ratingFinal: 'A',
  vetosAtivos: [],
  dimensoes: [
    { id: 'cadastral' },
    { id: 'juridico' },
    { id: 'fiscal' },
    { id: 'ambiental' },
    { id: 'agroclimatico' },
    { id: 'comportamental' },
    { id: 'garantias' },
  ],
  evidencias: [
    { id: 'e1', fonte: 'RECEITA_FEDERAL' },
    { id: 'e2', fonte: 'REDESIM' },
    { id: 'e3', fonte: 'DATAJUD_CNJ' },
  ],
  auditoria: { somaImpactos: 0, scoreReconstruido: 712, diferenca: 0 },
} as unknown as AvaliacaoDeRisco;

function resposta(parcial: Partial<RespostaDueDiligence> = {}): RespostaDueDiligence {
  return {
    encontrado: true,
    documento: '11444777000161',
    avaliacao: AVALIACAO,
    estagios: ESTAGIOS.map((estagio) => ({
      estagio: estagio.id,
      rotulo: estagio.rotulo,
      status: 'ok' as const,
      achados: [`${estagio.rotulo} · achado`],
      duracaoMs: 300,
    })),
    ...parcial,
  } as RespostaDueDiligence;
}

describe('honestidade do pipeline', () => {
  it('não conclui estágio nenhum enquanto a resposta do motor não chega', () => {
    for (const definicao of ESTAGIOS) {
      expect(dadoDisponivel(definicao, null)).toBe(false);
    }
  });

  it('conclui o estágio apenas quando a dimensão correspondente existe na avaliação', () => {
    const semAmbiental = resposta({
      avaliacao: {
        ...AVALIACAO,
        dimensoes: AVALIACAO.dimensoes.filter((dimensao) => dimensao.id !== 'ambiental'),
      },
    });
    const ambiental = ESTAGIOS.find((estagio) => estagio.id === 'AMBIENTAL')!;
    const cadastral = ESTAGIOS.find((estagio) => estagio.id === 'CADASTRAL')!;

    expect(dadoDisponivel(ambiental, semAmbiental)).toBe(false);
    expect(statusAposRevelar(ambiental, semAmbiental)).toBe('falha');
    expect(dadoDisponivel(cadastral, semAmbiental)).toBe(true);
  });

  it('não conclui o estágio quando o motor marcou aquele estágio como falho', () => {
    const comFalha = resposta({
      estagios: resposta().estagios.map((estagio) =>
        estagio.estagio === 'FISCAL' ? { ...estagio, status: 'falha' as const } : estagio,
      ),
    });
    const fiscal = ESTAGIOS.find((estagio) => estagio.id === 'FISCAL')!;
    expect(dadoDisponivel(fiscal, comFalha)).toBe(false);
  });

  it('só conclui SCORE quando a soma das contribuições fecha (I2)', () => {
    const score = ESTAGIOS[INDICE_SCORE];
    expect(dadoDisponivel(score, resposta())).toBe(true);

    const naoFecha = resposta({
      avaliacao: {
        ...AVALIACAO,
        auditoria: { somaImpactos: 0, scoreReconstruido: 700, diferenca: 12 },
      } as AvaliacaoDeRisco,
    });
    expect(dadoDisponivel(score, naoFecha)).toBe(false);
  });

  it('nunca marca RELATORIO como concluído — a narrativa é gerada na página do cliente', () => {
    const relatorio = ESTAGIOS[ESTAGIOS.length - 1];
    expect(relatorio.id).toBe('RELATORIO');
    expect(dadoDisponivel(relatorio, resposta())).toBe(false);
  });

  it('distingue "sem dado" de falha', () => {
    const semRegistro = resposta({
      estagios: resposta().estagios.map((estagio) =>
        estagio.estagio === 'AMBIENTAL'
          ? { ...estagio, achados: ['Nenhum registro encontrado'] }
          : estagio,
      ),
    });
    const ambiental = ESTAGIOS.find((estagio) => estagio.id === 'AMBIENTAL')!;
    expect(statusAposRevelar(ambiental, semRegistro)).toBe('sem_dado');
  });

  it('mantém a duração de exibição entre o piso de 280ms e o teto de 700ms', () => {
    expect(duracaoDeExibicao(0)).toBe(PISO_ESTAGIO_MS);
    expect(duracaoDeExibicao(undefined)).toBe(PISO_ESTAGIO_MS);
    expect(duracaoDeExibicao(400)).toBe(400);
    expect(duracaoDeExibicao(9_000)).toBe(TETO_ESTAGIO_MS);
  });

  it('conta as evidências das fontes do estágio e escreve o contador em texto', () => {
    const cadastral = ESTAGIOS.find((estagio) => estagio.id === 'CADASTRAL')!;
    expect(contarEvidencias(cadastral, AVALIACAO)).toBe(2);
    expect(contadorDoEstagio(cadastral, 'concluido', resposta())).toBe('2 documentos');
    expect(contadorDoEstagio(cadastral, 'pendente', resposta())).toBe('—');
    expect(contadorDoEstagio(cadastral, 'consultando', resposta())).toBe('consultando…');
  });

  it('escreve "Nenhum registro encontrado" no registro quando a fonte não retorna nada', () => {
    const semAchados = resposta({
      estagios: resposta().estagios.map((estagio) =>
        estagio.estagio === 'AMBIENTAL' ? { ...estagio, achados: [] } : estagio,
      ),
    });
    const ambiental = ESTAGIOS.find((estagio) => estagio.id === 'AMBIENTAL')!;
    const linhas = linhasDoRegistro(ambiental, semAchados, new Date('2026-09-12T14:32:07'));
    expect(linhas).toHaveLength(1);
    expect(linhas[0].texto).toBe('Nenhum registro encontrado');
    expect(linhas[0].estagio).toBe('AMBIENTAL');
  });
});

/* ------------------------------------------------------------------ */
/* Perfis demonstrativos (§6.7)                                        */
/* ------------------------------------------------------------------ */

function linha(id: string, rating: 'A' | 'B' | 'C' | 'D', origem: 'CARTEIRA' | 'PROSPECT', score: number) {
  return {
    cliente: { id, razaoSocial: id, documento: '11444777000161', origem },
    avaliacao: { ratingFinal: rating, scoreCalculado: score },
    alertasNaoLidos: 0,
  } as unknown as ClienteAvaliado;
}

describe('perfis demonstrativos', () => {
  it('classifica a faixa de crédito pelo rating final do motor', () => {
    expect(perfilDoRating('A')).toBe('aprovavel');
    expect(perfilDoRating('B')).toBe('aprovavel');
    expect(perfilDoRating('C')).toBe('limitrofe');
    expect(perfilDoRating('D')).toBe('recusavel');
  });

  it('prefere prospects e traz um representante por faixa', () => {
    const perfis = perfisDemonstrativos([
      linha('carteira-a', 'A', 'CARTEIRA', 800),
      linha('prospect-a', 'A', 'PROSPECT', 720),
      linha('prospect-c', 'C', 'PROSPECT', 520),
      linha('prospect-d', 'D', 'PROSPECT', 240),
    ]);

    expect(perfis.map((perfil) => perfil.linha.cliente.id)).toEqual([
      'prospect-a',
      'prospect-c',
      'prospect-d',
    ]);
    expect(perfis.every((perfil) => perfil.naCarteira === false)).toBe(true);
  });

  it('degrada para a carteira e sinaliza a origem quando não há prospect', () => {
    const perfis = perfisDemonstrativos([
      linha('carteira-b', 'B', 'CARTEIRA', 690),
      linha('carteira-d', 'D', 'CARTEIRA', 180),
    ]);
    expect(perfis).toHaveLength(2);
    expect(perfis.every((perfil) => perfil.naCarteira)).toBe(true);
  });

  it('devolve lista vazia sem dados, em vez de inventar documento', () => {
    expect(perfisDemonstrativos([])).toEqual([]);
  });
});
