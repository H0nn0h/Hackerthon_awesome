import streamlit as st
import chatbot
import analytic
import proto1

# 페이지 설정
st.set_page_config(layout="wide")

# 사이드바에 로고 및 네비게이션 설정
st.sidebar.markdown(
    """
    <style>
    .logo {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 150px;  /* 로고 크기 조정 */
    }


    
    </style>
    """, unsafe_allow_html=True
)


# 로고 삽입 (로고 파일의 경로)
st.sidebar.image("logo.png", use_column_width=True)
st.sidebar.markdown("<h1>Understanding Data,<br>Better Tomorrow!</h1>", unsafe_allow_html=True)


# Chatbot 페이지를 기본값으로 표시
if "page" not in st.session_state:
    st.session_state.page = "Chatbot"

# 페이지 선택 버튼 생성
if st.sidebar.button("Chatbot"):
    st.session_state.page = "Chatbot"
elif st.sidebar.button("Analytics"):
    st.session_state.page = "Analytics"

# 선택된 페이지에 따라 다른 모듈 불러오기
if st.session_state.page == "Chatbot":
    chatbot.app()  # chatbot 모듈에서 app 함수 실행
elif st.session_state.page == "Analytics":
    analytic.app()  # analytic 모듈에서 app 함수 실행