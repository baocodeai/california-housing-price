# FRAMEWORK TRIỂN KHAI MLOPS CHUẨN DOANH NGHIỆP TRÊN AWS
## (Universal Enterprise MLOps Playbook & Blueprint - Dual Guide: Console & CLI/SDK)
> **Mục tiêu**: Đây là bộ khung chuẩn (Master Blueprint) áp dụng cho **bất kỳ bài toán Machine Learning nào** (Dự đoán giá, Customer Churn, Fraud Detection, NLP, Computer Vision...) khi đưa lên AWS.
> 
> Mỗi bước đều được trình bày song song bằng **2 PHƯƠNG THỨC**:
> - 🖥️ **Cách 1: Thao tác bằng Giao diện trực quan (AWS Console & SageMaker Studio)** — Dành cho việc cấu hình trực quan, debug nhanh, demo sản phẩm.
> - 💻 **Cách 2: Tự động hoá bằng Mã lệnh (AWS CLI & Python SDK/Boto3)** — Dành cho việc tự động hoá 100%, Infrastructure-as-Code (IaC), script hoá cho dự án mới.

---

## 🗺️ 1. TỔNG QUAN KIẾN TRÚC MLOPS CHUẨN (6 KHỐI CỐT LÕI)

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ KHỐI 1: DATA INGESTION & DATA PROVENANCE (Lưu vết & Kiểm toán dữ liệu)                           │
│ [Data Source] ──> S3 Raw Bucket ──(S3 ObjectCreated)──> AWS Lambda (Tạo manifest_*.json)         │
│                                                              │ (Audit trail & Hash)              │
│                                                              ▼                                   │
│                                                   S3 Manifest Bucket                             │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ KHỐI 2: CI/CD AUTOMATION & COST GOVERNANCE (Kiểm soát chi phí & Tự động hoá)                     │
│ Developer ──> [Git Push: main] ──────────────────────────────────────────────────────────┐      │
│ Developer ──> [Git Tag: v*.*.*] ──> AWS CodePipeline                                     │      │
│                                           │                                              │      │
│                                           ▼                                              │      │
│                                  Stage 1: Source (GitHub)                                │      │
│                                           │                                              │      │
│                                           ▼                                              │      │
│                                  Stage 2: CI (CodeBuild: pytest, flake8)                 │      │
│                                           │                                              │      │
│                                           ▼                                              │      │
│                                  Stage 3: ML Pipeline Trigger                            │      │
│                                  (Có Tag mới Train - Không Tag chỉ Upsert DAG)           │      │
├───────────────────────────────────────────┼──────────────────────────────────────────────┴──────┤
│ KHỐI 3: ORCHESTRATION & TRAINING (SageMaker AI DAG)                                             │
│    ┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐    │
│    │ Step 1: Preprocessing   │───>│ Step 2: Model Training  │───>│ Step 3: Model Evaluation│    │
│    │ (Data Prep, Impute, OHE)│    │ (Train Algorithm)       │    │ (Metrics: R2, AUC, F1)  │    │
│    └─────────────────────────┘    └─────────────────────────┘    └────────────┬────────────┘    │
│                                                                               │                 │
│                                                       Condition: Metric >= Threshold ?          │
│                                                       ├── No ──> Dừng DAG, không lưu model      │
│                                                       └── Yes ─> Step 4: Đăng ký Model Registry │
├───────────────────────────────────────────────────────────────────────────────┬─────────────────┤
│ KHỐI 4: GOVERNANCE & APPROVAL (Human-in-the-Loop)                             ▼                 │
│ CodePipeline Stage 4: Manual Approval (SNS gửi Email cho Lead kèm Link xem Model Metrics)        │
│                                           │ (Lead bấm Approve)                                  │
│                                           ▼                                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ KHỐI 5: SERVING & CONSUMER LAYER (Serverless Architecture)                                      │
│ [Client / Web UI] ──> [CloudFront + S3 Web]                                                     │
│                            │                                                                    │
│                            ▼                                                                    │
│                 [Amazon API Gateway (HTTP API)]                                                 │
│                            │ (POST /predict, POST /feedback)                                    │
│                            ▼                                                                    │
│                 [AWS Lambda API Proxy]                                                          │
│                      ├── Invoke ──> [SageMaker Serverless Endpoint]                             │
│                      └── Lưu log ─> [Amazon DynamoDB Table: <Project>Predictions]               │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ KHỐI 6: MONITORING & CONTINUOUS LEARNING LOOP (Giám sát & Tự động Retrain)                       │
│ - Amazon CloudWatch: Cảnh báo Invocations, ModelLatency, Lỗi 4XX/5XX.                           │
│ - Feedback Loop: DynamoDB tích luỹ Ground Truth ──> Định kỳ đẩy vào S3 ──> Tự động Retrain.     │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ 2. CẤU TRÚC REPOSITORY MẪU KHI BẮT ĐẦU DỰ ÁN MỚI

Khi bắt đầu một dự án Machine Learning mới, hãy tổ chức mã nguồn theo đúng cấu trúc tiêu chuẩn:

