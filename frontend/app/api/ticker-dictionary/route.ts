import { NextRequest, NextResponse } from 'next/server';
import { API_BASE } from '@/lib/api';

// GET /api/ticker-dictionary — 티커 사전 목록 조회 프록시
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status');
    const market = searchParams.get('market');
    const qp = new URLSearchParams();
    if (status) qp.set('status', status);
    if (market) qp.set('market', market);
    const params = qp.toString() ? `?${qp.toString()}` : '';

    const res = await fetch(`${API_BASE}/api/ticker-dictionary${params}`, {
      cache: 'no-store',
    });

    if (!res.ok) {
      return NextResponse.json({ error: '백엔드 응답 에러' }, { status: res.status });
    }

    return NextResponse.json(await res.json());
  } catch (error) {
    console.error('티커 사전 프록시 에러:', error);
    return NextResponse.json({ error: '데이터를 가져오지 못했습니다.' }, { status: 500 });
  }
}
