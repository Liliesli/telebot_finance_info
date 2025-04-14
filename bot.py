import os
import logging
import re
from dotenv import load_dotenv
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import traceback
import time
from datetime import datetime, timedelta
from requests.exceptions import RequestException
import random
import asyncio

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


logger = logging.getLogger(__name__)

# 로그 기록용 함수
async def log_interaction(update: Update):
    chat_id = update.effective_chat.id
    user = update.effective_user.username or update.effective_user.full_name
    message = update.message.text
    timestamp = datetime.now().isoformat()
    logger.info(f"[{timestamp}] ChatID: {chat_id}, User: {user}, Message: {message}")
    print(f"[{timestamp}] ChatID: {chat_id}, User: {user}, Message: {message}")


# 환경 변수 로드
load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
PORT = int(os.environ.get('PORT', '8080'))

# 허용된 채팅방 ID 리스트
AUTHORIZED_CHAT_IDS = [-1001234567890, -1009876543210] 



# Yahoo Finance API 요청 제한 처리를 위한 지연 시간 (초)
MIN_DELAY = 2  # 최소 2초 대기
MAX_DELAY = 5  # 최대 5초 대기

# 캐시 저장소
stock_cache = {}
CACHE_DURATION = timedelta(minutes=5)  # 5분간 캐시 유지

def format_large_number(number):
    """큰 숫자를 읽기 쉽게 포맷팅합니다."""
    if number >= 1_000_000_000:
        return f"{number/1_000_000_000:.2f}B"
    elif number >= 1_000_000:
        return f"{number/1_000_000:.2f}M"
    elif number >= 1_000:
        return f"{number/1_000:.2f}K"
    else:
        return f"{number:.2f}"

# def calculate_volume_ratio(volume, avg_volume):
#     """거래량 비율을 계산하고 화살표를 반환합니다."""
#     if avg_volume == 0:
#         return "➡️", 0
#     ratio = (volume / avg_volume - 1) * 100
#     arrow = "🔺" if ratio > 0 else "🔻" if ratio < 0 else "➡️"
#     return arrow, ratio

def is_cache_valid(ticker):
    """캐시가 유효한지 확인합니다."""
    if ticker not in stock_cache:
        return False
    cache_time = stock_cache[ticker]['timestamp']
    return datetime.now() - cache_time < CACHE_DURATION

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """봇 시작 시 환영 메시지를 보냅니다."""
    welcome_message = """
🚀 똑똑이봇
주식의 티커 심볼을 '/p $티커' 형식으로 입력

예시:
/p $AAPL
/p $MSFT
/p $GOOGL
    """ 
    try:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=welcome_message)
    except Exception as e:
        print(f"start 명령어 처리 중 에러: {str(e)}")
        logging.error(f"Error in start command: {str(e)}")