```text
my-ml-project/
├── .github/                       # GitHub actions / templates
├── buildspecs/                    # File chỉ dẫn cho AWS CodeBuild
│   ├── buildspec_ci.yml           # Chạy pytest & flake8 kiểm tra mã nguồn
│   └── buildspec_ml.yml           # Kiểm tra Git Tag để quyết định huấn luyện
├── aws_sagemaker/                 # Chạy trên hạ tầng AWS SageMaker
│   ├── pipeline.py                # Định nghĩa biểu đồ DAG hoàn chỉnh
│   └── steps/                     # Script Mode chạy độc lập trong container
│       ├── preprocessing.py       # Bước 1: Làm sạch dữ liệu, chia tập Train/Val/Test
│       ├── train.py               # Bước 2: Huấn luyện mô hình ML
│       ├── evaluate.py            # Bước 3: Đánh giá mô hình & xuất evaluation.json
│       └── inference.py           # Bước 4: Hook phục vụ suy luận thời gian thực
├── src/                           # Business logic bài toán
├── tests/unit/                    # Bộ kiểm thử đơn vị
├── docs/                          # Tài liệu hướng dẫn & kiến trúc
├── requirements.txt               # Dependencies cho môi trường dev & CI
└── setup.py                       # Đóng gói package (`pip install -e .`)
```

---

## ⚙️ 3. BẢNG THAM SỐ BIẾN CẤU HÌNH (ENVIRONMENT VARIABLES)

Khi tạo dự án mới, bạn chỉ cần thay đổi giá trị biến `PROJECT_NAME`:

```bash
# KHAI BÁO THÔNG SỐ TOÀN CỤC CHO DỰ ÁN MỚI
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export PROJECT_NAME="my-awesome-project"            # Đặt tên dự án của bạn (chữ thường, gạch nối)

# CÁC BIẾN TỰ ĐỘNG SINH THEO QUY ƯỚC CHUẨN:
export DATA_BUCKET="${PROJECT_NAME}-data-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export MANIFEST_BUCKET="${PROJECT_NAME}-manifest-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export SAGEMAKER_ROLE_NAME="${PROJECT_NAME}-SageMakerExecutionRole"
export LAMBDA_ROLE_NAME="${PROJECT_NAME}-LambdaExecutionRole"
export PIPELINE_NAME="${PROJECT_NAME}-mlops-pipeline"
export MODEL_GROUP_NAME="${PROJECT_NAME}-PackageGroup"
export ENDPOINT_NAME="${PROJECT_NAME}-ep"
export DYNAMODB_TABLE="${PROJECT_NAME}-predictions"
export SNS_TOPIC_NAME="${PROJECT_NAME}-approval-topic"
```

---

# 🚀 HƯỚNG DẪN 7 BƯỚC TRIỂN KHAI CHI TIẾT (SONG SONG CONSOLE & CLI)

---

## BƯỚC 1: THIẾT LẬP LƯU TRỮ S3 VÀ PHÂN QUYỀN IAM TẬP TRUNG

> **Quy tắc vàng quản trị**: Toàn bộ dự án chỉ cần đúng **3 IAM Roles** rõ ràng. Không để mỗi dịch vụ tự động bấm "tạo role mặc định", tránh tình trạng tài khoản sinh ra hàng chục role rác không kiểm soát được quyền hạn.

### 1.1. Tạo 2 S3 Buckets (Data thô & Manifest Audit)

#### 🖥️ Cách 1: Thao tác trên AWS Console
1. Truy cập **AWS Console** $\rightarrow$ Tìm dịch vụ **S3**.
2. Bấm **Create bucket**:
   - **Bucket name**: Nhập tên `$DATA_BUCKET`.
   - **AWS Region**: Chọn `us-east-1`.
   - Để các tùy chọn mặc định $\rightarrow$ Cuộn xuống cuối bấm **Create bucket**.
3. Bấm **Create bucket** lần 2 để tạo bucket Manifest:
   - **Bucket name**: Nhập tên `$MANIFEST_BUCKET`.
   - Mục **Bucket Versioning**: Chọn **Enable** (Bắt buộc bật để lưu vết lịch sử dữ liệu).
   - Bấm **Create bucket**.
4. Vào trong `$DATA_BUCKET` $\rightarrow$ Bấm **Create folder** $\rightarrow$ Nhập `raw/` $\rightarrow$ Bấm **Create folder**.
5. Mở thư mục `raw/` $\rightarrow$ Bấm **Upload** $\rightarrow$ Tải file dữ liệu thô (ví dụ: `data.csv`) lên.

#### 💻 Cách 2: Bằng AWS CLI / Script
```bash
# 1. Tạo Data Bucket
aws s3api create-bucket --bucket $DATA_BUCKET --region $AWS_REGION

# 2. Tạo Manifest Bucket và BẬT Versioning
aws s3api create-bucket --bucket $MANIFEST_BUCKET --region $AWS_REGION
aws s3api put-bucket-versioning --bucket $MANIFEST_BUCKET --versioning-configuration Status=Enabled

# 3. Upload file dữ liệu thô vào folder raw/
aws s3 cp data/raw/data.csv s3://${DATA_BUCKET}/raw/data.csv
```

---

### 1.2. Tạo 3 IAM Roles Chuẩn Hóa

#### 🖥️ Cách 1: Thao tác trên IAM Console
1. Truy cập **IAM Console** (`https://console.aws.amazon.com/iam/`) $\rightarrow$ Chọn **Roles** $\rightarrow$ **Create role**.
2. **Role 1: SageMaker Execution Role**:
   - Trusted entity: **AWS service** $\rightarrow$ Use case: **SageMaker** $\rightarrow$ Bấm **Next**.
   - Gắn 2 chính sách: `AmazonSageMakerFullAccess` và `AmazonS3FullAccess`.
   - Đặt tên Role: `$SAGEMAKER_ROLE_NAME` $\rightarrow$ Bấm **Create role**.
