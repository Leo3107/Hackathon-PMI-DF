import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Ha dois package-lock.json no repo (raiz e web/). Fixar a raiz de rastreio
  // evita o aviso de inferencia do Next e o empacotamento de arquivos de fora.
  outputFileTracingRoot: __dirname,
  // Empacotamento minimo para a imagem Docker: o Next copia so o que a app usa.
  // Na Vercel quem empacota e a propria plataforma, e o modo standalone so
  // atrapalha — por isso ele vale apenas fora dela.
  output: process.env.VERCEL ? undefined : 'standalone',
  /* config options here */
};

export default nextConfig;
