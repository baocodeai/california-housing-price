# FRAMEWORK TRIỂN KHAI MLOPS CHUẨN DOANH NGHIỆP TRÊN AWS
## (MLOps Universal Enterprise Playbook & Blueprint)
> **Mục tiêu**: Tài liệu này là bộ khung chuẩn (Master Blueprint) có thể áp dụng cho **bất kỳ bài toán Machine Learning nào** (Dự đoán giá nhà, Churn Prediction, Fraud Detection, NLP, Computer Vision...) khi triển khai lên nền tảng đám mây AWS. Khi bắt đầu một dự án mới, bạn chỉ cần thay đổi biến cấu hình và logic bài toán mà không cần thiết kế lại hạ tầng từ đầu.

---

## 🏛️ PHẦN 1: MÔ HÌNH KIẾN TRÚC MLOPS CHUẨN TỔNG QUÁT (6 KHỐI CỐT LÕI)

Mọi dự án MLOps chuẩn doanh nghiệp đều vận hành dựa trên 6 khối độc lập nhưng kết nối chặt chẽ với nhau:

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

## 🗂️ PHẦN 2: CẤU TRÚC THƯ MỤC CHUẨN CỦA MỌI DỰ ÁN MLOPS

Khi khởi tạo bất kỳ dự án nào mới, hãy thiết lập cây thư mục chuẩn như sau:

```text
my-ml-project/
├── .github/                       # Workflows hoặc templates
├── buildspecs/                    # File cấu hình AWS CodeBuild
│   ├── buildspec_ci.yml           # CI: Linter, Unit test cho code
│   └── buildspec_ml.yml           # CD: Kiểm tra Git Tag để quyết định Train hay không
├── aws_sagemaker/                 # Toàn bộ mã nguồn chạy trên hạ tầng AWS SageMaker
│   ├── pipeline.py                # Định nghĩa DAG Pipeline (SageMaker Workflow SDK)
│   └── steps/                     # Các file Script Mode thực thi độc lập trong container
│       ├── preprocessing.py       # Bước 1: Tiền xử lý, feature engineering
│       ├── train.py               # Bước 2: Huấn luyện thuật toán ML
│       ├── evaluate.py            # Bước 3: Đánh giá mô hình & xuất evaluation.json
│       └── inference.py           # Bước 4: Hook phục vụ suy luận trên Endpoint (Serving)
├── src/                           # Core business logic của bài toán
│   ├── data/                      # Loaders, validators
│   ├── features/                  # Feature transforms
│   └── models/                    # Model wrappers
├── tests/                         # Unit tests & Integration tests
│   ├── unit/                      # Test tiền xử lý, test inference
│   └── integration/               # Test toàn bộ chuỗi
├── frontend/                      # (Tùy chọn) Giao diện demo Web React/Vue/Streamlit
├── docs/                          # Tài liệu kiến trúc và hướng dẫn vận hành
├── requirements.txt               # Dependencies cho môi trường dev & CI
├── setup.py                       # Đóng gói repo thành thư viện Python (`pip install -e .`)
└── README.md                      # Giới thiệu bài toán và runbook
```

---

## 🚀 PHẦN 3: QUY TRÌNH 7 BƯỚC TRIỂN KHAI DỰ ÁN MỚI TỪ A ĐẾN Z

---

### BƯỚC 1: XÁC ĐỊNH BẢNG BIẾN THIẾT LẬP (ENVIRONMENT CONFIGURATION)
*Trước khi gõ bất kỳ câu lệnh nào, hãy điền bảng thông số riêng cho dự án mới của bạn:*

```bash
# ĐẶT BIẾN CHO DỰ ÁN MỚI:
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export PROJECT_NAME="my-project"                    # Ví dụ: customer-churn, credit-risk, fraud-detection
export DATA_BUCKET="${PROJECT_NAME}-data-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export MANIFEST_BUCKET="${PROJECT_NAME}-manifest-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export SAGEMAKER_ROLE_NAME="${PROJECT_NAME}-SageMakerExecutionRole"
export LAMBDA_ROLE_NAME="${PROJECT_NAME}-LambdaExecutionRole"
export PIPELINE_NAME="${PROJECT_NAME}-mlops-pipeline"
export MODEL_GROUP_NAME="${PROJECT_NAME}-PackageGroup"
export ENDPOINT_NAME="${PROJECT_NAME}-ep"
export DYNAMODB_TABLE="${PROJECT_NAME}-predictions"
```

