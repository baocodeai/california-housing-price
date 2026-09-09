# HƯỚNG DẪN TRIỂN KHAI MLOPS TOÀN DIỆN TRÊN AWS SAGEMAKER AI
## Dự án: California Housing Price Prediction (Chuẩn Kiến Trúc MLOps)

Tài liệu này cung cấp toàn bộ quy trình, mã nguồn và các bước thao tác trên **AWS Management Console** và **Amazon SageMaker Studio** để đưa dự án California Housing Price lên môi trường Production trên AWS, bám sát 100% sơ đồ kiến trúc tham chiếu.

---

## 1. SƠ ĐỒ ÁNH XẠ KIẾN TRÚC

```text
[ Data Source ] ──> S3 Source Data Bucket ──(S3 Event)──> AWS Lambda
                                                               │ (Tạo manifest.json)
                                                               ▼
[ Code Push ]   ──> Source Repository (GitHub) ──> S3 Manifest Bucket
       │                                                   │
       └───────────────────────┬───────────────────────────┘
                               │ (Trigger)
                               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             AWS CodePipeline (CI/CD)                             │
│                                                                                  │
│  [Source] ──> [CI: CodeBuild] ──> [ML Pipeline] ──> [Manual Approval] ──> [Deploy│
│                   (pytest)       (SageMaker DAG)       (SNS Email)       Endpoint│
└──────────────────────────────────────┬───────────────────────────────────────────┘
                                       │ (Create/Update & Wait)
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   Amazon SageMaker AI Pipeline (Trong Studio)                    │
│                                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐  │
│  │ Data         │────>│ Model        │────>│ Model        │────>│ Model       │  │
│  │ Preprocessing│     │ Training     │     │ Evaluation   │     │ Validation  │  │
│  └──────────────┘     └──────────────┘     └──────────────┘     └──────┬──────┘  │
│                                                                        │         │
│                                                          R2 >= 0.80 ?  │         │
│                                                   ┌────────────────────┴──┐      │
│                                                Yes│                     No│      │
│                                                   ▼                       ▼      │
│                                         ┌───────────────────┐        ┌────────┐  │
│                                         │ Model Registration│        │  Stop  │  │
│                                         │ (Model Registry)  │        └────────┘  │
│                                         └─────────┬─────────┘                    │
└───────────────────────────────────────────────────┼──────────────────────────────┘
                                                    │ (Approve Model)
                                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         SageMaker Inference Serving                              │
│                                                                                  │
│                      [Model] ──> [Serverless Endpoint]                           │
└───────────────────────────────────────────▲──────────────────────────────────────┘
                                            │ (InvokeEndpoint)
┌───────────────────────────────────────────┴──────────────────────────────────────┐
│                              Model Consumer Layer                                │
│                                                                                  │
│  [Users] ──(UI)──> [Amazon CloudFront] ──> [Amazon S3 React Web]                 │
│    │                                                                             │
│    ├──(GetPrediction)─> [Amazon API Gateway] ──> [AWS Lambda Proxy] ──> [DynamoDB│
│    └──(ProvideFeedback)───────────────────────────────┘                          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. BƯỚC 0: THIẾT LẬP NỀN TẢNG & PHÂN QUYỀN IAM

### 2.1. Lấy SageMaker Execution Role có sẵn
Vì tài khoản của bạn đã có **Domain (1)** và **User Profile (1)** trên Dashboard:
1. Mở **Amazon SageMaker AI Console**.
2. Ở menu trái chọn **Environment configuration** $\rightarrow$ **Domains**.
3. Nhấp vào tên Domain của bạn $\rightarrow$ Chọn tab **Domain settings**.
4. Sao chép lại dòng **Execution role ARN** (Ví dụ: `arn:aws:iam::123456789012:role/service-role/AmazonSageMaker-ExecutionRole-...`).
   *(Ta quy ước gọi biến này là `$SAGEMAKER_ROLE_ARN`)*.

### 2.2. Tạo Role cho Lambda (`CaliforniaHousing-LambdaExecutionRole`)
1. Vào **IAM Console** (`https://console.aws.amazon.com/iam/`) $\rightarrow$ **Roles** $\rightarrow$ **Create role**.
2. Chọn **AWS service** $\rightarrow$ Use case: **Lambda** $\rightarrow$ Nhấn **Next**.
3. Đánh dấu chọn 4 policies:
   - `AWSLambdaBasicExecutionRole`
   - `AmazonS3FullAccess`
   - `AmazonSageMakerFullAccess`
   - `AmazonDynamoDBFullAccess`
