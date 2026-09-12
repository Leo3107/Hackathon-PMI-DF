# 05 — Design system

> Sistema visual e catálogo de primitivos do **Lastro**. Vive em `app/globals.css` (tokens),
> `components/ui/` (primitivos), `components/risk/` (compostos de risco), `lib/format.ts`
> (formatadores) e `lib/chart-theme.ts` (Recharts). **Dark-only, design system próprio,
> zero bibliotecas de componentes de terceiros** (`00-decisoes.md` D9). Todo valor abaixo é
> literal: copiar, não interpretar.

Referências: `00-decisoes.md` D3, D9, D11.5–7 · `01-modelo-de-dados.md` (enums `Rating`,
`Severidade`, `Tendencia`, `NaturezaGarantia`) · `02-motor-de-risco.md` §5 (faixas), §8 (veto), §10 (coberturas), §11 (delta)

---

## 0. Princípios (o que o implementador precisa internalizar)

1. **Ferramenta, não vitrine.** O usuário é um analista de crédito que abre isto oito horas por dia.
   Densidade alta, ruído zero, hierarquia tipográfica faz o trabalho que cor e sombra fariam num template.
2. **Cor é semântica ou é neutra.** Verde, âmbar, laranja e vermelho significam risco — sempre e só.
   Ciano-aço significa "a interface" (navegação, foco, ação, marca). Todo o resto é cinza-azulado.
3. **Nenhum estado de risco depende só de cor.** Cor + rótulo textual + ícone, sempre os três (§3).
4. **Números alinham.** `tabular-nums` em toda coluna numérica, valores monetários alinhados à direita.
5. **Superfícies se distinguem por tom, não por sombra.** Uma sombra permitida (§1.6), sem blur grande.
6. **Cantos discretos.** Raio máximo 8px. Nada é "pill" exceto o cursor do `ScoreGauge`.
7. **Movimento só onde comunica** (§9): pipeline da Nova Análise, streaming de prosa, transições de estado.

### Proibições verificáveis em code review

| Proibido | Como detectar |
|---|---|
| Gradientes, exceto o padrão hachurado do veto (§7.7) | `grep -rn "gradient" app components` deve retornar apenas `components/risk/ScoreGauge.tsx` |
| `backdrop-filter` / glassmorphism | `grep -rn "backdrop" app components` retorna vazio |
| Sombras com blur > 8px | `grep -rn "shadow-" ` só pode casar `shadow-raised` e `shadow-overlay` |
| `rounded-xl`, `rounded-2xl`, `rounded-3xl`, `rounded-full` (exceto cursor do gauge e avatar) | grep |
| Emoji em JSX/strings de UI | grep por faixa Unicode `[\u{1F300}-\u{1FAFF}]` em `app components lib` |
| Verde/âmbar/laranja/vermelho fora de `components/risk/` e dos tokens `--color-risk-*` | grep por `#3DD68C`, `#F2C037`, `#F28C3B`, `#F47474` e por `risk-` fora de `components/risk/` |
| Importar `@radix-ui`, `shadcn`, `@headlessui`, `@mui`, `antd`, `chakra` | `package.json` |
| Cores hexadecimais literais em componentes (fora de `globals.css` e `lib/chart-theme.ts`) | grep `#[0-9A-Fa-f]{6}` em `components/` |

---

## 1. Tokens (`app/globals.css`)

Bloco completo, pronto para colar. Tailwind v4 gera as utilities a partir do `@theme`
(`bg-surface-card`, `text-fg-secondary`, `border-line-default`, `text-risk-a`, etc.).

```css
@import "tailwindcss";

@theme {
  /* ------------------------------------------------------------------ */
  /* 1.1 Superfícies — escala fria, quase-preta, nunca #000               */
  /* ------------------------------------------------------------------ */
  --color-surface-page:     #0B0F14;  /* fundo da aplicação                         */
  --color-surface-card:     #11161D;  /* card padrão                                */
  --color-surface-raised:   #171E27;  /* drawer, modal, popover, tooltip, dropdown  */
  --color-surface-input:    #0D1218;  /* campos de formulário (mais fundo que card) */
  --color-surface-hover:    #1B232E;  /* hover de linha/item                        */
  --color-surface-sunken:   #080B0F;  /* trilhos de progresso, código, área de log  */
  --color-surface-overlay:  rgb(4 6 9 / 0.64); /* scrim atrás de modal/drawer       */

  /* ------------------------------------------------------------------ */
  /* 1.2 Bordas                                                          */
  /* ------------------------------------------------------------------ */
  --color-line-subtle:   #1E2833;  /* divisórias internas, grid de gráfico          */
  --color-line-default:  #283442;  /* borda de card e input                          */
  --color-line-strong:   #3A4756;  /* borda de hover/ativo, cabeçalho de tabela      */

  /* ------------------------------------------------------------------ */
  /* 1.3 Texto                                                           */
  /* ------------------------------------------------------------------ */
  --color-fg-primary:    #E6EBF0;  /* 16,0:1 sobre page · 15,1:1 sobre card          */
  --color-fg-secondary:  #A3AEBB;  /* 8,5:1 · 8,1:1                                  */
  --color-fg-tertiary:   #7B889A;  /* 5,3:1 · 5,0:1 · 4,7:1 sobre raised             */
  --color-fg-disabled:   #66727F;  /* 3,7:1 — isento (WCAG 1.4.3, componente inativo)*/
  --color-fg-inverse:    #0B0F14;  /* texto sobre botão de acento e badges sólidos   */

  /* ------------------------------------------------------------------ */
  /* 1.4 Acento de marca — azul-aço / ciano técnico                       */
  /*     Reservado a: navegação ativa, foco, links, ação primária, marca */
  /* ------------------------------------------------------------------ */
  --color-accent-300:  #7CCDF0;  /* hover de link, texto sobre tint          10,3:1 */
  --color-accent-400:  #4DB8E5;  /* texto/ícone de acento, link, foco         8,1:1 */
  --color-accent-500:  #2FA4D6;  /* fundo de botão primário (texto inverse)   6,8:1 */
  --color-accent-600:  #1F86B3;  /* botão primário :active (texto inverse)    4,7:1 */
  --color-accent-tint: #192D39;  /* = accent-400 @14% sobre card. Linha selecionada, nav ativa */
  --color-accent-line: #2A5A73;  /* borda de item ativo/selecionado                 */

  /* ------------------------------------------------------------------ */
  /* 1.5 Semântica de risco — EXCLUSIVA. Ver §2.                          */
  /*     Tints são pré-misturados a 14% sobre surface-card (opacos):     */
  /*     contraste determinístico, sem depender da superfície abaixo.    */
  /* ------------------------------------------------------------------ */
  --color-risk-a:        #3DD68C;  /* A · Baixo risco  · melhorando                 */
  --color-risk-a-tint:   #17312D;
  --color-risk-a-line:   #23694A;

  --color-risk-b:        #F2C037;  /* B · Risco moderado · severidade MÉDIA         */
  --color-risk-b-tint:   #312E21;
  --color-risk-b-line:   #6E5A22;

  --color-risk-c:        #F28C3B;  /* C · Risco elevado · ALTA · deteriorando       */
  --color-risk-c-tint:   #312721;
  --color-risk-c-line:   #6E4623;

  --color-risk-d:        #F47474;  /* D · Risco crítico · CRÍTICA · deter. acelerada · veto */
  --color-risk-d-tint:   #312329;
  --color-risk-d-line:   #6F3A3E;

  --color-risk-neutral:      #A3AEBB;  /* BAIXA/informativa · estável (= fg-secondary) */
  --color-risk-neutral-tint: #252B33;
  --color-risk-neutral-line: #3A4756;

  /* ------------------------------------------------------------------ */
  /* 1.6 Paleta categórica — séries SEM significado de risco (§8.4)     */
  /* ------------------------------------------------------------------ */
  --color-cat-1: #4DB8E5;  /* ciano (acento)   8,1:1 sobre card */
  --color-cat-2: #7D8CF0;  /* índigo           6,0:1 */
  --color-cat-3: #A48BF2;  /* violeta          6,5:1 */
  --color-cat-4: #D98BC7;  /* orquídea         7,3:1 */
  --color-cat-5: #8FA3B8;  /* ardósia          7,0:1 */
  --color-cat-6: #C9B79C;  /* areia            9,3:1 — último recurso */

  /* ------------------------------------------------------------------ */
  /* 1.7 Tipografia (famílias vêm do next/font, ver §4.1)                */
  /* ------------------------------------------------------------------ */
  --font-sans: var(--font-inter), ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
  --font-mono: var(--font-jetbrains-mono), ui-monospace, "Cascadia Mono", Consolas, monospace;

  /* ------------------------------------------------------------------ */
  /* 1.8 Raios — teto 8px                                                 */
  /* ------------------------------------------------------------------ */
  --radius-xs: 2px;   /* barras, ticks                        */
  --radius-sm: 4px;   /* badge, chip, input, botão            */
  --radius-md: 6px;   /* card, tile, tooltip                  */
  --radius-lg: 8px;   /* modal, drawer, gauge container       */

  /* ------------------------------------------------------------------ */
  /* 1.9 Sombras — apenas duas, sem blur difuso                           */
  /* ------------------------------------------------------------------ */
  --shadow-raised:  0 0 0 1px var(--color-line-default), 0 1px 2px 0 rgb(0 0 0 / 0.40);
  --shadow-overlay: 0 0 0 1px var(--color-line-strong), 0 8px 8px -4px rgb(0 0 0 / 0.55);

  /* ------------------------------------------------------------------ */
  /* 1.10 Movimento (§9)                                                  */
  /* ------------------------------------------------------------------ */
  --duration-fast:  120ms;  /* hover, foco, tooltip                */
  --duration-base:  200ms;  /* drawer, modal, chips, expand        */
  --duration-slow:  320ms;  /* pipeline steps, troca de rota       */
  --duration-gauge: 600ms;  /* preenchimento do gauge              */
  --ease-standard:  cubic-bezier(0.2, 0, 0, 1);
  --ease-exit:      cubic-bezier(0.4, 0, 1, 1);
  --ease-gauge:     cubic-bezier(0.16, 1, 0.3, 1);

  /* ------------------------------------------------------------------ */
  /* 1.11 Layout                                                          */
  /* ------------------------------------------------------------------ */
  --width-sidebar:            240px;
  --width-sidebar-collapsed:  56px;
  --width-content-max:        1440px;
  --width-drawer:             520px;
  --width-drawer-wide:        720px;
  --height-topbar:            48px;
  --height-banner:            28px;
  --height-row-dense:         36px;
  --height-row-comfortable:   44px;
  --height-table-header:      32px;
  --height-control:           32px;  /* input, botão, chip: altura única */
  --height-control-sm:        24px;
}

/* Base ------------------------------------------------------------------ */
html {
  color-scheme: dark;                 /* scrollbars, inputs nativos, seleção */
  background: var(--color-surface-page);
  color: var(--color-fg-primary);
  font-family: var(--font-sans);
  font-size: 13px;                    /* base densa (§4.2) */
  line-height: 20px;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
  font-feature-settings: "cv11", "ss01"; /* Inter: 'a' e dígitos alternativos mais legíveis */
}
body { min-width: 1024px; }           /* abaixo disso o produto não é suportado (D9) */
::selection { background: var(--color-accent-tint); color: var(--color-fg-primary); }
:focus-visible {
  outline: 2px solid var(--color-accent-400);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
button, [role="button"] { cursor: pointer; }
[disabled], [aria-disabled="true"] { cursor: not-allowed; }

/* Utilitários do sistema ------------------------------------------------- */
@utility tnum   { font-variant-numeric: tabular-nums lining-nums; }
@utility eyebrow {
  font-size: 11px; line-height: 16px; font-weight: 600;
  letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-fg-secondary);
}
@utility scrollbar-thin {
  scrollbar-width: thin;
  scrollbar-color: var(--color-line-strong) transparent;
}
```

Nada além destes tokens pode ser inventado. Se um componente precisar de uma cor que não está
aqui, a resposta é "use um destes" — não "adicione um novo".

---

## 2. Cores semânticas de risco — regra dura

**Verde, âmbar, laranja e vermelho pertencem exclusivamente à semântica de risco.** Não são
usados em botões, links, ilustrações, gráficos sem significado de risco, logotipo ou estados de
formulário genéricos. Consequências práticas:

- Sucesso de operação ("Decisão registrada") usa **acento** + ícone `Check`, não verde.
- Erro de sistema (`ErrorState`) usa **neutro** + ícone `ServerCrash`, não vermelho. Vermelho é "este cliente é crítico", não "a API caiu".
- Campo de formulário inválido usa borda `line-strong` + mensagem em `fg-primary` com ícone `CircleAlert`, não vermelho.
- O banner de dados simulados é **neutro** (§6.23), não âmbar.

