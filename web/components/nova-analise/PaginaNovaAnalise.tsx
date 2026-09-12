'use client';

/**
 * `/nova-analise` — due diligence de novo cliente (`03-ux-e-telas.md` §6).
 *
 * Três etapas na mesma rota, por transição de estado: `entrada` → `pipeline` → resultado. O
 * resultado não é uma quarta tela: ao concluir o estágio de score, a rota navega para
 * `/clientes/[id]`, que já **é** o relatório (§6.6).
 */

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { listarClientes } from '@/lib/api';
import { sessaoParaApi } from '@/lib/sessao';
import type { ClienteAvaliado } from '@/types';

import { Entrada } from './Entrada';
import { JaNaCarteira, NaoEncontrado } from './Desvios';
import { PainelDoPipeline } from './PainelDoPipeline';
import { analisarDocumento, mascararDocumento } from './documento';
import { perfisDemonstrativos } from './perfis';
import { useAnalise } from './usar-analise';

export function PaginaNovaAnalise() {
  const router = useRouter();
  const [valor, setValor] = useState('');
  const [linhas, setLinhas] = useState<ClienteAvaliado[] | null>(null);

  const irParaCliente = useCallback(
    (clienteId: string) => router.push(`/clientes/${clienteId}`),
    [router],
  );

  const analise = useAnalise(irParaCliente);
  const estado = useMemo(() => analisarDocumento(valor), [valor]);

  // A lista alimenta apenas os perfis demonstrativos. Falha aqui não derruba a tela: o campo
  // de documento continua operável, e o painel de perfis explica a ausência.
  useEffect(() => {
    let vivo = true;
    listarClientes(sessaoParaApi())
      .then((dados) => {
        if (vivo) setLinhas(dados);
      })
      .catch(() => {
        if (vivo) setLinhas([]);
      });
    return () => {
      vivo = false;
    };
  }, []);

  const perfis = useMemo(() => perfisDemonstrativos(linhas ?? []), [linhas]);

  const escolherPerfil = useCallback(
    (documento: string) => {
      setValor(mascararDocumento(documento));
      analise.consultar(documento);
    },
    [analise],
  );

  if (analise.etapa === 'consultando' || analise.etapa === 'pipeline') {
    return (
      <PainelDoPipeline
        documento={analise.documento}
        cliente={analise.cliente}
        estagios={analise.estagios}
        registro={analise.registro}
        erro={analise.erro}
        aoCancelar={analise.cancelar}
        aoTentarNovamente={analise.tentarNovamente}
      />
    );
  }

  if (analise.etapa === 'nao_encontrado') {
    return (
      <NaoEncontrado
        documento={analise.documento}
        aoTentarOutro={() => {
          setValor('');
          analise.voltarParaEntrada();
        }}
        aoVerPerfis={analise.voltarParaEntrada}
      />
    );
  }

  if (analise.etapa === 'ja_na_carteira' && analise.cliente) {
    const cliente = analise.cliente;
    return (
      <JaNaCarteira
        cliente={cliente}
        aoAbrirCliente={() => irParaCliente(cliente.id)}
        aoReanalisar={() => analise.consultar(cliente.documento, { forcarReanalise: true })}
        aoVoltar={() => {
          setValor('');
          analise.voltarParaEntrada();
        }}
      />
    );
  }

  return (
    <Entrada
      valor={valor}
      aoMudar={setValor}
      estado={estado}
      aoConsultar={() => analise.consultar(valor)}
      perfis={perfis}
      carregandoPerfis={linhas === null}
      aoEscolherPerfil={escolherPerfil}
    />
  );
}
