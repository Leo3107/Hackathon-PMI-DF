'use client';

/**
 * Os dois desfechos que **não** são o pipeline: documento já pertencente à carteira (§6.2) e
 * documento sem registro nas bases simuladas (§6.5).
 *
 * O segundo é deliberadamente informativo: transforma um caminho de erro em demonstração de
 * conhecimento de domínio. Por isso não usa `ErrorState` — não é falha, é resposta.
 */

import { Ban, ArrowRight, RotateCcw } from 'lucide-react';

import { Button, Card, SectionHeader } from '@/components/ui';
import { formatarDocumento } from '@/lib/format';
import type { Cliente } from '@/types';

const CENARIOS = [
  {
    titulo: 'CNPJ recém-constituído, sem histórico',
    detalhe: 'Exige garantia reforçada e limite inicial reduzido.',
  },
  {
    titulo: 'Documento inexistente ou digitado com erro',
    detalhe: 'Devolver ao comercial para conferência do cadastro.',
  },
  {
    titulo: 'Pessoa física sem inscrição estadual',
    detalhe: 'Avaliar elegibilidade à venda a prazo antes de prosseguir.',
  },
];

export interface NaoEncontradoProps {
  documento: string;
  aoTentarOutro: () => void;
  aoVerPerfis: () => void;
}

export function NaoEncontrado({ documento, aoTentarOutro, aoVerPerfis }: NaoEncontradoProps) {
  return (
    <Card destaque="b" className="mx-auto flex w-full max-w-[720px] flex-col gap-4" role="status">
      <div className="flex items-start gap-3">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-md bg-surface-input">
          <Ban size={20} strokeWidth={1.75} className="text-risk-b" aria-hidden="true" />
        </span>
        <div className="flex flex-col gap-1">
          <p className="type-eyebrow text-risk-b">Documento sem registro nas bases simuladas</p>
          <p className="type-body max-w-[68ch] text-fg-secondary">
            <span className="tnum text-fg-primary">
              {formatarDocumento(documento, { mascarar: false })}
            </span>{' '}
            tem dígito verificador válido, mas não corresponde a nenhum perfil do conjunto de dados
            demonstrativo do Lastro.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <p className="type-label">
          Em produção, este resultado significaria um de três cenários — e cada um tem tratamento
          diferente na política de crédito:
        </p>
        <ul className="flex flex-col gap-1.5">
          {CENARIOS.map((cenario) => (
            <li key={cenario.titulo} className="type-caption flex gap-2">
              <span aria-hidden="true" className="text-fg-tertiary">
                •
              </span>
              <span>
                <span className="text-fg-primary">{cenario.titulo}</span> — {cenario.detalhe}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button variante="primario" iconeEsquerda={RotateCcw} onClick={aoTentarOutro}>
          Tentar outro documento
        </Button>
        <Button variante="secundario" onClick={aoVerPerfis}>
          Ver perfis demonstrativos
        </Button>
      </div>
    </Card>
  );
}

export interface JaNaCarteiraProps {
  cliente: Cliente;
  aoAbrirCliente: () => void;
  aoReanalisar: () => void;
  aoVoltar: () => void;
}

export function JaNaCarteira({
  cliente,
  aoAbrirCliente,
  aoReanalisar,
  aoVoltar,
}: JaNaCarteiraProps) {
  return (
    <Card destaque="acento" className="mx-auto flex w-full max-w-[720px] flex-col gap-4">
      <SectionHeader
        titulo="Documento já pertence a um cliente da carteira"
        descricao="A due diligence completa é para prospects. Este documento já tem histórico, exposição e avaliação no Lastro."
      />
      <p className="type-body text-fg-primary">
        {cliente.razaoSocial}
        <span className="type-caption block text-fg-secondary">
          {formatarDocumento(cliente.documento, { mascarar: false })} · {cliente.municipio}/
          {cliente.uf}
        </span>
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <Button variante="primario" iconeDireita={ArrowRight} onClick={aoAbrirCliente}>
          Abrir cliente
        </Button>
        <Button variante="secundario" onClick={aoReanalisar}>
          Reanalisar mesmo assim
        </Button>
        <Button variante="fantasma" onClick={aoVoltar}>
          Consultar outro documento
        </Button>
      </div>
    </Card>
  );
}
