import streamlit as st
import os
import streamlit.components.v1 as components

# app.py와 htmls 폴더가 같은 위치에 있다고 가정합니다.
# Assuming app.py and the htmls folder are in the same location.
html_dir = os.path.join(os.path.dirname(__file__), 'htmls')

def load_html(file_name):
    """지정된 HTML 파일을 읽어 그 내용을 반환하는 함수"""
    """A function that reads a specified HTML file and returns its content"""
    file_path = os.path.join(html_dir, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"오류: '{file_name}' 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
        st.error(f"Error: '{file_name}' file not found. Please check the path.")
        return None

def main():
    st.set_page_config(layout="wide")
    st.title("HTML 파일 불러오기")

    # 드롭다운 메뉴를 만들어 사용자가 HTML 파일을 선택하게 합니다.
    # Create a dropdown menu to let the user select an HTML file.
    selected_file = st.selectbox(
        "불러올 HTML 파일을 선택하세요:",
        ('index.html', 'index2.html', 'index3.html', 'index4.html')
    )

    # 선택된 파일의 HTML 코드를 불러옵니다.
    # Load the HTML code of the selected file.
    html_code = load_html(selected_file)

    if html_code:
        # Streamlit에 HTML 콘텐츠를 렌더링합니다.
        # height와 scrolling은 필요에 따라 조절하세요.
        # Render the HTML content in Streamlit.
        # Adjust height and scrolling as needed.
        components.html(html_code, height=1000, scrolling=True)

if __name__ == "__main__":
    main()

