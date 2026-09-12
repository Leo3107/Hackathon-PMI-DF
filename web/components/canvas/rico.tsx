import { Fragment } from "react";

/**
 * Renderiza texto com marcação mínima: `**negrito**` e `*itálico*`.
 * Existe para que o texto final da spec 07 fique em strings literais,
 * sem ser reescrito em JSX e sem quebrar a regra de lint de entidades.
 */
export function Rico({ texto }: { texto: string }) {
  const partesFortes = texto.split("**");
  return (
    <>
      {partesFortes.map((parte, i) =>
        i % 2 === 1 ? (
          <strong key={i}>{parte}</strong>
        ) : (
          <Fragment key={i}>{italico(parte, i)}</Fragment>
        ),
      )}
    </>
  );
}

function italico(trecho: string, chaveBase: number) {
  const partes = trecho.split("*");
  if (partes.length === 1) return trecho;
  return partes.map((parte, i) =>
    i % 2 === 1 ? (
      <em key={`${chaveBase}-${i}`}>{parte}</em>
    ) : (
      <Fragment key={`${chaveBase}-${i}`}>{parte}</Fragment>
    ),
  );
}

/** Lista de itens do corpo de um bloco, com marcador fino. */
export function ListaRica({ itens }: { itens: string[] }) {
  return (
    <ul className="canvas-lista">
      {itens.map((item, i) => (
        <li key={i}>
          <Rico texto={item} />
        </li>
      ))}
    </ul>
  );
}
