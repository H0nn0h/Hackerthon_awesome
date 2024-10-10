import streamlit as st
import plotly.graph_objs as go
import pandas as pd
from invoke_agent import get_s3_data, ask_bedrock_agent  # Import necessary functions

# S3 settings
bucket_name = 'awesome-generations-waterdata'
file_key_1 = 'Nitrogen_Levels.csv'
file_key_2 = 'Phosphorus_Levels.csv'

# Function to render a bar or line chart based on the user's query
def render_chart(chart_type, data, title):
    try:
        # Replace spaces in column names
        data.columns = data.columns.str.replace(' ', '_')
        # Convert SampleDateTime to datetime
        data['SampleDateTime'] = pd.to_datetime(data['SampleDateTime'], format='%d/%m/%Y %H:%M')
            
        # Extract years and catchments
        years = data['SampleDateTime'].dt.year.unique().tolist()
        catchments = data['Catchment'].unique().tolist()

        if chart_type == "bar":
            st.subheader(title)
            fig = go.Figure()
            for catchment in catchments:
                filtered_data = data[data['Catchment'] == catchment]
                fig.add_trace(go.Bar(x=years, y=filtered_data[value_col], name=catchment))
            st.plotly_chart(fig)

        elif chart_type == "line":
            st.subheader(title)
            fig = go.Figure()
            for catchment in catchments:
                filtered_data = data[data['Catchment'] == catchment]
                fig.add_trace(go.Scatter(x=years, y=filtered_data[value_col], mode='lines+markers', name=catchment))
            st.plotly_chart(fig)

    except Exception as e:
        st.error(f"Error rendering chart: {str(e)}")

# App main function
def app():
    st.title("🐄 Smarter Farmer 🐟")

    # Layout with two columns: Left for data, right for chatbot
    col1, col2 = st.columns([2, 1])

    # Load the data from S3
    nitrogen_df = get_s3_data(bucket_name, file_key_1)
    phosphorus_df = get_s3_data(bucket_name, file_key_2)

     # Ensure data is loaded correctly
    if nitrogen_df is not None and phosphorus_df is not None:
  
        # Left column: Common Questions at the top, Charts based on user query
        with col1:
            st.subheader("Common Questions")
            common_questions = [
                "Show the bar chart for the catchment with the highest TP.",
                "Show the line chart for the catchment with the highest TP.",
                "Which catchment has the highest TP?",
                "Is it safe to apply fertilizer this week?",
                "What are the nitrogen levels near my farm?",
                "Have the nitrogen levels in the water reached a dangerous level?"
            ]
            common_response = None

            for question in common_questions:
                if st.button(question):
                    try:
                        # Fetch response from Bedrock for common questions
                        bot_response = ask_bedrock_agent(question)
                        common_response = bot_response
                        # Fetch response from Bedrock for common questions
                        #bot_response = ask_bedrock_agent(question)
                        #st.session_state.chat_history.append({"role": "bot", "message": bot_response})
                        st.write(f"**SFarmer:** {bot_response}")
                        
                        # If the response contains "bar chart" or "line chart," render the chart
                        if "bar chart for nitrogen" in question.lower():
                            render_chart("bar", nitrogen_df, "Bar Chart for Nitrogen Levels", 'Value')
                        elif "line chart for phosphorus" in question.lower():
                            render_chart("line", phosphorus_df, "Line Chart for Phosphorus Levels", 'Value')
                        
                        # 질문에 따라 차트 그리기
                        elif question == "Show the bar chart for nitrogen levels.":
                            render_chart("bar", nitrogen_df, "Bar Chart for Nitrogen Levels", 'Value')
                        elif question == "Show the line chart for phosphorus levels.":
                            render_chart("line", phosphorus_df, "Line Chart for Phosphorus Levels", 'Value')


                    except Exception as e:
                        st.error(f"Error fetching response: {str(e)}")

    # Right column: Chatbot interaction
    with col2:
        chatbot_interaction(nitrogen_df, phosphorus_df)

# Chatbot interaction function
def chatbot_interaction(nitrogen_data, phosphorus_data):
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    st.subheader("Chat with Smarter Farmer Assistant")

    # Display chat history
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.write(f"**You:** {chat['message']}")
        else:
            st.write(f"**SFarmer:** {chat['message']}")

    # User input field
    user_input = st.text_input("Ask a question to Smarter Farmer...")

    # Submit button for user input
    if st.button("Submit") and user_input:
        st.write(f"**You:** {user_input}")
        st.session_state.chat_history.append({"role": "user", "message": user_input})

        try:
            # Get response from Bedrock agent
            bot_response = ask_bedrock_agent(user_input)
            st.session_state.chat_history.append({"role": "bot", "message": bot_response})
            st.write(f"**SFarmer:** {bot_response}")

            # Render chart based on bot's response
            # 응답에 따라 차트 그리기
            if "bar chart for nitrogen" in bot_response.lower():
                render_chart("bar", nitrogen_data, "Bar Chart for Nitrogen Levels", 'Value')
            elif "line chart for phosphorus" in bot_response.lower():
                render_chart("line", phosphorus_data, "Line Chart for Phosphorus Levels", 'Value')

                
        except Exception as e:
            st.error(f"Error fetching response: {str(e)}")
