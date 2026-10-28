import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
 title: "TradingQuant | Laboratorio cuantitativo",
 description: "Diseña, explora y valida algoritmos de trading con evidencia estadística.",
};
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
 return <html lang="es"><body>{children}</body></html>;
}
