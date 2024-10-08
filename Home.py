import streamlit as st
import chatbot
import analytic
import main
# 페이지 선택
page = st.sidebar.selectbox("Select a page", ["Main", "Chatbot","Analytics"])

if page == "Main":
    main.app()  
elif page == "Chatbot":
    chatbot.app()  
elif page == "Analytic":
    analytic.app()
