import type { Metadata } from "next";
import "./globals.css";
import WikiLayout from "./wiki-layout";

export const metadata: Metadata = {
  title: "Wiki / Knowledgebase",
  description: "Modern organizational wiki",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <WikiLayout>{children}</WikiLayout>
      </body>
    </html>
  );
}