3. **Role 2: Lambda Execution Role**:
   - Bấm **Create role** $\rightarrow$ Trusted entity: **AWS service** $\rightarrow$ Use case: **Lambda** $\rightarrow$ Bấm **Next**.
   - Gắn 4 chính sách:
     - `service-role/AWSLambdaBasicExecutionRole`
     - `AmazonS3FullAccess`
     - `AmazonSageMakerFullAccess`
     - `AmazonDynamoDBFullAccess`
   - Đặt tên Role: `$LAMBDA_ROLE_NAME` $\rightarrow$ Bấm **Create role**.

#### 💻 Cách 2: Bằng AWS CLI
```bash
# 1. Tạo SageMaker Execution Role
cat << 'EOF' > trust-sagemaker.json
{
  "Version": "2012-10-17",
  "Statement": [{ "Effect": "Allow", "Principal": { "Service": "sagemaker.amazonaws.com" }, "Action": "sts:AssumeRole" }]
}
EOF

aws iam create-role --role-name $SAGEMAKER_ROLE_NAME --assume-role-policy-document file://trust-sagemaker.json
aws iam attach-role-policy --role-name $SAGEMAKER_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam attach-role-policy --role-name $SAGEMAKER_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# 2. Tạo Lambda Execution Role
cat << 'EOF' > trust-lambda.json
{
  "Version": "2012-10-17",
  "Statement": [{ "Effect": "Allow", "Principal": { "Service": "lambda.amazonaws.com" }, "Action": "sts:AssumeRole" }]
}
EOF

aws iam create-role --role-name $LAMBDA_ROLE_NAME --assume-role-policy-document file://trust-lambda.json
aws iam attach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam attach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
```

---

## BƯỚC 2: KHỐI DATA INGESTION VÀ S3 EVENT-DRIVEN MANIFEST

Mục tiêu: Đạt chuẩn kiểm định dữ liệu doanh nghiệp (Data Provenance & Audit Trail). Mỗi khi data engineer upload file mới vào S3 `raw/`, một Lambda function tự động tính toán ETag, kích thước, timestamp và ghi log `manifest_*.json` sang Manifest Bucket.

### 2.1. Triển khai Lambda Manifest Generator

#### 🖥️ Cách 1: Qua AWS Lambda Console
1. Truy cập **AWS Lambda Console** $\rightarrow$ Bấm **Create function**:
   - Chọn **Author from scratch**.
   - Tên hàm: `${PROJECT_NAME}-manifest-generator`.
   - Runtime: **Python 3.11**.
   - Mục **Change default execution role**: Chọn *Use an existing role* $\rightarrow$ Chọn `$LAMBDA_ROLE_NAME`.
   - Bấm **Create function**.
2. Ở tab **Code**, mở file `lambda_function.py`, dán đoạn mã sau:
```python
import json, urllib.parse, boto3, os
from datetime import datetime

s3 = boto3.client('s3')
MANIFEST_BUCKET = os.environ.get('MANIFEST_BUCKET')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'ml-project')

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))
    for record in event.get('Records', []):
        src_bucket = record['s3']['bucket']['name']
        src_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        
        manifest = {
            "project": PROJECT_NAME,
            "source_s3_uri": f"s3://{src_bucket}/{src_key}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "size_bytes": record['s3']['object']['size'],
            "etag": record['s3']['object']['eTag'],
            "status": "READY_FOR_TRAINING"
        }
        
        ts_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        manifest_key = f"manifests/manifest_{ts_str}.json"
        
        s3.put_object(
            Bucket=MANIFEST_BUCKET,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2),
            ContentType='application/json'
        )
        print(f"Logged manifest: s3://{MANIFEST_BUCKET}/{manifest_key}")
        
    return {"statusCode": 200, "body": "Manifest logged"}
```
3. Vào tab **Configuration** $\rightarrow$ **Environment variables** $\rightarrow$ Bấm **Edit**:
   - Thêm `MANIFEST_BUCKET` = Giá trị `$MANIFEST_BUCKET`.
   - Thêm `PROJECT_NAME` = Giá trị `$PROJECT_NAME`.
   - Bấm **Save**.
4. Bấm **Deploy** (màu cam/xanh).

#### 💻 Cách 2: Bằng AWS CLI
```bash
cat << 'EOF' > lambda_manifest.py
import json, urllib.parse, boto3, os
from datetime import datetime

s3 = boto3.client('s3')
MANIFEST_BUCKET = os.environ.get('MANIFEST_BUCKET')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'ml-project')

def lambda_handler(event, context):
    for record in event.get('Records', []):
        src_bucket = record['s3']['bucket']['name']
        src_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        manifest = {
            "project": PROJECT_NAME,
            "source_s3_uri": f"s3://{src_bucket}/{src_key}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "size_bytes": record['s3']['object']['size'],
            "etag": record['s3']['object']['eTag'],
            "status": "READY_FOR_TRAINING"
        }
        key = f"manifests/manifest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        s3.put_object(Bucket=MANIFEST_BUCKET, Key=key, Body=json.dumps(manifest, indent=2), ContentType='application/json')
    return {"statusCode": 200, "body": "OK"}
EOF

zip -j lambda_manifest.zip lambda_manifest.py

aws lambda create-function \
    --function-name "${PROJECT_NAME}-manifest-generator" \
    --runtime python3.11 \
    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME} \
    --handler lambda_manifest.lambda_handler \
    --zip-file fileb://lambda_manifest.zip \
    --environment Variables="{MANIFEST_BUCKET=${MANIFEST_BUCKET},PROJECT_NAME=${PROJECT_NAME}}" \
    --region $AWS_REGION
```

---

### 2.2. Gắn S3 Event Notification kích hoạt Lambda

