import streamlit as st
import plotly.graph_objs as go
import pandas as pd
from invoke_agent import ask_bedrock_agent  # 필요한 함수들 import
from lambda_function import get_s3_data_via_lambda
import json
from datetime import datetime




def render_chart(chart_type, data, title, value_col):
    try:
        # Lambda에서 받은 데이터가 딕셔너리 형태일 경우 처리
        if isinstance(data, dict):
            st.write(f"Received data in dict format, extracting 'body'.")
            if 'body' in data:
                body_data = json.loads(data['body'])  # 'body'가 JSON 문자열이라면 파싱
                if isinstance(body_data, list):  # 데이터가 리스트의 딕셔너리일 경우
                    #st.write(f"Converting 'body' to DataFrame.")
                    data = pd.DataFrame(body_data)  # 리스트를 DataFrame으로 변환
                else:
                    st.error("Unexpected body data format. Expected a list of dictionaries.")
                    return
            else:
                st.error("'body' not found in the data response.")
                return
        elif isinstance(data, pd.DataFrame):
            st.write(f"Data is already a DataFrame.")
        else:
            st.error(f"Unexpected data format. Expected dict or DataFrame, but got {type(data)}.")
            return

        # 'SampleDateTime' 컬럼이 있는지 확인
        if 'SampleDateTime' not in data.columns:
            st.error(f"'SampleDateTime' column not found in data. Available columns: {data.columns}")
            return

        # 'Value' 컬럼이 있는지 확인
        if value_col not in data.columns:
            st.error(f"'{value_col}' column not found in data. Available columns: {data.columns}")
            return

        # 'SampleDateTime'을 datetime으로 변환
        data['SampleDateTime'] = pd.to_datetime(data['SampleDateTime'], format='%d/%m/%Y %H:%M')


        ten_years_ago = datetime.now() - pd.DateOffset(years=10)
        data = data[data['SampleDateTime'] >= ten_years_ago]

        # 'Value' 컬럼이 문자열로 저장되어 있을 가능성이 있으므로, 이를 숫자로 변환
        data[value_col] = pd.to_numeric(data[value_col], errors='coerce')  # 숫자로 변환, 변환 불가능한 값은 NaN 처리

        top_catchments = data.groupby('Catchment')[value_col].mean().nlargest(4).index.tolist()

        # 연도별 데이터 처리
        data['Year'] = data['SampleDateTime'].dt.year
        yearly_data = data[data['Catchment'].isin(top_catchments)].groupby(['Year', 'Catchment'])[value_col].mean().reset_index()

         # 바 차트 그리기
        if chart_type == "bar":
            st.subheader(title)
            fig = go.Figure()
            for catchment in yearly_data['Catchment'].unique():
                filtered_data = yearly_data[yearly_data['Catchment'] == catchment]
                fig.add_trace(go.Bar(x=filtered_data['Year'], y=filtered_data[value_col], name=catchment))
            st.plotly_chart(fig)

        # 라인 차트 그리기
        elif chart_type == "line":
            st.subheader(title)
            fig = go.Figure()
            for catchment in yearly_data['Catchment'].unique():
                filtered_data = yearly_data[yearly_data['Catchment'] == catchment]
                fig.add_trace(go.Scatter(x=filtered_data['Year'], y=filtered_data[value_col], mode='lines+markers', name=catchment, marker=dict(size=8), line=dict(width=2)))
            st.plotly_chart(fig)

    except Exception as e:
        st.error(f"Error rendering chart: {str(e)}")


