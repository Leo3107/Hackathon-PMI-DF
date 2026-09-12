import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Ha dois package-lock.json no repo (raiz e web/). Fixar a raiz de rastreio
  // evita o aviso de inferencia do Next e o empacotamento de arquivos de fora.
  outputFileTracingRoot: __dirname,
  /* config options here */
};

export default nextConfig;