4. Đặt tên: `CaliforniaHousing-LambdaExecutionRole` $\rightarrow$ Nhấn **Create role**.

---

## 3. KHỐI 1: DATA INGESTION & EVENT TRIGGERS

### 3.1. Tạo 2 S3 Buckets trên S3 Console
- **Bucket 1 (Chứa data thô):** `california-housing-data-<your-alias>` (Mặc định).
- **Bucket 2 (Chứa manifest):** `california-housing-manifest-<your-alias>` (Bật **Bucket Versioning: Enable**).

### 3.2. Tạo Lambda Function `california-housing-manifest-generator`
1. Vào **AWS Lambda Console** $\rightarrow$ **Create function**:
   - Tên hàm: `california-housing-manifest-generator`.
   - Runtime: **Python 3.11**.
   - Execution role: Chọn *Use an existing role* $\rightarrow$ `CaliforniaHousing-LambdaExecutionRole`.
2. Dán đoạn mã sau vào `lambda_function.py`:
```python
import json
import urllib.parse
import boto3
from datetime import datetime

s3 = boto3.client('s3')
MANIFEST_BUCKET = 'california-housing-manifest-<your-alias>'  # Thay tên bucket của bạn

def lambda_handler(event, context):
    for record in event.get('Records', []):
        src_bucket = record['s3']['bucket']['name']
        src_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        size = record['s3']['object']['size']
        etag = record['s3']['object']['eTag']
        
        manifest = {
            "dataset_name": "california_housing",
            "source_s3_uri": f"s3://{src_bucket}/{src_key}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "size_bytes": size,
            "etag": etag,
            "status": "READY_FOR_TRAINING"
        }
        
        manifest_key = f"manifests/manifest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        s3.put_object(
            Bucket=MANIFEST_BUCKET,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2),
            ContentType='application/json'
        )
        print(f"Created manifest: s3://{MANIFEST_BUCKET}/{manifest_key}")
        
    return {"statusCode": 200, "body": json.dumps("Manifest created")}
```
3. Nhấn **Deploy**.

### 3.3. Cấu hình S3 Event Notification
1. Vào bucket `california-housing-data-<your-alias>` $\rightarrow$ Tab **Properties** $\rightarrow$ **Event notifications** $\rightarrow$ **Create event notification**.
2. Tên: `OnNewCsvUpload`.
3. Prefix: `raw/`, Suffix: `.csv`.
4. Event types: Tích chọn `All object create events` (`s3:ObjectCreated:*`).
5. Destination: **Lambda function** $\rightarrow$ Chọn `california-housing-manifest-generator`.
6. Nhấn **Save changes**.

---

## 4. KHỐI 2: SAGEMAKER AI PIPELINE & MODEL REGISTRY

### 4.1. Tạo Model Group trong SageMaker Studio
1. Mở **SageMaker AI Console** $\rightarrow$ Ở menu trái chọn **SageMaker Studio** $\rightarrow$ Nhấn **Open Studio**.
2. Trong Studio, vào menu trái chọn **Models** (hoặc **Model Registry**) $\rightarrow$ **Create model group**:
   - Tên: `CaliforniaHousingPackageGroup`.
   - Mô tả: `Mô hình Stacking Regressor cho California Housing Price`.
3. Nhấn **Create**.

### 4.2. Khởi tạo Bộ Scripts Script Mode trong Repository (`aws_sagemaker/steps/`)

#### 1. File `aws_sagemaker/steps/preprocessing.py`
```python
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split

if __name__ == "__main__":
    input_data_path = "/opt/ml/processing/input/housing.csv"
    print(f"Reading raw data from {input_data_path}...")
    df = pd.read_csv(input_data_path)

    # 1. Feature Engineering
    df["rooms_per_household"] = df["total_rooms"] / df["households"]
    df["bedrooms_per_room"] = df["total_bedrooms"] / df["total_rooms"]
    df["population_per_household"] = df["population"] / df["households"]

    X = df.drop(columns=["median_house_value"])
    y = df["median_house_value"]

    num_cols = [
        "longitude", "latitude", "housing_median_age", "total_rooms",
        "total_bedrooms", "population", "households", "median_income",
        "rooms_per_household", "bedrooms_per_room", "population_per_household"
    ]
    cat_cols = ["ocean_proximity"]

    preprocessor = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)
    ])

    X_transformed = preprocessor.fit_transform(X)

    # 2. Train / Val / Test Split (70% - 15% - 15%)
    X_train, X_temp, y_train, y_temp = train_test_split(X_transformed, y.values, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    output_dir = "/opt/ml/processing/output"
    os.makedirs(output_dir, exist_ok=True)

    np.save(os.path.join(output_dir, "train_X.npy"), X_train)
    np.save(os.path.join(output_dir, "train_y.npy"), y_train)
    np.save(os.path.join(output_dir, "val_X.npy"), X_val)
    np.save(os.path.join(output_dir, "val_y.npy"), y_val)
    np.save(os.path.join(output_dir, "test_X.npy"), X_test)
    np.save(os.path.join(output_dir, "test_y.npy"), y_test)
    joblib.dump(preprocessor, os.path.join(output_dir, "preprocessor.joblib"))
    print("Preprocessing completed successfully!")
```