---

### BƯỚC 2: THIẾT LẬP LƯU TRỮ VÀ PHÂN QUYỀN IAM TẬP TRUNG (MỘT LẦN DUY NHẤT)

> **Nguyên tắc quản lý tối ưu**: Tuyệt đối không để mỗi service tự bấm "Create default role" gây ra hàng chục role rác. Toàn bộ dự án chỉ cần đúng **3 IAM Roles** có tên định danh rõ ràng.

#### 1. Tạo S3 Buckets (Data + Manifest Versioning):
```bash
# Bucket chứa Data thô
aws s3api create-bucket --bucket $DATA_BUCKET --region $AWS_REGION

# Bucket chứa Manifest (Phải BẬT Versioning để phục vụ audit/provenance)
aws s3api create-bucket --bucket $MANIFEST_BUCKET --region $AWS_REGION
aws s3api put-bucket-versioning --bucket $MANIFEST_BUCKET --versioning-configuration Status=Enabled
```

#### 2. Tạo SageMaker Execution Role:
```bash
cat << 'EOF' > trust-sagemaker.json
{
  "Version": "2012-10-17",
  "Statement": [{ "Effect": "Allow", "Principal": { "Service": "sagemaker.amazonaws.com" }, "Action": "sts:AssumeRole" }]
}
EOF

aws iam create-role --role-name $SAGEMAKER_ROLE_NAME --assume-role-policy-document file://trust-sagemaker.json
aws iam attach-role-policy --role-name $SAGEMAKER_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam attach-role-policy --role-name $SAGEMAKER_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

#### 3. Tạo Lambda Execution Role:
```bash
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

### BƯỚC 3: XÂY DỰNG KHỐI DATA INGESTION & S3 EVENT TRIGGER

Khi có dữ liệu thô đẩy lên `s3://$DATA_BUCKET/raw/data.csv`:
1. S3 gửi sự kiện sang Lambda function.
2. Lambda tự động tính kích thước, thời gian, ETag và ghi file `manifest_*.json` vào `$MANIFEST_BUCKET`.

#### 1. Code Lambda Manifest Generator (`lambda_manifest.py`):
```python
import json, urllib.parse, boto3, os
from datetime import datetime

s3 = boto3.client('s3')
MANIFEST_BUCKET = os.environ['MANIFEST_BUCKET']
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
        print(f"Logged manifest: s3://{MANIFEST_BUCKET}/{key}")
    return {"statusCode": 200, "body": "OK"}
```

#### 2. Deploy Lambda & Gắn Event Notification:
```bash
zip -j lambda_manifest.zip lambda_manifest.py
aws lambda create-function \
    --function-name "${PROJECT_NAME}-manifest-generator" \
    --runtime python3.11 \
    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME} \
    --handler lambda_manifest.lambda_handler \
    --zip-file fileb://lambda_manifest.zip \
    --environment Variables="{MANIFEST_BUCKET=${MANIFEST_BUCKET},PROJECT_NAME=${PROJECT_NAME}}" \
    --region $AWS_REGION

# Cấp quyền gọi từ S3
aws lambda add-permission \
    --function-name "${PROJECT_NAME}-manifest-generator" \
    --statement-id AllowS3Invocation \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::${DATA_BUCKET} \
    --region $AWS_REGION

# Gắn Trigger S3 Event
cat << EOF > s3_notification.json
{
  "LambdaFunctionConfigurations": [{
    "LambdaFunctionArn": "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${PROJECT_NAME}-manifest-generator",
    "Events": ["s3:ObjectCreated:*"],
    "Filter": { "Key": { "FilterRules": [{ "Name": "prefix", "Value": "raw/" }] } }
  }]
}
EOF
aws s3api put-bucket-notification-configuration --bucket $DATA_BUCKET --notification-configuration file://s3_notification.json
```

