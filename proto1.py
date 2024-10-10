def invoke_lambda(function_name, payload):
    # Lambda 클라이언트 생성
    lambda_client = boto3.client('lambda', region_name='us-west-2')

    try:
        # Lambda 함수 호출
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # 동기 호출
            Payload=json.dumps(payload)
        )

        # 응답 처리
        response_payload = response['Payload'].read()
        return json.loads(response_payload)

    except Exception as e:
        print(f"Error invoking Lambda function: {e}")
        return None
# S3에서 데이터를 가져오는 함수 (두 개의 파일)
def load_catchment_data_from_s3(bucket_name, file_key_1, file_key_2):
    s3 = boto3.client('s3')

    def fetch_s3_file(key):
        try:
            obj = s3.get_object(Bucket=bucket_name, Key=key)
            body = obj['Body'].read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(body))
            return [row for row in reader]
        except Exception as e:
            print(f"Error fetching data from S3: {e}")
            return []

    # 두 파일에서 데이터를 각각 가져옴
    data_1 = fetch_s3_file(file_key_1)
    data_2 = fetch_s3_file(file_key_2)

    # 두 데이터를 합침 (리스트의 확장)
    combined_data = data_1 + data_2

    return combined_data

def get_named_parameter(event, name):
    """Lambda event에서 특정 파라미터 값을 찾는 함수"""
    return next(item for item in event['parameters'] if item['name'] == name)['value']

def catchmentResearch(event, catchment_data):
    """이벤트에 기반하여 유역(catchment) 정보를 검색하는 함수"""
    catchmentName = get_named_parameter(event, 'name').lower()
    print(f"Searching for catchment: {catchmentName}")
    
    for catchment_info in catchment_data:
        if catchment_info["Catchment"].lower() == catchmentName:
            return catchment_info
    return {"message": f"Catchment '{catchmentName}' not found"}

# Lambda 핸들러 함수
def lambda_handler(event, context):
    # S3에서 데이터를 불러오기
    bucket_name = 'knowledgebase-bedrock-agent-waterdata'
    file_key_1 = 'Nitrogen_Levels.csv'  # S3에 저장된 첫 번째 CSV 파일 경로
    file_key_2 = 'Phosphorus_Levels.csv'  # S3에 저장된 두 번째 CSV 파일 경로
    
    # 두 개의 파일에서 데이터를 로드
    catchment_data = load_catchment_data_from_s3(bucket_name, file_key_1, file_key_2)
    
    if not catchment_data:
        return {
            'statusCode': 500,
            'body': 'Error loading data from S3'
        }
    
    # 이벤트에서 catchment name을 추출하여 검색
    catchment_info = catchmentResearch(event, catchment_data)
    
    # 검색 결과 반환
    return {
        'statusCode': 200,
        'body': catchment_info
    }