#### 2. File `aws_sagemaker/steps/train.py`
```python
import os
import shutil
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.svm import SVR

if __name__ == "__main__":
    train_dir = os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train")
    X_train = np.load(os.path.join(train_dir, "train_X.npy"))
    y_train = np.load(os.path.join(train_dir, "train_y.npy"))

    print("Training Stacking Regressor (RF + SVR with Ridge Meta-Model)...")
    base_estimators = [
        ("rf", RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)),
        ("svr", SVR(C=1.0, epsilon=0.2))
    ]
    model = StackingRegressor(
        estimators=base_estimators,
        final_estimator=RidgeCV(),
        cv=5,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    model_dir = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(model, os.path.join(model_dir, "model.joblib"))

    # Đóng gói kèm preprocessor để Serving container tự khép kín
    preprocessor_src = os.path.join(train_dir, "preprocessor.joblib")
    if os.path.exists(preprocessor_src):
        shutil.copy(preprocessor_src, os.path.join(model_dir, "preprocessor.joblib"))
    print("Model training completed and saved.")
```

#### 3. File `aws_sagemaker/steps/evaluate.py`
```python
import json
import os
import tarfile
import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

if __name__ == "__main__":
    model_tar_path = "/opt/ml/processing/model/model.tar.gz"
    with tarfile.open(model_tar_path) as tar:
        tar.extractall(path="/opt/ml/processing/model_extracted")

    model = joblib.load("/opt/ml/processing/model_extracted/model.joblib")
    test_dir = "/opt/ml/processing/test"
    X_test = np.load(os.path.join(test_dir, "test_X.npy"))
    y_test = np.load(os.path.join(test_dir, "test_y.npy"))

    predictions = model.predict(X_test)
    r2 = float(r2_score(y_test, predictions))
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    mae = float(mean_absolute_error(y_test, predictions))

    print(f"Test R2 Score: {r2:.4f}, RMSE: {rmse:.4f}, MAE: {mae:.4f}")

    report_dict = {
        "regression_metrics": {
            "r2_score": {"value": r2},
            "rmse": {"value": rmse},
            "mae": {"value": mae}
        }
    }
    eval_dir = "/opt/ml/processing/evaluation"
    os.makedirs(eval_dir, exist_ok=True)
    with open(os.path.join(eval_dir, "evaluation.json"), "w") as f:
        json.dump(report_dict, f, indent=2)
```

#### 4. File `aws_sagemaker/steps/inference.py` (Cho Serving Container)
```python
import json
import os
import joblib
import pandas as pd

def model_fn(model_dir):
    model = joblib.load(os.path.join(model_dir, "model.joblib"))
    preprocessor = joblib.load(os.path.join(model_dir, "preprocessor.joblib"))
    return {"model": model, "preprocessor": preprocessor}

def input_fn(request_body, request_content_type):
    if request_content_type == "application/json":
        data = json.loads(request_body)
        cols = [
            "longitude", "latitude", "housing_median_age", "total_rooms",
            "total_bedrooms", "population", "households", "median_income",
            "ocean_proximity"
        ]
        df = pd.DataFrame(data["instances"], columns=cols)
        df["rooms_per_household"] = df["total_rooms"] / df["households"]
        df["bedrooms_per_room"] = df["total_bedrooms"] / df["total_rooms"]
        df["population_per_household"] = df["population"] / df["households"]
        return df
    raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, artifacts):
    transformed = artifacts["preprocessor"].transform(input_data)
    return artifacts["model"].predict(transformed)

def output_fn(prediction, accept):
    return json.dumps({"predictions": prediction.tolist()}), "application/json"
```

