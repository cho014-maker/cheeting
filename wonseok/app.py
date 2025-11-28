import streamlit as st
import requests
import json
import re
from datetime import datetime

# --- 기본 설정 및 상수 ---
st.set_page_config(page_title="급식 알레르기 체커", page_icon="🍱", layout="centered")

OFFICIAL_ALLERGENS = {
    '1': '난류(계란)', '2': '우유', '3': '메밀', '4': '땅콩', '5': '대두(콩)',
    '6': '밀', '7': '고등어', '8': '게', '9': '새우', '10': '돼지고기',
    '11': '복숭아', '12': '토마토', '13': '아황산염', '14': '호두',
    '15': '닭고기', '16': '쇠고기', '17': '오징어', '18': '조개류(굴, 전복, 홍합 포함)'
}

DEFAULT_RISK_MAP = {
    '난류(계란)': ['계란말이', '스크램블', '마요네즈', '카스테라'],
    '우유': ['치즈', '요거트', '아이스크림', '버터', '크림소스', '라떼'],
    '밀': ['빵', '국수', '라면', '파스타', '튀김옷', '밀가루', '만두피'],
    '대두(콩)': ['두부', '콩나물', '된장', '간장', '두유'],
    '새우': ['새우튀김', '새우', '액젓', '깐쇼새우'],
    '돼지고기': ['제육볶음', '돈까스', '햄', '소시지', '삼겹살']
}

# --- 세션 상태 초기화 (React의 useState 유사) ---
if 'risk_map' not in st.session_state:
    st.session_state.risk_map = DEFAULT_RISK_MAP.copy()
if 'safe_map' not in st.session_state:
    st.session_state.safe_map = {}
if 'analyzed_data' not in st.session_state:
    st.session_state.analyzed_data = None
if 'all_menu_items' not in st.session_state:
    st.session_state.all_menu_items = []

# --- 유틸리티 함수 ---

def check_gemini(menu_item, allergen, api_key):
    """Gemini API를 사용하여 알레르기 포함 여부를 확인합니다."""
    if not api_key:
        return False
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"Is the Korean dish '{menu_item}' highly likely to contain the ingredient '{allergen}' as a main ingredient or part of its actual preparation? Do not consider side dishes. Answer ONLY 'Yes' or 'No'."
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        text = response_data['candidates'][0]['content']['parts'][0]['text'].strip().lower()
        return text.startswith('yes')
    except Exception as e:
        st.error(f"Gemini API 오류: {e}")
        return False

def fetch_and_analyze(api_key, query_date, user_allergens_input, gemini_key):
    """NEIS API에서 급식 데이터를 가져와 분석합니다."""
    formatted_date = query_date.replace("-", "")
    ATPT_OFCDC_SC_CODE = "F10"  # 광주광역시 교육청
    SD_SCHUL_CODE = "7380076"   # 문흥중학교
    
    url = f"https://open.neis.go.kr/hub/mealServiceDietInfo?KEY={api_key}&Type=json&pSize=100&pIndex=1&ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}&SD_SCHUL_CODE={SD_SCHUL_CODE}&MLSV_YMD={formatted_date}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            analyze_meals(rows, user_allergens_input, gemini_key)
        elif "RESULT" in data and data["RESULT"]["CODE"] == "INFO-200":
            st.error("해당 날짜에 급식 정보가 없습니다.")
            st.session_state.analyzed_data = None
        else:
            st.error("데이터를 불러오지 못했습니다. API 키를 확인하세요.")
            st.session_state.analyzed_data = None
            
    except Exception as e:
        st.error(f"네트워크 오류: {e}")
        st.session_state.analyzed_data = None