#### 🖥️ Cách 1: Qua S3 Console
1. Mở **S3 Console** $\rightarrow$ Bấm vào `$DATA_BUCKET`.
2. Chọn tab **Properties** $\rightarrow$ Cuộn xuống mục **Event notifications** $\rightarrow$ Bấm **Create event notification**.
3. Cấu hình:
   - Event name: `TriggerManifestOnDataUpload`.
   - Prefix: `raw/`
   - Suffix: `.csv`
   - Event types: Tích chọn `All object create events` (`s3:ObjectCreated:*`).
   - Destination: Chọn **Lambda function** $\rightarrow$ Chọn `${PROJECT_NAME}-manifest-generator`.
4. Bấm **Save changes**.

#### 💻 Cách 2: Bằng AWS CLI
```bash
# 1. Cấp quyền cho S3 gọi Lambda
aws lambda add-permission \
    --function-name "${PROJECT_NAME}-manifest-generator" \
    --statement-id AllowS3Invocation \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::${DATA_BUCKET} \
    --region $AWS_REGION

# 2. Cấu hình Event Notification
cat << EOF > s3_notification.json
{
  "LambdaFunctionConfigurations": [{
    "LambdaFunctionArn": "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${PROJECT_NAME}-manifest-generator",
    "Events": ["s3:ObjectCreated:*"],
    "Filter": { "Key": { "FilterRules": [{ "Name": "prefix", "Value": "raw/" }, { "Name": "suffix", "Value": ".csv" }] } }
  }]
}
EOF

aws s3api put-bucket-notification-configuration \
    --bucket $DATA_BUCKET \
    --notification-configuration file://s3_notification.json
```

---

## BƯỚC 3: XÂY DỰNG KHỐI HUẤN LUYỆN SAGEMAKER AI DAG (SCRIPT MODE)

> **Mô hình Script Mode chuẩn**: Code ML được chia thành 4 scripts độc lập trong thư mục `aws_sagemaker/steps/`.

### 3.1. Thiết kế 4 Scripts Cốt Lõi:
1. **`preprocessing.py`**:
   - Đọc dữ liệu từ `/opt/ml/processing/input/`.
   - Xử lý Missing Value, Mã hoá phân loại, Chuẩn hoá dữ liệu.
   - Tách Train/Val/Test (ví dụ: 70% / 15% / 15%).
   - **BẮT BUỘC**: Lưu cả file `preprocessor.joblib` vào `/opt/ml/processing/output/`.
2. **`train.py`**:
   - Đọc dữ liệu Train từ `$SM_CHANNEL_TRAIN`.
   - Huấn luyện thuật toán cốt lõi.
   - Lưu `model.joblib` vào `/opt/ml/model/`.
   - **BÍ QUYẾT DOANH NGHIỆP**: Copy file `preprocessor.joblib` vào cùng thư mục `/opt/ml/model/` để tạo mô hình tự thân (Self-Contained Model).
3. **`evaluate.py`**:
   - Đọc mô hình đã huấn luyện và dữ liệu Test (unseen data).
   - Đo lường chỉ số chuẩn ($R^2$, RMSE, MAE đối với Regression; AUC, F1 đối với Classification).
   - Xuất file chuẩn `/opt/ml/processing/evaluation/evaluation.json`:
   ```json
   { "regression_metrics": { "r2_score": { "value": 0.82 } } }
   ```
4. **`inference.py`**:
   - Cung cấp 4 hook: `model_fn`, `input_fn`, `predict_fn`, `output_fn` để container Serverless Endpoint phục vụ suy luận thời gian thực.

---

### 3.2. Script `aws_sagemaker/pipeline.py` (Định nghĩa DAG)

File này kết nối 4 scripts trên thành một đồ thị có hướng (DAG) bằng SageMaker Python SDK:
- Dùng `ProcessingStep` cho Preprocessing và Evaluation.
- Dùng `TrainingStep` cho Training.
- Dùng `PropertyFile` và **`JsonGet`** để trích xuất số float từ JSON metric:
```python
cond_metric = ConditionGreaterThanOrEqualTo(
    left=JsonGet(
        step_name=step_eval.name,
        property_file=eval_report,
        json_path="regression_metrics.r2_score.value"
    ),
    right=r2_threshold
)
```
- Dùng `ModelStep` để đăng ký vào **Model Registry** với `approval_status="PendingManualApproval"`.
- **Cơ chế Auto-Cancellation**: Trước khi gọi `pipeline.start()`, tự động tìm và huỷ các đợt chạy cũ đang `Executing` để tránh tốn tài nguyên.

---

### 3.3. Theo dõi và Vận hành DAG trên Giao diện Studio vs CLI

#### 🖥️ Cách 1: Trên giao diện Amazon SageMaker Studio
1. Mở **Amazon SageMaker AI Console** $\rightarrow$ Chọn **SageMaker Studio** ở menu trái $\rightarrow$ Bấm **Open Studio**.
2. Tại thanh điều hướng bên trái Studio, bấm vào biểu tượng **Pipelines**.
3. Bấm chọn pipeline `${PROJECT_NAME}-mlops-pipeline`:
   - Tab **Graph**: Xem biểu đồ trực quan DAG (các nút đổi màu xanh lá khi hoàn thành).
   - Tab **Executions**: Xem danh sách các lần chạy.
   - Bấm vào từng Step để xem chi tiết: Input/Output S3 URIs, logs CloudWatch thời gian thực, thông số máy ảo instance.
4. Kiểm tra **Model Registry**:
   - Menu trái Studio chọn **Models** $\rightarrow$ **Model Registry** $\rightarrow$ Bấm vào `${PROJECT_NAME}-PackageGroup`.
   - Xem Version 1: Xem bảng chỉ số metrics $R^2$, RMSE, MAE.

