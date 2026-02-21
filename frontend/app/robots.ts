// src/app/robots.ts

import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*', // 모든 검색 엔진 봇 허용 (구글, 네이버, 빙 등)
      allow: '/',     // 모든 경로 접근 허용
    },
    // 방금 만든 사이트맵의 절대 경로 명시
    sitemap: 'https://stock.rheeeuro.com/sitemap.xml',
  };
}