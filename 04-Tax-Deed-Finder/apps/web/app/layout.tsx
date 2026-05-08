import type { Metadata } from "next";
import { Cinzel, IBM_Plex_Sans, DM_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import Providers from "@/components/Providers";

const cinzel = Cinzel({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  variable: "--font-cinzel",
});
const ibmPlex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-ibm",
});
const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "LandHQ — Monitor de Leilões de Tax Deed",
  description: "Monitoramento automatizado de imóveis em leilão fiscal nos EUA",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${cinzel.variable} ${ibmPlex.variable} ${dmMono.variable}`}>
      <body className="bg-bg-primary text-parchment font-ibm">
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 ml-64 p-8">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
