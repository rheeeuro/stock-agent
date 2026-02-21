// src/app/sitemap.ts

import { MetadataRoute } from 'next';
import { DailySummary } from '@/types';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://stock.rheeeuro.com';

  // 1. 고정된 페이지 (메인 대시보드)
  const routes: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'always', // 매일 내용이 바뀌므로 always나 daily로 설정
      priority: 1.0,             // 메인 페이지이므로 중요도 최고점(1.0)
    },
  ];

  // 2. 동적 페이지 (과거 AI 투자 리포트들)
  try {
    // limit=100으로 넉넉하게 최근 100일치 데이터를 가져옵니다.
    const res = await fetch('http://127.0.0.1:8000/api/daily-summary-list?limit=100', {
      next: { revalidate: 3600 }, // 1시간(3600초)마다 사이트맵 갱신
    });

    if (res.ok) {
      const reports: DailySummary[] = await res.json();
      
      const dynamicRoutes = reports.map((report) => ({
        url: `${baseUrl}/report/${report.report_date}`,
        lastModified: new Date(), // DB에 created_at이 있다면 그걸 써도 좋습니다.
        changeFrequency: 'never' as const, // 과거 리포트는 내용이 안 바뀌므로 never
        priority: 0.8, // 세부 페이지는 중요도 0.8 정도 할당
      }));

      routes.push(...dynamicRoutes);
    }
  } catch (error) {
    console.error('사이트맵 생성 중 에러 발생:', error);
  }

  return routes;
}