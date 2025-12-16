import { ReactNode } from "react";
import Navbar from "./Navbar";
import Head from "next/head";

type LayoutProps = {
  children: ReactNode;
};

export default function Layout({ children }: LayoutProps) {
  return (
    <>
      <Head>
        <title>Agentic Baseball Simulator</title>
        <meta name="description" content="A baseball simulation game powered by AI agents" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <Navbar />
      <main style={{ minHeight: "calc(100vh - 64px)" }}>
        {children}
      </main>
    </>
  );
}