### 2.1 Mapa de cor por conceito

Todas as cores vêm de quatro famílias. O mesmo tom é reutilizado entre rating, severidade e tendência
porque significam a mesma intensidade de risco — isso é intencional e ensina o olho do analista.

| Família | Rating | Severidade de red flag | Tendência | Outros |
|---|---|---|---|---|
| `risk-a` (verde) | **A** — Baixo risco | — | `melhorando` | cobertura ≥ 100% |
| `risk-b` (âmbar) | **B** — Risco moderado | **MÉDIA** | — | — |
| `risk-c` (laranja) | **C** — Risco elevado | **ALTA** | `deteriorando` | teto C (veto `TETO_*`) |
| `risk-d` (vermelho) | **D** — Risco crítico / Alerta de RJ | **CRÍTICA** | `deterioracao_acelerada` | veto `FORCA_D`, Stay Period ativo, exposição em risco |
| `risk-neutral` (ardósia) | — | **BAIXA** / informativa | `estavel` | status `resolvida` |

### 2.2 Pares texto/fundo e contraste calculado

Método: WCAG 2.x luminância relativa, `(L1 + 0,05) / (L2 + 0,05)`. Tints são opacos
(pré-misturados a 14% sobre `#11161D`), portanto o contraste é o mesmo em qualquer contexto.
Calculado em 2026-09-12 por script; valores arredondados a duas casas.

| Uso | Texto | Fundo | Razão | Mín. exigido | Status |
|---|---|---|---|---|---|
| A texto sobre card | `#3DD68C` | `#11161D` | **9,68:1** | 4,5 | passa |
| A badge (texto sobre tint) | `#3DD68C` | `#17312D` | **7,40:1** | 4,5 | passa |
| A sólido (texto inverso sobre cor) | `#0B0F14` | `#3DD68C` | **10,25:1** | 4,5 | passa |
| B texto sobre card | `#F2C037` | `#11161D` | **10,70:1** | 4,5 | passa |
| B badge | `#F2C037` | `#312E21` | **8,02:1** | 4,5 | passa |
| B sólido | `#0B0F14` | `#F2C037` | **11,32:1** | 4,5 | passa |
| C texto sobre card | `#F28C3B` | `#11161D` | **7,43:1** | 4,5 | passa |
| C badge | `#F28C3B` | `#312721` | **5,95:1** | 4,5 | passa |
| C sólido | `#0B0F14` | `#F28C3B` | **7,86:1** | 4,5 | passa |
| D texto sobre card | `#F47474` | `#11161D` | **6,57:1** | 4,5 | passa |
| D badge | `#F47474` | `#312329` | **5,41:1** | 4,5 | passa |
| D sólido | `#0B0F14` | `#F47474` | **6,95:1** | 4,5 | passa |
| Neutro texto sobre card | `#A3AEBB` | `#11161D` | **8,07:1** | 4,5 | passa |
| Neutro badge | `#A3AEBB` | `#252B33` | **6,34:1** | 4,5 | passa |
| Texto sobre superfície `raised` (drawer) | | | | | |
| A sobre raised | `#3DD68C` | `#171E27` | **8,95:1** | 4,5 | passa |
| B sobre raised | `#F2C037` | `#171E27` | **9,89:1** | 4,5 | passa |
| C sobre raised | `#F28C3B` | `#171E27` | **6,86:1** | 4,5 | passa |
| D sobre raised | `#F47474` | `#171E27` | **6,07:1** | 4,5 | passa |
| Acento e neutros | | | | | |
| Acento texto/link sobre card | `#4DB8E5` | `#11161D` | **8,05:1** | 4,5 | passa |
| Botão primário (texto inverso sobre accent-500) | `#0B0F14` | `#2FA4D6` | **6,77:1** | 4,5 | passa |
| Botão primário `:active` (accent-600) | `#0B0F14` | `#1F86B3` | **4,69:1** | 4,5 | passa |
| Texto primário sobre linha selecionada | `#E6EBF0` | `#192D39` | **12,26:1** | 4,5 | passa |
| Texto terciário sobre raised | `#7B889A` | `#171E27` | **4,66:1** | 4,5 | passa |
| Texto desabilitado sobre card | `#66727F` | `#11161D` | **3,70:1** | isento | ver nota |
| Borda default vs card (não-texto) | `#283442` | `#11161D` | 1,44:1 | 3,0 (1.4.11) | ver nota |
| Faixas do gauge (cor a 28% sobre card) | `#3DD68C` | `#1D4C3C` | 5,20:1 | 3,0 (gráfico) | passa |

**Pares que não atingiram 4,5:1 na primeira rodada e como foram resolvidos:**

1. **Texto claro `#E6EBF0` sobre `accent-600 #1F86B3` = 3,42:1 — reprovado.** Resolução: o botão
   primário **nunca** usa texto claro. Usa `fg-inverse #0B0F14` sobre `accent-500` (6,77:1),
   hover clareia para `accent-400` (8,51:1) e `:active` escurece para `accent-600` (4,69:1, ainda
   acima do mínimo). `accent-600` fica proibido como fundo de texto claro.
2. **Vermelho candidato `#F16B6B` sobre tint a 16% = 4,91:1** — passava, mas com margem de 0,4.
   Resolução: vermelho D fixado em `#F47474` e tint a 14% → 5,41:1 sobre card e 4,95:1 se o mesmo
   tint fosse recalculado sobre `raised`. Como os tints são opacos, o valor efetivo é sempre 5,41:1.
3. **Texto desabilitado `#4B5664` = 2,43:1.** Isento pela WCAG 1.4.3 (componente inativo), mas
   ficava ilegível. Resolução: elevado para `#66727F` (3,70:1). Regra: `fg-disabled` só em controles
   `disabled`; nunca em conteúdo informativo. Placeholder de input usa `fg-tertiary`, não `fg-disabled`.