#### 5. File `aws_sagemaker/pipeline.py` (Định nghĩa DAG)
```python
import sagemaker
from sagemaker.sklearn.estimator import SKLearn
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.workflow.parameters import ParameterFloat, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.model_step import ModelStep
from sagemaker.model import Model
from sagemaker.workflow.properties import PropertyFile

def get_pipeline(role, default_bucket, model_package_group_name="CaliforniaHousingPackageGroup"):
    sagemaker_session = sagemaker.Session()
    
    r2_threshold = ParameterFloat(name="R2Threshold", default_value=0.80)
    input_data_uri = ParameterString(
        name="InputDataUrl",
        default_value=f"s3://{default_bucket}/raw/housing.csv"
    )

    # 1. Processing Step
    sklearn_processor = SKLearnProcessor(
        framework_version="1.2-1",
        instance_type="ml.t3.medium",
        instance_count=1,
        base_job_name="california-housing-prep",
        role=role
    )
    step_process = ProcessingStep(
        name="DataPreprocessing",
        processor=sklearn_processor,
        inputs=[ProcessingInput(source=input_data_uri, destination="/opt/ml/processing/input")],
        outputs=[ProcessingOutput(output_name="data", source="/opt/ml/processing/output")],
        code="aws_sagemaker/steps/preprocessing.py"
    )

    # 2. Training Step
    sklearn_estimator = SKLearn(
        entry_point="train.py",
        source_dir="aws_sagemaker/steps",
        framework_version="1.2-1",
        instance_type="ml.m5.xlarge",
        instance_count=1,
        role=role
    )
    step_train = TrainingStep(
        name="ModelTraining",
        estimator=sklearn_estimator,
        inputs={"train": step_process.properties.ProcessingOutputConfig.Outputs["data"].S3Output.S3Uri}
    )

    # 3. Evaluation Step
    eval_report = PropertyFile(name="EvaluationReport", output_name="evaluation", path="evaluation.json")
    step_eval = ProcessingStep(
        name="ModelEvaluation",
        processor=sklearn_processor,
        inputs=[
            ProcessingInput(source=step_train.properties.ModelArtifacts.S3ModelArtifacts, destination="/opt/ml/processing/model"),
            ProcessingInput(source=step_process.properties.ProcessingOutputConfig.Outputs["data"].S3Output.S3Uri, destination="/opt/ml/processing/test")
        ],
        outputs=[ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation")],
        code="aws_sagemaker/steps/evaluate.py",
        property_files=[eval_report]
    )

    # 4. Condition & Model Registration
    model = Model(
        image_uri=sklearn_estimator.image_uri,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        sagemaker_session=sagemaker_session,
        role=role,
        entry_point="aws_sagemaker/steps/inference.py"
    )
    step_register = ModelStep(
        name="RegisterModel",
        step_args=model.register(
            content_types=["application/json"],
            response_types=["application/json"],
            inference_instances=["ml.t3.medium", "ml.m5.large"],
            transform_instances=["ml.m5.large"],
            model_package_group_name=model_package_group_name,
            approval_status="PendingManualApproval"
        )
    )

    cond_r2 = ConditionGreaterThanOrEqualTo(
        left=step_eval.properties.ProcessingOutputConfig.Outputs["evaluation"].S3Output.S3Uri,
        right=r2_threshold
    )
    step_cond = ConditionStep(
        name="CheckEvaluationMetrics",
        conditions=[cond_r2],
        if_steps=[step_register],
        else_steps=[]
    )

    pipeline = Pipeline(
        name="CaliforniaHousingMLOpsPipeline",
        parameters=[r2_threshold, input_data_uri],
        steps=[step_process, step_train, step_eval, step_cond]
    )
    return pipeline
```

---

## 5. KHỐI 3: CI/CD PIPELINE (CODEPIPELINE & CODEBUILD)

### 5.1. Tạo Amazon SNS Topic cho Manual Approval
1. Mở **Amazon SNS Console** $\rightarrow$ **Topics** $\rightarrow$ **Create topic**:
   - Type: **Standard**, Name: `california-housing-approval-topic`.
2. Tạo Subscription: Protocol: **Email**, Endpoint: Nhập email nhận duyệt của bạn.
3. Mở email cá nhân bấm link **Confirm subscription**.

### 5.2. Chuẩn bị 2 file Buildspec trong thư mục `buildspecs/`