---

### BƯỚC 4: THIẾT KẾ MÃ NGUỒN SAGEMAKER AI DAG (SCRIPT MODE)

> **Điểm cốt lõi**: Giữ cho các step chạy độc lập dưới dạng **Script Mode** để có thể debug cục bộ và tái sử dụng container chính hãng của AWS (`SKLearn`, `PyTorch`, `XGBoost`, `TensorFlow`).

#### 1. Bước Tiền xử lý (`aws_sagemaker/steps/preprocessing.py`):
- Đọc raw data từ `/opt/ml/processing/input/`.
- Thực hiện Data Cleaning, Missing Value Imputation, Categorical Encoding, Feature Scaling.
- Chia dữ liệu (ví dụ: Train 70%, Val 15%, Test 15%).
- **QUAN TRỌNG**: Lưu cả file `preprocessor.joblib` (hoặc pipeline tiền xử lý) cùng với dữ liệu npy/csv vào `/opt/ml/processing/output/`.

#### 2. Bước Huấn luyện Model (`aws_sagemaker/steps/train.py`):
- Đọc train data từ môi trường `$SM_CHANNEL_TRAIN` (`/opt/ml/input/data/train`).
- Huấn luyện thuật toán của bài toán đó (Stacking, LightGBM, XGBoost, Deep Learning...).
- Đóng gói file mô hình `model.joblib` vào `/opt/ml/model/`.
- **BÍ QUYẾT DOANH NGHIỆP**: Copy file `preprocessor.joblib` từ thư mục train vào `/opt/ml/model/`. Điều này giúp mô hình trở nên **tự thân hoàn chỉnh (Self-Contained)**: Container Endpoint khi deploy chỉ cần nhận chuỗi JSON từ client và tự động qua tiền xử lý rồi dự đoán, không cần client phải biến đổi feature!

#### 3. Bước Đánh giá Model (`aws_sagemaker/steps/evaluate.py`):
- Đọc `model.tar.gz` và dữ liệu Test (15% unseen data).
- Tính toán metrics đặc thù của bài toán:
  - Bài toán Hồi quy (Regression): $R^2$, RMSE, MAE.
  - Bài toán Phân loại (Classification): AUC, F1-Score, Precision, Recall.
- Xuất file chuẩn `/opt/ml/processing/evaluation/evaluation.json`:
```json
{
  "regression_metrics": {
    "r2_score": { "value": 0.82 }
  }
}
```

#### 4. Bước Serving Hook (`aws_sagemaker/steps/inference.py`):
Cung cấp 4 hàm hook chuẩn cho SageMaker Hosting container:
```python
def model_fn(model_dir):
    # Load model và preprocessor từ model_dir
    return {"model": joblib.load(os.path.join(model_dir, "model.joblib")),
            "prep": joblib.load(os.path.join(model_dir, "preprocessor.joblib"))}

def input_fn(body, content_type):
    # Parse payload JSON từ client
    return pd.DataFrame(json.loads(body)["instances"])

def predict_fn(df, artifacts):
    # Biến đổi feature và dự đoán
    return artifacts["model"].predict(artifacts["prep"].transform(df))

def output_fn(predictions, accept):
    # Trả kết quả JSON về cho client
    return json.dumps({"predictions": predictions.tolist()}), "application/json"
```

#### 5. Kết nối toàn bộ DAG trong `aws_sagemaker/pipeline.py`:
- Dùng `ProcessingStep` cho Preprocessing và Evaluation.
- Dùng `TrainingStep` cho Training.
- Dùng `PropertyFile` và **`JsonGet`** để trích xuất số float từ `evaluation.json`:
  ```python
  cond_metric = ConditionGreaterThanOrEqualTo(
      left=JsonGet(step_name=step_eval.name, property_file=eval_report, json_path="regression_metrics.r2_score.value"),
      right=threshold
  )
  ```