def analyze_meals(rows, user_allergens_input, gemini_key):
    """급식 데이터를 순회하며 알레르기 위험도를 분석합니다."""
    user_allergens = [s.strip() for s in user_allergens_input.split(',') if s.strip()]
    user_allergens_lower = set(a.lower() for a in user_allergens)
    
    analyzed_rows = []
    collected_menu_items = set()
    
    for row in rows:
        dish_name = row['DDISH_NM']
        # <br/> 태그로 메뉴 분리
        dish_parts = [p.strip() for p in dish_name.split('<br/>') if p.strip()]
        
        menu_display_data = []
        meal_risk_found = False
        total_codes = set()
        
        for raw_item in dish_parts:
            # 정규식으로 알레르기 코드 추출 (예: 밥(1.2.5))
            code_match = re.search(r'\(([\d\.\s]+)\)', raw_item)
            codes = []
            if code_match:
                codes = re.split(r'\s+', code_match.group(1).replace('.', ' '))
            
            clean_item = re.sub(r'\([\d\.\s]+\)', '', raw_item).strip()
            clean_item_lower = clean_item.lower()
            collected_menu_items.add(clean_item)
            
            for c in codes:
                total_codes.add(c)
                
            item_allergy_names = [OFFICIAL_ALLERGENS.get(c, "") for c in codes if c in OFFICIAL_ALLERGENS]
            
            risk_level = "NONE"
            detected_allergen = ""
            
            # 1. 공식 코드 매칭
            for name in item_allergy_names:
                if name.lower() in user_allergens_lower:
                    risk_level = "RISK"
                    detected_allergen = name
                    break
            
            # 2. 커스텀 맵(Risk Map) 매칭
            if risk_level == "NONE":
                for user_alg in user_allergens_lower:
                    if user_alg in st.session_state.risk_map and clean_item in st.session_state.risk_map[user_alg]:
                        risk_level = "RISK"
                        detected_allergen = user_alg
                        break
            
            # 3. AI 검증 (Gemini)
            if risk_level == "NONE" and gemini_key:
                for user_alg in user_allergens_lower:
                    # 안전 맵(Safe Map)에 있으면 건너뜀
                    if user_alg in st.session_state.safe_map and clean_item in st.session_state.safe_map[user_alg]:
                        continue
                        
                    # 단순 키워드 매칭
                    if user_alg in clean_item_lower:
                        risk_level = "RISK"
                        detected_allergen = user_alg
                        break
                        
                    # Gemini 호출 (실제 앱에서는 속도 문제로 버튼 클릭 시 수행하는 것이 좋을 수 있음)
                    is_risky = check_gemini(clean_item, user_alg, gemini_key)
                    if is_risky:
                        risk_level = "SUSPICION"
                        detected_allergen = user_alg
                        break
            
            badge_html = ""
            if risk_level == "RISK":
                badge_html = f'<span style="color:red; font-weight:bold; font-size:0.9em; margin-left:4px;">({detected_allergen} 위험 ⚠️)</span>'
                meal_risk_found = True
            elif risk_level == "SUSPICION":
                badge_html = f'<span style="color:orange; font-weight:bold; font-size:0.9em; margin-left:4px;">({detected_allergen}? 의심 ❓)</span>'
            
            menu_display_data.append(f"{clean_item}{badge_html}")
            
        total_allergen_names = sorted([OFFICIAL_ALLERGENS.get(c, "") for c in total_codes if c in OFFICIAL_ALLERGENS])
        
        analyzed_rows.append({
            "type": row['MMEAL_SC_NM'],
            "menus": menu_display_data,
            "allergens": total_allergen_names,
            "risk_found": meal_risk_found
        })
        
    st.session_state.analyzed_data = analyzed_rows
    st.session_state.all_menu_items = sorted(list(collected_menu_items))

# --- UI 구성 ---

# 사이드바: 설정
with st.sidebar:
    st.header("⚙️ 설정")
    neis_key = st.text_input("NEIS API Key", type="password", help="나이스 교육정보 개방 포털에서 발급받은 키")
    gemini_key = st.text_input("Gemini API Key", type="password", help="AI 분석을 위한 구글 제미나이 키")
    user_allergens_input = st.text_input("나의 알레르기", placeholder="예: 우유, 새우, 복숭아")
    
    st.info("입력된 정보는 브라우저 새로고침 시 초기화됩니다.")

# 메인 화면
st.title("🍱 급식 알레르기 체커")
st.markdown("AI 기반 위험/의심 메뉴 분석 및 자가 학습 (문흥중학교)")

col1, col2 = st.columns([2, 1])
with col1:
    query_date = st.date_input("날짜 선택", datetime.now())