# 앱 메인 함수
def app():
    st.title("🐄 Smarter Farmer 🐟")

    # 레이아웃 설정 (왼쪽: 데이터, 오른쪽: 챗봇)
    col1, col2 = st.columns([2, 1])

    # Lambda를 통해 S3에서 데이터 가져오기
    nitrogen_df = get_s3_data_via_lambda('awesome-generations-waterdata', 'Nitrogen_Levels.csv')
    phosphorus_df = get_s3_data_via_lambda('awesome-generations-waterdata', 'Phosphorus_Levels.csv')

    # 데이터가 제대로 로드됐는지 확인
    if nitrogen_df is not None and phosphorus_df is not None:
        # 왼쪽 컬럼: 공통 질문과 차트
        with col1:
            st.subheader("Common Questions")
            common_questions = [
                "Show the bar chart for the catchment with the highest Total Nitrogen.",
                "Show the line chart for the catchment with the highest Total Nitrogen.",
                "Show the bar chart for the catchment with the highest Total Phosphorus.",
                "Show the line chart for the catchment with the highest Total Phosphorus.",
                "Which catchment has the highest Total Nitrogen?",
                "Is it safe to apply fertilizer this week?",
                "What are the nitrogen levels near waikato River?",
                "Have the nitrogen levels in the water reached a dangerous level?",
                "What are the legal limits for Total Nitrogen (TN) levels in freshwater in this region?",
                "Are there any subsidies for farmers to reduce Total Nitrogen and Total Phosphorus runoff?",
                "Is it mandatory to report Total Nitrogen levels in water for industrial or agricultural facilities?",
                "Are there any tax incentives for using low-nitrogen fertilizers to comply with environmental laws?"
            ]

            for question in common_questions:
                if st.button(question):
                    try:
                        # Bedrock에서 응답 받기
                        bot_response = ask_bedrock_agent(question)
                        st.write(f"**SFarmer:** {bot_response}")
                        
                        # 질문에 따라 차트 그리기
                        if question == "Show the bar chart for the catchment with the highest Total Phosphorus.":
                            render_chart("bar", phosphorus_df, "Bar Chart for Catchment with Highest TP", 'Value')
                        elif question == "Show the line chart for the catchment with the highest Total Phosphorus.":
                            render_chart("line", phosphorus_df, "Line Chart for Catchment with Highest TP", 'Value')

                        elif question == "Show the bar chart for the catchment with the highest Total Nitrogen.":
                            render_chart("bar", nitrogen_df, "Bar Chart for Catchment with Highest TN", 'Value')
                        elif question == "Show the line chart for the catchment with the highest Total Nitrogen.":
                            render_chart("line", nitrogen_df, "Line Chart for Catchment with Highest TN", 'Value')

                    except Exception as e:
                        st.error(f"Error fetching response: {str(e)}")

    # 오른쪽 컬럼: 챗봇 상호작용
    with col2:
        chatbot_interaction(nitrogen_df, phosphorus_df)

# 챗봇 상호작용 함수
def chatbot_interaction(nitrogen_data, phosphorus_data):
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    st.subheader("Chat with Smarter Farmer Assistant")

    # 채팅 기록 표시
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.write(f"**You:** {chat['message']}")
        else:
            st.write(f"**SFarmer:** {chat['message']}")

    # 사용자 입력 필드
    user_input = st.text_input("Ask a question to Smarter Farmer...")

    # 입력값 제출 버튼
    if st.button("Submit") and user_input:
        st.write(f"**You:** {user_input}")
        st.session_state.chat_history.append({"role": "user", "message": user_input})

        try:
            # Bedrock 에이전트로부터 응답 받기
            bot_response = ask_bedrock_agent(user_input)
            st.session_state.chat_history.append({"role": "bot", "message": bot_response})
            st.write(f"**SFarmer:** {bot_response}")

            # 응답에 따라 차트 그리기
            if "bar chart for nitrogen" in bot_response.lower():
                render_chart("bar", nitrogen_data, "Bar Chart for Nitrogen Levels", 'Value')
            elif "line chart for nitrogen" in bot_response.lower():
                render_chart("line", nitrogen_data, "Line Chart for Nitrogen Levels", "Value")
            elif "line chart for phosphorus" in bot_response.lower():
                render_chart("line", phosphorus_data, "Line Chart for Phosphorus Levels", 'Value')
            elif "bar chart for phosphorus" in bot_response.lower():
                render_chart("bar", phosphorus_data, "Bar Chart for Phosphorus Levels", "Value")

        except Exception as e:
            st.error(f"Error fetching response: {str(e)}")
