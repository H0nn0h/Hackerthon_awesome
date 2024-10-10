from boto3.session import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json
import os
import requests
import boto3
import pandas as pd
import streamlit as st
from io import StringIO
import uuid

# AWS Bedrock 클라이언트 생성
def get_bedrock_client():
    session = get_aws_session()
    if session is None:
        raise Exception("AWS session failed.")
    
    return session.client('bedrock-runtime', region_name='us-west-2')

bedrock_agent_runtime= boto3.client('bedrock-agent-runtime',region_name='us-west-2')

# AWS 세션을 생성하는 함수
def get_aws_session():
    try:
        # 환경 변수에서 AWS 자격 증명을 가져옴
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', 'ASIA3HXWUQ2UAOEXNMBI')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'HRgMShSwv82UEjYxHtegqJnSpOspqbK2VclV+uRA')
        aws_session_token = os.getenv('AWS_SESSION_TOKEN', 'IQoJb3JpZ2luX2VjEBoaCXVzLWVhc3QtMSJHMEUCIQCteEgXTgAwOoLMew+R8jaRg/EVKJFoR8iSweHWls2eXQIgbXu1B1tT7mZDqe2DhLZS8AxERUFWSJJF1Dhcw+kXhVYqmQIIcxACGgw3NzI1Mzc2MTYwNDAiDPLpAh80EojPVw0VDCr2AYz/etT8AFV7cb2gayLsPD0TwiL450uq/7+WSHKgNz0+PhYAxyRGFksBAHIPFzZ3i3Ek3sm0dO4zYVlObF5XIxUEfr3zrjnQLgstwIRap/7ipiifaX2KCHX2z08gVCevhMH7XHJw2eNy1DXba4EzWJs1u9N8ekVYlavJr7K8DC+rTlBfGsNvdQ2lbIhXLW+ueODhJ0iZF/E3hVadzr5xtWWZCEBpYMWpCV2yWAcXjldoLE6dAhaYqMsnMLmF8m13rOfCs8ZBou3DCWAJIFGf7o3ZI3QtAA2TjltPx4VE4jA0KV3zWYsY2ebHAxgIdsXwDnGqX1+ggzDkxJ64BjqdAZExaDh6EhLUIoNBXdELdU/BgXx/U7jGq82oDpGwwkDtbwAq9yh5n8WwXxo2NsNDrEKVs2seAtTUYQO4DdoKpXK6Wrqlf0jvz0EzEvJyWnELPB/BVaXHE3wZ4eXqzSK6W7QuUqY9xDaeuCSZA6zA1wTVIdDaJEfOIDA8yWp7J6EHgdqvw/48uo98bnXEBalu8dq6rIiMlBIi1lkJL+I=')

        # boto3 세션 생성
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token
        )
        # bedrock-agent-runtime 클라이언트 생성
        bedrock_agent_runtime = session.client('bedrock-agent-runtime', region_name='us-west-2')
        return session, bedrock_agent_runtime

    except Exception as e:
        print(f"Error fetching AWS session: {e}")
        return None, None


# S3에서 지정된 버킷과 파일 키로 데이터를 가져오는 함수
def get_s3_data(bucket_name, file_key):
    session, _ = get_aws_session()
    
    if session is None:
        print("Error: AWS session could not be created.")
        return None


    # S3 클라이언트 생성
    s3 = session.client('s3')
    
    try:
        # S3에서 객체 가져오기
        csv_obj = s3.get_object(Bucket=bucket_name, Key=file_key)
        body = csv_obj['Body'].read().decode('utf-8')
        df = pd.read_csv(StringIO(body))
        return df
    except Exception as e:
        print(f"Error loading {file_key} from S3: {e}")
        return None

# SigV4 서명 생성 함수
def sign_request(url, method, service, region, credentials, body=None):
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    req = AWSRequest(method=method, url=url, data=body, headers={'Content-Type': 'application/json'})
    SigV4Auth(credentials, service, region).add_auth(req)
    return req.prepare()

def ask_bedrock_agent(question):
    try:
        # AWS 세션 및 Bedrock 클라이언트 가져오기
        session, bedrock_agent_runtime = get_aws_session()
        if session is None or bedrock_agent_runtime is None:
            raise Exception("AWS 세션을 생성하는 데 실패했습니다.")

        # Bedrock 요청 본문 설정
        agent_id = "ZDTJFHLHBP"  # Bedrock agent ID
        agent_alias_id = "MEZTV7Z0SQ"  # Bedrock agent alias ID
        session_id = 'test-session-001'  # 세션 ID 설정

        # Bedrock agent runtime invoke_agent 호출
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=question
        )

        # Response 처리
        full_response = ""
        if 'completion' in response:
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        full_response += chunk['bytes'].decode('utf-8')
            return full_response.strip()  # Remove leading/trailing whitespace
        else:
            print("No 'completion' field found in response.")
            return None
        
        if not full_response:
            print("Empty response received from Bedrock agent.")
            return None

    except Exception as e:
        print(f"Error invoking agent: {e}")
        return None


# Bedrock API 응답 디코딩 함수
def decode_response(response):
    if not response:
        print("No response received")
        return None, None

    string = ""
    for line in response.iter_content():
        try:
            string += line.decode(encoding='utf-8')
        except:
            continue

    print("Decoded response", string)
    return string