- Dùng `ModelStep` để đăng ký vào **Model Registry** với `approval_status="PendingManualApproval"`.
- **Cơ chế Auto-Cancellation**: Trước khi `pipeline.start()`, tự động tìm các lần chạy cũ đang `Executing` và gọi `stop_pipeline_execution` để chống lãng phí tài nguyên!

---

### BƯỚC 5: TỐI ƯU HOÁ QUY TRÌNH CI/CD & KIỂM SOÁT CHI PHÍ (COST GOVERNANCE)

> **Vấn đề thường gặp**: Mỗi khi lập trình viên sửa code (sửa doc, sửa CSS frontend, viết unit test...) và push lên GitHub, hệ thống lại kích hoạt SageMaker Pipeline huấn luyện tốn hàng chục USD.

#### 💡 GIẢI PHÁP CHUẨN: "TAG-TRIGGERED RETRAINING"
- **Push code lên `main` thường xuyên**: Chỉ chạy CI (Flake8 linting + Pytest unit tests) và cập nhật định nghĩa Pipeline (`pipeline.upsert()`), **TUYỆT ĐỐI KHÔNG BẬT MÁY ẢO HUẤN LUYỆN**.
- **Chỉ huấn luyện thật khi**: Tạo Git Release Tag (ví dụ: `v1.0.0`, `v2.0.0`).

#### Cấu hình `buildspecs/buildspec_ml.yml`:
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
          echo ">>> PHÁT HIỆN RELEASE TAG: '$GIT_TAG'. TIẾN HÀNH TRAIN MODEL..."
          python aws_sagemaker/pipeline.py --role-arn $SAGEMAKER_ROLE_ARN --bucket $DATA_BUCKET --execute
        else
          echo ">>> Push commit thường (Không có Git Tag)."
          echo ">>> CHỈ CẬP NHẬT ĐỊNH NGHĨA DAG (UPSERT), KHÔNG CHẠY HUẤN LUYỆN. TIẾT KIỆM TÀI NGUYÊN!"
          python aws_sagemaker/pipeline.py --role-arn $SAGEMAKER_ROLE_ARN --bucket $DATA_BUCKET
        fi
```

#### Thiết lập CodePipeline 4 Stages:
1. **Source**: GitHub V2 Connector.
2. **Build (CI)**: Chạy `buildspecs/buildspec_ci.yml` (chạy pytest).
3. **ML_Pipeline**: Chạy `buildspecs/buildspec_ml.yml` (kiểm tra tag).
4. **Approval**: Manual Approval kết nối với Amazon SNS Topic để gửi email cho Lead duyệt mô hình.

---

### BƯỚC 6: TRIỂN KHAI SERVERLESS SERVING ENDPOINT & CONSUMER LAYER

Sau khi Lead phê duyệt Model trong **SageMaker Model Registry**:

#### 1. Tạo Serverless Endpoint (Tiết kiệm 90% chi phí so với Real-time):
```bash
# 1. Lấy Package ARN mới nhất
PACKAGE_ARN=$(aws sagemaker list-model-packages --model-package-group-name $MODEL_GROUP_NAME --query "ModelPackageSummaryList[0].ModelPackageArn" --output text --region $AWS_REGION)

# 2. Tạo Model
aws sagemaker create-model \
    --model-name "${PROJECT_NAME}-model-v1" \
    --primary-container ModelPackageName=$PACKAGE_ARN \
    --execution-role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/${SAGEMAKER_ROLE_NAME} \
    --region $AWS_REGION

# 3. Tạo Endpoint Config Serverless (Memory 2048MB, MaxConcurrency 10)
aws sagemaker create-endpoint-config \
    --endpoint-config-name "${PROJECT_NAME}-serverless-cfg" \
    --production-variants '[{
        "VariantName": "AllTraffic",
        "ModelName": "'${PROJECT_NAME}'-model-v1",
        "ServerlessConfig": { "MemorySizeInMB": 2048, "MaxConcurrency": 10 }
    }]' \
    --region $AWS_REGION

