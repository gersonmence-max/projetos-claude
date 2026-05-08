import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SMB OS",
  description: "Small and Medium Business Operating System",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
