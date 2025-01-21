import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Cycling Race Predictor',
  description: 'Predict winning chances for top cyclists in major races',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} app-background`}>
        <div className="main-content">
          {children}
        </div>
      </body>
    </html>
  )
}