4. **Borda default vs card = 1,44:1.** Bordas de card não são componente de interface acionável
   (isentas de 1.4.11); servem à separação de superfície, reforçada pela diferença de tom
   page→card. Controles acionáveis (input, botão secundário, chip) usam `line-strong` no estado
   normal quando o fundo é `surface-card`… e o **anel de foco** `accent-400` (8,05:1) garante a
   percepção do estado. Inputs sobre `surface-input` (#0D1218) com borda `line-default` ganham
   contraste adicional pelo fundo mais escuro.

---

## 3. Redundância de canal — trio obrigatório

Nenhum estado de risco é comunicado só por cor. Cada estado tem **cor + rótulo textual + ícone
`lucide-react`** fixos, centralizados em `lib/risk-presentation.ts` e consumidos por `Badge`,
`RatingBadge`, `TrendIndicator`, `AlertRow`, `ScoreGauge` e pelos gráficos.

```ts
// lib/risk-presentation.ts
import type { LucideIcon } from 'lucide-react';
import {
  ShieldCheck, Shield, ShieldAlert, ShieldX,
  OctagonAlert, TriangleAlert, CircleAlert, Info,
  TrendingUp, MoveRight, TrendingDown, ChevronsDown,
  Gavel, Hourglass, Lock, LockOpen,
} from 'lucide-react';
import type { Rating, Severidade, Tendencia } from '@/types';

export type FamiliaRisco = 'a' | 'b' | 'c' | 'd' | 'neutral';

export interface ApresentacaoRisco {
  familia: FamiliaRisco;      // resolve para --color-risk-{familia}, -tint, -line
  rotulo: string;             // texto SEMPRE renderizado (pode ser visually-hidden só em ícone isolado com aria-label)
  rotuloCurto: string;        // para células estreitas
  Icone: LucideIcon;
}

export const RATING: Record<Rating, ApresentacaoRisco> = {
  A: { familia: 'a', rotulo: 'Baixo risco',                  rotuloCurto: 'A', Icone: ShieldCheck },
  B: { familia: 'b', rotulo: 'Risco moderado',               rotuloCurto: 'B', Icone: Shield },
  C: { familia: 'c', rotulo: 'Risco elevado',                rotuloCurto: 'C', Icone: ShieldAlert },
  D: { familia: 'd', rotulo: 'Risco crítico · Alerta de RJ', rotuloCurto: 'D', Icone: ShieldX },
};

export const SEVERIDADE: Record<Severidade, ApresentacaoRisco> = {
  CRITICA: { familia: 'd',       rotulo: 'Crítica', rotuloCurto: 'CRÍT.', Icone: OctagonAlert },
  ALTA:    { familia: 'c',       rotulo: 'Alta',    rotuloCurto: 'ALTA',  Icone: TriangleAlert },
  MEDIA:   { familia: 'b',       rotulo: 'Média',   rotuloCurto: 'MÉDIA', Icone: CircleAlert },
  BAIXA:   { familia: 'neutral', rotulo: 'Baixa',   rotuloCurto: 'BAIXA', Icone: Info },
};

export const TENDENCIA: Record<Tendencia, ApresentacaoRisco> = {
  melhorando:             { familia: 'a',       rotulo: 'Melhorando',             rotuloCurto: 'Melhor.',  Icone: TrendingUp },
  estavel:                { familia: 'neutral', rotulo: 'Estável',                rotuloCurto: 'Estável',  Icone: MoveRight },
  deteriorando:           { familia: 'c',       rotulo: 'Deteriorando',           rotuloCurto: 'Deter.',   Icone: TrendingDown },
  deterioracao_acelerada: { familia: 'd',       rotulo: 'Deterioração acelerada', rotuloCurto: 'Acelerada', Icone: ChevronsDown },
};

/** Conceitos jurídicos com ícone fixo (usados em Badge variant="natureza" e no painel de Stay Period). */
export const JURIDICO = {
  veto:           { familia: 'd' as FamiliaRisco, rotulo: 'Veto',           Icone: Gavel },
  tetoC:          { familia: 'c' as FamiliaRisco, rotulo: 'Teto C',         Icone: Gavel },
  stayPeriod:     { familia: 'd' as FamiliaRisco, rotulo: 'Stay Period',    Icone: Hourglass },
  extraconcursal: { familia: 'a' as FamiliaRisco, rotulo: 'Extraconcursal', Icone: Lock },
  concursal:      { familia: 'c' as FamiliaRisco, rotulo: 'Concursal',      Icone: LockOpen },
} as const;
```

Regras:

- Ícone sempre `size={14}` em badges e células, `size={16}` em cabeçalhos, `strokeWidth={2}`.
  Ícone e texto compartilham a cor `--color-risk-{familia}`.
- Quando o espaço só permite ícone (ex.: coluna de 32px), o elemento recebe
  `aria-label={rotulo}` e um `Tooltip` com o rótulo completo. Isso é exceção, não padrão.
- Letras de rating (A–D) nunca aparecem soltas: sempre dentro de `RatingBadge`, que carrega ícone e
  `title`. Em texto corrido, escreve-se "rating B (risco moderado)".
- Extraconcursal usa verde porque é **proteção que sobrevive à RJ**; concursal usa laranja porque
  **entra no plano com deságio**. Isso é semântica de risco legítima (§10 do motor), não decoração.

---

## 4. Tipografia

### 4.1 Famílias e carregamento

**Inter** (variável, 400–700) para tudo; **JetBrains Mono** (400, 500) exclusivamente para
identificadores técnicos (CPF/CNPJ, IDs de processo, hashes de evidência, contador de tokens).
Ambas via `next/font/google` — o Next baixa em build e serve do próprio domínio; **nenhuma
requisição a CDN externo em runtime**. Nunca importar por `<link>` ou `@import url()`.

```ts
// app/fonts.ts
import { Inter, JetBrains_Mono } from 'next/font/google';

export const inter = Inter({
  subsets: ['latin', 'latin-ext'],
  display: 'swap',
  variable: '--font-inter',
  axes: ['opsz'],           // eixo óptico: melhora o número gigante do gauge
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
  variable: '--font-jetbrains-mono',
});
```

```tsx
// app/layout.tsx
<html lang="pt-BR" className={`${inter.variable} ${jetbrainsMono.variable}`}>
```

### 4.2 Escala

Base densa de **13px/20px**. Nomes são as classes utilitárias a definir em `globals.css` via `@utility`.

| Nome | Uso | Tamanho / linha | Peso | Tracking | Extras |
|---|---|---|---|---|---|
| `type-score-xl` | número central do `ScoreGauge` lg | 56px / 56px | 600 | −0.03em | `tnum`, `font-optical-sizing: auto` |
| `type-score-md` | gauge md | 40px / 40px | 600 | −0.025em | `tnum` |
| `type-score-sm` | gauge sm, célula de score em tabela destacada | 28px / 28px | 600 | −0.02em | `tnum` |
| `type-kpi` | valor de `KpiTile` | 24px / 28px | 600 | −0.015em | `tnum` |
| `type-kpi-sm` | KPI compacto (drawer) | 18px / 24px | 600 | −0.01em | `tnum` |
| `type-page-title` | h1 da página (razão social do cliente, "Carteira") | 22px / 28px | 600 | −0.01em | `fg-primary` |
| `type-section-title` | h2 de card/seção | 15px / 20px | 600 | −0.005em | `fg-primary` |
| `type-eyebrow` | rótulo de bloco acima de KPI e de seção (caixa alta) | 11px / 16px | 600 | +0.08em | uppercase, `fg-secondary` |
| `type-label` | rótulo de campo, cabeçalho de tabela | 12px / 16px | 500 | +0.01em | `fg-secondary`; cabeçalho de tabela em uppercase +0.04em |
| `type-body` | texto padrão da interface, células | 13px / 20px | 400 | 0 | `fg-primary` |
| `type-body-strong` | ênfase em linha (nome do cliente na tabela) | 13px / 20px | 500 | 0 | |
| `type-prose` | parecer, explicações do LLM, copiloto | 14px / 22px | 400 | 0 | `max-width: 68ch` |
| `type-caption` | texto auxiliar, fontes, datas de consulta, notas | 12px / 16px | 400 | 0 | `fg-tertiary` |
| `type-num` | **toda célula numérica** | herda tamanho | 500 | 0 | `tnum`, `text-align: right` |
| `type-mono` | documento, ID de processo, tokens | 12px / 16px | 400 | 0 | `font-mono`, `fg-secondary` |
| `type-badge` | texto dentro de `Badge`/chip | 11px / 16px | 600 | +0.02em | `tnum` quando contém número |

### 4.3 Regras numéricas (inegociáveis)

- `font-variant-numeric: tabular-nums lining-nums` em **toda** célula, KPI, score, percentual,
  delta e eixo de gráfico. `DataTable` aplica automaticamente quando `coluna.numerica === true`.
- Valores monetários **alinhados à direita**, cabeçalho da coluna também à direita.
- Sinal negativo é **U+2212 (−)**, nunca hífen. Positivo explícito em deltas: "+12".
- Casas decimais **constantes dentro de uma coluna**. Uma coluna em "R$ mi" mostra sempre uma casa.
- Percentuais sem espaço antes do símbolo: "17,1%".
- Unidades em `fg-tertiary` peso 400 quando separadas do número (ex.: `604` grande, `/ 1000` pequeno).

---

## 5. Espaçamento, grid e densidade

### 5.1 Escala de espaçamento

Escala padrão do Tailwind (múltiplos de 4px). Valores permitidos: **2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48**.
Nada de 10px, 14px, 18px. Uso canônico:

| Token | px | Onde |
|---|---|---|
| `0.5` | 2 | gap ícone–texto em badge |
| `1` | 4 | gap interno de chips, padding vertical de badge |
| `1.5` | 6 | gap ícone–texto em botão/célula |
| `2` | 8 | gap entre badges, padding de badge horizontal, gap de itens em linha |
| `3` | 12 | padding de célula (horizontal), padding de card compacto, gap entre KPIs de um tile |
| `4` | 16 | **padding padrão de card**, gap de grid, gap entre campos |
| `5` | 20 | padding de drawer/modal |
| `6` | 24 | **gap entre seções**, padding da página |
| `8` | 32 | separação entre grupos de seções |
| `10`/`12` | 40/48 | padding vertical de `EmptyState`/`ErrorState` |

### 5.2 Shell da aplicação

```
┌──────────────────────────────────────────────────────────────────────┐
│ SimulatedDataBanner (28px, fixo, largura total)                     │
├────────────┬─────────────────────────────────────────────────────────┤
│ Sidebar    │ Topbar 48px: breadcrumb · busca global · CostCounter · persona │
│ 240px      ├─────────────────────────────────────────────────────────┤
│ (56px      │ Conteúdo: padding 24px · max-width 1440px · grid 12 col │
│ colapsada) │ gap 16px                                                 │
└────────────┴─────────────────────────────────────────────────────────┘
```

- Largura de projeto: **1280–1440px**. Suporte mínimo: 1024px (sidebar colapsa automaticamente
  abaixo de 1280px). Sem layout mobile — o produto é desktop (D9).
- Grid de conteúdo: 12 colunas, `gap: 16px`. Colunas típicas: página do cliente = 8 (principal) + 4
  (lateral: gauge, KPIs, recomendação); carteira = 12 (tabela) com faixa de KPIs 4×3 acima.
- Altura de linha-base: tudo se alinha a múltiplos de 4px.

### 5.3 Densidade de tabela

| Modo | Altura de linha | Padding célula | Fonte |
|---|---|---|---|
| `densa` (padrão) | 36px | 0 12px | 13px |
| `confortavel` | 44px | 0 16px | 13px |
| Cabeçalho | 32px | 0 12px | 12px uppercase +0.04em `fg-secondary` |

Zebra proibida. Separador de linha `line-subtle` 1px. Hover `surface-hover`. Selecionada `accent-tint`
com borda esquerda 2px `accent-400`. Coluna fixa à esquerda (nome do cliente) com sombra de 1px `line-default` à direita ao rolar.

### 5.4 Padding de card

- Padrão: `16px` em todos os lados. `SectionHeader` dentro do card tem `padding-bottom: 12px` e
  borda inferior `line-subtle`; o conteúdo começa 12px abaixo.
- Compacto (`densidade="compacta"`): `12px`. Usado em tiles laterais e dentro de drawers.
- Card que contém apenas `DataTable`: `padding: 0`; a tabela toca as bordas; o header do card
  mantém `12px 16px`.
- Cards **não** se aninham. Dentro de um card, agrupamento é por `SectionHeader` e divisórias.

---

## 6. Catálogo de primitivos

Convenções gerais:

- Arquivos em `components/ui/<Nome>.tsx` (genéricos) e `components/risk/<Nome>.tsx` (compostos
  de risco: `RatingBadge`, `TrendIndicator`, `ScoreGauge`, `FactorBar`, `StackedBar`, `AlertRow`,
  `EvidenceCard`, `Timeline`, `CostCounter`, `SimulatedDataBanner`).
- Props em **pt-BR**, com exceção das convenções React (`children`, `className`, `id`, `ref`,
  `aria-*`). Handlers começam com `ao` (`aoSelecionar`). Booleanos são adjetivos (`carregando`, `desabilitado`).
- Todo componente aceita `className` e o funde com `clsx` **depois** das classes internas.
- Estados obrigatórios (quando aplicáveis): `normal`, `hover`, `focus-visible`, `active`, `disabled`, `loading`.
  Transições de cor/borda em `--duration-fast --ease-standard`.
- Componentes interativos são `'use client'`; os puramente visuais são Server Components.
- Sem `forwardRef` legado: React 19 passa `ref` como prop.

### 6.0 `Button` e `IconButton` (base para os demais)

```ts
type VarianteBotao = 'primario' | 'secundario' | 'fantasma' | 'perigo-neutro';
// 'perigo-neutro': ação destrutiva de UI (ex.: "Restaurar dados da demonstração").
// Usa fg-primary + borda line-strong; NÃO usa vermelho (vermelho é risco de crédito).

interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variante?: VarianteBotao;        // padrão 'secundario'
  tamanho?: 'sm' | 'md';           // 24px | 32px de altura
  iconeEsquerda?: LucideIcon;
  iconeDireita?: LucideIcon;
  carregando?: boolean;            // troca iconeEsquerda por LoaderCircle animado, mantém largura, aria-busy
  larguraTotal?: boolean;
  children: React.ReactNode;
}

interface IconButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  icone: LucideIcon;
  rotulo: string;                  // obrigatório → aria-label + Tooltip
  variante?: 'secundario' | 'fantasma';
  tamanho?: 'sm' | 'md';
}
```

| Variante | Normal | Hover | Active | Disabled |
|---|---|---|---|---|
| `primario` | bg `accent-500`, texto `fg-inverse`, sem borda | bg `accent-400` | bg `accent-600` | bg `line-default`, texto `fg-disabled` |
| `secundario` | bg `surface-card`, borda `line-strong`, texto `fg-primary` | bg `surface-hover` | bg `surface-input` | borda `line-default`, texto `fg-disabled` |
| `fantasma` | transparente, texto `fg-secondary` | bg `surface-hover`, texto `fg-primary` | bg `surface-input` | texto `fg-disabled` |
| `perigo-neutro` | como secundário, ícone `RotateCcw`/`Trash2` | idem | idem | idem |

Raio `radius-sm`. Altura fixa `height-control`. Padding horizontal 12px (md) / 8px (sm). Texto 13px/500 (md), 12px/500 (sm).
Um único `primario` por região visual.

### 6.1 `Card`

```ts
interface CardProps {
  children: React.ReactNode;
  densidade?: 'padrao' | 'compacta';    // 16px | 12px
  semPadding?: boolean;                 // para DataTable interna
  interativo?: boolean;                 // hover surface-hover + borda line-strong; usado como link/botão
  destaque?: 'nenhum' | 'acento' | FamiliaRisco; // borda esquerda 2px na cor (ex.: card de veto = 'd')
  as?: 'div' | 'section' | 'article';
  className?: string;
}
```

Visual: bg `surface-card`, borda 1px `line-default`, raio `radius-md`, **sem sombra** (sombra só
em elementos flutuantes). `destaque` desenha `border-left: 2px solid var(--color-risk-{x} | accent-400)`.

### 6.2 `SectionHeader`

```ts
interface SectionHeaderProps {
  titulo: string;                         // type-section-title
  sobretitulo?: string;                   // type-eyebrow acima do título (ex.: "DIMENSÃO 2 · 20%")
  descricao?: string;                     // type-caption abaixo
  acoes?: React.ReactNode;                // botões/chips alinhados à direita
  meta?: React.ReactNode;                 // ex.: <Badge> de fonte ou contagem, ao lado do título
  nivel?: 2 | 3;                          // h2 (card) | h3 (subseção)
  termo?: TermoGlossario;                 // adiciona ícone Info com Tooltip do glossário ao título
  divisor?: boolean;                      // padrão true dentro de Card
}
```

### 6.3 `Badge`

```ts
type VarianteBadge =
  | { variante: 'neutro'; }
  | { variante: 'acento'; }
  | { variante: 'risco'; familia: FamiliaRisco }         // uso interno por RatingBadge/severidade
  | { variante: 'severidade'; severidade: Severidade }    // resolve via SEVERIDADE[]
  | { variante: 'natureza'; natureza: NaturezaGarantia }  // Lock/LockOpen, a/c
  | { variante: 'status'; status: StatusRedFlag }         // nova=acento · analisada=neutro · resolvida=neutro tracejado
  | { variante: 'fonte'; fonte: FonteId }                 // neutro, texto = nome curto da fonte
  | { variante: 'simulado' };                             // neutro, ícone FlaskConical, texto "simulado"

type BadgeProps = VarianteBadge & {
  children?: React.ReactNode;     // sobrescreve o rótulo padrão da variante
  icone?: LucideIcon | null;      // null suprime o ícone padrão (só permitido para 'neutro' | 'acento' | 'fonte')
  tamanho?: 'sm' | 'md';          // 16px | 20px de altura
  aparencia?: 'tint' | 'solido' | 'contorno';  // padrão 'tint'
  titulo?: string;                // title/aria-label complementar
  className?: string;
};
```

Visual `tint`: bg `--color-risk-{f}-tint`, texto e ícone `--color-risk-{f}`, borda 1px
`--color-risk-{f}-line`. `solido`: bg `--color-risk-{f}`, texto `fg-inverse` (só para `RatingBadge`
e para severidade CRÍTICA em `AlertRow`). `contorno`: transparente, borda `-line`, texto `-color`
(usado para "rating calculado" ao lado do "final" no veto). Raio `radius-sm`, padding `0 8px`,
gap 4px, `type-badge`. Nunca clicável — para filtro, use `FilterChips`.

### 6.4 `RatingBadge`

```ts
interface RatingBadgeProps {
  rating: Rating;
  tamanho?: 'sm' | 'md' | 'lg';          // 20px letra só · 24px letra+rótulo · 32px letra+rótulo+ícone
  mostrarRotulo?: boolean;               // padrão: true em md/lg, false em sm (sm mantém title + aria-label)
  aparencia?: 'tint' | 'solido';         // padrão 'solido' em lg, 'tint' nos demais
  calculado?: Rating;                    // se ≠ rating, renderiza par "calculado → final" (ver §7.7)
  className?: string;
}
```

A letra do rating usa peso 700 e `tnum`; em `lg` a letra tem 16px e o rótulo 12px/500 ao lado.
Quando `calculado` difere de `rating`: `[B ○contorno] → [D ●sólido]` com ícone `Gavel` 14px entre eles
e `aria-label="Rating calculado B, rebaixado para D por regra de negócio"`.

### 6.5 `TrendIndicator`

```ts
interface TrendIndicatorProps {
  tendencia: Tendencia;
  delta?: number;                 // variação de score no período; renderiza formatarDelta()
  periodo?: string;               // ex.: "90d" → "−108 · 90d"
  tamanho?: 'sm' | 'md';
  somenteIcone?: boolean;         // exige tooltip automático com rótulo completo
  className?: string;
}
```

Renderiza `[Ícone] Rótulo  −108 · 90d`, cor `--color-risk-{familia}`. `delta` em `tnum`.
Em tabela usa `tamanho="sm"` sem rótulo textual completo mas com `rotuloCurto` visível.

### 6.6 `ScoreGauge` — ver §7 (especificação dedicada)

```ts
interface ScoreGaugeProps {
  score: number;                     // scoreCalculado 0..1000
  ratingCalculado: Rating;
  ratingFinal: Rating;
  vetos?: VetoAtivo[];               // length > 0 → modo veto (§7.7)
  scoreAnterior?: number;            // marcador fantasma + arco de delta (§7.5)
  periodoDelta?: string;             // "90d"
  tendencia?: Tendencia;
  tamanho?: 'sm' | 'md' | 'lg';      // 120 · 200 · 280 px de largura
  animar?: boolean;                  // padrão true; respeita prefers-reduced-motion
  rotulo?: string;                   // aria-label base; padrão "Score de risco"
  className?: string;
}
```

### 6.7 `KpiTile`

```ts
interface KpiTileProps {
  rotulo: string;                        // type-eyebrow
  valor: string;                         // já formatado (lib/format.ts) — o tile NÃO formata
  unidade?: string;                      // "/ 1000", "%", "meses"
  variacao?: { delta: string; tendencia: Tendencia | 'neutra'; periodo?: string }; // usa TrendIndicator
  familia?: FamiliaRisco;                // colore o valor (ex.: PD alta) — só quando semanticamente risco
  termo?: TermoGlossario;                // ícone Info + Tooltip no rótulo (PD, RJ…)
  rodape?: React.ReactNode;              // type-caption (ex.: "Método: curva logística sobre score")
  tamanho?: 'md' | 'sm';                 // type-kpi | type-kpi-sm
  carregando?: boolean;                  // skeleton do valor (barra 60% largura, 24px)
  aoClicar?: () => void;                 // torna o tile interativo (borda line-strong no hover)
  className?: string;
}
```

Regra: `valor` em `fg-primary` por padrão. Só recebe cor de risco se representar um indicador de
risco com faixa definida (PD, RJ, cobertura). Exposição em R$ é sempre neutra.

### 6.8 `DataTable`

```ts
interface Coluna<T> {
  id: string;
  cabecalho: string;
  celula: (linha: T) => React.ReactNode;
  alinhamento?: 'esquerda' | 'direita' | 'centro';   // padrão esquerda; numerica força direita
  numerica?: boolean;                                // aplica type-num, tnum, alinhamento direita
  largura?: number | string;                         // px ou '20%'; sem largura = flex
  minLargura?: number;
  ordenavel?: boolean;
  valorOrdenacao?: (linha: T) => number | string | null; // obrigatório se ordenavel e celula não é primitiva
  fixa?: 'esquerda';                                 // sticky
  termo?: TermoGlossario;                            // Tooltip do glossário no cabeçalho
  ocultarAbaixoDe?: 1280 | 1440;                     // responsividade por corte de coluna, nunca por wrap
}

interface Ordenacao { colunaId: string; direcao: 'asc' | 'desc' }

interface DataTableProps<T> {
  colunas: Coluna<T>[];
  linhas: T[];
  obterId: (linha: T) => string;
  densidade?: 'densa' | 'confortavel';               // padrão 'densa'
  ordenacao?: Ordenacao;                             // controlado
  ordenacaoInicial?: Ordenacao;                      // não controlado
  aoOrdenar?: (ordenacao: Ordenacao) => void;
  selecao?: {
    modo: 'unica' | 'multipla';
    selecionados: ReadonlySet<string>;
    aoMudar: (ids: Set<string>) => void;
  };
  linhaAtiva?: string | null;                        // realce persistente (cliente aberto no drawer)
  aoClicarLinha?: (linha: T) => void;                // linha vira role="button"; Enter/Espaço ativam
  familiaLinha?: (linha: T) => FamiliaRisco | null;  // borda esquerda 2px na cor (ex.: rating D)
  carregando?: boolean;
  linhasEsqueleto?: number;                          // padrão 8
  vazio?: React.ReactNode;                           // EmptyState; padrão "Nenhum registro"
  cabecalhoFixo?: boolean;                           // sticky top dentro de alturaMaxima
  alturaMaxima?: number | string;
  rodape?: React.ReactNode;                          // linha de totais (tnum, peso 600, borda superior line-strong)
  'aria-label': string;
}
```

Comportamentos:

- Ordenação: clique no cabeçalho alterna `asc → desc → sem ordenação`. Ícone `ArrowUpDown` 12px
  em `fg-tertiary` no hover; `ArrowUp`/`ArrowDown` em `accent-400` quando ativo. `aria-sort` no `th`.
  Ordenação numérica usa `valorOrdenacao`; strings usam `localeCompare('pt-BR', { numeric: true, sensitivity: 'base' })`.
- Seleção múltipla: coluna de 40px com checkbox autoral (16px, raio 2px, borda `line-strong`,
  marcado bg `accent-500` + `Check` 12px `fg-inverse`). Checkbox do cabeçalho suporta `indeterminate`.
- Estado vazio ocupa a área do corpo com `EmptyState` compacto (min-height 160px).
- Carregando: `linhasEsqueleto` linhas com barras `surface-hover` de largura variável (70/45/85%), sem shimmer.
- Sem paginação: dataset de 18 clientes. Rolagem vertical com `cabecalhoFixo`.

### 6.9 `FilterChips`

```ts
interface OpcaoChip<V extends string> {
  valor: V;
  rotulo: string;
  contagem?: number;               // "(4)" em tnum, fg-tertiary
  familia?: FamiliaRisco;          // chip de rating/severidade herda ícone e cor quando ativo
  icone?: LucideIcon;
}

interface FilterChipsProps<V extends string> {
  opcoes: OpcaoChip<V>[];
  selecionados: ReadonlySet<V>;
  aoMudar: (proximos: Set<V>) => void;
  modo?: 'multiplo' | 'unico';     // padrão 'multiplo'
  rotulo: string;                  // aria-label do grupo (role="group")
  limparRotulo?: string;           // se presente, mostra chip "Limpar" quando há seleção
}
```

Chip: altura 24px, raio `radius-sm`, `type-badge` peso 500. Inativo: borda `line-default`, texto
`fg-secondary`. Hover: borda `line-strong`. Ativo genérico: bg `accent-tint`, borda `accent-line`,
texto `accent-300`. Ativo com `familia`: bg/borda/texto da família (ícone incluso). `aria-pressed`.

### 6.10 `SearchInput`

```ts
interface SearchInputProps {
  valor: string;
  aoMudar: (valor: string) => void;
  placeholder?: string;              // padrão "Buscar cliente, CNPJ ou município"
  atalho?: string;                   // ex.: "/" → exibe <kbd> à direita e registra atalho global
  carregando?: boolean;              // LoaderCircle substitui o ícone Search
  limpavel?: boolean;                // padrão true: botão X quando há texto
  tamanho?: 'sm' | 'md';
  autoFocus?: boolean;
  'aria-label': string;
}
```

Visual: bg `surface-input`, borda `line-default`, raio `radius-sm`, altura `height-control`,
ícone `Search` 14px `fg-tertiary` à esquerda (padding-left 32px), texto 13px. Focus: borda
`accent-400` + anel `:focus-visible` interno (`box-shadow: 0 0 0 1px var(--color-accent-400)`), sem
outline duplo. `<kbd>`: `type-mono` 11px, borda `line-default`, padding 0 4px.

### 6.11 `Drawer`

```ts
interface DrawerProps {
  aberto: boolean;
  aoFechar: () => void;
  titulo: string;
  subtitulo?: string;                       // ex.: documento mascarado + município
  largura?: 'padrao' | 'larga';             // 520 | 720 px
  cabecalhoExtra?: React.ReactNode;         // RatingBadge, TrendIndicator ao lado do título
  rodape?: React.ReactNode;                 // barra de ações fixa (Button primário à direita)
  children: React.ReactNode;
  retornarFocoPara?: React.RefObject<HTMLElement>;
}
```

Posição: direita, altura total abaixo do banner. bg `surface-raised`, borda esquerda `line-strong`,
`shadow-overlay`. Scrim `surface-overlay`. Header 56px com `IconButton X`. Conteúdo com
`padding: 20px` e `scrollbar-thin`. Foco preso; `Esc` fecha; `role="dialog"` `aria-modal`
`aria-labelledby`. Entrada: `translateX(16px) → 0` + opacidade, `--duration-base --ease-standard`.
Saída: `--duration-fast --ease-exit`. A URL **não** muda ao abrir (drawer é pré-visualização; a
página do cliente é a rota).

### 6.12 `Modal`

```ts
interface ModalProps {
  aberto: boolean;
  aoFechar: () => void;
  titulo: string;
  descricao?: string;                        // aria-describedby
  tamanho?: 'sm' | 'md' | 'lg';              // 400 · 560 · 760 px
  acoes: React.ReactNode;                    // obrigatório: pelo menos um Button
  fecharAoClicarFora?: boolean;              // padrão true; false para "Registrar decisão"
  children: React.ReactNode;
}
```

Centralizado, bg `surface-raised`, borda `line-strong`, raio `radius-lg`, `shadow-overlay`,
header 20px, corpo 20px, rodapé com ações à direita separadas por 8px. Entrada:
`scale(0.98) → 1` + opacidade em `--duration-base`. Um modal por vez; modal sobre drawer é permitido
(z-index 60 vs 50). Uso canônico: "Registrar decisão do analista" e "Simular evento de monitoramento".

### 6.13 `Tooltip` e glossário

```ts
type TermoGlossario =
  | 'PD' | 'RJ' | 'CNDT' | 'CAR' | 'ZARC' | 'CPR'
  | 'EXTRACONCURSAL' | 'CONCURSAL' | 'STAY_PERIOD'
  | 'PGFN' | 'CRF_FGTS' | 'COVENANT' | 'BARTER' | 'HAIRCUT';

interface TooltipProps {
  conteudo: React.ReactNode;                  // texto curto (≤ 240 caracteres) ou <dl>
  termo?: TermoGlossario;                     // se presente, conteudo = GLOSSARIO[termo]
  lado?: 'cima' | 'baixo' | 'esquerda' | 'direita';  // padrão 'cima', com flip automático
  atraso?: number;                            // ms, padrão 150
  children: React.ReactElement;               // trigger; recebe aria-describedby
}

/** Atalho: <Termo sigla="PD" /> renderiza a sigla com sublinhado pontilhado + Tooltip. */
interface TermoProps { sigla: TermoGlossario; children?: React.ReactNode }
```

Visual: bg `surface-raised`, borda `line-strong`, raio `radius-md`, padding 8px 10px, 12px/16px
`fg-primary`, max-width 280px, `shadow-overlay`, seta de 6px. Abre em hover e em foco de teclado;
fecha em `Esc`. Termo gatilho: `text-decoration: underline dotted var(--color-fg-tertiary)`,
`text-underline-offset: 3px`, cursor `help`.

Textos do glossário (`lib/glossario.ts`), obrigatórios e literais:

| Termo | Texto |
|---|---|
| `PD` | **Probabilidade de Default.** Probabilidade estimada de o cliente ficar inadimplente no horizonte indicado (6, 12 ou 24 meses). Derivada do score por curva logística. Não é o mesmo que risco de RJ. |
| `RJ` | **Recuperação Judicial** (Lei 11.101/2005). Processo em que o devedor renegocia dívidas sob supervisão judicial. Créditos anteriores ao pedido entram no plano com deságio; execuções ficam suspensas durante o Stay Period. |
| `CNDT` | **Certidão Negativa de Débitos Trabalhistas** (TST). "Positiva" indica débito trabalhista com trânsito em julgado e não quitado — passivo com preferência sobre credores quirografários. |
| `CAR` | **Cadastro Ambiental Rural** (SICAR). Registro obrigatório do imóvel rural. Situação irregular ou ausente compromete a regularidade fundiária e o valor de execução da garantia. |
| `ZARC` | **Zoneamento Agrícola de Risco Climático** (MAPA). Classifica o risco climático da cultura na região e a janela de plantio recomendada. Base para seguro e crédito rural. |
| `CPR` | **Cédula de Produto Rural.** Título de promessa de entrega de produto (CPR física) ou de pagamento em dinheiro (CPR financeira). Registrada, a CPR financeira é garantia extraconcursal. |
| `EXTRACONCURSAL` | Crédito ou garantia **fora dos efeitos da RJ** (ex.: alienação fiduciária). Pode ser executado mesmo com plano em curso. É a única cobertura que protege de fato em cenário de RJ. |
| `CONCURSAL` | Crédito ou garantia **sujeito ao plano de RJ** (ex.: penhor, hipoteca, aval). Recebe com deságio e no prazo do plano aprovado pelos credores. |
| `STAY_PERIOD` | Suspensão de **180 dias** (prorrogável uma vez) das execuções e cobranças contra o devedor após o deferimento da RJ (art. 6º, Lei 11.101/2005). Garantias extraconcursais não são atingidas. |
| `PGFN` | **Procuradoria-Geral da Fazenda Nacional.** Inscrição em dívida ativa federal; crédito tributário tem preferência sobre o crédito comercial. |
| `CRF_FGTS` | **Certificado de Regularidade do FGTS** (Caixa). Irregularidade indica atraso de obrigações trabalhistas acessórias. |
| `COVENANT` | Cláusula contratual de desempenho (ex.: limite de endividamento). Rompida, configura **inadimplência técnica** — antes de qualquer atraso de pagamento. |
| `BARTER` | Operação de troca: insumos fornecidos hoje contra entrega de safra futura. Exposição depende de produtividade, clima e integridade da área plantada. |
| `HAIRCUT` | Deságio aplicado ao valor declarado da garantia para estimar o valor de realização em execução. Varia por tipo (ex.: penhor de safra 40%, alienação fiduciária 20%). |

### 6.14 `Timeline`

```ts
interface ItemTimeline {
  id: string;
  data: string;                        // ISO
  titulo: string;
  descricao?: string;
  severidade?: Severidade;             // colore o marcador; ausente = neutro
  fonte?: FonteId;
  deltaScore?: number;                 // "−42" em TrendIndicator sem rótulo
  scoreApos?: number;
  icone?: LucideIcon;                  // por tipo de evento (mapa em lib/eventos-presentation.ts)
  evidenciaIds?: string[];
  destaque?: boolean;                  // evento injetado pela demo (D10): borda accent + Badge "simulado agora"
}

interface TimelineProps {
  itens: ItemTimeline[];               // o componente ordena desc por data
  agruparPorMes?: boolean;             // padrão true: eyebrow "SET 2026" separa grupos
  aoSelecionarEvidencia?: (id: string) => void;
  limite?: number;                     // colapsa além de N com botão "Mostrar mais (12)"
  vazio?: React.ReactNode;
}
```

Visual: trilho vertical 1px `line-default` a 8px da borda esquerda; marcador de 10px (círculo,
borda 2px na cor da severidade, preenchimento `surface-card`; CRÍTICA preenche sólido). Data em
`type-caption tnum` alinhada à esquerda com largura fixa 88px; conteúdo à direita.

### 6.15 `ProgressBar` (coberturas)

```ts
interface ProgressBarProps {
  valor: number;                          // fração 0..∞ (cobertura pode passar de 1)
  maximo?: number;                        // padrão 1; barra clampa visualmente em 1 e mostra excedente por texto
  rotulo: string;                         // "Cobertura extraconcursal"
  valorFormatado?: string;                // padrão formatarPercentual(valor, 0)
  familia?: FamiliaRisco | 'auto';        // 'auto': ≥1 → a · ≥0,6 → b · ≥0,3 → c · <0,3 → d
  marcas?: { valor: number; rotulo: string }[];   // ticks (ex.: {valor: 1, rotulo: '100%'})
  termo?: TermoGlossario;
  altura?: 6 | 8;
}
```

Trilho `surface-sunken` com borda 1px `line-subtle`, raio `radius-xs`. Preenchimento sólido na cor.
Rótulo à esquerda e valor à direita na linha acima (12px). Ticks: linha 1px `fg-tertiary` de altura
da barra + 2px, rótulo `type-caption` abaixo.

### 6.16 `StackedBar` (exposição protegida vs em risco)

```ts
interface SegmentoBarra {
  id: string;
  rotulo: string;                    // "Extraconcursal", "Concursal", "Em risco"
  valor: number;                     // R$
  familia: FamiliaRisco;             // extraconcursal=a · concursal=c · em risco=d
  padrao?: 'solido' | 'hachurado';   // hachurado para "em risco em RJ" (o que o penhor deixa de cobrir)
}

interface StackedBarProps {
  segmentos: SegmentoBarra[];
  total: number;                     // exposicaoTotal — base de 100%
  altura?: 12 | 16;
  legenda?: 'abaixo' | 'lateral' | 'nenhuma';   // cada item: quadrado 8px + rótulo + valor + %
  destaque?: string;                 // id do segmento a realçar (borda fg-primary 1px) — usado para exposicaoEmRiscoEmRJ
  formatarValor?: (v: number) => string;        // padrão formatarMoedaCompacta
  'aria-label': string;
}
```

Segmentos separados por 2px de `surface-card`. Cores sólidas; padrão hachurado é o mesmo
`<pattern>` do veto (§7.7) com a cor do segmento. Legenda em grade de 3 colunas com valores `tnum`.

### 6.17 `AlertRow`

```ts
interface AlertRowProps {
  alerta: Alerta;
  aoAbrirCliente: (clienteId: string) => void;
  aoMarcarLido?: (id: string) => void;
  compacto?: boolean;              // topbar dropdown
  selecionado?: boolean;
}
```

Layout em linha (min-height 56px, padding 12px 16px): `[Badge severidade sólido para CRÍTICA/tint
demais] [título 13px/500 + cliente em fg-secondary] … [data relativa tnum] [ChevronRight]`.
Não lido: borda esquerda 2px `accent-400` e título em `fg-primary`; lido: título em `fg-secondary`.
Segunda linha (não compacto): `impacto` em `type-caption` e `acaoRecomendada` com ícone `ArrowRight`.
Hover `surface-hover`. Toda a linha é clicável.

### 6.18 `EvidenceCard`

```ts
interface EvidenceCardProps {
  evidencia: Evidencia;
  fatoresRelacionados?: { id: string; rotulo: string; impacto: number }[]; // resolvidos pelo chamador
  aoClicarFator?: (fatorId: string) => void;
  expandida?: boolean;
  aoAlternar?: () => void;
}
```

Card compacto (`densidade="compacta"`). Cabeçalho: ícone por `tipo` (`CERTIDAO` FileCheck ·
`PROCESSO` Scale · `PUBLICACAO` Newspaper · `CADASTRO` Building2 · `LAUDO` ClipboardList ·
`SERIE_HISTORICA` LineChart · `INTERNO` Database) 16px `fg-secondary`; `titulo` 13px/500;
`Badge variante="fonte"` + **`Badge variante="simulado"` obrigatório** (D11.6). Linha meta:
"Consulta em 12/09/2026 · Documento de 03/08/2026" em `type-caption tnum`. Corpo: `resumo` em
`type-body fg-secondary`. Rodapé (expandida): lista de fatores como chips clicáveis com impacto
formatado (`formatarDelta`). `urlFicticia` renderiza como texto mono não clicável com ícone `Link2Off`.

### 6.19 `FactorBar` (barra divergente)

```ts
interface FactorBarProps {
  fatores: Array<Pick<FatorCalculado, 'id' | 'rotulo' | 'detalhe' | 'direcao' | 'dimensao'> & { impacto: number }>;
  // impacto = impactoGlobalAjustado (contribuição ao score) ou delta (variação); o chamador decide
  modo: 'contribuicao' | 'delta';    // muda cabeçalho ("Impacto no score" | "Variação no período") e sinal zero
  escalaMaxima?: number;             // padrão max(|impacto|) arredondado para cima em múltiplo de 10
  limite?: number;                   // exibe N maiores por |impacto|, botão "Mostrar todos (23)"
  aoSelecionar?: (fatorId: string) => void;
  selecionado?: string | null;
  mostrarDimensao?: boolean;         // eyebrow com o nome da dimensão à esquerda do rótulo
  somaEsperada?: number;             // se informado, renderiza rodapé "Σ = −108 · fecha com score" (auditoria I2/I6)
}
```

Geometria: linha de 28px por fator; coluna de rótulo 40% (texto 13px, `detalhe` em caption
abaixo se houver, truncado com tooltip), coluna de barra 60% com eixo zero central em 1px
`line-strong`. Barras de 8px, raio `radius-xs`: impacto negativo cresce para a esquerda em
`risk-d`; positivo para a direita em `risk-a`. Valor numérico (`formatarDelta`) em `tnum` 12px/500
na ponta externa da barra, na cor da barra. Barra selecionada recebe contorno 1px `fg-primary`.
Ordenação: por `|impacto|` desc. Rodapé de soma em `type-label` com ícone `Sigma` — quando
`|soma − somaEsperada| > 0,5` mostra `TriangleAlert` neutro e texto "não fecha" (isso é bug, nunca deve aparecer em produção).

O uso de verde/vermelho aqui é semântico (proteção vs risco) e permitido.

### 6.20 `StreamingText`

```ts
type EstadoStreaming = 'aguardando' | 'transmitindo' | 'concluido' | 'degradado' | 'erro';

interface StreamingTextProps {
  texto: string;                      // acumulado até agora
  estado: EstadoStreaming;
  linhasEsqueleto?: number;           // padrão 4 — usado em 'aguardando'
  origem: 'llm' | 'deterministico';   // renderiza rótulo "Gerado por IA" ou "Texto padrão (LLM indisponível)"
  modelo?: string;                    // "gpt-5.4-mini" em type-mono no rodapé quando origem='llm'
  aoTentarNovamente?: () => void;     // exibido em 'erro'
  className?: string;
}
```

- `aguardando`: N barras de skeleton (`surface-hover`, alturas 14px, larguras 92/100/78/60%),
  animação `opacity 0.6 ↔ 1` em 1,6s linear alternado. Acima, eyebrow "GERANDO PARECER" com
  `LoaderCircle` 12px girando.
- `transmitindo`: `type-prose`; Markdown mínimo (parágrafos, `**negrito**`, listas). Cursor de
  digitação: bloco `2px × 1em` em `accent-400` após o último caractere, piscando `steps(2)` a 1s.
- `concluido`: cursor removido; rodapé `type-caption`: "Gerado por IA · gpt-5.4-mini · os números
  vêm do motor determinístico" com ícone `Sparkles` 12px `fg-tertiary`.
- `degradado`: texto renderizado de imediato (sem streaming), rodapé "Texto padrão — LLM
  indisponível ou orçamento atingido" com ícone `CircuitBoard`. Sem vermelho.
- `erro`: `ErrorState` compacto inline com botão "Tentar novamente".
- Todo número que aparece na prosa é **texto**, não fonte de verdade; nunca receber destaque de cor de risco.

### 6.21 `EmptyState`

```ts
interface EmptyStateProps {
  icone?: LucideIcon;              // padrão Inbox
  titulo: string;                  // "Nenhum alerta no período"
  descricao?: string;
  acao?: { rotulo: string; aoClicar: () => void; icone?: LucideIcon };
  compacto?: boolean;              // 160px min-height (tabela) vs 320px (página)
}
```

Ícone 32px `fg-tertiary` strokeWidth 1.5 dentro de quadrado 56px bg `surface-input` raio
`radius-md`; título `type-section-title` `fg-secondary`; descrição `type-caption`; botão `secundario`.
Centralizado. Nenhuma ilustração.

### 6.22 `ErrorState`

```ts
interface ErrorStateProps {
  titulo?: string;                 // padrão "Não foi possível carregar"
  detalhe?: string;                // mensagem técnica em type-mono, colapsada por padrão ("Ver detalhes")
  aoTentarNovamente?: () => void;
  compacto?: boolean;
}
```

Como `EmptyState`, com ícone `ServerCrash`. **Neutro** — sem vermelho (regra §2). Botão
`secundario` com ícone `RotateCcw`.

### 6.23 `SimulatedDataBanner`

```ts
interface SimulatedDataBannerProps {
  variante?: 'app' | 'impressao';   // 'app' fixo no topo; 'impressao' cabeçalho de PDF (§10)
}
```

Texto fixo: **`DADOS SIMULADOS — protótipo demonstrativo · nenhuma consulta real a órgão público`**.
Altura 28px, largura total, bg `surface-input`, borda inferior 1px `line-strong`, texto `type-eyebrow`
em `fg-secondary`, ícone `FlaskConical` 12px. Fundo com listras diagonais sutis:
`repeating-linear-gradient(135deg, transparent 0 10px, rgb(255 255 255 / 0.025) 10px 12px)` —
**esta é a única exceção à proibição de gradiente fora do gauge**, e é permitida por ser textura de
aviso, não decoração. Não é fechável. Não usa âmbar.

### 6.24 `CostCounter`

```ts
interface CostCounterProps {
  tokensEntrada: number;
  tokensSaida: number;
  custoUsd: number;               // estimado
  orcamentoUsd: number;           // LASTRO_LLM_BUDGET_USD
  llmAtivo: boolean;              // false → "LLM desligado" e ícone CircuitBoard
  chamadas: number;
}
```

Fica na topbar. Renderiza `[Coins 12px] US$ 0,42 / 10,00 · 18,3k tokens` em `type-mono` 11px
`fg-secondary`, com mini `ProgressBar` de 48px × 4px em `accent-400`. Quando `custoUsd/orcamentoUsd ≥ 0,8`:
texto vira `fg-primary` e ícone `TriangleAlert` neutro — **não** laranja (não é risco de crédito).
Quando `≥ 1`: rótulo "Orçamento atingido — modo determinístico". Tooltip detalha entrada/saída/chamadas.
Custo em US$ formatado `pt-BR` com 2 casas (`formatarNumero(custo, 2)` prefixado "US$ ").

---

## 7. `ScoreGauge` — especificação detalhada

O elemento mais visível do produto. SVG autoral, sem biblioteca. Arquivo `components/risk/ScoreGauge.tsx`
+ `lib/gauge-geometry.ts` (funções puras testáveis).

### 7.1 Geometria

- `viewBox="0 0 200 172"`, centro do arco `C = (100, 104)`, raio da linha média do arco `R = 80`.
  O gauge escala por `width` (120/200/280 px); tudo abaixo é em unidades do viewBox.
- **Varredura de 240°**: ângulo `θ(score) = −120° + 240° × (score / 1000)`, medido a partir das
  12 horas, positivo no sentido horário. Score 0 → −120° (posição "8h"), 500 → 0° (topo),
  1000 → +120° ("4h"). A abertura de 120° na base acomoda o `TrendIndicator` e os badges.
- Ponto no arco: `x = Cx + R·sin(θ)`, `y = Cy − R·cos(θ)`.
- Comprimento total do arco: `L = 2π·R·(240/360) = 335,10`.
- **Trilho** (`<path>` do arco completo): `stroke-width 12`, `stroke-linecap butt`, cor `surface-sunken`
  com `stroke` adicional de 1px `line-subtle` desenhado como segundo path de `stroke-width 14` atrás.
- **Faixas de rating** sobre o trilho: quatro `<path>` de `stroke-width 12` cobrindo os intervalos
  0–399, 400–599, 600–749, 750–1000, cores `--color-risk-d/c/b/a` com `opacity 0.28`. Sem gap entre
  faixas; a divisão é marcada pelos ticks.
- **Ticks de faixa** em 400, 600, 750: linha radial de `R−10` a `R+10`, `stroke-width 1.5`,
  cor `fg-tertiary`. Rótulo numérico (`400`, `600`, `750`) em 9px/500 `tnum` `fg-tertiary`, a `R+18`
  do centro, com `text-anchor` conforme o quadrante (`end` para θ<0, `middle` para |θ|<8°, `start` para θ>0).
  Ticks extremos `0` e `1000` só rótulo, sem linha.
- **Preenchimento** (`<path>` do arco de 0 até `θ(score)`): `stroke-width 12`, `stroke-linecap butt`,
  cor **sólida** `--color-risk-{ratingCalculado}`, desenhado via `stroke-dasharray="${L} ${L}"` e
  `stroke-dashoffset = L × (1 − score/1000)` para permitir animação (§7.6).
- **Cursor** na posição do score: pequeno pill radial de `6 × 18` (largura tangencial 6, comprimento
  radial de `R−9` a `R+9`), raio 3 (única forma "pill" do sistema), preenchimento `fg-primary`,
  `stroke 2px surface-card`. Rotacionado por `transform="rotate(θ Cx Cy)"`.

### 7.2 Centro tipográfico

Empilhado no centro `(100, 96)`, alinhado por `text-anchor="middle"`:

| Camada | Conteúdo | Estilo (lg / md / sm) | Posição y |
|---|---|---|---|
| Número | `formatarScore(score)` | `type-score-xl` / `-md` / `-sm`, `fg-primary`, `dominant-baseline: central` | 92 |
| Denominador | `/ 1000` | 11px/400 `fg-tertiary` `tnum` (oculto em `sm`) | 118 |
| Rótulo do rating | `RatingBadge tamanho="md"` renderizado em `<foreignObject>` de 120×24 (md/lg) ou fora do SVG (sm) | | 130 |
| Delta | `TrendIndicator` com `delta` e `periodo` (`<foreignObject>` 140×20) | oculto em `sm` | 156 |

Em `sm`, apenas número e um `RatingBadge tamanho="sm"` abaixo do SVG. O componente sempre expõe
`role="img"` e `aria-label` completo, ex.: *"Score de risco 604 de 1000, rating B, risco
moderado, variação de −108 pontos em 90 dias, deterioração acelerada"*.

### 7.3 Faixas e valor do número

O número central **nunca** é colorido: `fg-primary` sempre. A cor está no arco, no badge e no
ícone — três canais bastam, e o número em cor faria o analista ler "vermelho" antes de ler "604".

### 7.4 Rotulagem semântica do arco

Cada faixa colorida recebe `<title>` ("Faixa D · 0–399 · Risco crítico") para leitura em hover.
O `ScoreGauge` inteiro tem `Tooltip` opcional com as faixas.

### 7.5 Variação em relação ao score anterior (mesmo elemento)

Quando `scoreAnterior` é fornecido e `|score − scoreAnterior| ≥ 1`:

- **Marcador fantasma** na posição `θ(scoreAnterior)`: círculo `r=3`, `fill: none`,
  `stroke 1.5px fg-tertiary`, centrado a `R+14` (fora do trilho, para não competir com o cursor).
- **Arco de delta** entre `θ(scoreAnterior)` e `θ(score)`, raio `R+14`, `stroke-width 2`,
  `stroke-dasharray 3 3`, cor `--color-risk-{TENDENCIA[tendencia].familia}` (se `tendencia` ausente:
  `risk-c` para queda, `risk-a` para alta, `neutral` para |Δ| < 25).
- Seta na ponta do arco de delta (triângulo 5×4) apontando para a posição atual.
- O `TrendIndicator` no centro mostra `−108 · 90d` com ícone e rótulo. Quatro canais para o mesmo fato
  é o máximo permitido; não adicionar um quinto (nenhum "−108" flutuando no arco).

### 7.6 Animação

Na montagem, se `animar` e o usuário não pediu redução de movimento: `stroke-dashoffset` anima de
`L` até o valor final em `--duration-gauge --ease-gauge`; o cursor gira junto (`transition: transform`).
O número faz contagem de `0 → score` no mesmo tempo, com `requestAnimationFrame` e `Math.round`
por frame. Ao recalcular (evento simulado, D10): preenchimento e cursor animam da posição antiga
para a nova em `--duration-gauge`; o marcador fantasma **surge** na posição antiga com fade de
`--duration-base`. `prefers-reduced-motion: reduce` → tudo instantâneo.

### 7.7 Modo veto (`vetos.length > 0`, portanto `ratingFinal ≠ ratingCalculado`)

O gauge tem de deixar inequívoco que **o quantitativo disse uma coisa e a regra de negócio impôs outra**,
sem esconder nenhum dos dois (motor §8).

1. **Preenchimento hachurado**: o arco de 0 a `θ(score)` mantém a cor do `ratingCalculado`, mas o
   `stroke` passa a usar `url(#lastro-hatch-{familia})`, um `<pattern patternUnits="userSpaceOnUse"
   width="6" height="6" patternTransform="rotate(45)">` com `<rect width="6" height="6" fill="var(--color-risk-{familia}-tint)"/>`
   e `<rect width="2.5" height="6" fill="var(--color-risk-{familia})"/>`. Leitura: "este era o
   valor calculado, mas está sobrestado".
2. **Anel externo do rating final**: arco completo de 240° a `R+14` (mesma órbita do delta, que
   neste modo é suprimido), `stroke-width 3`, cor sólida `--color-risk-{ratingFinal}` (`d` para
   `FORCA_D`, `c` para `TETO_C`). É a única vez que o gauge tem um anel externo contínuo.
3. **Centro**: número inalterado (é o `scoreCalculado`, honesto). Abaixo dele, em vez do
   `RatingBadge` simples, o par `RatingBadge rating={ratingFinal} calculado={ratingCalculado}`:
   `[B contorno] → Gavel → [D sólido]`.
4. **Rótulo do veto**: linha de 11px/600 uppercase `fg-primary` em `y=156`:
   `VETO · RJ DEFERIDA` (ou o `rotulo` do primeiro veto por efeito mais severo; se houver mais de um:
   `VETO · RJ DEFERIDA +1`). Ícone `Gavel` 12px `--color-risk-{final}` à esquerda.
5. **`aria-label`** passa a: *"Score calculado 520 de 1000, rating calculado C. Classificação
   final D por regra de negócio: RJ deferida. Risco crítico, alerta de RJ."*
6. Abaixo do gauge (fora do SVG, responsabilidade da página), o card **"Classificação final após
   regras de negócio"** lista cada `VetoAtivo` com `justificativa` e links para `evidenciaIds`. O gauge
   comunica que houve veto; o card explica.

Em modo veto **não** se mostra arco de delta (evitar três órbitas); o `TrendIndicator` continua
no centro em `y=170` só nos tamanhos `lg`.

### 7.8 Assinatura das funções de geometria (testáveis com Vitest)

```ts
// lib/gauge-geometry.ts
export const GAUGE = { cx: 100, cy: 104, r: 80, sweep: 240, start: -120, strokeWidth: 12 } as const;
export function anguloDoScore(score: number): number;                       // graus, clamp 0..1000
export function pontoNoArco(anguloGraus: number, raio?: number): { x: number; y: number };
export function pathArco(scoreInicio: number, scoreFim: number, raio?: number): string; // "M … A …"
export function comprimentoArco(raio?: number): number;                     // 335,10 para r=80
export function dashOffset(score: number, raio?: number): number;
export function ancoraTexto(anguloGraus: number): 'start' | 'middle' | 'end';
```

Testes obrigatórios: `anguloDoScore(0) === -120`, `anguloDoScore(500) === 0`, `anguloDoScore(1000) === 120`,
`anguloDoScore(750) === 60`, `comprimentoArco()` ≈ 335,1 (tolerância 0,01), `pontoNoArco(0)` = `(100, 24)`.

---

## 8. Gráficos (Recharts)

Recharts é a única biblioteca de gráfico. Tema central em `lib/chart-theme.ts`; **nenhum
componente de gráfico define cor, fonte ou grid inline**.

### 8.1 Tema

```ts
// lib/chart-theme.ts
// Strings `var(--…)` funcionam em atributos de apresentação SVG e re-tematizam no print (§10).
export const CHART = {
  font: 'var(--font-sans)',
  tick: { fontSize: 11, fill: 'var(--color-fg-tertiary)', fontVariantNumeric: 'tabular-nums' },
  axisLabel: { fontSize: 11, fill: 'var(--color-fg-secondary)' },
  grid: { stroke: 'var(--color-line-subtle)', strokeWidth: 1, vertical: false },
  axis: { axisLine: false, tickLine: false, tickMargin: 8 },
  cursor: { stroke: 'var(--color-line-strong)', strokeWidth: 1, strokeDasharray: '3 3' },
  series: {
    principal: 'var(--color-accent-400)',
    categoricas: [
      'var(--color-cat-1)', 'var(--color-cat-2)', 'var(--color-cat-3)',
      'var(--color-cat-4)', 'var(--color-cat-5)', 'var(--color-cat-6)',
    ],
    risco: {
      a: 'var(--color-risk-a)', b: 'var(--color-risk-b)',
      c: 'var(--color-risk-c)', d: 'var(--color-risk-d)', neutral: 'var(--color-risk-neutral)',
    },
  },
  bandas: {        // ReferenceArea das faixas de rating no histórico de score
    opacity: 0.08,
    label: { fontSize: 10, fill: 'var(--color-fg-tertiary)' },
  },
  line: { strokeWidth: 2, dot: false, activeDot: { r: 4, strokeWidth: 2, stroke: 'var(--color-surface-card)' } },
  area: { fillOpacity: 0.12, strokeWidth: 2 },
  bar: { radius: [2, 2, 0, 0] as [number, number, number, number], maxBarSize: 28, barGap: 4 },
  animation: false,   // isAnimationActive={false} em todas as séries (movimento só onde comunica, §9)
  margin: { top: 8, right: 8, bottom: 0, left: 0 },
} as const;
```

### 8.2 Regras de estilo

| Aspecto | Regra |
|---|---|
| Grid | Só linhas horizontais, `line-subtle`, sólidas 1px. `<CartesianGrid vertical={false} />`. |
| Eixos | Sem `axisLine`, sem `tickLine`. Ticks 11px `fg-tertiary` `tnum`. Eixo Y à esquerda com `width` calculado pelo maior rótulo (`tickFormatter` já compacto). |
| Rótulos de eixo | Evitar. Se necessário, na legenda do card (`SectionHeader.descricao`), não no gráfico. |
| Linhas | 2px, sem pontos (`dot={false}`), `activeDot` 4px. `type="monotone"` para série de score; `type="linear"` para financeiras. |
| Áreas | Preenchimento **plano** a 12% de opacidade. Proibido `<defs><linearGradient>`. |
| Barras | Raio 2px no topo, `maxBarSize 28`. Barra única por categoria usa `series.principal`; barras por rating usam `series.risco`. |
| Tooltip | Sempre `<ChartTooltip />` autoral (§8.3). Nunca o default. `cursor={CHART.cursor}`. |
| Legenda | Nunca a `<Legend>` do Recharts. Legenda autoral acima/abaixo em `type-caption` com quadrado 8px. |
| Animação | `isAnimationActive={false}` em toda série. Sem exceção. |
| Responsividade | `<ResponsiveContainer width="100%" height={H}>` com `H` fixo por uso: sparkline 40, tile 120, card 240, página 320. |
| Vazio | Sem dados → `EmptyState compacto`, não gráfico vazio. |
| Efeitos | Proibido: sombras em séries, brilho, 3D, donut com espessura variável, `label` em cada ponto, pontos animados, "glow" em `activeDot`, gráficos de radar decorativos. |
| Pizza/donut | Permitido **um** donut por página no máximo, espessura 12px, sem rótulos internos, valor central em `type-kpi`. Preferir `StackedBar`. |

### 8.3 `ChartTooltip`

```ts
interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color?: string; payload: Record<string, unknown> }>;
  label?: string | number;
  formatarRotulo?: (label: string | number) => string;     // padrão: formatarData(label, 'media')
  formatarValor: (valor: number, nome: string) => string;  // obrigatório: formatarMoedaCompacta | formatarPercentual | formatarScore
  extra?: (payload: Record<string, unknown>) => React.ReactNode;  // ex.: RatingBadge do ponto
}
```

Visual idêntico ao `Tooltip` (§6.13): bg `surface-raised`, borda `line-strong`, raio `radius-md`,
padding 8px 10px. Cabeçalho `type-caption` (data). Linhas `[quadrado 8px cor] nome  valor` com valor
em `tnum` alinhado à direita (grid 2 colunas, gap 12px). Sem seta.

### 8.4 Quando usar cada paleta

- **`series.principal` (acento)**: qualquer série única sem significado de risco — histórico de
  exposição, evolução do limite, distribuição de vencimentos, decomposição por dimensão (as 7 dimensões
  em barras **monocromáticas**, não arco-íris).
- **`series.risco`**: quando a categoria **é** um rating, severidade ou tendência — distribuição da
  carteira por rating, red flags por severidade, exposição por rating. Histórico de score usa
  `principal` para a linha e `ReferenceArea` das faixas em `bandas.opacity`.
- **`series.categoricas`**: séries múltiplas de entidades sem risco — exposição por tipo de operação
  (`VENDA_A_PRAZO` cat-1, `BARTER` cat-2, `CPR` cat-3), culturas, fontes de dados por agente, meses
  comparados. Ordem fixa pelo índice da categoria no enum; nunca embaralhar entre gráficos.
- **Proibido** usar `categoricas` para rating e `risco` para entidades. Se um gráfico mistura os
  dois (ex.: exposição por operação × rating), o rating vai para o eixo/ordem e a cor fica categórica,
  com `RatingBadge` no tooltip.

### 8.5 Formatação em eixos e tooltips

| Grandeza | Eixo (`tickFormatter`) | Tooltip |
|---|---|---|
| R$ | `formatarMoedaCompacta` sem "R$" (`{ prefixo: false }`) → `1,2 mi`, `850 mil` | `formatarMoeda` completo → `R$ 1.234.567,00` |
| Percentual (0..1) | `formatarPercentual(v, 0)` → `17%` | `formatarPercentual(v, 1)` → `17,1%` |
| Score | `formatarScore` → `604` | `formatarScore` + `RatingBadge` no `extra` |
| Datas (eixo X) | `formatarData(v, 'mes')` → `set/26` | `formatarData(v, 'media')` → `12 set 2026` |
| Dias | `formatarDias` → `90 d` (eixo) | `90 dias` |

---

## 9. Movimento

### 9.1 Vocabulário

| Token | Valor | Uso |
|---|---|---|
| `--duration-fast` | 120ms | hover/focus de cor e borda, aparição de tooltip, saída de qualquer coisa |
| `--duration-base` | 200ms | drawer, modal, chips, expandir/colapsar, aparição de linha nova em tabela/timeline |
| `--duration-slow` | 320ms | troca de etapa do pipeline, entrada de card recalculado |
| `--duration-gauge` | 600ms | preenchimento do gauge, contagem do número, barras de `FactorBar` na montagem |
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | entradas e transições de estado |
| `--ease-exit` | `cubic-bezier(0.4, 0, 1, 1)` | saídas |
| `--ease-gauge` | `cubic-bezier(0.16, 1, 0.3, 1)` | gauge, barras (desacelera longo, sem overshoot) |

### 9.2 Onde a animação é permitida

1. **Pipeline da Nova Análise** (fluxo A). Quatro etapas (Coletor & Parser → Risco Agro & Climático →
   Motor de Decisão & Scoring → Sintetizador). Cada etapa: ícone em `fg-tertiary` → `LoaderCircle`
   girando (`1s linear infinite`) em `accent-400` → `Check` em `accent-400`; conector entre etapas
   preenche da esquerda para a direita em `--duration-slow`; etapas entram com stagger de 80ms.
   Os três primeiros estágios são determinísticos e completam em ≤ 1,2s total (tempo **encenado**,
   já que o motor é síncrono — rotular como "processamento local"); o quarto exibe o streaming real.
   Ao concluir, os cards de resultado aparecem com `translateY(4px) → 0` + opacidade em `--duration-slow`, stagger 60ms.
2. **Streaming de texto**: cursor piscando `steps(2, end) 1s infinite`; texto novo aparece sem
   fade (aparição de caracteres já é o movimento).
3. **Gauge** (§7.6) e **`FactorBar`**: barras crescem de 0 em `--duration-gauge` na montagem; ao
   recalcular, transitam para o novo valor.
4. **Recalculo por evento simulado** (D10): KPIs afetados recebem um flash de fundo `accent-tint → transparent`
   em 800ms (`--ease-exit`) uma única vez; a linha nova da timeline entra com `translateY(−4px)` + opacidade.
5. **Transições de estado de controle**: cor, borda, fundo, opacidade em `--duration-fast`.
6. **Drawer/Modal/Tooltip**: conforme §6.11–6.13.

### 9.3 Proibido

Bounce, spring com overshoot, parallax, gradientes animados, shimmer em skeleton (pulso de opacidade
é o limite), contagem animada fora do gauge, rotação de ícones fora do `LoaderCircle`, hover que move
elementos (`translate`/`scale` em hover), animação de entrada em tabelas ao ordenar, confete de
qualquer natureza, transição de rota com movimento.

### 9.4 `prefers-reduced-motion`

```css
@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-fast: 0ms; --duration-base: 0ms; --duration-slow: 0ms; --duration-gauge: 0ms;
  }
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
  .streaming-cursor { animation: none; opacity: 1; }
  .pipeline-spinner { animation: none; }  /* mostra ícone estático Loader com aria-busy */
}
```

O hook `useReducedMotion()` (autoral, `matchMedia`) desliga a contagem do gauge e o stagger.

---

## 10. Impressão (parecer e Project Canvas)

Arquivo `app/print.css`, importado em `globals.css` dentro de `@media print`. Rotas com
`window.print()`: `/clientes/[id]/parecer` e `/canvas` (D11.4). Botão "Exportar PDF" chama
`window.print()` após `document.fonts.ready`.

### 10.1 Tema claro no papel (sobrescrita de tokens)

```css
@media print {
  :root {
    color-scheme: light;
    --color-surface-page:   #FFFFFF;
    --color-surface-card:   #FFFFFF;
    --color-surface-raised: #FFFFFF;
    --color-surface-input:  #F5F7F9;
    --color-surface-hover:  #FFFFFF;
    --color-surface-sunken: #EEF1F4;
    --color-line-subtle:    #E2E6EA;
    --color-line-default:   #C9D0D8;
    --color-line-strong:    #9AA5B1;
    --color-fg-primary:     #111827;   /* 17,7:1 sobre branco */
    --color-fg-secondary:   #4B5563;   /*  7,6:1 */
    --color-fg-tertiary:    #6B7280;   /*  4,8:1 */
    --color-fg-disabled:    #9CA3AF;
    --color-fg-inverse:     #FFFFFF;
    --color-accent-400:     #0E7490;   /*  5,4:1 */
    --color-accent-500:     #0E7490;
    --color-accent-tint:    #E0F2FE;
    --color-accent-line:    #7DD3FC;
    --color-risk-a: #15803D; --color-risk-a-tint: #DCFCE7; --color-risk-a-line: #86EFAC;  /* 5,0:1 · 4,6:1 sobre tint */
    --color-risk-b: #854D0E; --color-risk-b-tint: #FEF3C7; --color-risk-b-line: #FCD34D;  /* 6,9:1 · 6,2:1 */
    --color-risk-c: #C2410C; --color-risk-c-tint: #FFEDD5; --color-risk-c-line: #FDBA74;  /* 5,2:1 · 4,5:1 */
    --color-risk-d: #B91C1C; --color-risk-d-tint: #FEE2E2; --color-risk-d-line: #FCA5A5;  /* 6,5:1 · 5,3:1 */
    --color-risk-neutral: #4B5563; --color-risk-neutral-tint: #F3F4F6; --color-risk-neutral-line: #D1D5DB;
    --color-cat-1: #0E7490; --color-cat-2: #4338CA; --color-cat-3: #6D28D9;
    --color-cat-4: #A21CAF; --color-cat-5: #475569; --color-cat-6: #78350F;
    --shadow-raised: none; --shadow-overlay: none;
  }
  html { font-size: 11px; line-height: 16px; }
  * { print-color-adjust: exact; -webkit-print-color-adjust: exact; }  /* badges e faixas do gauge mantêm cor */
  a { color: inherit; text-decoration: none; }
}
```

Como gauge, gráficos e badges usam `var(--…)`, tudo re-tematiza sem código adicional. Os hex do
tema de impressão também foram verificados: todos os textos de risco ≥ 4,5:1 sobre branco e sobre o
próprio tint (menores: C sobre tint 4,52:1; A sobre tint 4,57:1).

### 10.2 O que é escondido

`.no-print { display: none !important }` aplicado a: `SimulatedDataBanner variante="app"`, sidebar,
topbar, `CostCounter`, `SearchInput`, `FilterChips`, todos os `Button`/`IconButton`, copiloto
("Pergunte sobre este cliente"), controle "Simular evento", `Drawer`, `Modal`, `Tooltip`, cursor de
streaming, `<kbd>`, links "Ver todos", `Timeline` além dos 12 itens mais recentes, elementos
`aria-hidden`. `StreamingText` em estado ≠ `concluido`/`degradado` imprime o placeholder
*"[Parecer textual não gerado no momento da exportação]"* em `type-caption`.

### 10.3 Cabeçalho e rodapé de página

Elemento `.print-header` (renderizado sempre, `display: none` na tela, `display: flex` no print),
`position: fixed; top: 0` para repetir em toda página:

```
DADOS SIMULADOS — protótipo demonstrativo · nenhuma consulta real a órgão público
Lastro · Parecer de Risco · Vale do Araguaia Agropecuária Ltda. · CNPJ 12.345.678/0001-90 (simulado) · Ref. 12/09/2026
```

Primeira linha em `type-eyebrow` com ícone `FlaskConical` e borda inferior 1px `line-strong`; segunda
em `type-caption`. Altura 40px; `body { padding-top: 48px }` no print. Rodapé `.print-footer`
fixo: *"Gerado por Lastro em 12/09/2026 14:32 · Analista: Persona Demo · Decisão final sujeita à
avaliação do analista responsável."* em `type-caption`. Numeração de página via `@page` não é
confiável entre navegadores — omitir.

### 10.4 Quebras de página

```css
@media print {
  @page { size: A4 portrait; margin: 14mm 12mm 16mm; }
  .print-section, .card, tr, .evidence-card, .timeline-item, .kpi-tile { break-inside: avoid; }
  h1, h2, h3, .section-header { break-after: avoid; }
  .print-break-before { break-before: page; }
  table { break-inside: auto; } thead { display: table-header-group; }
  .score-gauge { width: 200px; }  /* força tamanho md no papel */
}
```

Ordem do parecer impresso e quebras: (1) cabeçalho do cliente + gauge + KPIs de PD/RJ + veto;
(2) recomendação com aviso obrigatório; `.print-break-before` (3) decomposição por dimensão +
`FactorBar`; (4) red flags; `.print-break-before` (5) garantias, `StackedBar`, Stay Period se ativo;
(6) "por que mudou" + timeline; (7) evidências (cada `EvidenceCard` indivisível); (8) trilha de decisão.

### 10.5 Project Canvas (`/canvas`)

```css
@media print {
  .route-canvas { @page { size: A4 landscape; margin: 8mm; } }
  .canvas-grid {
    display: grid; grid-template-columns: repeat(5, 1fr); grid-template-rows: repeat(2, 1fr);
    gap: 4mm; height: 180mm; break-inside: avoid;
  }
  .canvas-block { border: 1px solid var(--color-line-strong); padding: 3mm; overflow: hidden; font-size: 8.5px; line-height: 12px; }
  .canvas-block h3 { font-size: 9px; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 2mm; }
}
```

**Exatamente uma página** (D1): os 10 blocos da §7.1 do desafio em grade 5×2. Sem imagem, sem
gráfico dentro dos blocos; cabeçalho de dados simulados idem ao §10.3, reduzido a uma linha.
O teste E2E de Playwright verifica `page.pdf({ format: 'A4', landscape: true })` com 1 página.

---

## 11. Formatadores (`lib/format.ts`)

Funções puras, sem `Date.now()`; datas relativas recebem a referência explicitamente (coerente com o
motor, §14). `Intl` com `locale 'pt-BR'`. Arredondamento **sempre `halfExpand`** (o "meio para cima
comercial" que analista espera: 0,125 → 0,13; −0,125 → −0,13). Sinal negativo é **U+2212**.

```ts
export const MENOS = '−';
const nbsp = ' ';

/** "R$ 1.234.567,00" · "−R$ 1.234,00" · casas 2 padrão; 0 para tabelas de grandes valores. */
export function formatarMoeda(
  valor: number,
  opts?: { casas?: 0 | 2; sinal?: boolean; prefixo?: boolean }   // sinal=true força "+" em positivos
): string;
// Intl.NumberFormat('pt-BR', { style:'currency', currency:'BRL', minimumFractionDigits: casas, maximumFractionDigits: casas, roundingMode:'halfExpand' })
// Pós-processa: troca "-" por MENOS, garante "R$" + NBSP. NaN/undefined → "—" (U+2014).

/**
 * Abreviada. Regras (aplicadas ao |valor| já arredondado na escala-alvo, para evitar "R$ 1.000 mil"):
 *   |v| ≥ 1e9  → "R$ 1,2 bi"   (1 casa, sempre — inclusive ",0")
 *   |v| ≥ 1e6  → "R$ 1,2 mi"   (1 casa, sempre)
 *   |v| ≥ 1e3  → "R$ 850 mil"  (0 casas)
 *   |v| < 1e3  → formatarMoeda(valor, { casas: 2 })
 * Promoção: se round(v/1e3) ≥ 1000 → trata como mi; se round(v/1e6, 1) ≥ 1000 → bi.
 * Ex.: 999.600 → "R$ 1,0 mi" · 2.000.000 → "R$ 2,0 mi" · 1.480.000 → "R$ 1,5 mi" · 350 → "R$ 350,00"
 */
export function formatarMoedaCompacta(valor: number, opts?: { prefixo?: boolean; sinal?: boolean }): string;

/**
 * Entrada é FRAÇÃO (0,1713 → "17,1%"). Casas por contexto — o chamador é obrigado a escolher:
 *   PD / risco de RJ → 1  ·  coberturas e utilização de limite → 0  ·  quebra de safra e desvios → 0
 *   variação percentual (delta) → 1, com sinal
 * Sem espaço antes de "%". ≥ 1 permitido (cobertura 132%). Valores 0 < v < 0,0005 com casas=1 → "<0,1%".
 */
export function formatarPercentual(fracao: number, casas: 0 | 1 | 2, opts?: { sinal?: boolean }): string;

/** Inteiro sem separador de milhar: 604 → "604" · 1000 → "1000". Math.round (half-up para não-negativos). Clamp 0..1000. */
export function formatarScore(score: number): string;

/** "+12" · "−108" · "0" (zero sem sinal). Sufixo opcional: formatarDelta(-108, 'pts') → "−108 pts". */
export function formatarDelta(delta: number, sufixo?: 'pts' | 'pp' | ''): string;

/** Inteiro ou decimal genérico em pt-BR. formatarNumero(18342) → "18.342" · (0.4231, 2) → "0,42". */
export function formatarNumero(valor: number, casas?: 0 | 1 | 2): string;

/** Tokens: 18342 → "18,3k" · 1_250_000 → "1,25M" · < 1000 → "842". 1 casa (k), 2 casas (M). */
export function formatarTokens(n: number): string;

/**
 * Datas de ISO ('2026-09-12' ou ISO datetime). Interpretadas em fuso America/Sao_Paulo.
 *   'curta' → "12/09/2026"       'media' → "12 set 2026"     'longa' → "12 de setembro de 2026"
 *   'mes'   → "set/26"           'mesAno'→ "setembro de 2026"
 * Meses abreviados em minúsculas sem ponto (padrão Intl pt-BR remove o ponto via replace).
 */
export function formatarData(iso: string, formato?: 'curta' | 'media' | 'longa' | 'mes' | 'mesAno'): string;

/** "12/09/2026 14:32" (24h, sem segundos). */
export function formatarDataHora(iso: string): string;

/**
 * Relativa a `referencia` (obrigatória — nunca Date.now()). Diferença em dias inteiros de calendário.
 *   0 → "hoje" · 1 → "ontem" · −1 → "amanhã" · 2..29 → "há 12 dias" · 30..364 → "há 3 meses" (round(d/30))
 *   ≥ 365 → "há 2 anos" (round(d/365)) · futuro: "em 12 dias" / "em 2 meses"
 * Implementação: Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' }).
 */
export function formatarDataRelativa(iso: string, referencia: string): string;

/** "1 dia" · "12 dias" · "0 dias". Variante curta para eixos: formatarDias(90, true) → "90 d". */
export function formatarDias(n: number, curto?: boolean): string;

/**
 * Aceita dígitos puros ou já formatado. Detecta pelo comprimento (11 = CPF, 14 = CNPJ).
 *   CNPJ → "12.345.678/0001-90" (dado público; nunca mascarado)
 *   CPF  → "•••.456.789-••" quando mascarar (padrão true); "123.456.789-09" quando false
 * O sufixo " (simulado)" NÃO é do formatador — é <Badge variante="simulado" /> ao lado.
 * Entrada inválida → devolve a string original inalterada.
 */
export function formatarDocumento(doc: string, opts?: { mascarar?: boolean }): string;

/** "Soja, Milho safrinha e Algodão" — Intl.ListFormat pt-BR conjunction long. */
export function formatarLista(itens: string[]): string;

/** Clamp de PD/RJ para exibição: probabilidade 1 com eventoJaOcorrido → "Evento ocorrido", não "100,0%". */
export function formatarProbabilidadeRJ(risco: RiscoRJ): string;
```

### 11.1 Tabela de casos de teste obrigatórios (Vitest, `lib/format.test.ts`)

| Chamada | Esperado |
|---|---|
| `formatarMoeda(1234567)` | `R$ 1.234.567,00` |
| `formatarMoeda(-1234.5)` | `−R$ 1.234,50` |
| `formatarMoeda(0.125)` | `R$ 0,13` |
| `formatarMoeda(5_000_000, { casas: 0 })` | `R$ 5.000.000` |
| `formatarMoedaCompacta(1_480_000)` | `R$ 1,5 mi` |
| `formatarMoedaCompacta(999_600)` | `R$ 1,0 mi` |
| `formatarMoedaCompacta(850_000)` | `R$ 850 mil` |
| `formatarMoedaCompacta(999_499)` | `R$ 999 mil` |
| `formatarMoedaCompacta(2_000_000)` | `R$ 2,0 mi` |
| `formatarMoedaCompacta(350)` | `R$ 350,00` |
| `formatarMoedaCompacta(-3_200_000)` | `−R$ 3,2 mi` |
| `formatarMoedaCompacta(1_250_000, { prefixo: false })` | `1,3 mi` |
| `formatarPercentual(0.1713, 1)` | `17,1%` |
| `formatarPercentual(0.1713, 0)` | `17%` |
| `formatarPercentual(1.32, 0)` | `132%` |
| `formatarPercentual(0.0003, 1)` | `<0,1%` |
| `formatarPercentual(-0.045, 1, { sinal: true })` | `−4,5%` |
| `formatarPercentual(0.045, 1, { sinal: true })` | `+4,5%` |
| `formatarScore(603.5)` | `604` |
| `formatarScore(1200)` | `1000` |
| `formatarDelta(-108)` | `−108` |
| `formatarDelta(12, 'pts')` | `+12 pts` |
| `formatarDelta(0)` | `0` |
| `formatarData('2026-09-12')` | `12/09/2026` |
| `formatarData('2026-09-12', 'media')` | `12 set 2026` |
| `formatarData('2026-09-12', 'longa')` | `12 de setembro de 2026` |
| `formatarData('2026-09-12', 'mes')` | `set/26` |
| `formatarDataHora('2026-09-12T14:32:00-03:00')` | `12/09/2026 14:32` |
| `formatarDataRelativa('2026-09-12', '2026-09-12')` | `hoje` |
| `formatarDataRelativa('2026-09-11', '2026-09-12')` | `ontem` |
| `formatarDataRelativa('2026-08-31', '2026-09-12')` | `há 12 dias` |
| `formatarDataRelativa('2026-06-10', '2026-09-12')` | `há 3 meses` |
| `formatarDataRelativa('2026-09-24', '2026-09-12')` | `em 12 dias` |
| `formatarDocumento('12345678000190')` | `12.345.678/0001-90` |
| `formatarDocumento('12345678909')` | `•••.456.789-••` |
| `formatarDocumento('123.456.789-09', { mascarar: false })` | `123.456.789-09` |
| `formatarDias(1)` / `formatarDias(90, true)` | `1 dia` / `90 d` |
| `formatarTokens(18342)` | `18,3k` |
| `formatarLista(['Soja','Milho safrinha','Algodão'])` | `Soja, Milho safrinha e Algodão` |

Nota de implementação: `Intl.NumberFormat` com `roundingMode` exige Node ≥ 20 e navegadores 2023+;
Node 22 está disponível (D3). O fallback para ambientes sem suporte não é necessário.

---

## 12. Checklist de aceitação do design system

Um PR de UI só passa se:

- [ ] Nenhum hex fora de `globals.css`, `print.css` e `chart-theme.ts`.
- [ ] Nenhuma ocorrência das proibições da tabela do §0.
- [ ] Toda coluna numérica de `DataTable` tem `numerica: true`.
- [ ] Todo rating, severidade e tendência renderiza via `RATING`/`SEVERIDADE`/`TENDENCIA` (§3) — nunca cor avulsa.
- [ ] Todo `EvidenceCard` mostra `Badge variante="simulado"`.
- [ ] Toda sigla do glossário (§6.13) aparece envolvida em `<Termo>` na primeira ocorrência de cada página.
- [ ] `ScoreGauge` em modo veto mostra hachura, anel externo, par de badges e rótulo do veto (teste visual Playwright com cliente em RJ).
- [ ] Recharts: nenhuma `<Legend>`, nenhum `<defs>`, `isAnimationActive={false}` em todas as séries.
- [ ] `/clientes/[id]/parecer` e `/canvas` imprimem em claro com cabeçalho de dados simulados (Playwright `emulateMedia({ media: 'print' })`).
- [ ] `prefers-reduced-motion` desliga gauge, stagger e cursor (Playwright `emulateMedia({ reducedMotion: 'reduce' })`).
- [ ] `lib/format.test.ts` verde com todos os casos do §11.1.
