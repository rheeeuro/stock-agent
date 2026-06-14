"""kiwoom 데이터 서버 repository — 토큰 저장만 사용.

jongalab 의 repository/__init__.py 와 달리 다른 도메인 repo 를 re-export 하지 않는다
(kiwoom 서버에는 content/source/ticker 등 테이블 접근 코드가 없다).
`from core.repository import kiwoom_token` 형태의 서브모듈 import 만 사용한다.
"""