- **File `buildspecs/buildspec_ci.yml`**:
```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install -e .
      - pip install pytest flake8
  pre_build:
    commands:
      - flake8 src tests aws_sagemaker --count --max-line-length=127 --statistics
  build:
    commands:
      - pytest tests/unit/ -v
```

- **File `buildspecs/buildspec_ml.yml`**:
```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install sagemaker boto3
  build:
    commands:
      - python -c "from aws_sagemaker.pipeline import get_pipeline; p = get_pipeline('$SAGEMAKER_ROLE_ARN', '$DATA_BUCKET'); p.upsert(role_arn='$SAGEMAKER_ROLE_ARN'); execution = p.start(); print('Pipeline started:', execution.arn)"
```

### 5.3. Tạo CodePipeline trên AWS Console
1. Mở **AWS CodePipeline Console** $\rightarrow$ **Create pipeline**:
   - Pipeline name: `california-housing-mlops-pipeline`.
   - Service role: Chọn **New service role** *(AWS tự động sinh role)*.
2. **Stage 1 (Source):** GitHub (Version 2) $\rightarrow$ Chọn repo `nvbao117/california-housing-price`, branch `main`.
3. **Stage 2 (CI):** CodeBuild $\rightarrow$ Tạo project `california-housing-ci` trỏ tới `buildspecs/buildspec_ci.yml`.
4. Nhấn Next $\rightarrow$ Chọn **Skip deploy stage** $\rightarrow$ Nhấn **Create pipeline**.
5. Nhấn **Edit** pipeline vừa tạo:
   - Thêm Stage sau CI: `ML_Pipeline` $\rightarrow$ Action provider: CodeBuild (chạy `buildspecs/buildspec_ml.yml`).
   - Thêm Stage sau đó: `Manual_Approval` $\rightarrow$ Action provider: **Manual approval** $\rightarrow$ Gắn SNS Topic `california-housing-approval-topic`.
   - Nhấn **Save**.
6. **Cấp quyền PassRole cho CodeBuild Role:**
   - Vào IAM Console $\rightarrow$ Roles $\rightarrow$ Tìm role CodeBuild vừa tạo $\rightarrow$ Add Inline Policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["iam:PassRole", "sagemaker:*", "s3:*"],
         "Resource": "*"
       }
     ]
   }
   ```

---

## 6. KHỐI 4: SAGEMAKER INFERENCE (SERVERLESS SERVING ENDPOINT)

### 6.1. Phê duyệt Model trong SageMaker Studio
1. Mở **SageMaker Studio** $\rightarrow$ Vào **Model Registry** $\rightarrow$ Nhấp vào `CaliforniaHousingPackageGroup`.
2. Bấm vào Model Version 1 $\rightarrow$ Xem bảng chỉ số $R^2$, RMSE, MAE.
3. Nhấn **Update status** $\rightarrow$ Chọn **Approved**.

### 6.2. Tạo Serverless Endpoint (Deployments & inference)
Thao tác trên menu **Deployments & inference** (nằm ở menu trái của Console):
1. **Models:** Nhấn Create model $\rightarrow$ Chọn model package version 1 đã Approved từ Model Registry.
2. **Endpoint configurations:**
   - Chọn **Serverless**.
   - Gắn model vừa tạo.
   - Memory size: **2048 MB**, Max concurrency: **10**.
3. **Endpoints:**
   - Nhấn Create endpoint.
   - Tên: `california-housing-ep`.
   - Gắn configuration vừa tạo $\rightarrow$ Chờ 2 phút đến khi trạng thái là `InService`.

---

## 7. KHỐI 5: CONSUMER LAYER & FEEDBACK LOOP

### 7.1. Tạo Amazon DynamoDB Table
1. Mở **DynamoDB Console** $\rightarrow$ **Create table**:
   - Table name: `CaliforniaHousingPredictions`.
   - Partition key: `prediction_id` (String).
   - Capacity mode: **On-demand** $\rightarrow$ Nhấn **Create table**.

### 7.2. Tạo AWS Lambda API Proxy
1. Mở **AWS Lambda Console** $\rightarrow$ **Create function**:
   - Name: `california-housing-api-proxy` (Python 3.11).
   - Role: `CaliforniaHousing-LambdaExecutionRole`.
2. Dán mã nguồn vào `lambda_function.py`:
```python
import json
import uuid
import os
from datetime import datetime
import boto3

