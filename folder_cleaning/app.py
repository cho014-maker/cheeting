import streamlit as st
import os
import zipfile
import shutil

# 임시 저장소 경로 설정
UPLOAD_DIR = "st_uploaded_files"
SORTED_DIR = "st_sorted_files"

st.set_page_config(page_title="클릭형 파일 정리기", page_icon="📂", layout="centered")

st.title("📂 나만의 클릭형 파일 정리기 (Streamlit)")
st.write("폴더를 먼저 생성해둔 뒤, 화면에 나오는 파일을 버튼 클릭 한 번으로 분류하세요!")

# ------------------------------------------------------------------
# [시스템 메모리 세션 초기화] Streamlit은 버튼을 누를 때마다 코드가 재실행되므로 기록 장치가 필수입니다.
# ------------------------------------------------------------------
if "my_folders" not in st.session_state:
    st.session_state.my_folders = []
if "remaining_files" not in st.session_state:
    st.session_state.remaining_files = []
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "process_complete" not in st.session_state:
    st.session_state.process_complete = False

# ------------------------------------------------------------------
# 1️⃣단계: 정리할 폴더 만들기
# ------------------------------------------------------------------
st.subheader("1️⃣ 정리할 폴더 만들기")
with st.form(key="folder_form", clear_on_submit=True):
    new_folder = st.text_input("생성할 폴더 이름을 입력하세요 (예: 수학, 과제, 사진):")
    submit_folder = st.form_submit_button("폴더 추가")
    
    if submit_folder and new_folder.strip():
        folder_name = new_folder.strip()
        if folder_name not in st.session_state.my_folders:
            st.session_state.my_folders.append(folder_name)
        else:
            st.warning("이미 추가된 폴더 이름입니다.")

# 생성된 폴더 시각적으로 보여주기
if st.session_state.my_folders:
    st.write("📌 **현재 생성된 폴더 템플릿:**")
    # 예쁜 버블 형태로 생성된 폴더 목록 노출
    folder_tags = " ".join([f"`📁 {f}`" for f in st.session_state.my_folders])
    st.markdown(folder_tags)
else:
    st.caption("아직 생성된 폴더가 없습니다. 정리할 폴더를 먼저 만들어주세요.")

st.write("---")

# ------------------------------------------------------------------
# 2️⃣단계: 정리할 파일 업로드
# ------------------------------------------------------------------
st.subheader("2️⃣ 정리할 파일 업로드")

# 파일 업로더 컴포넌트 (폴더를 최소 1개 이상 만들었을 때만 활성화)
disabled_upload = len(st.session_state.my_folders) == 0
uploaded_files = st.file_uploader(
    "정리할 파일들을 한 번에 모두 선택하세요.", 
    accept_multiple_files=True,
    disabled=disabled_upload,
    help="파일을 올리기 전에 폴더를 최소 1개 이상 만들어야 합니다."
)

# 파일이 새로 올라왔고, 아직 분류 데이터 세팅 전이라면 초기화 진행
if uploaded_files and not st.session_state.remaining_files and not st.session_state.process_complete:
    # 기존 흔적들 깔끔하게 밀어버리기
    for d in [UPLOAD_DIR, SORTED_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
        
    file_names = []
    for file in uploaded_files:
        # 일단 모든 파일을 서버 임시 공간에 저장
        with open(os.path.join(UPLOAD_DIR, file.name), "wb") as f:
            f.write(file.getbuffer())
        file_names.append(file.name)
        
    st.session_state.remaining_files = file_names
    st.session_state.current_idx = 0
    st.rerun()

# ------------------------------------------------------------------
# 3️⃣단계: 파일 매칭 단계 (대화형 버튼 클릭 분류)
# ------------------------------------------------------------------
if st.session_state.remaining_files and not st.session_state.process_complete:
    st.write("---")
    st.subheader("3️⃣ 파일 매칭 단계 (폴더 버튼을 누르세요)")
    
    idx = st.session_state.current_idx
    files_list = st.session_state.remaining_files
    
    if idx < len(files_list):
        current_file = files_list[idx]
        
        # 상단에 진행 상황 바 표시
        progress_val = idx / len(files_list)
        st.progress(progress_val)
        st.write(f"📊 남은 파일 개수: **{len(files_list) - idx}** / {len(files_list)}개")
        
        # 현재 타겟 파일 명시
        st.info(f"📄 현재 분류할 파일: **{current_file}**")
        
        st.write("👇 이 파일을 어느 폴더로 보낼까요?")
        
        # 사용자가 만든 폴더 개수대로 가로 버튼 배열 배치
        cols = st.columns(min(len(st.session_state.my_folders), 5)) # 한 줄에 최대 5개 배치
        for i, folder in enumerate(st.session_state.my_folders):
            col_target = cols[i % 5]
            if col_target.button(f"📁 {folder}", key=f"btn_{folder}_{idx}", use_container_width=True):
                # 클릭 시 해당 폴더로 파일 이동 처리
                dest_path = os.path.join(SORTED_DIR, folder)
                os.makedirs(dest_path, exist_ok=True)
                shutil.move(os.path.join(UPLOAD_DIR, current_file), os.path.join(dest_path, current_file))
                
                st.session_state.current_idx += 1
                st.rerun()
                
        # 어떤 폴더에도 넣고 싶지 않을 때의 예외 버튼
        if st.button("🚫 어디 안 넣고 그냥 두기", key=f"skip_{idx}", use_container_width=True):
            dest_path = os.path.join(SORTED_DIR, "미분류_파일")
            os.makedirs(dest_path, exist_ok=True)
            shutil.move(os.path.join(UPLOAD_DIR, current_file), os.path.join(dest_path, current_file))
            
            st.session_state.current_idx += 1
            st.rerun()
    else:
        st.session_state.process_complete = True
        st.rerun()

# ------------------------------------------------------------------
# 4️⃣단계: 분류 완료 및 ZIP 압축 파일 다운로드
# ------------------------------------------------------------------
if st.session_state.process_complete:
    st.write("---")
    st.success("🎉 모든 파일의 폴더 매칭이 완벽하게 끝났습니다!")
    
    # 임시 업로드 폴더 정리
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
        
    # ZIP 파일로 패키징 하기
    zip_filename = "정리완료_파일.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(SORTED_DIR):
            for file in files:
                fp = os.path.join(root, file)
                zipf.write(fp, os.path.relpath(fp, SORTED_DIR))
                
    # Streamlit 내장 다운로드 시스템 가동 (Flask와 달리 다운로드 실패 버그가 전혀 발생하지 않습니다)
    with open(zip_filename, "rb") as f:
        st.download_button(
            label="🎁 정리된 압축파일(.zip) 다운로드 받기",
            data=f,
            file_name=zip_filename,
            mime="application/zip",
            use_container_width=True,
            type="primary"
        )
        
    if st.button("🔄 처음부터 새로 정리하기", use_container_width=True):
        st.session_state.clear()
        st.rerun()
