import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '反向跟单交易机器人',
  description: '智能时间套利系统',
}

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  )
}
