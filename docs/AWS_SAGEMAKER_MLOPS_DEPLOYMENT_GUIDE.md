# 🏗️ BÁO CÁO KỸ THUẬT & HƯỚNG DẪN TRIỂN KHAI MLOPS TOÀN DIỆN TRÊN AWS

> **Dự án**: Dự đoán Giá Nhà California (California Housing Price Prediction)  
> **Kiến trúc**: Chuẩn Enterprise MLOps Data Lakehouse (4 S3 Buckets & 3 IAM Roles)  
> **Stack**: SageMaker · CodePipeline · CodeBuild · Lambda · API Gateway · DynamoDB · S3 · CloudFront · SNS  
> **Phiên bản**: 3.0 Enterprise Edition (Đầy đủ Console UI + CLI cho mọi bước)  
> **Cập nhật**: 09/09/2026

---

## 📑 MỤC LỤC

1. [Tổng quan Kiến trúc & Nguyên lý Vận hành](#1-tổng-quan-kiến-trúc--nguyên-lý-vận-hành)
2. [Khối 1: Hạ tầng Lưu trữ (4 S3 Buckets) & Bảo mật (3 IAM Roles)](#2-khối-1-hạ-tầng-lưu-trữ-4-s3-buckets--bảo-mật-3-iam-roles)
3. [Khối 2: Lõi Machine Learning DAG Pipeline (Amazon SageMaker)](#3-khối-2-lõi-machine-learning-dag-pipeline-amazon-sagemaker)
4. [Khối 3: Tự động hóa CI/CD (AWS CodePipeline + CodeBuild + SNS)](#4-khối-3-tự-động-hóa-cicd-aws-codepipeline--codebuild--sns)
5. [Khối 4: Triển khai Mô hình (Model Registry ➔ Serverless Endpoint)](#5-khối-4-triển-khai-mô-hình-model-registry--serverless-endpoint)
6. [Khối 5: Tầng API Tiêu thụ (DynamoDB + Lambda Proxy + API Gateway)](#6-khối-5-tầng-api-tiêu-thụ-dynamodb--lambda-proxy--api-gateway)
7. [Khối 6: Giao diện Người dùng (React SPA + S3 Static + CloudFront CDN)](#7-khối-6-giao-diện-người-dùng-react-spa--s3-static--cloudfront-cdn)
8. [Khối 7: Giám sát Hệ thống (CloudWatch Alarms & Logging)](#8-khối-7-giám-sát-hệ-thống-cloudwatch-alarms--logging)
9. [Bảng Tổng Hợp 10 Lỗi Kỹ Thuật Thực Tế & Cách Khắc Phục](#9-bảng-tổng-hợp-10-lỗi-kỹ-thuật-thực-tế--cách-khắc-phục)
10. [Quy Trình Dọn Dẹp Tài Nguyên (Teardown Script)](#10-quy-trình-dọn-dẹp-tài-nguyên-teardown-script)

---

## 1. TỔNG QUAN KIẾN TRÚC & NGUYÊN LÝ VẬN HÀNH

### 1.1 Sơ đồ luồng hoạt động End-to-End

```
┌────────────────────────────────────────────────────────────────────────┐
│  DEVELOPER WORKFLOW: git tag v1.0.0 && git push origin v1.0.0          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Webhook Trigger (Tag Push)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  KHỐI 3: CI/CD LAYER (AWS CodePipeline)                                │
│  Source (GitHub) ➔ Build (CodeBuild) ➔ ML Trigger ➔ Manual Approval   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ python pipeline.py --execute
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  KHỐI 2: SAGEMAKER AI DAG PIPELINE                                     │
│  [Raw Bucket]                                                          │
│        ↓                                                               │
│  DataPreprocessing ➔ ModelTraining ➔ ModelEvaluation                   │
│                                            ↓                           │
│                                 Validation Gate (R² >= 0.7)            │
│                                            ↓ True                      │
│                                 RegisterModel ➔ [Artifacts Bucket]     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Model Approved in Registry
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  KHỐI 4: SERVING LAYER                                                 │
│  SageMaker Model ➔ Endpoint Config (Serverless) ➔ SageMaker Endpoint   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ sagemaker:InvokeEndpoint
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  KHỐI 5: CONSUMER & API LAYER                                          │
│  Client Request ➔ API Gateway HTTP ➔ Lambda Proxy (30s timeout)       │
│                                            │                           │
│                                            └➔ Log to DynamoDB Table    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  KHỐI 6: PRESENTATION LAYER (React + Vite trên S3 + CloudFront CDN)   │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Tại sao Khối 2 (SageMaker DAG) nằm trước Khối 3 (CodePipeline)?
* **Lõi nghiệp vụ vs. Vỏ bọc tự động**: SageMaker Pipeline chứa toàn bộ thuật toán ML, tiền xử lý và cổng kiểm định (Quality Gate). CodePipeline chỉ đóng vai trò là "người gọi lệnh" (`caller`).
* **Quy trình phát triển chuẩn**: Kỹ sư MLOps phải kiểm thử đồ thị DAG chạy thông suốt từ máy cục bộ trước khi bàn giao cho CI/CD tự động hóa. Nếu dựng CodePipeline trước, hệ thống sẽ liên tục bị `Failed` ở bước Build do thiếu định nghĩa ML.

---

## 2. KHỐI 1: HẠ TẦNG LƯU TRỮ (4 S3 BUCKETS) & BẢO MẬT (3 IAM ROLES)

### 2.1 Bảng Phân Bổ 4 S3 Buckets (Chuẩn Enterprise Data Lakehouse)

| STT | Tên Bucket | Tầng kiến trúc | Phân quyền | Cấu hình đặc biệt | Chức năng chi tiết |
|:---:|:---|:---:|:---:|:---:|:---|
| **1** | `california-housing-raw-678551739301-us-east-1-an` | **Data Lake** | Private | **Versioning: Enabled** | Chứa file dữ liệu gốc `housing.csv`. SageMaker chỉ có quyền Đọc (Read-Only). |
| **2** | `california-housing-artifacts-678551739301-us-east-1-an` | **ML Storage** | Private | Lifecycle (60 ngày) | Chứa `train.csv`, `test.csv`, **`model.tar.gz`**, `evaluation.json`, `sourcedir.tar.gz`. |
| **3** | `california-housing-manifest-678551739301-us-east-1-an` | **CI/CD** | Private | Mặc định | Lưu `SourceArtifact.zip`, `BuildArtifact.zip` cho CodePipeline. |
| **4** | `california-housing-web-678551739301-us-east-1-an` | **Web UI** | Public Read | **Static Hosting: Enabled** | Chứa mã nguồn bundle React (`index.html`, thư mục `assets/`). |

#### 🖥️ Thao tác tạo 4 Buckets trên AWS Console:
1. **Raw Bucket**: S3 ➔ **Create bucket** ➔ Tên: `california-housing-raw-678551739301-us-east-1-an` ➔ Bật **Bucket Versioning: Enable** ➔ Create.
2. **Artifacts Bucket**: S3 ➔ **Create bucket** ➔ Tên: `california-housing-artifacts-678551739301-us-east-1-an` ➔ Create.
3. **Manifest Bucket**: S3 ➔ **Create bucket** ➔ Tên: `california-housing-manifest-678551739301-us-east-1-an` ➔ Create.
4. **Web Bucket**: S3 ➔ **Create bucket** ➔ Tên: `california-housing-web-678551739301-us-east-1-an` ➔ Bỏ chọn *Block all public access* ➔ Create.
   * Sau đó vào bucket: **Properties** ➔ **Static website hosting** ➔ **Enable** (Index: `index.html`, Error: `index.html`).
   * Vào **Permissions** ➔ **Bucket policy** ➔ Dán policy Public Read:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [{
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::california-housing-web-678551739301-us-east-1-an/*"
       }]
     }
     ```

#### ⌨️ Thao tác tạo 4 Buckets qua AWS CLI:
```bash
ACCOUNT_ID="678551739301"
REGION="us-east-1"
SUFFIX="an"

# 1. Raw Data Bucket
aws s3api create-bucket --bucket california-housing-raw-${ACCOUNT_ID}-${REGION}-${SUFFIX} --region ${REGION}
aws s3api put-bucket-versioning --bucket california-housing-raw-${ACCOUNT_ID}-${REGION}-${SUFFIX} --versioning-configuration Status=Enabled

# 2. ML Artifacts Bucket
aws s3api create-bucket --bucket california-housing-artifacts-${ACCOUNT_ID}-${REGION}-${SUFFIX} --region ${REGION}

# 3. CI/CD Manifest Bucket
aws s3api create-bucket --bucket california-housing-manifest-${ACCOUNT_ID}-${REGION}-${SUFFIX} --region ${REGION}

# 4. Web Bucket
WEB_BUCKET="california-housing-web-${ACCOUNT_ID}-${REGION}-${SUFFIX}"
aws s3api create-bucket --bucket ${WEB_BUCKET} --region ${REGION}
aws s3api delete-public-access-block --bucket ${WEB_BUCKET}
aws s3 website s3://${WEB_BUCKET}/ --index-document index.html --error-document index.html
```

---

### 2.2 Bảng Phân Bổ 3 IAM Roles

| STT | Tên IAM Role | Dịch vụ tin cậy (Trusted Entity) | Quyền hạn đính kèm (Policies) | Hậu quả nếu thiếu |
|:---:|:---|:---|:---|:---|
| **1** | `CaliforniaHousing-SageMakerExecutionRole` | `sagemaker.amazonaws.com` | • `AmazonSageMakerFullAccess`<br>• `AmazonS3FullAccess` | SageMaker báo lỗi `AccessDenied` ngay bước Preprocessing/Training. |
| **2** | `CaliforniaHousing-LambdaExecutionRole` | `lambda.amazonaws.com` | • `AWSLambdaBasicExecutionRole`<br>• Inline: `LambdaCustomPolicy` (`sagemaker:InvokeEndpoint`, `dynamodb:*`) | Web báo lỗi `500`; không gọi được Endpoint và không ghi được log DynamoDB. |
| **3** | `AWSCodePipelineServiceRole-us-east-1-california-housing-mlops-p` | `codepipeline.amazonaws.com` | • `AWSCodePipelineServiceRole`<br>• Inline: **`AllowSNSPublish`** (`sns:Publish`) | CodePipeline dừng khẩn cấp tại bước Manual Approval vì không gửi được email SNS. |

#### ⌨️ Lệnh tạo 3 IAM Roles hoàn chỉnh qua CLI:
```bash
# 1. SageMaker Role
aws iam create-role --role-name CaliforniaHousing-SageMakerExecutionRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"sagemaker.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name CaliforniaHousing-SageMakerExecutionRole --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam attach-role-policy --role-name CaliforniaHousing-SageMakerExecutionRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# 2. Lambda Role
aws iam create-role --role-name CaliforniaHousing-LambdaExecutionRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name CaliforniaHousing-LambdaExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name CaliforniaHousing-LambdaExecutionRole --policy-name LambdaCustomPolicy --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect":"Allow","Action":["sagemaker:InvokeEndpoint"],"Resource":"*"},
    {"Effect":"Allow","Action":["dynamodb:PutItem","dynamodb:GetItem","dynamodb:UpdateItem"],"Resource":"*"}
  ]
}'

# 3. CodePipeline Role
aws iam create-role --role-name AWSCodePipelineServiceRole-us-east-1-california-housing-mlops-p \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"codepipeline.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam put-role-policy --role-name AWSCodePipelineServiceRole-us-east-1-california-housing-mlops-p --policy-name AllowSNSPublish --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{"Effect":"Allow","Action":["sns:Publish"],"Resource":"arn:aws:sns:us-east-1:678551739301:alifornia-housing-approval-topic"}]
}'
```

---

## 3. KHỐI 2: LÕI MACHINE LEARNING DAG PIPELINE (AMAZON SAGEMAKER)

### 3.1 Cấu trúc mã nguồn Script Mode (`aws_sagemaker/`)
```text
aws_sagemaker/
├── pipeline.py           # Định nghĩa đồ thị DAG, liên kết các Step, Quality Gate
└── steps/
    ├── preprocessing.py  # Xử lý missing data, One-Hot Encode, chia train 80% / test 20%
    ├── train.py          # Huấn luyện RandomForestRegressor, xuất model.tar.gz
    ├── evaluate.py       # Đánh giá R² score trên test.csv, xuất evaluation.json
    └── inference.py      # Custom Handler giải mã request & trả về dự đoán khi serving
```

* **Base Container Image**: `683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3`

---

### 3.2 Đồ thị DAG & Cơ chế Model Validation (Quality Gate)

```
                    ┌──────────────────────────┐
                    │ 1. DataPreprocessing     │ Đọc từ: Raw Bucket
                    └────────────┬─────────────┘
                                 │ train.csv, test.csv
                                 ▼
                    ┌──────────────────────────┐
                    │ 2. ModelTraining         │ Huấn luyện Random Forest
                    └────────────┬─────────────┘
                                 │ model.tar.gz ➔ Artifacts Bucket
                                 ▼
                    ┌──────────────────────────┐
                    │ 3. ModelEvaluation       │ Đánh giá độc lập trên test.csv
                    └────────────┬─────────────┘
                                 │ evaluation.json
                                 ▼
                    ┌──────────────────────────┐
                    │ 4. Quality Gate (R²>=0.7)│ Model Validation
                    └────────────┬─────────────┘
                         True    │    False
                   ┌─────────────┴────────────┐
                   ▼                          ▼
        ┌─────────────────────┐      ┌──────────────────┐
        │ 5. RegisterModel    │      │ Dừng Pipeline    │
        │ Model Registry (V1) │      │ Loại bỏ mô hình  │
        └─────────────────────┘      └──────────────────┘
```

---

### 3.3 ⚠️ Lưu ý kỹ thuật: Lỗi `BinaryCondition Type Mismatch` & Giải pháp `JsonGet`

* **Lỗi**: `ClientError: BinaryCondition left=<S3Uri (String)> right=<0.7 (Float)> – Type mismatch`.
* **Nguyên nhân**: Truyền trực tiếp `Outputs["evaluation"]` sẽ trả về chuỗi String đường dẫn S3 thay vì giá trị số thực bên trong JSON.
* **Giải pháp chuẩn**:
```python
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep

# 1. Khai báo PropertyFile
eval_report = PropertyFile(name="EvaluationReport", output_name="evaluation", path="evaluation.json")

# 2. Bóc tách số thực float bằng JsonGet
cond_r2 = ConditionGreaterThanOrEqualTo(
    left=JsonGet(step_name=step_evaluate.name, property_file=eval_report, json_path="regression_metrics.r2_score.value"),
    right=0.7
)

# 3. Tạo ConditionStep
step_cond = ConditionStep(name="CheckEvaluationMetrics", conditions=[cond_r2], if_steps=[step_register], else_steps=[])
```

---

### 3.4 Vận hành & Thực thi Pipeline

#### 🖥️ Theo dõi qua AWS Console UI:
1. **SageMaker → Pipelines** ➔ Chọn `CaliforniaHousingMLOpsPipeline`.
2. Tab **Executions** ➔ Click vào Execution ID đang chạy.
3. Quan sát đồ thị trực quan: Các node chuyển màu xanh lá cây khi hoàn thành. Click vào từng node ➔ **View logs** để xem stdout/stderr thời gian thực.
4. Click vào node `CheckEvaluationMetrics` ➔ Tab **Condition** để xem kết quả $R^2 \ge 0.70 \implies \text{True}$.
5. Vào **Model registry → CaliforniaHousingPackageGroup** để thấy `Version 1` ở trạng thái `PendingManualApproval`.

#### ⌨️ Chạy bằng CLI (có cơ chế Auto-Cancel job cũ):
```bash
python aws_sagemaker/pipeline.py \
  --region us-east-1 \
  --role arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole \
  --input-data s3://california-housing-raw-678551739301-us-east-1-an/housing.csv \
  --default-bucket california-housing-artifacts-678551739301-us-east-1-an \
  --execute
```

---

## 4. KHỐI 3: TỰ ĐỘNG HÓA CI/CD (AWS CODEPIPELINE + CODEBUILD + SNS)

### 4.1 Cơ chế Tag-Triggered Retraining (Tiết kiệm chi phí)
Để tránh lãng phí chi phí huấn luyện mỗi khi push code sửa giao diện hoặc tài liệu, `buildspecs/buildspec_ml.yml` chỉ kích hoạt chạy huấn luyện khi phát hiện **Git Tag phiên bản** (`v*.*.*`):

```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install sagemaker boto3
  pre_build:
    commands:
      - |
        CURRENT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
        if [[ "${CURRENT_TAG}" == v* ]] || [[ "${FORCE_TRAIN}" == "true" ]]; then
          echo "SHOULD_TRAIN=true" > /tmp/train_flag
        else
          echo "SHOULD_TRAIN=false" > /tmp/train_flag
        fi
  build:
    commands:
      - SHOULD_TRAIN=$(grep SHOULD_TRAIN /tmp/train_flag | cut -d= -f2)
      - |
        if [[ "${SHOULD_TRAIN}" == "true" ]]; then
          python aws_sagemaker/pipeline.py --region us-east-1 --role arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole --default-bucket california-housing-artifacts-678551739301-us-east-1-an --execute
        else
          python aws_sagemaker/pipeline.py --region us-east-1 --role arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole --default-bucket california-housing-artifacts-678551739301-us-east-1-an
        fi
```

### 4.2 Thao tác Kích hoạt:
```bash
# Push code thông thường (Không tốn tiền train)
git add . && git commit -m "docs: update guide" && git push origin main

# Kích hoạt huấn luyện tự động (CI/CD Tag Push)
git tag v1.0.1 -m "Release v1.0.1" && git push origin v1.0.1
```

---

## 5. KHỐI 4: TRIỂN KHAI MÔ HÌNH (MODEL REGISTRY ➔ SERVERLESS ENDPOINT)

### 5.1 Phê duyệt mô hình
* **Console**: SageMaker ➔ Model Registry ➔ `CaliforniaHousingPackageGroup` ➔ Chọn version ➔ **Update status ➔ Approved**.
* **CLI**:
```bash
aws sagemaker update-model-package \
  --model-package-arn "arn:aws:sagemaker:us-east-1:678551739301:model-package/CaliforniaHousingPackageGroup/1" \
  --model-approval-status Approved
```

---

### 5.2 ⚠️ Lưu ý kỹ thuật: Lỗi Network Isolation trên Serverless Inference

* **Vấn đề**: Tạo Model từ giao diện Console qua Model Registry sẽ tự động gán `EnableNetworkIsolation=True`. Điều này dẫn đến lỗi: `ValidationException: Network isolation is not supported for Serverless Inference`.
* **Giải pháp chuẩn**: Tạo SageMaker Model qua CLI chỉ định tường minh Container Image và Artifacts:

```bash
aws sagemaker create-model \
  --model-name california-housing-model-v1 \
  --execution-role-arn arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole \
  --primary-container '{
    "Image": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
    "ModelDataUrl": "s3://california-housing-artifacts-678551739301-us-east-1-an/pipelines-.../output/model.tar.gz",
    "Environment": {
      "SAGEMAKER_PROGRAM": "training.py",
      "SAGEMAKER_SUBMIT_DIRECTORY": "s3://california-housing-artifacts-678551739301-us-east-1-an/.../sourcedir.tar.gz"
    }
  }'
```

---

### 5.3 Khởi tạo Serverless Endpoint (Tối ưu 100% chi phí chạy nhàn rỗi)

```bash
# 1. Endpoint Configuration (Memory: 2048 MB, Max Concurrency: 10)
aws sagemaker create-endpoint-config \
  --endpoint-config-name california-housing-serverless-cfg \
  --production-variants '[{
    "VariantName": "AllTraffic",
    "ModelName": "california-housing-model-v1",
    "ServerlessConfig": {"MemorySizeInMB": 2048, "MaxConcurrency": 10}
  }]'

# 2. Create Endpoint
aws sagemaker create-endpoint \
  --endpoint-name california-housing-ep \
  --endpoint-config-name california-housing-serverless-cfg

# 3. Test Invoke trực tiếp
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name california-housing-ep \
  --content-type application/json \
  --body '{"instances": [[-122.23, 37.88, 41.0, 880.0, 129.0, 322.0, 126.0, 8.3252, 0]]}' \
  --cli-binary-format raw-in-base64-out /tmp/output.json && cat /tmp/output.json
# Kết quả: {"predictions": [425027.58]}
```

---

## 6. KHỐI 5: TẦNG API TIÊU THỤ (DYNAMODB + LAMBDA PROXY + API GATEWAY)

### 6.1 Khởi tạo DynamoDB Table
```bash
aws dynamodb create-table \
  --table-name CaliforniaHousingPredictions \
  --attribute-definitions AttributeName=prediction_id,AttributeType=S \
  --key-schema AttributeName=prediction_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

---

### 6.2 Triển khai Lambda Proxy (`aws_lambda/lambda_function.py`)
* ⚠️ **Lưu ý Timeout**: Tăng timeout Lambda lên **30 giây** trong mục Configuration để tránh lỗi gián đoạn do cold start của Serverless Endpoint (15-20s).

```python
import json, boto3, uuid, os
from datetime import datetime

ENDPOINT_NAME = os.environ.get("ENDPOINT_NAME", "california-housing-ep")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "CaliforniaHousingPredictions")

sm_runtime = boto3.client("sagemaker-runtime")
dynamodb = boto3.resource("dynamodb")

def lambda_handler(event, context):
    path = event.get("rawPath", "/predict")
    body = json.loads(event.get("body", "{}"))

    if path == "/predict":
        response = sm_runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME, ContentType="application/json", Body=json.dumps(body)
        )
        result = json.loads(response["Body"].read().decode())
        predicted = result["predictions"][0]

        pred_id = str(uuid.uuid4())
        dynamodb.Table(TABLE_NAME).put_item(Item={
            "prediction_id": pred_id,
            "timestamp": datetime.utcnow().isoformat(),
            "features": json.dumps(body),
            "predicted_price": str(predicted)
        })

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"prediction_id": pred_id, "predicted_value": predicted})
        }
```

---

### 6.3 Tạo API Gateway HTTP API
* Tạo 2 Routes: `POST /predict` và `POST /feedback` trỏ tới Lambda.
* Bật CORS: `AllowOrigins: *`, `AllowMethods: POST, OPTIONS`.
* Invoke URL thu được: `https://1modfu9v9k.execute-api.us-east-1.amazonaws.com`

---

## 7. KHỐI 6: GIAO DIỆN NGƯỜI DÙNG (REACT SPA + S3 STATIC + CLOUDFRONT CDN)

### 7.1 ⚠️ Lưu ý kỹ thuật: Khắc phục Màn hình trắng & Lỗi Timeout ISP
1. **Khắc phục màn hình trắng (White Screen)**:
   * S3 Static Hosting không hỗ trợ HTML5 PushState. Sửa `frontend/src/App.jsx` sang **`HashRouter`**.
   * Trong `frontend/vite.config.js`: Thêm **`base: './'`** để đường dẫn nạp assets là tương đối.
2. **Khắc phục lỗi Timeout (ERR_TIMED_OUT)**:
   * S3 Website Endpoint sử dụng HTTP (Port 80) bị chặn bởi các nhà mạng tại Việt Nam.
   * **Giải pháp**: Tạo **AWS CloudFront Distribution** hỗ trợ HTTPS (Port 443) với **Default Root Object: `index.html`**.

### 7.2 Build & Upload Frontend:
```bash
cd frontend
npm install && npm run build

# Đồng bộ file bên trong dist/ vào root bucket (KHÔNG upload cả folder dist)
aws s3 sync dist/ s3://california-housing-web-678551739301-us-east-1-an/ --delete
```

---

## 8. KHỐI 7: GIÁM SÁT HỆ THỐNG (CLOUDWATCH ALARMS & LOGGING)

### 8.1 Tạo Alarm cảnh báo lỗi Endpoint
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "CaliforniaHousingEndpointErrors" \
  --metric-name InvocationModelErrors \
  --namespace AWS/SageMaker \
  --dimensions Name=EndpointName,Value=california-housing-ep Name=VariantName,Value=AllTraffic \
  --statistic Sum --period 300 --evaluation-periods 1 --threshold 5 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:678551739301:alifornia-housing-approval-topic"
```

---

## 9. BẢNG TỔNG HỢP 10 LỖI KỸ THUẬT THỰC TẾ & CÁCH KHẮC PHỤC

| # | Lỗi Gặp Phải | Nguyên Nhân Gốc Rễ | Giải Pháp Triệt Để |
|:---:|:---|:---|:---|
| **1** | `SNS:Publish not authorized` trong CodePipeline | Role CodePipeline tự tạo thiếu quyền SNS mặc định | Thêm Inline Policy `sns:Publish` vào Role CodePipeline. |
| **2** | `BinaryCondition type mismatch (String vs Float)` | Dùng trực tiếp S3Uri String trong ConditionStep | Dùng `JsonGet` với `PropertyFile` để bóc tách giá trị float. |
| **3** | `Network isolation not supported for Serverless` | Tạo Model qua Console tự động bật Network Isolation | Tạo SageMaker Model qua CLI không truyền cờ isolation. |
| **4** | `UnexpectedParameter TrainingPlanArnEquals` | Bug giao diện AWS Console trong Create Model dialog | Sử dụng luồng chỉ định container image & artifacts thủ công. |
| **5** | Màn hình trắng hoàn toàn khi load web từ S3 | `BrowserRouter` & Vite absolute path (`/`) không tương thích S3 | Đổi sang `HashRouter` và thêm `base: './'` trong `vite.config.js`. |
| **6** | Bucket S3 hiển thị folder `dist/` | Kéo thả nguyên cả thư mục `dist/` thay vì nội dung bên trong | Upload các file BÊN TRONG `dist/` vào root bucket hoặc dùng `aws s3 sync`. |
| **7** | `ERR_TIMED_OUT` khi truy cập S3 Website URL | ISP Việt Nam chặn cổng HTTP 80 của AWS S3 endpoints | Tạo AWS CloudFront Distribution để phục vụ web qua HTTPS 443. |
| **8** | Web gọi `http://localhost:8000` bị lỗi Network | URL API bị hardcode từ môi trường phát triển local | Cấu hình biến môi trường `.env.production` trỏ vào API Gateway. |
| **9** | Lambda Timeout sau 3 giây | Default Lambda timeout quá ngắn so với cold start Serverless (15-20s) | Tăng timeout của Lambda lên 30 giây trong General Configuration. |
| **10** | Huấn luyện chạy lãng phí mỗi lần git push | CodePipeline kích hoạt mặc định với mọi commit vào `main` | Cấu hình Tag Filter `v*` và kiểm tra tag trong `buildspec_ml.yml`. |

---

## 10. QUY TRÌNH DỌN DẸP TÀI NGUYÊN (TEARDOWN SCRIPT)

Chạy script PowerShell sau để xoá toàn bộ tài nguyên, ngắt 100% phát sinh chi phí:

```powershell
$ACCOUNT_ID = "678551739301"
$REGION = "us-east-1"
$SUFFIX = "an"

Write-Host "=== DỌN DẸP TOÀN BỘ DỰ ÁN ===" -ForegroundColor Yellow

# 1. Serving Layer
aws sagemaker delete-endpoint --endpoint-name california-housing-ep
aws sagemaker delete-endpoint-config --endpoint-config-name california-housing-serverless-cfg
aws sagemaker delete-model --model-name california-housing-model-v1

# 2. Consumer Layer
aws apigatewayv2 delete-api --api-id 1modfu9v9k
aws lambda delete-function --function-name california-housing-api-proxy
aws dynamodb delete-table --table-name CaliforniaHousingPredictions

# 3. CI/CD & Pipeline
aws codepipeline delete-pipeline --name california-housing-mlops-pipeline
aws codebuild delete-project --name california-housing-mlops-build
aws cloudwatch delete-alarms --alarm-names "CaliforniaHousingEndpointErrors"
aws sagemaker delete-pipeline --pipeline-name CaliforniaHousingMLOpsPipeline

# 4. S3 Buckets (Xoá sạch 4 Buckets)
$buckets = @(
    "california-housing-raw-$ACCOUNT_ID-$REGION-$SUFFIX",
    "california-housing-artifacts-$ACCOUNT_ID-$REGION-$SUFFIX",
    "california-housing-manifest-$ACCOUNT_ID-$REGION-$SUFFIX",
    "california-housing-web-$ACCOUNT_ID-$REGION-$SUFFIX"
)
foreach ($b in $buckets) {
    aws s3 rm "s3://$b" --recursive
    aws s3 rb "s3://$b" --force
}

# 5. IAM Roles
aws iam delete-role-policy --role-name CaliforniaHousing-LambdaExecutionRole --policy-name LambdaCustomPolicy
aws iam detach-role-policy --role-name CaliforniaHousing-LambdaExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name CaliforniaHousing-LambdaExecutionRole

aws iam detach-role-policy --role-name CaliforniaHousing-SageMakerExecutionRole --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam detach-role-policy --role-name CaliforniaHousing-SageMakerExecutionRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam delete-role --role-name CaliforniaHousing-SageMakerExecutionRole

Write-Host "✓ ĐÃ DỌN DẸP HOÀN TẤT TOÀN BỘ HỆ THỐNG!" -ForegroundColor Green
```
