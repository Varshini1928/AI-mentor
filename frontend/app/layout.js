import "./globals.css";

export const metadata = {
  title: "AI Dev Mentor",
  description: "AI-powered coding assistant: generate, review, and debug code.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-900 text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
