from flask import Flask, render_template, request
import requests
import json
from datetime import datetime
import functools

app = Flask(__name__)

# --- 설정 정보 ---
API_KEY = "YOUR_API_KEY"  # <-- 여기에 발급받은 API 키를 넣으세요!
BASE_URL = "https://open.api.nexon.com"
HEADERS = {
    "x-nxopenapi-api-key": API_KEY
}

# --- 선수 메타데이터 캐시 (SPID -> 선수 이름) ---
SPID_MAP = {}
# --- 선수 시세 정보 캐시 (SPID -> 가격) ---
PRICE_CACHE = {}

# --- 유틸리티 함수 ---

def load_spid_metadata():
    """선수 고유 식별자(spid) 메타데이터를 불러와 SPID_MAP에 저장합니다."""
    global SPID_MAP
    url = f"{BASE_URL}/fconline/v1/metadata/spid"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        metadata = response.json()
        SPID_MAP = {str(item['id']): item['name'] for item in metadata}
        print("✅ 선수 메타데이터 로드 완료.")
    except Exception as e:
        print(f"❌ 선수 메타데이터 로드 실패: {e}")

@app.before_first_request
def setup():
    """Flask 애플리케이션 시작 시 메타데이터를 로드합니다."""
    load_spid_metadata()

def get_ouid(nickname):
    """닉네임으로 사용자 고유 식별자(ouid)를 조회합니다."""
    url = f"{BASE_URL}/fconline/v1/id?nickname={nickname}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json().get('ouid')
    except Exception:
        return None

def get_trade_history(ouid):
    """ouid로 사용자 거래 기록 (구매/판매)을 조회합니다."""
    trade_data = []
    
    # 구매 및 판매 내역을 각각 조회 (최근 50건씩)
    for trade_type in ['buy', 'sell']:
        url = f"{BASE_URL}/fconline/v1/user/trade?ouid={ouid}&trade_type={trade_type}&limit=50"
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            trade_data.extend(response.json().get('tradeInfo', []))
        except Exception:
            pass

    # 시간 순으로 정렬 (최신 순)
    trade_data.sort(key=lambda x: x['tradeDate'], reverse=True)
    return trade_data

# functools.lru_cache를 사용하여 SPID별 시세 정보를 캐싱하여 API 호출 제한에 대비
@functools.lru_cache(maxsize=128)
def get_player_average_price(spid):
    """선수의 현재 평균 거래가를 조회합니다."""
    spid_str = str(spid)
    url = f"{BASE_URL}/fconline/v1/trade/average?spid={spid_str}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        price_data = response.json()
        return price_data.get('tradePrice') # 최신 거래가 반환
    except Exception:
        return None

def get_player_image_url(spid):
    """선수 SPID를 이용해 이미지 URL을 생성합니다."""
    spid_str = str(spid)
    # FC Online 이미지 서버 URL 패턴을 사용하여 이미지 경로 생성
    # 시즌 ID는 SPID의 앞 3자리 또는 6자리 (100번대, 200000번대 등)로 구성됨
    # 가장 일반적인 미니 페이스온 경로는 seasonid/p(spid).png 또는 spid.png 형태가 많음.
    # 여기서는 spid 전체를 사용한 경로를 기본으로 사용합니다.
    
    # ⚠️ FC Online API는 공식 이미지 URL을 제공하지 않으므로, 이 URL은 비공식 경로이며
    # 넥슨의 정책 변화에 따라 작동하지 않을 수 있음에 유의해야 합니다.
    return f"https://fconline.nexon.com/externalAssets/player/face/{spid_str}.png"


# --- Flask 라우트 ---

@app.route('/', methods=['GET', 'POST'])
def index():
    trade_history = None
    nickname = None
    error = None

    if request.method == 'POST':
        nickname = request.form.get('nickname').strip()
        
        if not nickname:
            error = "닉네임을 입력해 주세요."
        else:
            ouid = get_ouid(nickname)
            if not ouid:
                error = f"'{nickname}'의 사용자 정보를 찾을 수 없습니다."
            else:
                history = get_trade_history(ouid)
                
                if not history:
                    error = f"'{nickname}'의 거래 기록이 없습니다."
                else:
                    trade_history = []
                    for record in history:
                        spid = str(record['spid'])
                        
                        player_name = SPID_MAP.get(spid, f"알 수 없는 선수 ({spid})")
                        current_price = get_player_average_price(spid)
                        image_url = get_player_image_url(spid)
                        
                        trade_history.append({
                            'tradeDate': record['tradeDate'],
                            'tradeType': '구매' if record['tradeType'] == 'buy' else '판매',
                            'playerName': player_name,
                            'saleValue': f"{record['saleValue']:,}",
                            'currentPrice': f"{current_price:,}" if current_price else "정보 없음",
                            'image_url': image_url
                        })

    return render_template('index.html', history=trade_history, nickname=nickname, error=error)

if __name__ == '__main__':
    # 디버그 모드로 실행하여 개발 편의성 높임
    app.run(debug=True)
