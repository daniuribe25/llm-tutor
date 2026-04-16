import type { Metadata } from "next";
import { Geist, JetBrains_Mono, Public_Sans } from "next/font/google";
import { HighlightJsTheme } from "@/components/highlight-js-theme";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import "katex/dist/katex.min.css";
import "./globals.css";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-sans",
});

const publicSansHeading = Public_Sans({
  subsets: ["latin"],
  variable: "--font-heading",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "LLM Tutor",
  description: "AI-powered tutor that searches the web to teach you anything",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        "h-full font-sans antialiased",
        geist.variable,
        publicSansHeading.variable,
        jetbrainsMono.variable
      )}
    >
      <head>
        <link
          id="hljs-theme-stylesheet"
          rel="stylesheet"
          href="/hljs/github-dark.css"
        />
      </head>
      <body className="h-full">
        <ThemeProvider>
          <HighlightJsTheme />
          <TooltipProvider delay={300}>{children}</TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