#### 💻 Cách 2: Bằng AWS CLI / Python SDK
```bash
# Liệt kê danh sách Pipelines
aws sagemaker list-pipelines --region $AWS_REGION

# Xem danh sách các đợt chạy của Pipeline
aws sagemaker list-pipeline-executions --pipeline-name $PIPELINE_NAME --region $AWS_REGION

# Xem trạng thái từng step trong một đợt chạy cụ thể
aws sagemaker list-pipeline-execution-steps --pipeline-execution-arn <EXECUTION_ARN> --region $AWS_REGION
```

---

## BƯỚC 4: THIẾT LẬP CI/CD VÀ KIỂM SOÁT CHI PHÍ (COST GOVERNANCE)

> **Nguyên tắc tiết kiệm chi phí tối thượng**: 
> - Khi lập trình viên push code thường xuyên lên `main` (sửa doc, sửa CSS, refactor, viết test): **CHỈ CHẠY CI (PYTEST & LINTER) VÀ UPSERT ĐỊNH NGHĨA DAG, TUYỆT ĐỐI KHÔNG BẬT MÁY ẢO HUẤN LUYỆN!**
> - **CHỈ HUẤN LUYỆN MODEL THẬT KHI**: Có gắn Git Release Tag (ví dụ: `git tag v1.0.0 && git push origin v1.0.0`).

### 4.1. Chuẩn bị 2 File Buildspec trong thư mục `buildspecs/`

- **File `buildspecs/buildspec_ci.yml`** (Kiểm tra chất lượng code):
```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install --upgrade pip
      - pip install -e .
      - pip install pytest flake8
  pre_build:
    commands:
      - flake8 src tests aws_sagemaker --count --max-line-length=127 --statistics || true
  build:
    commands:
      - echo "Chay Unit Tests..."
      - pytest tests/unit/ -v
```

- **File `buildspecs/buildspec_ml.yml`** (Kiểm tra Git Tag để quyết định huấn luyện):
```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install --upgrade pip
      - pip install "sagemaker<3.0.0" boto3
  build:
    commands:
      - |
        echo "Kiem tra Git Release Tag..."
        GIT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
        
        if [ -n "$GIT_TAG" ] || [ "$FORCE_TRAIN" = "true" ]; then
          echo ">>> PHAT HIEN RELEASE TAG: '$GIT_TAG'. TIEN HANH HUAN LUYEN MODEL..."
          python aws_sagemaker/pipeline.py --role-arn $SAGEMAKER_ROLE_ARN --bucket $DATA_BUCKET --execute
        else
          echo ">>> Commit thuong (khong co Git Tag)."
          echo ">>> CHI CAP NHAT DINH NGHIA DAG, KHONG BAT MAY AO HUAN LUYEN. TIET KIEM TAI NGUYEN!"
          python aws_sagemaker/pipeline.py --role-arn $SAGEMAKER_ROLE_ARN --bucket $DATA_BUCKET
        fi
```

---

### 4.2. Thiết lập SNS Topic cho Manual Approval

#### 🖥️ Cách 1: Qua SNS Console
1. Mở **Amazon SNS Console** $\rightarrow$ Chọn **Topics** $\rightarrow$ Bấm **Create topic**.
2. Type: **Standard**, Name: `$SNS_TOPIC_NAME` $\rightarrow$ Bấm **Create topic**.
3. Bấm **Create subscription**:
   - Protocol: **Email**.
   - Endpoint: Nhập email nhận duyệt của bạn $\rightarrow$ Bấm **Create subscription**.
4. **QUAN TRỌNG**: Mở email cá nhân bấm vào liên kết **Confirm subscription**.

#### 💻 Cách 2: Bằng AWS CLI
```bash
aws sns create-topic --name $SNS_TOPIC_NAME --region $AWS_REGION

aws sns subscribe \
    --topic-arn arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:${SNS_TOPIC_NAME} \
    --protocol email \
    --notification-endpoint your-email@example.com \
    --region $AWS_REGION
```

---

### 4.3. Tạo CodePipeline 4 Stages Hoàn Chỉnh

#### 🖥️ Thao tác trên AWS CodePipeline Console
1. Truy cập **AWS CodePipeline Console** $\rightarrow$ Bấm **Create pipeline**:
   - Pipeline name: `$PIPELINE_NAME`.
   - Service role: Chọn **New service role** $\rightarrow$ Bấm **Next**.
2. **Stage 1 (Source)**:
   - Source provider: Chọn **GitHub (Version 2)** (kết nối repo GitHub của bạn).
   - Repository: Chọn repo dự án, Branch: `main` $\rightarrow$ Bấm **Next**.
3. **Stage 2 (Build / CI)**:
   - Provider: **AWS CodeBuild**.
   - Bấm *Create project* đặt tên `${PROJECT_NAME}-ci` $\rightarrow$ Chọn file buildspec `buildspecs/buildspec_ci.yml` $\rightarrow$ Bấm **Continue to CodePipeline**.
   - Bấm **Next**.
4. Chọn **Skip deploy stage** $\rightarrow$ Bấm **Create pipeline**.
5. **Thêm 2 Stage tiếp theo (Edit Pipeline)**:
   - Bấm nút **Edit** ở đầu trang pipeline:
   - Sau Stage Build $\rightarrow$ Bấm **+ Add stage** đặt tên: `ML_Pipeline`.
     - Action name: `Run_SageMaker_Pipeline`.
     - Action provider: **AWS CodeBuild**.
     - Bấm *Create project* đặt tên `${PROJECT_NAME}-ml-trigger` trỏ vào `buildspecs/buildspec_ml.yml`.
     - Khai báo Environment Variables trong CodeBuild này:
       - `SAGEMAKER_ROLE_ARN` = ARN của `$SAGEMAKER_ROLE_NAME`.
       - `DATA_BUCKET` = Giá trị `$DATA_BUCKET`.
   - Sau Stage ML_Pipeline $\rightarrow$ Bấm **+ Add stage** đặt tên: `Approval`.
     - Action name: `Lead_Approve_Model`.
     - Action provider: **Manual approval**.
     - SNS topic ARN: Chọn topic ARN vừa tạo ở bước 4.2.
   - Bấm **Save** để lưu Pipeline.
