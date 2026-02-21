import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
}); 

export const metadata: Metadata = {
  title: "주식 AI 에이전트",
  description: "AI가 분석해주는 매일의 주식 시장 요약",
  verification: {
    google: "7Mm6OvLkEKXRXU0eZZune2CuZoZwRdKikruNXDMMH6s",
    other: {
      "naver-site-verification": "fd7c7a2a4a893dab722c75eab1ab9255a97ccf56",
      "google-adsense-account": "ca-pub-1583778688623269",
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1583778688623269"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
