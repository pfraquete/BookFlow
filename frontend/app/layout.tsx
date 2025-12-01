import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'BookFlow - Diagramação de Livros com IA',
  description: 'Sistema inteligente de diagramação e formatação de livros',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <body className="font-sans">
        <div className="min-h-screen bg-gray-50">
          {children}
        </div>
      </body>
    </html>
  )
}
