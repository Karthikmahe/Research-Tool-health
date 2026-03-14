import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Research Tool Health",
  description: "AI-assisted health sciences literature search",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="page">
          <header className="header">
            <div>
              <h1>Research Tool Health</h1>
              <p>AI-assisted health sciences literature search</p>
            </div>
          </header>
          <main className="main">{children}</main>
          <footer className="footer">
            <span>Prototype • PubMed + Scopus • OpenAI Summaries</span>
          </footer>
        </div>
      </body>
    </html>
  );
}
