import type { Metadata } from "next";
import type { ReactNode } from "react";
import { I18nProvider } from "@/lib/i18n";

import "./globals.css";

export const metadata: Metadata = {
  title: "ChangeProof",
  description: "Evidence-backed database change risk analysis",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="ko">
      <body>
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