with col2:
    st.write("") # 줄바꿈 용
    st.write("") 
    analyze_btn = st.button("🔍 조회하기", type="primary", use_container_width=True)

if analyze_btn:
    if not neis_key:
        st.warning("NEIS API Key를 입력해주세요.")
    elif not user_allergens_input:
        st.warning("알레르기 정보를 입력해주세요.")
    else:
        with st.spinner("급식 정보를 분석하고 있습니다... (AI 분석 시 시간이 걸릴 수 있습니다)"):
            date_str = query_date.strftime("%Y%m%d")
            fetch_and_analyze(neis_key, date_str, user_allergens_input, gemini_key)

# 결과 표시
if st.session_state.analyzed_data:
    st.divider()
    for meal in st.session_state.analyzed_data:
        container_bg = "background-color: #fef2f2; border: 1px solid #fecaca;" if meal['risk_found'] else "background-color: #ffffff; border: 1px solid #e5e7eb;"
        
        with st.container():
            st.markdown(f"""
            <div style="padding: 15px; border-radius: 10px; margin-bottom: 10px; {container_bg}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                    <h3 style="margin:0; color:#374151;">{meal['type']}</h3>
                    {'<span style="color:red; font-weight:bold;">⚠️ 주의</span>' if meal['risk_found'] else '<span style="color:green; font-weight:bold;">✅ 안전</span>'}
                </div>
                <div style="margin-bottom: 10px; line-height: 1.6;">
                    {'  '.join([f'<span style="display:inline-block; margin-right:8px;">{m}</span>' for m in meal['menus']])}
                </div>
                <div style="font-size: 0.8em; color: #6b7280; background: white; padding: 5px; border-radius: 5px; display:inline-block;">
                    <b>공식 성분:</b> {', '.join(meal['allergens']) if meal['allergens'] else '없음'}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 학습 인터페이스
    st.divider()
    st.subheader("💾 AI & 데이터 학습시키기")
    st.caption("AI 판단 오류를 수정하거나 위험/안전 항목을 수동으로 추가합니다. (현재 세션 동안만 유지됩니다)")
    
    l_col1, l_col2 = st.columns(2)
    
    # 긍정 학습 (위험 추가)
    with l_col1:
        st.markdown("**👎 위험 추가 (Positive)**")
        pos_menu = st.selectbox("메뉴 선택", ["선택"] + st.session_state.all_menu_items, key="pos_menu_sel")
        pos_alg = st.selectbox("알레르기 선택", ["선택"] + [a.strip() for a in user_allergens_input.split(',') if a.strip()], key="pos_alg_sel")
        
        if st.button("위험 목록에 추가", key="btn_pos"):
            if pos_menu != "선택" and pos_alg != "선택":
                if pos_alg not in st.session_state.risk_map:
                    st.session_state.risk_map[pos_alg] = []
                
                if pos_menu not in st.session_state.risk_map[pos_alg]:
                    st.session_state.risk_map[pos_alg].append(pos_menu)
                    st.success(f"'{pos_menu}' -> '{pos_alg}' 위험군 등록 완료")
                    st.rerun() # 화면 갱신
                else:
                    st.info("이미 등록된 항목입니다.")

    # 부정 학습 (안전 추가)
    with l_col2:
        st.markdown("**👍 의심 제외 (Negative)**")
        neg_menu = st.selectbox("메뉴 선택", ["선택"] + st.session_state.all_menu_items, key="neg_menu_sel")
        neg_alg = st.selectbox("알레르기 선택", ["선택"] + [a.strip() for a in user_allergens_input.split(',') if a.strip()], key="neg_alg_sel")
        
        if st.button("안전 목록에 추가", key="btn_neg"):
            if neg_menu != "선택" and neg_alg != "선택":
                if neg_alg not in st.session_state.safe_map:
                    st.session_state.safe_map[neg_alg] = []
                
                if neg_menu not in st.session_state.safe_map[neg_alg]:
                    st.session_state.safe_map[neg_alg].append(neg_menu)
                    st.success(f"'{neg_menu}' -> '{neg_alg}' 안전군 등록 완료")
                    st.rerun() # 화면 갱신
                else:
                    st.info("이미 등록된 항목입니다.")