async def get_stock_data(ticker):
    """주식 정보를 안정적으로 가져옵니다."""
    # 캐시 확인
    if is_cache_valid(ticker):
        print(f"{ticker} 캐시된 데이터 사용")
        return stock_cache[ticker]['data']
    
    try:
        # API 요청 제한을 피하기 위한 랜덤 지연
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        await asyncio.sleep(delay)
        
        stock = yf.Ticker(ticker)
        # 기본 정보 확인
        info = stock.info
        if not info:
            raise Exception("주식 정보를 가져올 수 없습니다.")
        
        # 현재 가격과 기본 정보
        current_price = info.get('regularMarketPrice', 0)
        previous_close = info.get('previousClose', 0)
        day_high = info.get('dayHigh', 0)
        day_low = info.get('dayLow', 0)
        # market_cap = info.get('marketCap', 0)
        currency = info.get('currency', 'USD')
        
        # 회사 정보
        company_name = info.get('longName', ticker)
        
        if not current_price or not previous_close:
            raise Exception("가격 정보를 가져올 수 없습니다.")
        
        # 캐시 업데이트
        stock_data = {
            'company_name': company_name,
            'current_price': current_price,
            'previous_close': previous_close,
            'day_high': day_high,
            'day_low': day_low,
            # 'market_cap': market_cap,
            'currency': currency,
            # 'volume': volume,
            # 'avg_volume': avg_volume
        }
        
        stock_cache[ticker] = {
            'data': stock_data,
            'timestamp': datetime.now()
        }
        
        return stock_data
        
    except Exception as e:
        print(f"주식 데이터 가져오기 실패: {str(e)}")
        print(traceback.format_exc())
        raise

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """모든 메시지를 처리합니다."""
    try:
        chat_id = update.effective_chat.id
        
        # 채팅 ID 확인
        if chat_id not in AUTHORIZED_CHAT_IDS:
            print(f"권한 없는 채팅 ID 접근 시도: {chat_id}")
            return
        
        # 로그 기록
        await log_interaction(update)
        
        if update.message:
            text = update.message.text
            print(f"일반 채팅에서 받은 메시지: {text}")
        elif update.channel_post:
            text = update.channel_post.text
            print(f"채널에서 받은 메시지: {text}")
        else:
            print("처리할 수 없는 메시지 유형")
            return
            
        # /start 명령어 처리
        if text.lower() == '/start':
            await start(update, context)
            return
            
        # 주식 티커 명령어가 아닌 경우 무시
        if not text.startswith('/p $'):
            print("명령어가 아닌 메시지 무시")
            return
            
        # 티커 추출 (앞의 '/p $' 제거)
        ticker = text[4:].strip().upper()
        if not ticker:
            await context.bot.send_message(chat_id=chat_id, text="티커를 입력해주세요. 예: /p $AAPL")
            return
            
        print(f"처리할 티커: {ticker}")
        
        try:
            # 주식 정보 가져오기
            print(f"{ticker} 정보 가져오는 중...")
            stock_data = await get_stock_data(ticker)
            
            current_price = stock_data['current_price']
            previous_close = stock_data['previous_close']
            day_high = stock_data['day_high']
            day_low = stock_data['day_low']
            # market_cap = stock_data['market_cap']
            currency = stock_data['currency']
            company_name = stock_data['company_name']
            # volume = stock_data['volume']
            # avg_volume = stock_data['avg_volume']

            # 등락률 계산
            if previous_close > 0:
                change_percent = ((current_price - previous_close) / previous_close) * 100
                price_change = current_price - previous_close
            else:
                change_percent = 0
                price_change = 0
                
            # 화살표 이모지 선택 (색상 변경)
            price_arrow = "🟩" if change_percent > 0 else "🟥" if change_percent < 0 else "➡️"
            
            # # 거래량 비교
            # volume_arrow, volume_ratio = calculate_volume_ratio(volume, avg_volume)
            
            # 통화 기호 설정
            currency_symbol = "$" if currency == "USD" else "₩" if currency == "KRW" else currency
            
            # 응답 메시지 구성
            response = f"""📊 {company_name} [{currency_symbol}{ticker}]

{price_arrow} Change: {currency_symbol}{abs(price_change):.2f} ({change_percent:+.2f}%)
💰 Price [{currency}]: {currency_symbol}{current_price:.2f}
📈 High: {currency_symbol}{day_high:.2f}
📉 Low: {currency_symbol}{day_low:.2f}
"""
            print("응답 메시지 전송 중...")
            await context.bot.send_message(chat_id=chat_id, text=response)
            print("응답 전송 완료")
            
        except Exception as e:
            print(f"주식 정보 가져오기 실패: {str(e)}")
            print(traceback.format_exc())
            error_message = f"{ticker} 정보 가져오기 실패."
            await context.bot.send_message(chat_id=chat_id, text=error_message)
            logging.error(f"Error fetching stock info for {ticker}: {str(e)}")
            
    except Exception as e:
        print(f"메시지 처리 중 에러 발생: {str(e)}")
        print(traceback.format_exc())
        logging.error(f"Error in handle_message: {str(e)}")

def main():
    """봇을 실행합니다."""
    print("봇 시작 중...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 모든 메시지를 하나의 핸들러로 처리
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # 봇 실행
    print("봇이 메시지 대기 중...")
    
    # Render.com을 위한 웹훅 설정
    if os.environ.get('RENDER'):
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=os.environ.get('RENDER_EXTERNAL_URL')
        )
    else:
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 