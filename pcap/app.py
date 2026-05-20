import streamlit as st
import pandas as pd
from scapy.all import rdpcap, IP
import tempfile
import os
import warnings

# Scapy 내부의 불필요한 암호화 경고 메시지 차단
warnings.filterwarnings("ignore", category=UserWarning)

# 1. 웹 브라우저 레이아웃 및 탭 설정
st.set_page_config(page_title="네트워크 트래픽 분석기", layout="wide", page_icon="📊")

# 웹페이지 헤더 구역
st.title("📊 암호화 네트워크 트래픽 분석 대시보드")
st.markdown("와이어샤크로 캡처한 패킷 파일(`.pcap`, `.pcapng`)을 업로드하면, 내부 키워드를 추적하여 트래픽을 분류하고 시각화합니다.")
st.markdown("---")

# 2. 파일 업로드 컴포넌트 배치
uploaded_file = st.file_uploader("분석할 pcap / pcapng 패킷 파일을 선택하세요.", type=["pcap", "pcapng"])

if uploaded_file is not None:
    # 파일 분석 중 표시될 로딩 애니메이션
    with st.spinner("🚀 패킷 데이터를 정밀 분석하는 중입니다... 잠시만 기다려 주세요."):
        
        # Streamlit의 메모리 상 파일 데이터를 Scapy가 읽을 수 있도록 임시 파일로 변환
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pcapng") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            # 패킷 로드
            packets = rdpcap(tmp_path)
        except Exception as e:
            st.error(f"❌ 파일을 읽는 중 오류가 발생했습니다: {e}")
            os.unlink(tmp_path)
            st.stop()

        # 로드가 완료되면 안전하게 임시 파일 삭제
        os.unlink(tmp_path)

        # [분석 로직] 1단계: 키워드 기반 IP-서비스 매핑 지도 구축
        ip_to_service = {}
        for pkt in packets:
            if pkt.haslayer(IP):
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst
                pkt_bytes = bytes(pkt)
                
                # 바이너리 데이터 검색을 통한 서비스 식별
                if b"youtube" in pkt_bytes or b"googlevideo" in pkt_bytes or b"ytimg" in pkt_bytes:
                    ip_to_service[src_ip] = "동영상 스트리밍 (YouTube)"
                    ip_to_service[dst_ip] = "동영상 스트리밍 (YouTube)"
                elif b"kakao" in pkt_bytes or b"kakaocdn" in pkt_bytes:
                    ip_to_service[src_ip] = "인스턴트 메신저 (KakaoTalk)"
                    ip_to_service[dst_ip] = "인스턴트 메신저 (KakaoTalk)"
                elif b"naver" in pkt_bytes or b"pstatic" in pkt_bytes:
                    ip_to_service[src_ip] = "웹 서핑 (Naver)"
                    ip_to_service[dst_ip] = "웹 서핑 (Naver)"

        # [분석 로직] 2단계: 구축된 지도를 기반으로 전체 패킷 데이터 통계 집계
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
                    service = "Unknown (기타/기본암호화)"
                    
                traffic_data.append([service, packet_size])

        # 3. 데이터 시각화 및 웹 UI 구성
        if not traffic_data:
            st.warning("⚠️ 파일 내에 분석 가능한 IPv4 패킷이 존재하지 않습니다.")
        else:
            # Pandas 데이터프레임 변환 및 그룹화 집계
            df = pd.DataFrame(traffic_data, columns=['Service_Domain', 'PacketSize'])
            summary = df.groupby('Service_Domain').agg(
                PacketCount=('PacketSize', 'count'),
                AvgSize=('PacketSize', 'mean'),
                TotalData_KB=('PacketSize', lambda x: x.sum() / 1024)
            ).reset_index()
            summary = summary.sort_values(by='TotalData_KB', ascending=False)

            # 상단 핵심 지표 요약 박스 (Metrics)
            st.success(f"✅ 분석 완료! 총 {len(packets):,}개의 패킷 중에서 {len(ip_to_service)}개의 통신 호스트를 식별했습니다.")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("📊 총 분석 패킷 수", f"{len(df):,} 개")
            m2.metric("🔍 식별된 서비스 카테고리", f"{summary['Service_Domain'].nunique()} 개")
            
            total_kb = summary['TotalData_KB'].sum()
            if total_kb > 1024:
                m3.metric("💾 총 트래픽 용량", f"{total_kb / 1024:.2f} MB")
            else:
                m3.metric("💾 총 트래픽 용량", f"{total_kb:.2f} KB")

            st.markdown("###") # 여백 추가

            # 좌우 2분할 레이아웃 디자인 (왼쪽: 그래프, 오른쪽: 통계 표)
            left_col, right_col = st.columns([1.3, 1])

            with left_col:
                st.subheader("📈 서비스별 누적 트래픽 용량 (KB)")
                # Streamlit 제공 막대그래프 시각화
                st.bar_chart(data=summary, x="Service_Domain", y="TotalData_KB", color="#2b5c8f")

            with right_col:
                st.subheader("📋 데이터 분석 통계 보고서")
                
                # 웹 화면용 단위 포맷팅 가공
                display_df = summary.copy()
                display_df['PacketCount'] = display_df['PacketCount'].map('{:,} 개'.format)
                display_df['AvgSize'] = display_df['AvgSize'].map('{:,.1f} Byte'.format)
                display_df['TotalData_KB'] = display_df['TotalData_KB'].map('{:,.2f} KB'.format)
                
                # 표 데이터 출력
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
            st.markdown("---")
            st.caption("ℹ️ 본 대시보드는 암호화 프로토콜(TCP/UDP/QUIC)에 무관하게 패킷 내부의 평문 스트림 분석 기법을 상호보완적으로 활용하여 작동합니다.")
