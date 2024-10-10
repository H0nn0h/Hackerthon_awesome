import boto3
import csv
import io
import json
import os
import boto3 
import invoke_agent
from botocore.exceptions import ClientError
import pandas as pd

def get_aws_client(service_name, region_name='us-east-1'):
    # Retrieve the credentials
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', 'ASIA3HXWUQ2UAOEXNMBI')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'HRgMShSwv82UEjYxHtegqJnSpOspqbK2VclV+uRA')
    aws_session_token = os.getenv('AWS_SESSION_TOKEN', 'IQoJb3JpZ2luX2VjEBoaCXVzLWVhc3QtMSJHMEUCIQCteEgXTgAwOoLMew+R8jaRg/EVKJFoR8iSweHWls2eXQIgbXu1B1tT7mZDqe2DhLZS8AxERUFWSJJF1Dhcw+kXhVYqmQIIcxACGgw3NzI1Mzc2MTYwNDAiDPLpAh80EojPVw0VDCr2AYz/etT8AFV7cb2gayLsPD0TwiL450uq/7+WSHKgNz0+PhYAxyRGFksBAHIPFzZ3i3Ek3sm0dO4zYVlObF5XIxUEfr3zrjnQLgstwIRap/7ipiifaX2KCHX2z08gVCevhMH7XHJw2eNy1DXba4EzWJs1u9N8ekVYlavJr7K8DC+rTlBfGsNvdQ2lbIhXLW+ueODhJ0iZF/E3hVadzr5xtWWZCEBpYMWpCV2yWAcXjldoLE6dAhaYqMsnMLmF8m13rOfCs8ZBou3DCWAJIFGf7o3ZI3QtAA2TjltPx4VE4jA0KV3zWYsY2ebHAxgIdsXwDnGqX1+ggzDkxJ64BjqdAZExaDh6EhLUIoNBXdELdU/BgXx/U7jGq82oDpGwwkDtbwAq9yh5n8WwXxo2NsNDrEKVs2seAtTUYQO4DdoKpXK6Wrqlf0jvz0EzEvJyWnELPB/BVaXHE3wZ4eXqzSK6W7QuUqY9xDaeuCSZA6zA1wTVIdDaJEfOIDA8yWp7J6EHgdqvw/48uo98bnXEBalu8dq6rIiMlBIi1lkJL+I=')

    if not all([aws_access_key_id, aws_secret_access_key, aws_session_token]):
        raise ValueError("Missing required AWS credentials")

    try:
        # Create the session with the credentials
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token
        )
        
        # Create and return the client
        client = session.client(service_name, region_name=region_name)
        print(f"Successfully created client for {service_name}")
        return client
    except ClientError as e:
        print(f"Error creating AWS client: {e}")
        raise

# Lambda에서 데이터를 가져오는 함수 (예시)
def get_s3_data_via_lambda(bucket_name, file_key):
    payload = {
        'bucket_name': bucket_name,
        'file_key': file_key
    }
    return lambda_handler('read-river-data', payload)

# Use this function to create your S3 and Lambda clients
s3 = get_aws_client('s3')
#lambda_client = get_aws_client('lambda')

def load_catchment_data_from_s3(bucket_name, file_keys):
    """두 개의 S3 파일을 불러와서 데이터를 반환하는 함수"""
    combined_data = []

    for file_key in file_keys:
        try:
            print(f"Attempting to load data from bucket: {bucket_name}, file key: {file_key}")
            obj = s3.get_object(Bucket=bucket_name, Key=file_key)
            body = obj['Body'].read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(body))
            combined_data.extend(list(reader))  # 두 파일의 데이터를 하나의 리스트로 합침
        except Exception as e:
            print(f"Error fetching data from S3: {e}")
    
    return pd.DataFrame(combined_data)

# 예시로 사용할 버킷 이름과 파일 키
bucket_name = 'awesome-generations-waterdata'
file_keys = ['Nitrogen_Levels.csv', 'Phosphorus_Levels.csv']

# 파라미터를 event에서 가져오는 함수
def get_named_parameter(event, name, default=None):
    try:
        if 'parameters' not in event:
            raise ValueError(f"'parameters' not found in event")
        if isinstance(event.get('parameters'), list):
            return next(item['value'] for item in event['parameters'] if item.get('name') == name)
        else:
            raise ValueError(f"Expected 'parameters' to be a list, but got {type(event.get('parameters'))}")
    except StopIteration:
        # 파라미터를 찾지 못했을 경우 기본값 반환 (예: 'Waikato River')
        if default:
            return default
        else:
            raise ValueError(f"Parameter '{name}' not found in event")

# Catchment 데이터를 검색하는 함수 (catchment_name이 없으면 Waikato River 사용)
def catchment_research(event, catchment_data):
    try:
        # 문자열 event일 경우 처리 로직
        if isinstance(event, str):
            print(f"Received a string event: {event}")
            if event == "read-river-data":  # 특정 이벤트가 들어왔을 때 처리
                print("Processing default catchment data for 'read-river-data'")
                return catchment_data  # 전체 데이터를 반환하거나 기본 응답을 설정

        # dict 형태의 event일 경우
        if isinstance(event, dict):
            # 파라미터에서 'Catchment' 값을 찾고, 없으면 기본값으로 'Waikato River' 사용
            catchment_name = get_named_parameter(event, 'Catchment', default='Waikato River').lower()
            print(f"Searching for catchment: {catchment_name}")
            
            for catchment_info in catchment_data:
                if catchment_info["Catchment"].lower() == catchment_name:
                    return catchment_info

            # Catchment를 찾지 못한 경우
            return {"message": f"Catchment '{catchment_name}' not found"}

        # event가 문자열도 아니고 딕셔너리도 아닌 경우
        else:
            raise ValueError(f"Expected event to be a dict or str, but got {type(event)}")

    except Exception as e:
        print(f"Error in catchment_research: {str(e)}")
        return {"error": str(e)}

# 람다 핸들러 함수
def lambda_handler(event, context):
    try:
        # 두 파일에서 데이터를 로드
        bucket_name = 'awesome-generations-waterdata'
        file_keys = ['Nitrogen_Levels.csv', 'Phosphorus_Levels.csv']
        
        # S3에서 데이터를 로드
        catchment_data = load_catchment_data_from_s3(bucket_name, file_keys)
        
        # catchment_data가 비어있는지 확인 (DataFrame일 경우)
        if isinstance(catchment_data, pd.DataFrame) and catchment_data.empty:
            raise ValueError('Error loading data from S3 or no data available')

        # 데이터를 처리 및 반환 (특정 catchment가 없으면 Waikato River 사용)
        catchment_info = catchment_research(event, catchment_data)
        
        # DataFrame을 딕셔너리로 변환하여 JSON으로 반환할 수 있도록 처리
        if isinstance(catchment_info, pd.DataFrame):
            catchment_info = catchment_info.to_dict(orient='records')  # 각 행을 딕셔너리로 변환

        return {
            'statusCode': 200,
            'body': json.dumps(catchment_info)  # catchment_info를 JSON으로 직렬화
        }
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
        }
