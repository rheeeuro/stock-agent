import { NextResponse } from 'next/server';
import { API_BASE } from '@/lib/api';

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/market-indices`, {
      cache: 'no-store'
    });

    if (!res.ok) {
      return NextResponse.json({ error: "백엔드 응답 에러" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("프록시 에러:", error);
    return NextResponse.json({ error: "데이터를 가져오지 못했습니다." }, { status: 500 });
  }
}
