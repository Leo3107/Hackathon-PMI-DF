import type { Metadata } from "next";

import { FolhaCanvas } from "@/components/canvas/folha";

import { obterIndicadoresDaCarteira } from "./dados";
import "./canvas.css";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Project Canvas — Lastro",
  description:
    "Project Canvas do Lastro: inteligência de risco de crédito e alerta precoce de RJ no agronegócio. Hackathon PMI-DF 2026, desafio Krill Tech.",
};

export default async function PaginaCanvas() {
  const indicadores = await obterIndicadoresDaCarteira();
  return <FolhaCanvas indicadores={indicadores} />;
}