6. **Cấp quyền SNS cho CodePipeline Service Role**:
   - Vào IAM Console $\rightarrow$ Tìm Role của CodePipeline vừa sinh ra $\rightarrow$ Thêm Inline Policy cho phép `sns:Publish` để gửi email thành công.

---

## BƯỚC 5: PHÊ DUYỆT VÀ TRIỂN KHAI SERVERLESS SERVING ENDPOINT

Mục tiêu: Đưa mô hình đã được Lead duyệt ra Serverless Serving Endpoint. Cơ chế Serverless tự động mở rộng theo lưu lượng và **tự động tắt (scale-to-zero) khi không có request**, giúp tiết kiệm hơn 90% chi phí máy chủ hàng tháng.

### 5.1. Phê duyệt Model trong Model Registry

#### 🖥️ Cách 1: Qua SageMaker Studio
1. Mở **SageMaker Studio** $\rightarrow$ Chọn **Models** $\rightarrow$ **Model Registry**.
2. Nhấp vào `$MODEL_GROUP_NAME` $\rightarrow$ Chọn Version mới nhất.
3. Quan sát các chỉ số đánh giá.
4. Bấm nút **Update status** ở góc phải $\rightarrow$ Chọn trạng thái **Approved** $\rightarrow$ Bấm **Update status**.

#### 💻 Cách 2: Bằng AWS CLI
```bash
# Lấy Model Package ARN mới nhất
PACKAGE_ARN=$(aws sagemaker list-model-packages \
    --model-package-group-name $MODEL_GROUP_NAME \
    --query "ModelPackageSummaryList[0].ModelPackageArn" \
    --output text \
    --region $AWS_REGION)

# Phê duyệt Model Package
aws sagemaker update-model-package \
    --model-package-arn $PACKAGE_ARN \
    --model-approval-status Approved \
    --approval-description "Approved for production release" \
    --region $AWS_REGION
```

---

### 5.2. Khởi tạo Serverless Endpoint

#### 🖥️ Cách 1: Qua SageMaker Console (Deployments & Inference)
1. Mở **SageMaker AI Console** $\rightarrow$ Menu trái chọn **Inference** (hoặc **Deployments & inference**).
2. **Tạo Model**:
   - Chọn **Models** $\rightarrow$ Bấm **Create model**.
   - Model name: `${PROJECT_NAME}-model-v1`.
   - Primary container: Chọn **Use a model package from Model Registry** $\rightarrow$ Chọn package đã Approved.
   - IAM role: Chọn `$SAGEMAKER_ROLE_NAME` $\rightarrow$ Bấm **Create model**.
3. **Tạo Endpoint Configuration**:
   - Chọn **Endpoint configurations** $\rightarrow$ Bấm **Create endpoint configuration**.
   - Name: `${PROJECT_NAME}-serverless-cfg`.
   - Chọn loại: **Serverless**.
   - Bấm **Add model** $\rightarrow$ Chọn `${PROJECT_NAME}-model-v1`.
   - Đặt **Memory size**: `2048 MB` (2 GB), **Max concurrency**: `10`.
   - Bấm **Create endpoint configuration**.
4. **Tạo Endpoint**:
   - Chọn **Endpoints** $\rightarrow$ Bấm **Create endpoint**.
   - Endpoint name: `$ENDPOINT_NAME`.
   - Chọn configuration vừa tạo $\rightarrow$ Bấm **Create endpoint**.
   - Chờ 2-3 phút đến khi trạng thái hiển thị **`InService`**.

#### 💻 Cách 2: Bằng AWS CLI
```bash
# 1. Tạo Model
aws sagemaker create-model \
    --model-name "${PROJECT_NAME}-model-v1" \
    --primary-container ModelPackageName=$PACKAGE_ARN \
    --execution-role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/${SAGEMAKER_ROLE_NAME} \
    --region $AWS_REGION

# 2. Tạo Endpoint Config Serverless
aws sagemaker create-endpoint-config \
    --endpoint-config-name "${PROJECT_NAME}-serverless-cfg" \
    --production-variants '[{
        "VariantName": "AllTraffic",
        "ModelName": "'${PROJECT_NAME}'-model-v1",
        "ServerlessConfig": { "MemorySizeInMB": 2048, "MaxConcurrency": 10 }
    }]' \
    --region $AWS_REGION

# 3. Tạo Endpoint
aws sagemaker create-endpoint \
    --endpoint-name $ENDPOINT_NAME \
    --endpoint-config-name "${PROJECT_NAME}-serverless-cfg" \
    --region $AWS_REGION

# Kiểm tra trạng thái đến khi trả về 'InService'
aws sagemaker describe-endpoint --endpoint-name $ENDPOINT_NAME --query "EndpointStatus" --output text --region $AWS_REGION
```

---

## BƯỚC 6: CONSUMER LAYER & CONTINUOUS FEEDBACK LOOP

Mục tiêu: Xây dựng tầng giao tiếp chuẩn REST API bảo mật cho client (React Web/Mobile), lưu vết toàn bộ dữ liệu dự đoán và phản hồi thực tế vào DynamoDB để phục vụ giám sát Data Drift và tái huấn luyện mô hình.

