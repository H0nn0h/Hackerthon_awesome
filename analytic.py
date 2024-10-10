import streamlit as st
import plotly.graph_objs as go
import pandas as pd
import pydeck as pdk
from lambda_function import get_s3_data_via_lambda
import json

# Lambda를 통해 S3에서 CSV 데이터를 가져오는 함수
def load_csv_from_lambda(bucket_name, file_key):
    try:
        data = get_s3_data_via_lambda(bucket_name, file_key)  # Lambda 호출
        
        if isinstance(data, dict):
            if 'body' in data:
                data = json.loads(data['body'])  # JSON 형식일 경우 파싱
                
        if isinstance(data, list):
            df = pd.DataFrame(data)  # 리스트일 경우 DataFrame으로 변환
        else:
            st.error("Unexpected data format from Lambda. Expected list of records.")
            return None
        
        return df
    except Exception as e:
        st.error(f"Error loading {file_key} from Lambda: {e}")
        return None

# 데이터 전처리 함수
def preprocess_data(df):
    

    if 'SampleDateTime' in df.columns:
        df['SampleDateTime'] = pd.to_datetime(df['SampleDateTime'], format='%d/%m/%Y %H:%M')
        df['Year'] = df['SampleDateTime'].dt.year
    else:
        st.error("The 'SampleDateTime' column is missing from the data.")
    
    # TP와 TN 값 열을 수치형으로 변환
    if 'Value' in df.columns:  # 'Value' 열이 있다고 가정
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    else:
        st.error("The 'Value' column is missing from the data.")
    
    return df

def render_chart(chart_type, data, title, value_col, selected_catchments, selected_years):
    try:
        # 받은 데이터 처리
        if isinstance(data, dict):
            if 'body' in data:
                body_data = json.loads(data['body'])
                if isinstance(body_data, list):
                    data = pd.DataFrame(body_data)
                else:
                    st.error("Unexpected body data format. Expected a list of dictionaries.")
                    return
        elif isinstance(data, pd.DataFrame):
            pass
        else:
            st.error(f"Unexpected data format. Expected dict or DataFrame, but got {type(data)}.")
            return

        # 필요한 컬럼 확인
        if 'SampleDateTime' not in data.columns:
            st.error("'SampleDateTime' column not found in data.")
            return
        if value_col not in data.columns:
            st.error(f"'{value_col}' column not found in data.")
            return

        # SampleDateTime을 datetime으로 변환
        data['SampleDateTime'] = pd.to_datetime(data['SampleDateTime'], format='%d/%m/%Y %H:%M')
        data['Year'] = data['SampleDateTime'].dt.year

        filtered_data = data[(data['Catchment'].isin(selected_catchments)) & (data['Year'].isin(selected_years))]

        # 필터링된 데이터가 비어있는지 확인
        if filtered_data.empty:
            st.warning("선택한 필터에 맞는 데이터가 없습니다.")
            return
        # 바 차트 그리기
        if chart_type == "bar":
            st.subheader(title)
            fig = go.Figure()
            for catchment in filtered_data['Catchment'].unique():
                catchment_data = filtered_data[filtered_data['Catchment'] == catchment]
                fig.add_trace(go.Bar(x=catchment_data['Year'], y=catchment_data[value_col], name=catchment))

            st.plotly_chart(fig, key=f"bar_chart_{title}_{'_'.join(selected_catchments)}")
        # 라인 차트 그리기
        if chart_type == "line":
            st.subheader(title)
            fig = go.Figure()

            for catchment in selected_catchments:
                catchment_data = filtered_data[filtered_data['Catchment'] == catchment]
                if not catchment_data.empty:
                    yearly_avg = catchment_data.groupby('Year')[value_col].mean().reset_index()
                    fig.add_trace(go.Scatter(
                        x=yearly_avg['Year'], y=yearly_avg[value_col],
                        mode='lines+markers', name=catchment,
                        line=dict(width=2),
                        marker=dict(size=8)
                    ))

            st.plotly_chart(fig, key=f"line_chart_{title}_{'_'.join(selected_catchments)}")

    except Exception as e:
        st.error(f"Error rendering chart: {str(e)}")


# 메인 앱 함수
def app():
    bucket_name = 'awesome-generations-waterdata'
    phosphorus_file_key = 'Phosphorus_Levels.csv'
    nitrogen_file_key = 'Nitrogen_Levels.csv'
    
    st.title("🐟 Water Data Analytics 🐚")
    st.subheader(f"Please select the rivers & Year you want to see data for")

    # 데이터 로드
    phosphorus_data = load_csv_from_lambda(bucket_name, phosphorus_file_key)
    nitrogen_data = load_csv_from_lambda(bucket_name, nitrogen_file_key)
    
    if nitrogen_data is None or phosphorus_data is None:
        return

    # 데이터 전처리
    phosphorus_df = preprocess_data(phosphorus_data)
    nitrogen_df = preprocess_data(nitrogen_data)

    # Catchment 및 Year 필터 설정
    catchments = phosphorus_df['Catchment'].unique().tolist()
    years = phosphorus_df['Year'].unique().tolist()

    # **필터 패널** --------------------
    st.sidebar.title("Filter Options")
    selected_catchments = st.sidebar.multiselect("Select Catchments", catchments)
    selected_years = st.sidebar.multiselect("Select Years", years)

    # Search 버튼 추가
    if st.sidebar.button("Search"):
        # 필터가 선택된 경우에만 대시보드와 지도 표시
        if selected_catchments and selected_years:
            # **Phosphorus (TP) 차트** --------------------
            st.title("📊 Analytics Dashboard 📈")

            render_chart("line", phosphorus_df, "TP Trend Changes by Catchment", "Value", selected_catchments, selected_years)
            render_chart("bar", phosphorus_df, "TP Changes by Catchment and Year", "Value", selected_catchments, selected_years)

            render_chart("line", nitrogen_df, "TN Trend Changes by Catchment", "Value", selected_catchments, selected_years)
            render_chart("bar", nitrogen_df, "TN Changes by Catchment and Year", "Value", selected_catchments, selected_years)
      
                   
        