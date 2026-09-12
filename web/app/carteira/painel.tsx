'use client';

/**
 * `/carteira` — onde está o risco da carteira (`03-ux-e-telas.md` §2).
 *
 * Tela de abertura da aplicação e do pitch: precisa ser legível sem rolagem em 1440×900 e
 * responder, em segundos, "onde está o risco da minha carteira agora?".
 *
 * Ordem fixa: faixa de atenção imediata → indicadores → matriz de risco e concentração → tabela
 * "onde está o dinheiro em risco". Cada bloco é clicável e leva a `/clientes` com o filtro já
 * aplicado (contrato de drill-down, §2.7); nenhum abre modal.
 *
 * **Hierarquia**: um único elemento lidera a página — a exposição em risco em cenário de RJ, em
 * `type-score-xl`. Tudo o mais é satélite. Por isso o card quase desapareceu daqui: a única
 * superfície elevada que resta é a da tabela, onde a borda separa a grade de dados do resto. O
 * agrupamento das demais seções é feito por espaço, régua de 1px e proximidade. As colunas usam
 * `items-start`: cada bloco tem a altura do seu conteúdo, nunca a do vizinho mais alto.
 */

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  BlocoDeConcentracao,
  DinheiroEmRisco,
  EsqueletoDaCarteira,
  EstadoDeFalha,
  ExposicaoPorRating,
  FaixaDeAtencao,
  KpisDaCarteira,
  MatrizDeRisco,
} from '@/components/carteira';
import { Card, EmptyState, SectionHeader, Termo, Tooltip } from '@/components/ui';
import { obterCarteira } from '@/lib/api';
import { assinarSessao, sessaoParaApi } from '@/lib/sessao';
import type { ResumoCarteira } from '@/types';

export function PainelDaCarteira() {
  const router = useRouter();
  const [resumo, setResumo] = useState<ResumoCarteira | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  const [tentativa, setTentativa] = useState(0);
  const [versaoSessao, setVersaoSessao] = useState(0);

  useEffect(() => assinarSessao(() => setVersaoSessao((v) => v + 1)), []);

  useEffect(() => {
    let vivo = true;
    obterCarteira(sessaoParaApi())
      .then((dados) => {
        if (!vivo) return;
        setResumo(dados);
        setErro(null);
      })
      .catch((causa: unknown) => {
        if (vivo) {
          setResumo(null);
          setErro(causa);
        }
      });
    return () => {
      vivo = false;
    };
  }, [tentativa, versaoSessao]);

  if (erro) {
    return (
      <EstadoDeFalha
        erro={erro}
        contexto="a carteira"
        aoTentarNovamente={() => setTentativa((n) => n + 1)}
      />
    );
  }

  if (resumo === null) return <EsqueletoDaCarteira />;

  const semClientes = resumo.totalClientes === 0;

  return (
    <div className="flex flex-col gap-8">
      <FaixaDeAtencao
        cartoes={resumo.atencaoImediata ?? []}
        ultimaVarredura={resumo.ultimaVarredura}
      />

      <KpisDaCarteira resumo={resumo} />

      {semClientes ? (
        <Card>
          <EmptyState
            titulo="Carteira sem clientes"
            descricao="Nenhum cliente carregado. Verifique se o serviço de dados está ativo."
            acao={{ rotulo: 'Recarregar', aoClicar: () => setTentativa((n) => n + 1) }}
          />
        </Card>
      ) : (
        <>
          <div className="grid items-start gap-x-10 gap-y-8 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
            <section className="flex flex-col gap-3">
              <SectionHeader
                nivel={3}
                titulo="Matriz de risco da carteira"
                descricao="Quais clientes combinam alta probabilidade de calote com muito dinheiro desprotegido?"
                acoes={
                  <Tooltip conteudo="Eixo horizontal: probabilidade de inadimplência em 12 meses. Eixo vertical: exposição que ficaria desprotegida se o cliente pedisse recuperação judicial amanhã.">
                    <span
                      tabIndex={0}
                      role="note"
                      aria-label="Como ler a matriz de risco"
                      className="type-caption cursor-default rounded-sm"
                    >
                      ?
                    </span>
                  </Tooltip>
                }
              />
              {resumo.matrizDeRisco.length === 0 ? (
                <EmptyState
                  compacto
                  titulo="Sem pontos para plotar"
                  descricao="Quais clientes combinam alta probabilidade de calote com muito dinheiro desprotegido? A resposta aparece quando o motor devolver as avaliações."
                />
              ) : (
                <MatrizDeRisco pontos={resumo.matrizDeRisco} />
              )}
            </section>

            <div className="flex flex-col gap-7 lg:border-l lg:border-line-subtle lg:pl-10">
              <section className="flex flex-col gap-3">
                <SectionHeader
                  nivel={3}
                  titulo="Exposição por rating"
                  descricao="Quanto do meu dinheiro está em cada faixa de risco. Não quantos clientes: quanto dinheiro."
                />
                <ExposicaoPorRating
                  porRating={resumo.clientesPorRating}
                  aoAbrirRating={(rating) => router.push(`/clientes?rating=${rating}`)}
                />
              </section>

              <BlocoDeConcentracao
                porCultura={resumo.concentracaoPorCultura ?? []}
                porUf={resumo.concentracaoPorUf ?? []}
                aoAbrirCultura={(cultura) =>
                  router.push(`/clientes?cultura=${encodeURIComponent(cultura)}`)
                }
                aoAbrirUf={(uf) => router.push(`/clientes?uf=${encodeURIComponent(uf)}`)}
              />
            </div>
          </div>

          <section className="flex flex-col gap-3">
            <SectionHeader
              nivel={3}
              titulo="Onde está o dinheiro em risco"
              descricao="As oito maiores exposições desprotegidas em cenário de recuperação judicial."
              meta={
                <span className="type-caption">
                  <Termo sigla="EXTRACONCURSAL" /> já descontada
                </span>
              }
            />
            {/* Única superfície elevada da tela: aqui a borda separa a grade de dados do resto. */}
            <Card semPadding className="flex flex-col">
              <DinheiroEmRisco linhas={resumo.dinheiroEmRisco ?? []} />
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