sm_runtime = boto3.client('sagemaker-runtime')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CaliforniaHousingPredictions')
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME', 'california-housing-ep')

def lambda_handler(event, context):
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    path = event.get('rawPath', '')
    
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

    if method == 'OPTIONS':
        return {"statusCode": 200, "headers": headers, "body": "{}"}

    # Route 1: POST /predict (Dự đoán và ghi log)
    if path.endswith('/predict') and method == 'POST':
        body = json.loads(event.get('body', '{}'))
        instances = body.get('instances', [])
        
        resp = sm_runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps({"instances": instances})
        )
        res_body = json.loads(resp['Body'].read().decode())
        pred_val = res_body['predictions'][0]
        
        pred_id = str(uuid.uuid4())
        table.put_item(
            Item={
                'prediction_id': pred_id,
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'features': json.dumps(instances[0]),
                'predicted_price': str(pred_val),
                'actual_price': None
            }
        )
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"prediction_id": pred_id, "predicted_value": pred_val})
        }

    # Route 2: POST /feedback (Ghi nhận phản hồi thực tế)
    elif path.endswith('/feedback') and method == 'POST':
        body = json.loads(event.get('body', '{}'))
        pred_id = body.get('prediction_id')
        actual_price = body.get('actual_price')
        
        table.update_item(
            Key={'prediction_id': pred_id},
            UpdateExpression="SET actual_price = :val, feedback_timestamp = :ts",
            ExpressionAttributeValues={
                ':val': str(actual_price),
                ':ts': datetime.utcnow().isoformat() + "Z"
            }
        )
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "Feedback saved"})}

    return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Not Found"})}
```
3. Configuration $\rightarrow$ Environment variables: `ENDPOINT_NAME` = `california-housing-ep` $\rightarrow$ Nhấn **Deploy**.

### 7.3. Tạo Amazon API Gateway (HTTP API)
1. Mở **API Gateway Console** $\rightarrow$ **Create API** ở mục **HTTP API**:
   - Name: `california-housing-api`.
2. Add integration: Chọn **Lambda** $\rightarrow$ Chọn `california-housing-api-proxy`.
3. Routes: `POST /predict`, `POST /feedback`.
4. Bật **CORS**: Origin: `*`, Methods: `POST, OPTIONS`, Headers: `*`.
5. Lưu lại **Invoke URL** (Ví dụ: `https://xyz.execute-api.us-east-1.amazonaws.com`).

### 7.4. Deploy Frontend React (S3 + CloudFront)
1. Trong thư mục `frontend/`, sửa file `.env.production`:
   ```env
   REACT_APP_API_BASE_URL=https://xyz.execute-api.us-east-1.amazonaws.com
   ```
2. Chạy `npm run build`.
3. Tạo S3 bucket `california-housing-web-<your-alias>`, bật **Static website hosting**, tải toàn bộ thư mục `build/` lên.
4. Mở **CloudFront Console** $\rightarrow$ **Create distribution** trỏ vào S3 bucket web, cấu hình **Redirect HTTP to HTTPS**.
5. Bạn sẽ có domain HTTPS công khai để người dùng truy cập định giá nhà.

---

## 8. DANH MỤC KIỂM THỬ CUỐI CÙNG (END-TO-END ACCEPTANCE)

| Thao tác kiểm thử | Kết quả kỳ vọng | Trạng thái |
| :--- | :--- | :---: |
| **Upload file `housing.csv` vào S3 raw bucket** | File `manifest.json` xuất hiện trong manifest bucket sau vài giây. | [ ] |
| **Push commit mới lên nhánh `main`** | CodePipeline tự động kích hoạt, test CI pass và gọi SageMaker Pipeline. | [ ] |
| **Mở SageMaker Studio $\rightarrow$ Pipelines** | Đồ thị DAG hiển thị các bước chạy, đổi màu xanh lá cây thành công. | [ ] |
| **Kiểm tra Model Registry trong Studio** | Model package version 1 xuất hiện với $R^2 \approx 0.82$. Bấm nút Approved. | [ ] |
| **Kiểm tra Serving Endpoint** | Endpoint `california-housing-ep` ở trạng thái `InService`. | [ ] |
| **Gửi request trên giao diện Web React** | Giá nhà được dự đoán tức thì và xuất hiện bản ghi mới trong DynamoDB. | [ ] |
| **Gửi feedback giá bán thực tế** | Bản ghi trong DynamoDB được cập nhật trường `actual_price`. | [ ] |