# 4. Tạo Endpoint
aws sagemaker create-endpoint \
    --endpoint-name $ENDPOINT_NAME \
    --endpoint-config-name "${PROJECT_NAME}-serverless-cfg" \
    --region $AWS_REGION
```

#### 2. Tạo DynamoDB Table lưu trữ Audit Logs & Feedback Loop:
```bash
aws dynamodb create-table \
    --table-name $DYNAMODB_TABLE \
    --attribute-definitions AttributeName=prediction_id,AttributeType=S \
    --key-schema AttributeName=prediction_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $AWS_REGION
```

#### 3. Tạo Lambda API Proxy (Hỗ trợ 2 routes: `/predict` và `/feedback`):
Lambda này nhận request từ API Gateway $\rightarrow$ gọi SageMaker Endpoint $\rightarrow$ lưu toàn bộ input features, dự đoán và `actual_value` vào DynamoDB.

#### 4. Tạo Amazon API Gateway (HTTP API):
Tạo HTTP API với CORS bật sẵn (`*`), liên kết với Lambda API Proxy để cấp link HTTPS công khai cho Web Frontend / Mobile App.

---

### BƯỚC 7: VẬN HÀNH GIÁM SÁT (MONITORING) & RETRAINING LOOP TỰ ĐỘNG

1. **CloudWatch Alarms**:
   - Cảnh báo tỷ lệ lỗi 5XX trên Endpoint (`Invocation5XXErrors >= 1`).
   - Cảnh báo độ trễ mô hình (`ModelLatency > 200ms`).
2. **Vòng lặp Tái huấn luyện tự động (Continuous Retraining Loop)**:
   ```text
   Người dùng Web ──> Gửi thực tế qua POST /feedback
                            │
                            ▼
                DynamoDB Table tích luỹ bản ghi
                            │
                            ▼ (Khi đạt 1.000 mẫu mới hoặc định kỳ cuối tuần)
                Export DynamoDB ──> S3: raw/new_data.csv
                            │
                            ▼
                S3 Event kích hoạt CodePipeline với cờ FORCE_TRAIN=true
                            │
                            ▼
                SageMaker AI tự động huấn luyện phiên bản Model mới!
   ```

---

## 📑 PHẦN 4: CHECKLIST BÀN GIAO DỰ ÁN MLOPS (PRODUCTION ACCEPTANCE)

Khi áp dụng khung này cho bất kỳ dự án nào, hãy tích đủ 10 tiêu chí nghiệm thu sau:

- [ ] **1. IAM Roles chuẩn hoá**: Không dùng role cá nhân, có 3 role định danh rõ ràng (`SageMakerRole`, `LambdaRole`, `CodePipelineRole`).
- [ ] **2. Data Provenance**: Upload file thô vào S3 có sinh file `manifest_*.json` lưu kích thước và ETag.
- [ ] **3. CI Code Quality**: CodeBuild CI chạy `flake8` và `pytest` đạt 100% trước khi chạm vào hạ tầng.
- [ ] **4. Cost Governance**: Push commit thông thường KHÔNG tự ý bật máy ảo SageMaker; chỉ kích hoạt khi có Git Tag (`git tag v*.*`).
- [ ] **5. Concurrency Management**: Khi có đợt chạy mới, hệ thống tự huỷ đợt chạy cũ đang dang dở để tránh chạy trùng.
- [ ] **6. Quality Gate**: Mô hình chỉ được đưa vào Model Registry nếu đạt ngưỡng chất lượng ($R^2 \ge \text{threshold}$ hoặc $\text{AUC} \ge \text{threshold}$).
- [ ] **7. Human-in-the-loop**: Lead nhận email SNS và bấm duyệt (Approve) trên CodePipeline hoặc Studio.
- [ ] **8. Serverless Endpoint**: Endpoint hoạt động ở trạng thái `InService`, tự scale về 0 khi không có tải.
- [ ] **9. Feedback Logging**: Mọi dự đoán và phản hồi thực tế được ghi nhận đầy đủ vào DynamoDB.
- [ ] **10. CloudWatch Alarms**: Cấu hình cảnh báo lỗi 5XX và độ trễ về email người quản trị.
