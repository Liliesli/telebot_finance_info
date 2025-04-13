# 주식 정보 텔레그램 봇

실시간 주식 정보를 제공하는 텔레그램 봇입니다.

## 기능

- 주식 티커 심볼을 입력하면 실시간 주가 정보를 제공
- 현재가, 고가, 저가, 거래량 등 상세 정보 표시
- 이전 종가 대비 등락률 표시
- 거래량 비교 기능

## 설치 방법

1. 저장소 클론
```bash
git clone [저장소 URL]
```

2. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
`.env` 파일을 생성하고 다음 변수들을 설정하세요:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id
```

## 사용 방법

1. 봇 시작: `/start`
2. 주식 정보 조회: `/p [티커심볼]`
   예: `/p AAPL`, `/p MSFT`

## 기술 스택

- Python
- python-telegram-bot
- yfinance 