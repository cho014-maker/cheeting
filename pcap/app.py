import streamlit as st
import pandas as pd
from scapy.all import rdpcap, IP
import tempfile
import os
import warnings

# Scapy 내부의 불필요한 암호화 경고 메시지 차단
warnings.filterwarnings("ignore", category=UserWarning)

# 1. 웹 브라우저 레이아웃 및 탭 설정
st.set_page_config(page_title="커스텀 트래픽 분석기", layout="wide", page_icon="🔍")

st.title("🔍 사용자 정의 키워드 기반 트래픽 분석기")
st.markdown("추적하고 싶은 **도메인 핵심 키워드**와 **서비스 명칭**을 웹 화면에서 직접 입력한 뒤 패킷 파일을 업로드하여 분석하세요.")
st.markdown("---")

# 2. 사이드바(Sidebar)에서 사용자가 분석할 키워드를 동적으로 추가하는 구역
st.sidebar.header("⚙️ 분석 키워드 설정")
st.sidebar.markdown("패킷 내부에서 찾아낼 키워드와 서비스 이름을 지정해 주세요.")

# 기본 세팅값 제공 (사용자가 수정/삭제 가능)
if "custom_rules" not in st.session_state:
    st.session_state.custom_rules = [
        {"keyword": "youtube", "name": "동영상 스트리밍 (YouTube)"},
        {"keyword": "kakao", "name": "인스턴트 메신저 (KakaoTalk)"},
        {"keyword": "naver", "name": "웹 서핑 (Naver)"}
    ]

# 새로운 규칙 추가 입력창
with st.sidebar.form("add_rule_form", clear_on_submit=True):
    new_keyword = st.text_input("1. 탐색할 키워드 (예: netflix, instagram)", placeholder="소문자 권장")
    new_name = st.text_input("2. 표시할 서비스명 (예: 넷플릭스 영상)", placeholder="화면에 뜰 이름")
    submit_button = st.form_submit_button(label="➕ 규칙 추가하기")
    
    if submit_button:
        if new_keyword and new_name:
            st.session_state.custom_rules.append({"keyword": new_keyword.strip().lower(), "name": new_name.strip()})
            st.sidebar.success(f"'{new_name}' 규칙이 추가되었습니다!")
        else:
            st.sidebar.error("키워드와 서비스명을 모두 입력해 주세요.")

# 현재 적용된 규칙 리스트 보여주기 및 초기화 버튼
st.sidebar.markdown("### 📋 현재 적용 중인 규칙")
for idx, rule in enumerate(st.session_state.custom_rules):
    st.sidebar.text(f"• [{rule['keyword']}] ➔ {rule['name']}")

if st.sidebar.button("🔄 규칙 전체 초기화"):
    st.session_state.custom_rules = []
    st.rerun()

# 3. 메인 화면: 파일 업로드 컴포넌트 배치
uploaded_file = st.file_uploader("분석할 pcap / pcapng 패킷 파일을 선택하세요.", type=["pcap", "pcapng"])

if uploaded_file is not None:
    if not st.session_state.custom_rules:
        st.warning("⚠️ 사이드바에서 먼저 분석할 규칙(키워드)을 최소 1개 이상 추가해 주세요!")
        st.stop()

    with st.spinner("🚀 설정하신 커스텀 규칙으로 패킷 데이터를 정밀 분석 중입니다..."):
        
        # 임시 파일 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pcapng") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            packets = rdpcap(tmp_path)
        except Exception as e:
            st.error(f"❌ 파일을 읽는 중 오류가 발생했습니다: {e}")
            os.unlink(tmp_path)
            st.stop()

        os.unlink(tmp_path)

        # [분석 로직] 1단계: 웹에서 입력받은 규칙(st.session_state.custom_rules)을 기반으로 IP 매핑
        ip_to_service = {}
        for pkt in packets:
            if pkt.haslayer(IP):
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst
                pkt_bytes = bytes(pkt)
                
                # 사용자가 입력한 키워드들을 순회하며 패킷 매칭
                for rule in st.session_state.custom_rules:
                    # 문자열 키워드를 바이너리 바이트(bytes)로 변환하여 검색
                    target_bytes = rule["keyword"].encode('utf-8')
                    if target_bytes in pkt_bytes:
                        ip_to_service[src_ip] = rule["name"]
                        ip_to_service[dst_ip] = rule["name"]
                        break # 한 번 매칭되면 다음 패킷으로

        # [분석 로직] 2단계: 매핑 완료된 지도를 기준으로 전체 패킷 통계 집계
        traffic_data = []
        for pkt in packets:
            if pkt.haslayer(IP):
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst
                packet_size = len(pkt)
                
                if src_ip in ip_to_service:
                    service = ip_to_service[src_ip]
                elif dst_ip in ip_to_service:
                    service = ip_to_service[dst_ip]
                else:
                    service = "Unknown (지정되지 않은 암호화 트래픽)"
                    
                traffic_data.append([service, packet_size])

        # 4. 결과 시각화 출력
        if not traffic_data:
            st.warning("⚠️ 파일 내에 분석 가능한 IPv4 패킷이 존재하지 않습니다.")
        else:
            df = pd.DataFrame(traffic_data, columns=['Service_Domain', 'PacketSize'])
            summary = df.groupby('Service_Domain').agg(
                PacketCount=('PacketSize', 'count'),
                AvgSize=('PacketSize', 'mean'),
                TotalData_KB=('PacketSize', lambda x: x.sum() / 1024)
            ).reset_index()
            summary = summary.sort_values(by='TotalData_KB', ascending=False)

            st.success(f"✅ 분석 완료! 설정된 규칙을 바탕으로 총 {len(packets):,}개의 패킷 분석을 마쳤습니다.")
            
            # 대시보드 지표 카드
            m1, m2, m3 = st.columns(3)
            m1.metric("📊 총 분석 패킷 수", f"{len(df):,} 개")
            m2.metric("🔍 매칭된 서비스 종류", f"{df['Service_Domain'].nunique()} 개")
            
            total_kb = summary['TotalData_KB'].sum()
            if total_kb > 1024:
                m3.metric("💾 총 트래픽 용량", f"{total_kb / 1024:.2f} MB")
            else:
                m3.metric("💾 총 트래픽 용량", f"{total_kb:.2f} KB")

            st.markdown("###")

            # 레이아웃 배치
            left_col, right_col = st.columns([1.3, 1])

            with left_col:
                st.subheader("📈 지정 서비스별 누적 트래픽 용량 (KB)")
                st.bar_chart(data=summary, x="Service_Domain", y="TotalData_KB", color="#e67e22")

            with right_col:
                st.subheader("📋 실시간 통계 보고서 테이블")
                display_df = summary.copy()
                display_df['PacketCount'] = display_df['PacketCount'].map('{:,} 개'.format)
                display_df['AvgSize'] = display_df['AvgSize'].map('{:,.1f} Byte'.format)
                display_df['TotalData_KB'] = display_df['TotalData_KB'].map('{:,.2f} KB'.format)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
