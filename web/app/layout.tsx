import "./globals.css";
import type { Metadata, Viewport } from "next";
import Shell from "@/components/Shell";

export const metadata: Metadata = { title: "cricintel: cricket intelligence", description: "See how cricket really works, ball by ball." };
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#070b16" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