### 6.1. Tạo DynamoDB Table lưu trữ Prediction & Feedback Logs

#### 🖥️ Qua DynamoDB Console
1. Truy cập **Amazon DynamoDB Console** $\rightarrow$ Chọn **Tables** $\rightarrow$ Bấm **Create table**.
2. Table name: `$DYNAMODB_TABLE`.
3. Partition key: `prediction_id` (Kiểu: `String`).
4. Capacity mode: Chọn **On-demand** (chỉ trả phí theo số lượng request thực tế).
5. Bấm **Create table**.

#### 💻 Qua AWS CLI
```bash
aws dynamodb create-table \
    --table-name $DYNAMODB_TABLE \
    --attribute-definitions AttributeName=prediction_id,AttributeType=S \
    --key-schema AttributeName=prediction_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $AWS_REGION
```

---

### 6.2. Tạo AWS Lambda API Proxy Function

Lambda function `${PROJECT_NAME}-api-proxy` nhận request từ API Gateway, gọi SageMaker Serverless Endpoint và ghi log vào DynamoDB.

#### 🖥️ Qua AWS Lambda Console
1. Mở **AWS Lambda Console** $\rightarrow$ Bấm **Create function**:
   - Tên hàm: `${PROJECT_NAME}-api-proxy`.
   - Runtime: **Python 3.11**.
   - Execution role: Chọn *Use an existing role* $\rightarrow$ Chọn `$LAMBDA_ROLE_NAME`.
   - Bấm **Create function**.
2. Dán đoạn mã sau vào tab **Code**:
```python
import json, uuid, os, boto3
from datetime import datetime

sm_runtime = boto3.client('sagemaker-runtime')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE'))
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME')

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

    # Route 1: POST /predict (Dự đoán và lưu log DynamoDB)
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
                'predicted_value': str(pred_val),
                'actual_value': None
            }
        )
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"prediction_id": pred_id, "predicted_value": pred_val})
        }

    # Route 2: POST /feedback (Ghi nhận giá trị thực tế của khách hàng)
    elif path.endswith('/feedback') and method == 'POST':
        body = json.loads(event.get('body', '{}'))
        pred_id = body.get('prediction_id')
        actual_val = body.get('actual_value')
        
        table.update_item(
            Key={'prediction_id': pred_id},
            UpdateExpression="SET actual_value = :val, feedback_timestamp = :ts",
            ExpressionAttributeValues={
                ':val': str(actual_val),
                ':ts': datetime.utcnow().isoformat() + "Z"
            }
        )
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "Feedback saved", "prediction_id": pred_id})
        }

    return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Not Found"})}
```
3. Tab **Configuration** $\rightarrow$ **Environment variables**:
   - `ENDPOINT_NAME` = Giá trị `$ENDPOINT_NAME`.
   - `DYNAMODB_TABLE` = Giá trị `$DYNAMODB_TABLE`.
   - Bấm **Save**.
4. Bấm **Deploy**.

#### 💻 Qua AWS CLI
```bash
cat << 'EOF' > lambda_proxy.py
import json, uuid, os, boto3
from datetime import datetime

sm_runtime = boto3.client('sagemaker-runtime')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE'))
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME')

def lambda_handler(event, context):
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    path = event.get('rawPath', '')
    headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "*"}
    if method == 'OPTIONS': return {"statusCode": 200, "headers": headers, "body": "{}"}
    if path.endswith('/predict') and method == 'POST':
        body = json.loads(event.get('body', '{}'))
        instances = body.get('instances', [])
        resp = sm_runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME, ContentType='application/json', Body=json.dumps({"instances": instances}))
        pred_val = json.loads(resp['Body'].read().decode())['predictions'][0]
        pred_id = str(uuid.uuid4())
        table.put_item(Item={'prediction_id': pred_id, 'timestamp': datetime.utcnow().isoformat() + "Z", 'features': json.dumps(instances[0]), 'predicted_value': str(pred_val), 'actual_value': None})
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"prediction_id": pred_id, "predicted_value": pred_val})}
    elif path.endswith('/feedback') and method == 'POST':
        body = json.loads(event.get('body', '{}'))
        table.update_item(Key={'prediction_id': body.get('prediction_id')}, UpdateExpression="SET actual_value = :val, feedback_timestamp = :ts", ExpressionAttributeValues={':val': str(body.get('actual_value')), ':ts': datetime.utcnow().isoformat() + "Z"})
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "Feedback saved"})}
    return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Not Found"})}
EOF

zip -j lambda_proxy.zip lambda_proxy.py

aws lambda create-function \
    --function-name "${PROJECT_NAME}-api-proxy" \
    --runtime python3.11 \
    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME} \
    --handler lambda_proxy.lambda_handler \
    --zip-file fileb://lambda_proxy.zip \
    --environment Variables="{ENDPOINT_NAME=${ENDPOINT_NAME},DYNAMODB_TABLE=${DYNAMODB_TABLE}}" \
    --region $AWS_REGION
```

---

### 6.3. Tạo Amazon API Gateway (HTTP API)

#### 🖥️ Qua API Gateway Console
1. Truy cập **API Gateway Console** $\rightarrow$ Mục **HTTP API** $\rightarrow$ Bấm **Build**:
   - API name: `${PROJECT_NAME}-api`.
   - Bấm **Next**.
2. **Configure routes**:
   - Thêm route 1: Method `POST`, Resource path: `/predict`.
   - Thêm route 2: Method `POST`, Resource path: `/feedback`.
   - Bấm **Next**.
