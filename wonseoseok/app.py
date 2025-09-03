import streamlit as st
import os

# HTML 파일의 경로를 지정합니다.
# 이 경로는 app.py가 실행되는 위치를 기준으로 합니다.
html_file_path = os.path.join(os.path.dirname(__file__), 'htmls', 'index.html')

def main():
    st.set_page_config(layout="wide")

    try:
        # 지정된 경로에서 HTML 파일을 읽어옵니다.
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_code = f.read()
        
        # Streamlit에 HTML 콘텐츠를 렌더링합니다.
        st.components.v1.html(html_code, height=1000, scrolling=True)

    except FileNotFoundError:
        st.error(f"오류: HTML 파일을 찾을 수 없습니다. 경로를 확인해주세요. '{html_file_path}'")
        st.info("파일 구조는 아래와 같아야 합니다: app.py, 그리고 htmls 폴더 안에 index.html")

if __name__ == "__main__":
    main()
