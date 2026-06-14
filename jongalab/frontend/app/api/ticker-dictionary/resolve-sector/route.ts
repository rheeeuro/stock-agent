import { NextRequest, NextResponse } from 'next/server';
import { API_BASE } from '@/lib/api';

// GET /api/ticker-dictionary/resolve-sector?ticker=... — 섹터 조회 프록시
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const ticker = searchParams.get('ticker');
    if (!ticker) {
      return NextResponse.json({ error: 'ticker가 필요합니다.' }, { status: 400 });
    }
    const qp = new URLSearchParams({ ticker });
    const res = await fetch(
      `${API_BASE}/api/ticker-dictionary/resolve-sector?${qp.toString()}`,
      { cache: 'no-store' },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '백엔드 응답 에러' }));
      return NextResponse.json(err, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch (error) {
    console.error('섹터 조회 프록시 에러:', error);
    return NextResponse.json({ error: '조회에 실패했습니다.' }, { status: 500 });
  }
}