3. Để Stage mặc định `$default` (Auto-deploy: ON) $\rightarrow$ Bấm **Next** $\rightarrow$ Bấm **Create**.
4. **Tạo Integration**:
   - Menu trái chọn **Integrations** $\rightarrow$ Bấm **Manage integrations** $\rightarrow$ **Create**:
     - Integration type: **Lambda function**.
     - Lambda function: Chọn `${PROJECT_NAME}-api-proxy`.
     - Bấm **Create**.
   - Gắn integration này vào cả 2 route `/predict` và `/feedback`.
5. **Bật CORS**:
   - Menu trái chọn **CORS** $\rightarrow$ Bấm **Configure**:
     - Access-Control-Allow-Origin: `*`
     - Access-Control-Allow-Methods: `POST, OPTIONS`
     - Access-Control-Allow-Headers: `*`
   - Bấm **Save**.
6. Sao chép lại đường link **Invoke URL** (ví dụ: `https://xyz.execute-api.us-east-1.amazonaws.com`).

#### 💻 Qua AWS CLI
```bash
API_ID=$(aws apigatewayv2 create-api \
    --name "${PROJECT_NAME}-api" \
    --protocol-type HTTP \
    --cors-configuration '{"AllowOrigins":["*"],"AllowMethods":["POST","OPTIONS"],"AllowHeaders":["*"]}' \
    --query "ApiId" --output text --region $AWS_REGION)

INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${PROJECT_NAME}-api-proxy \
    --payload-format-version "2.0" \
    --query "IntegrationId" --output text --region $AWS_REGION)

aws apigatewayv2 create-route --api-id $API_ID --route-key "POST /predict" --target integrations/$INTEGRATION_ID --region $AWS_REGION
aws apigatewayv2 create-route --api-id $API_ID --route-key "POST /feedback" --target integrations/$INTEGRATION_ID --region $AWS_REGION
aws apigatewayv2 create-stage --api-id $API_ID --stage-name '$default' --auto-deploy --region $AWS_REGION

aws lambda add-permission \
    --function-name "${PROJECT_NAME}-api-proxy" \
    --statement-id AllowApiGateway \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*" \
    --region $AWS_REGION

echo ">>> API Gateway Invoke URL: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com"
```

---

## BƯỚC 7: GIÁM SÁT (MONITORING) & TỰ ĐỘNG RETRAINING LOOP

### 7.1. Cấu hình Cảnh báo CloudWatch Alarms
Cảnh báo qua email khi Serverless Endpoint gặp lỗi hoặc độ trễ cao:
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "${PROJECT_NAME}-endpoint-5xx-alarm" \
    --metric-name Invocation5XXErrors \
    --namespace AWS/SageMaker \
    --statistic Sum \
    --period 60 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --evaluation-periods 1 \
    --dimensions Name=EndpointName,Value=$ENDPOINT_NAME \
    --alarm-actions arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:${SNS_TOPIC_NAME} \
    --region $AWS_REGION
```

### 7.2. Vòng lặp Tái Huấn Luyện Tự Động (Continuous Retraining Loop)
```text
Client gửi dữ liệu thực tế ──> POST /feedback ──> DynamoDB Table lưu trữ
                                                        │
                                                        ▼ (Khi tích luỹ đủ 1.000 mẫu)
                                            Export dữ liệu mới ra CSV
                                                        │
                                                        ▼
                                            Upload S3: raw/retrain_data.csv
                                                        │
                                                        ▼
                                            S3 Event Notification
                                                        │
                                                        ▼
                                            Kích hoạt CodePipeline với FORCE_TRAIN=true
                                                        │
                                                        ▼
                                    SageMaker AI tự động huấn luyện Model Version mới!
```

---

## 🏁 BẢNG CHECKLIST NGHIỆM THU DỰ ÁN MLOPS (PRODUCTION ACCEPTANCE)

| STT | Hạng mục kiểm tra | Cách thực hiện | Kết quả đạt yêu cầu |
| :---: | :--- | :--- | :--- |
| **1** | **IAM Roles Tập Trung** | Kiểm tra IAM Console | Chỉ có đúng 3 Role chuẩn định danh, không có role rác. |
| **2** | **Data Audit Trail** | Upload data thô vào S3 | Sinh file `manifests/manifest_*.json` trong Manifest bucket. |
| **3** | **CI Test Tự Động** | Push code lên nhánh `main` | CodeBuild CI chạy `flake8` và `pytest` đạt 100%. |
| **4** | **Cost Governance** | Push commit sửa code thường | CodePipeline chỉ chạy CI, **KHÔNG** bật máy ảo SageMaker. |
| **5** | **Release Retrain Trigger** | Chạy `git tag v1.0.0 && git push origin v1.0.0` | SageMaker AI Pipeline tự động kích hoạt huấn luyện! |
| **6** | **Auto-Cancellation** | Kích hoạt đợt chạy mới | Hệ thống tự động huỷ đợt chạy cũ đang dang dở. |
| **7** | **Quality Gate** | Kiểm tra `evaluation.json` | Chỉ đăng ký Model Registry nếu metric vượt ngưỡng ($R^2 \ge 0.80$). |
| **8** | **Human Approval** | Kiểm tra hộp thư Email | Nhận email SNS và Lead phê duyệt thành công trên CodePipeline. |
| **9** | **Serverless Serving** | Gọi `POST /predict` | Trả kết quả JSON, tự scale về 0 khi rảnh rỗi. |
| **10**| **Audit & Feedback Log**| Kiểm tra DynamoDB Table | Lưu vết input features, kết quả dự đoán và giá trị `actual_value`. |
