# 🏗️ Hướng Dẫn Triển Khai MLOps Toàn Diện trên AWS SageMaker

> **Dự án**: California Housing Price Prediction
> **Stack**: SageMaker · CodePipeline · Lambda · API Gateway · DynamoDB · S3 · CloudFront
> **Phiên bản**: 2.1 – Song song Console UI + CLI/SDK cho **mọi bước**
> **Cập nhật**: 09/09/2026 – Dựa trên triển khai thực tế

---

## Mục Lục

1. [Kiến trúc tổng quan](#1-kiến-trúc-tổng-quan)
2. [Khối 1: S3 + IAM](#2-khối-1-s3--iam)
3. [Khối 2: SageMaker DAG Pipeline](#3-khối-2-sagemaker-dag-pipeline)
4. [Khối 3: CI/CD – CodePipeline + CodeBuild](#4-khối-3-cicd--codepipeline--codebuild)
5. [Khối 4: Model Registry → Serverless Endpoint](#5-khối-4-model-registry--serverless-endpoint)
6. [Khối 5: Consumer Layer – DynamoDB + Lambda + API Gateway](#6-khối-5-consumer-layer)
7. [Khối 6: Frontend React trên S3 + CloudFront](#7-khối-6-frontend-react-trên-s3--cloudfront)
8. [Khối 7: Monitoring với CloudWatch](#8-khối-7-monitoring-với-cloudwatch)
9. [Checklist sản xuất](#9-checklist-sản-xuất)
10. [Tóm tắt lỗi & cách khắc phục](#10-tóm-tắt-lỗi--cách-khắc-phục)

---

## 1. Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────────────────┐
│  DEVELOPER: git tag v1.0.0 && git push origin v1.0.0               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ GitHub Webhook (tag push only)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  KHỐI 3: CI/CD (AWS CodePipeline)                                   │
│  Source(GitHub) → Build(CodeBuild) → ML_Pipeline → Approval(SNS)   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ pipeline.start()
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  KHỐI 2: SAGEMAKER AI PIPELINE (DAG)                                │
│  DataPreprocessing → ModelTraining → ModelEvaluation                │
│                                           ↓                         │
│                              CheckEvaluationMetrics (R²≥0.7)        │
│                                           ↓ True                    │
│                                     RegisterModel                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Model approved in Registry
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  KHỐI 4: SERVING LAYER                                              │
│  Model Registry → SageMaker Model → Endpoint Config → Serverless EP│
└──────────────────────────────┬──────────────────────────────────────┘
                               │ InvokeEndpoint
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  KHỐI 5: CONSUMER LAYER                                             │
│  API Gateway (HTTP) → Lambda → SageMaker Endpoint                  │
│                            └→ DynamoDB (log predictions)            │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  KHỐI 6: FRONTEND (React + Vite trên S3 + CloudFront)              │
└─────────────────────────────────────────────────────────────────────┘
```

### Tài nguyên đã triển khai (Account: 678551739301, Region: us-east-1)

| Tài nguyên | Tên / ID |
|---|---|
| S3 Data | `california-housing-data-678551739301-us-east-1-an` |
| S3 Web | `california-housing-web-678551739301-us-east-1-an` |
| SageMaker Role | `CaliforniaHousing-SageMakerExecutionRole` |
| Lambda Role | `CaliforniaHousing-LambdaExecutionRole` |
| SageMaker Pipeline | `CaliforniaHousingMLOpsPipeline` |
| Model Registry Group | `CaliforniaHousingPackageGroup` |
| SageMaker Model | `california-housing-model-v1` |
| Endpoint Config | `california-housing-serverless-cfg` |
| Endpoint | `california-housing-ep` (Serverless, InService) |
| DynamoDB | `CaliforniaHousingPredictions` |
| Lambda | `california-housing-api-proxy` (Python 3.11, timeout=30s) |
| API Gateway | `california-housing-api` (ID: `1modfu9v9k`) |
| SNS Topic | `alifornia-housing-approval-topic` ⚠️ *thiếu chữ C đầu* |
| CodePipeline | `california-housing-mlops-pipeline` |

---

## 2. Khối 1: S3 + IAM

### 2.1 Tạo S3 Buckets

> **Lưu ý**: Tên bucket phải **globally unique**. Nên nhúng Account ID + Region vào tên để tránh xung đột.

#### 🖥️ Qua Console – Data Bucket (Private)

1. Vào **S3 → Create bucket**
2. **Bucket name**: `california-housing-data-678551739301-us-east-1-an`
3. **AWS Region**: `us-east-1`
4. **Object Ownership**: ACLs disabled (mặc định)
5. **Block Public Access**: ✅ Block all (giữ nguyên)
6. **Bucket Versioning**: Enable (giữ lịch sử data)
7. Click **Create bucket**

#### 🖥️ Qua Console – Web Bucket (Static Hosting)

1. Tạo bucket: `california-housing-web-678551739301-us-east-1-an`
2. **Block Public Access**: ❌ Bỏ check "Block all public access" → Confirm
3. Sau khi tạo → **Properties → Static website hosting → Edit**:
   - Enable: ✅
   - Index document: `index.html`
   - Error document: `index.html` ← quan trọng cho React SPA
   - **Save changes**
4. **Permissions → Bucket policy → Edit** → paste:

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

#### ⌨️ Qua CLI

> ⚠️ **us-east-1 exception**: Khi tạo bucket ở `us-east-1`, **KHÔNG** thêm `--create-bucket-configuration`. Chỉ các region khác mới cần.

```bash
ACCOUNT_ID=678551739301
REGION=us-east-1

# Data bucket (private)
aws s3api create-bucket \
  --bucket california-housing-data-${ACCOUNT_ID}-${REGION}-an \
  --region ${REGION}

# Bật versioning
aws s3api put-bucket-versioning \
  --bucket california-housing-data-${ACCOUNT_ID}-${REGION}-an \
  --versioning-configuration Status=Enabled

# Web bucket
aws s3api create-bucket \
  --bucket california-housing-web-${ACCOUNT_ID}-${REGION}-an \
  --region ${REGION}

# Bỏ block public access
aws s3api delete-public-access-block \
  --bucket california-housing-web-${ACCOUNT_ID}-${REGION}-an

# Static website hosting (error về index.html để React SPA xử lý routing)
aws s3 website s3://california-housing-web-${ACCOUNT_ID}-${REGION}-an/ \
  --index-document index.html \
  --error-document index.html

# Public read policy
aws s3api put-bucket-policy \
  --bucket california-housing-web-${ACCOUNT_ID}-${REGION}-an \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::california-housing-web-678551739301-us-east-1-an/*"
    }]
  }'
```

---

### 2.2 Tạo IAM – SageMaker Execution Role

#### 🖥️ Qua Console

1. **IAM → Roles → Create role**
2. **Trusted entity type**: AWS service
3. **Use case**: SageMaker → **SageMaker**
4. Click **Next**
5. Attach policies:
   - ✅ `AmazonSageMakerFullAccess`
   - ✅ `AmazonS3FullAccess`
6. **Role name**: `CaliforniaHousing-SageMakerExecutionRole`
7. Click **Create role**

#### ⌨️ Qua CLI

```bash
cat > /tmp/sm-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "sagemaker.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name CaliforniaHousing-SageMakerExecutionRole \
  --assume-role-policy-document file:///tmp/sm-trust.json

aws iam attach-role-policy \
  --role-name CaliforniaHousing-SageMakerExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy \
  --role-name CaliforniaHousing-SageMakerExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

---

### 2.3 Tạo IAM – Lambda Execution Role

#### 🖥️ Qua Console

1. **IAM → Roles → Create role**
2. **Trusted entity**: AWS service → **Lambda**
3. Attach: ✅ `AWSLambdaBasicExecutionRole`
4. **Role name**: `CaliforniaHousing-LambdaExecutionRole`
5. Click **Create role**
6. Vào role vừa tạo → **Add permissions → Create inline policy → JSON**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeSageMaker",
      "Effect": "Allow",
      "Action": ["sagemaker:InvokeEndpoint"],
      "Resource": "arn:aws:sagemaker:us-east-1:678551739301:endpoint/california-housing-ep"
    },
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem","dynamodb:GetItem","dynamodb:UpdateItem","dynamodb:Query"],
      "Resource": "arn:aws:dynamodb:us-east-1:678551739301:table/CaliforniaHousingPredictions"
    }
  ]
}
```

7. **Policy name**: `LambdaCustomPolicy` → **Create policy**

#### ⌨️ Qua CLI

```bash
cat > /tmp/lambda-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name CaliforniaHousing-LambdaExecutionRole \
  --assume-role-policy-document file:///tmp/lambda-trust.json

aws iam attach-role-policy \
  --role-name CaliforniaHousing-LambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam put-role-policy \
  --role-name CaliforniaHousing-LambdaExecutionRole \
  --policy-name LambdaCustomPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Sid":"InvokeSM","Effect":"Allow",
       "Action":["sagemaker:InvokeEndpoint"],
       "Resource":"arn:aws:sagemaker:us-east-1:678551739301:endpoint/california-housing-ep"},
      {"Sid":"DDB","Effect":"Allow",
       "Action":["dynamodb:PutItem","dynamodb:GetItem","dynamodb:UpdateItem","dynamodb:Query"],
       "Resource":"arn:aws:dynamodb:us-east-1:678551739301:table/CaliforniaHousingPredictions"}
    ]
  }'
```

---

## 3. Khối 2: SageMaker DAG Pipeline

### 3.1 Cấu trúc Script Mode

Mô hình dùng **Script Mode**: code Python chạy trong container SageMaker dựng sẵn, không cần tự build Docker image.

```
aws_sagemaker/
├── pipeline.py           # Định nghĩa DAG pipeline (entry point)
└── steps/
    ├── preprocessing.py  # SKLearnProcessor: encode features, train/test split
    ├── training.py       # SKLearn Estimator: train RandomForest
    └── evaluate.py       # ScriptProcessor: tính R², xuất evaluation.json
```

**Container mặc định (scikit-learn 1.2)**:
```
683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3
```

### 3.2 ⚠️ CẢNH BÁO: Dùng JsonGet cho ConditionStep

**Lỗi gặp phải**:
```
ClientError: BinaryCondition left=<S3Uri (String)> right=<r2_threshold (Float)> – type mismatch
```

**Nguyên nhân**: Dùng `step_evaluate.properties.Outputs["evaluation"]` trực tiếp trả về `S3Uri` (String), không so sánh được với float `0.7`.

**✅ Giải pháp – Dùng JsonGet + PropertyFile**:

```python
from sagemaker.workflow.functions import JsonGet       # PHẢI import
from sagemaker.workflow.properties import PropertyFile

evaluation_report = PropertyFile(
    name="EvaluationReport",
    output_name="evaluation",    # khớp output_name trong ProcessingOutput
    path="evaluation.json"       # tên file evaluate.py ghi ra
)

step_evaluate = ProcessingStep(
    name="ModelEvaluation",
    # ...
    property_files=[evaluation_report],
)

cond = ConditionGreaterThanOrEqualTo(
    left=JsonGet(
        step_name=step_evaluate.name,
        property_file=evaluation_report,
        json_path="regression_metrics.r2_score.value"
    ),
    right=0.7
)
```

**evaluate.py phải ghi đúng cấu trúc JSON**:

```python
metrics = {
    "regression_metrics": {
        "r2_score": {
            "value": float(r2),     # PHẢI là Python float, không phải string
            "standard_deviation": "NaN"
        }
    }
}
output_dir = "/opt/ml/processing/evaluation"
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "evaluation.json"), "w") as f:
    json.dump(metrics, f)
```

### 3.3 Theo dõi và Chạy Pipeline

#### 🖥️ Theo dõi qua Console

1. **SageMaker → Pipelines** (menu trái)
2. Chọn **CaliforniaHousingMLOpsPipeline**
3. Tab **Executions** → click vào execution đang chạy
4. Xem **DAG graph**: xanh = thành công, đỏ = lỗi, xám = chưa chạy
5. Click vào bất kỳ node → **View logs** → mở CloudWatch Logs

#### ⌨️ Chạy Pipeline qua CLI

```bash
cd aws_sagemaker

# Chỉ upsert pipeline definition (không train – dùng khi sửa pipeline.py)
python pipeline.py \
  --region us-east-1 \
  --role arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole \
  --default-bucket california-housing-data-678551739301-us-east-1-an

# Upsert + chạy training ngay
python pipeline.py \
  --region us-east-1 \
  --role arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole \
  --default-bucket california-housing-data-678551739301-us-east-1-an \
  --execute

# Xem trạng thái executions gần nhất
aws sagemaker list-pipeline-executions \
  --pipeline-name CaliforniaHousingMLOpsPipeline \
  --sort-by CreationTime --sort-order Descending --max-results 5 \
  --query "PipelineExecutionSummaries[*].{Status:PipelineExecutionStatus,Started:StartTime}"
```

### 3.4 Auto-cancel Concurrent Executions

Thêm vào `pipeline.py` trước `pipeline.start()` để tránh chạy song song tốn tiền:

```python
if args.execute:
    sm_client = boto3.client("sagemaker", region_name=args.region)
    running = sm_client.list_pipeline_executions(
        PipelineName=pipeline_name,
        SortBy="CreationTime", SortOrder="Descending",
    )
    for ex in running["PipelineExecutionSummaries"]:
        if ex["PipelineExecutionStatus"] in ("Executing", "Stopping"):
            print(f"Stopping concurrent: {ex['PipelineExecutionArn']}")
            sm_client.stop_pipeline_execution(
                PipelineExecutionArn=ex["PipelineExecutionArn"]
            )
    pipeline.start()
```

---

## 4. Khối 3: CI/CD – CodePipeline + CodeBuild

### 4.1 Kết nối GitHub (CodeStar Connections)

#### 🖥️ Qua Console

1. **Developer Tools → Settings → Connections → Create connection**
2. **Provider**: GitHub
3. **Connection name**: `github-california-housing`
4. Click **Connect to GitHub** → Authorize → **Install AWS Connector for GitHub**
5. Chọn repository `nvbao117/california-housing-price` → **Save**
6. Click **Connect** → Status phải là **Available** ✅
7. **Copy Connection ARN** để dùng trong bước tạo CodePipeline

#### ⌨️ Qua CLI

```bash
# Tạo connection (vẫn cần hoàn thành GitHub OAuth handshake qua Console lần đầu)
aws codestar-connections create-connection \
  --provider-type GitHub \
  --connection-name github-california-housing

# Kiểm tra ARN
aws codestar-connections list-connections \
  --provider-type GitHub \
  --query "Connections[?ConnectionName=='github-california-housing'].ConnectionArn" \
  --output text
```

---

### 4.2 Tạo CodePipeline

#### 🖥️ Qua Console (step-by-step)

**Bước 1 – Pipeline settings**:
1. **CodePipeline → Pipelines → Create pipeline**
2. **Pipeline name**: `california-housing-mlops-pipeline`
3. **Pipeline type**: V2
4. **Execution mode**: SUPERSEDED
5. **Service role**: New service role (auto-tạo)
6. Click **Next**

**Bước 2 – Source stage**:
1. **Source provider**: GitHub (Version 2)
2. **Connection**: chọn `github-california-housing`
3. **Repository name**: `nvbao117/california-housing-price`
4. **Default branch**: `main`
5. **Trigger type**: Tags filter → **Include**: `v*`
6. Click **Next**

**Bước 3 – Build stage**:
1. **Build provider**: AWS CodeBuild → **Create project** (tab mới):
   - **Project name**: `california-housing-mlops-build`
   - **Environment**: Amazon Linux 2 → Standard → `aws/codebuild/standard:7.0`
   - **Buildspec**: Use a buildspec file → path: `buildspecs/buildspec_ml.yml`
   - **Service role**: New service role
   - Click **Continue to CodePipeline**
2. Click **Next**

**Bước 4 – Deploy stage**: Click **Skip deploy stage**

**Bước 5 – Review** → **Create pipeline**

**Thêm Approval stage** (sau khi pipeline tạo xong):
1. Pipeline → **Edit**
2. Sau stage Build → **Add stage** → tên: `Approval`
3. **Add action group**:
   - Action name: `ManualApproval`
   - Action provider: **Manual approval**
   - **SNS topic ARN**: `arn:aws:sns:us-east-1:678551739301:alifornia-housing-approval-topic`
4. **Done → Save**

#### ⌨️ Kích hoạt pipeline chạy qua CLI

```bash
# Trigger thủ công (không cần push code)
aws codepipeline start-pipeline-execution \
  --name california-housing-mlops-pipeline

# Xem trạng thái pipeline
aws codepipeline get-pipeline-state \
  --name california-housing-mlops-pipeline \
  --query "stageStates[*].{Stage:stageName,Status:latestExecution.status}"
```

---

### 4.3 Tag-triggered Training (Tiết kiệm chi phí)

**Vấn đề**: Trigger mặc định (mọi push vào main) → mỗi lần sửa README cũng tốn ~$1-5 training.

**`buildspecs/buildspec_ml.yml`**:

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
        echo "Tag hien tai: ${CURRENT_TAG}"
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
          python aws_sagemaker/pipeline.py \
            --region us-east-1 \
            --role arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole \
            --default-bucket california-housing-data-678551739301-us-east-1-an \
            --execute
        else
          python aws_sagemaker/pipeline.py \
            --region us-east-1 \
            --role arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole \
            --default-bucket california-housing-data-678551739301-us-east-1-an
          echo "Pipeline definition updated. No training (no tag)."
        fi
```

**Cách sử dụng**:

```bash
# Push code thông thường – KHÔNG train (chỉ update pipeline definition)
git add . && git commit -m "fix: update feature engineering"
git push origin main

# Kích hoạt training – gắn tag version
git tag v1.0.1 -m "Release v1.0.1: improved model features"
git push origin v1.0.1
# → CodePipeline nhận webhook tag → buildspec detect tag → python pipeline.py --execute
```

---

### 4.4 ⚠️ CẢNH BÁO: CodePipeline Role Thiếu Quyền SNS

**Lỗi**:
```
User: arn:aws:sts::678551739301:assumed-role/AWSCodePipelineServiceRole-...
is not authorized to perform: SNS:Publish on resource: alifornia-housing-approval-topic
```

#### 🖥️ Sửa qua Console

1. **IAM → Roles** → tìm role: `AWSCodePipelineServiceRole-us-east-1-california-housing-mlops-p`
2. Tab **Permissions → Add permissions → Create inline policy**
3. Chọn tab **JSON** → paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowSNSPublish",
    "Effect": "Allow",
    "Action": ["sns:Publish"],
    "Resource": "arn:aws:sns:us-east-1:678551739301:alifornia-housing-approval-topic"
  }]
}
```

4. **Policy name**: `AllowSNSPublish` → **Create policy**

#### ⌨️ Sửa qua CLI

```bash
aws iam put-role-policy \
  --role-name "AWSCodePipelineServiceRole-us-east-1-california-housing-mlops-p" \
  --policy-name AllowSNSPublish \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Sid":"AllowSNSPublish","Effect":"Allow",
    "Action":["sns:Publish"],
    "Resource":"arn:aws:sns:us-east-1:678551739301:alifornia-housing-approval-topic"}]
  }'
```

---

## 5. Khối 4: Model Registry → Serverless Endpoint

### 5.1 Approve Model trong Registry

#### 🖥️ Qua Console

1. **SageMaker → Model Registry** (menu trái)
2. Click **CaliforniaHousingPackageGroup**
3. Click vào **Version 1**
4. Click **Update status** → chọn **Approved** → **Update status**

#### ⌨️ Qua CLI

```bash
aws sagemaker update-model-package \
  --model-package-arn \
  "arn:aws:sagemaker:us-east-1:678551739301:model-package/CaliforniaHousingPackageGroup/1" \
  --model-approval-status Approved
```

---

### 5.2 ⚠️ CẢNH BÁO: Tạo SageMaker Model

**Lỗi 1 – UI Bug** (khi chọn "Use a model package from Model Registry"):
```
UnexpectedParameter: Unexpected key 'TrainingPlanArnEquals' found in params
```

**Lỗi 2 – Network Isolation** (ngay cả khi bỏ qua lỗi UI):
```
ValidationException: Network isolation is not supported for Serverless Inference
```
Console tự bật `EnableNetworkIsolation=True` khi tạo model từ Registry → Serverless endpoint không hoạt động.

#### 🖥️ Workaround qua Console (tránh 2 lỗi trên)

1. **SageMaker → Models → Create model**
2. **Model name**: `california-housing-model-v1`
3. **IAM role**: `CaliforniaHousing-SageMakerExecutionRole`
4. **Container definition**: Chọn **"Provide model artifacts and inference image location"** ← KHÔNG chọn "Use model package from Model Registry"
5. **Location of inference code image**:
   ```
   683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3
   ```
6. **Location of model artifacts**:
   ```
   s3://california-housing-data-678551739301-us-east-1-an/pipelines-j8xrbofjibb6-ModelTraining-Be3xL1AJnD/output/model.tar.gz
   ```
7. **Container environment variables** – Add 2 biến:
   - Key: `SAGEMAKER_PROGRAM` → Value: `training.py`
   - Key: `SAGEMAKER_SUBMIT_DIRECTORY` → Value: `s3://california-housing-data-678551739301-us-east-1-an/sagemaker-scikit-learn-2026-09-09-03-28-28-876/sourcedir.tar.gz`
8. **Network isolation**: ❌ **KHÔNG bật**
9. Click **Create model**

#### ⌨️ Tạo Model qua CLI (cách chắc chắn nhất)

```bash
aws sagemaker create-model \
  --model-name california-housing-model-v1 \
  --execution-role-arn \
    arn:aws:iam::678551739301:role/CaliforniaHousing-SageMakerExecutionRole \
  --primary-container '{
    "Image": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
    "ModelDataUrl": "s3://california-housing-data-678551739301-us-east-1-an/pipelines-j8xrbofjibb6-ModelTraining-Be3xL1AJnD/output/model.tar.gz",
    "Environment": {
      "SAGEMAKER_PROGRAM": "training.py",
      "SAGEMAKER_SUBMIT_DIRECTORY": "s3://california-housing-data-678551739301-us-east-1-an/sagemaker-scikit-learn-2026-09-09-03-28-28-876/sourcedir.tar.gz"
    }
  }'
# Không có --enable-network-isolation → mặc định False → OK với Serverless
```

> **Lưu ý**: Mỗi lần pipeline chạy lại, đường dẫn `model.tar.gz` sẽ thay đổi. Lấy đường dẫn mới:
> ```bash
> aws sagemaker list-training-jobs \
>   --sort-by CreationTime --sort-order Descending --max-results 1 \
>   --query "TrainingJobSummaries[0].TrainingJobName" --output text | \
>   xargs aws sagemaker describe-training-job --training-job-name \
>   --query "ModelArtifacts.S3ModelArtifacts"
> ```

---

### 5.3 Tạo Serverless Endpoint Config

#### 🖥️ Qua Console

1. **SageMaker → Endpoint configurations → Create endpoint configuration**
2. **Name**: `california-housing-serverless-cfg`
3. **Type**: Serverless
4. **Add model**:
   - Model name: `california-housing-model-v1`
   - Memory size: `2048 MB`
   - Max concurrency: `10`
5. Click **Create endpoint configuration**

#### ⌨️ Qua CLI

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name california-housing-serverless-cfg \
  --production-variants '[{
    "VariantName": "AllTraffic",
    "ModelName": "california-housing-model-v1",
    "ServerlessConfig": {
      "MemorySizeInMB": 2048,
      "MaxConcurrency": 10
    }
  }]'
```

---

### 5.4 Tạo và Kiểm tra Endpoint

#### 🖥️ Qua Console

1. **SageMaker → Endpoints → Create endpoint**
2. **Endpoint name**: `california-housing-ep`
3. **Endpoint configuration**: `california-housing-serverless-cfg`
4. Click **Create endpoint**
5. Chờ **Status: Creating → InService** (~5-10 phút)
6. Refresh để xem trạng thái cập nhật

#### ⌨️ Qua CLI

```bash
# Tạo endpoint
aws sagemaker create-endpoint \
  --endpoint-name california-housing-ep \
  --endpoint-config-name california-housing-serverless-cfg

# Chờ endpoint sẵn sàng (block terminal cho đến khi xong)
aws sagemaker wait endpoint-in-service \
  --endpoint-name california-housing-ep
echo "Endpoint sẵn sàng!"

# Kiểm tra trạng thái
aws sagemaker describe-endpoint \
  --endpoint-name california-housing-ep \
  --query "{Status:EndpointStatus,Type:ProductionVariants[0].CurrentServerlessConfig}"

# Test invoke trực tiếp
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name california-housing-ep \
  --content-type application/json \
  --body '{"instances": [[-122.23, 37.88, 41.0, 880.0, 129.0, 322.0, 126.0, 8.3252, 0]]}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/sm-output.json && cat /tmp/sm-output.json
# Mong đợi: {"predictions": [425027.58]}
```

> **Thứ tự cột instances**: `[longitude, latitude, housing_median_age, total_rooms, total_bedrooms, population, households, median_income, ocean_proximity_encoded]`
> PHẢI khớp chính xác với thứ tự cột trong `preprocessing.py`.

---

## 6. Khối 5: Consumer Layer

### 6.1 Tạo DynamoDB Table

#### 🖥️ Qua Console

1. **DynamoDB → Tables → Create table**
2. **Table name**: `CaliforniaHousingPredictions`
3. **Partition key**: `prediction_id` (type: **String**)
4. **Sort key**: để trống
5. **Table settings**: Customize settings
6. **Capacity mode**: **On-demand** (trả theo lượng dùng, không cần predict traffic)
7. Click **Create table**
8. Chờ **Status: Active** (~30 giây)

#### ⌨️ Qua CLI

```bash
aws dynamodb create-table \
  --table-name CaliforniaHousingPredictions \
  --attribute-definitions AttributeName=prediction_id,AttributeType=S \
  --key-schema AttributeName=prediction_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Chờ table active
aws dynamodb wait table-exists \
  --table-name CaliforniaHousingPredictions
echo "DynamoDB table ready!"
```

---

### 6.2 Tạo Lambda Function

#### ⚠️ CẢNH BÁO: Tăng Timeout lên 30 giây

**Lỗi**: Lambda bị timeout sau 3 giây (default). Serverless Endpoint cold start 15-20 giây → Lambda chết trước khi nhận được kết quả.

#### 🖥️ Tạo Lambda qua Console

1. **Lambda → Functions → Create function**
2. **Author from scratch**
3. **Function name**: `california-housing-api-proxy`
4. **Runtime**: Python 3.11
5. **Architecture**: x86_64
6. **Execution role**: Use an existing role → `CaliforniaHousing-LambdaExecutionRole`
7. Click **Create function**

**Deploy code**:
8. **Code tab** → click vào `lambda_function.py` → xóa code mặc định → paste code bên dưới
9. Click **Deploy**

**Tăng timeout** ← ĐỪng bỏ qua bước này:
10. **Configuration tab → General configuration → Edit**
    - **Timeout**: `0 min` `30 sec`
    - Click **Save**

**Thêm Environment variables**:
11. **Configuration tab → Environment variables → Edit → Add environment variable**:
    - `ENDPOINT_NAME` = `california-housing-ep`
    - `DYNAMODB_TABLE` = `CaliforniaHousingPredictions`
    - `REGION` = `us-east-1`
    - Click **Save**

**Test Lambda từ Console**:
12. **Test tab → Create new event**:
    - Event name: `TestPredict`
    - Paste:
```json
{
  "rawPath": "/predict",
  "body": "{\"instances\": [[-122.23, 37.88, 41.0, 880.0, 129.0, 322.0, 126.0, 8.3252, 0]]}"
}
```
13. Click **Test** → Xem kết quả

#### ⌨️ Tạo Lambda qua CLI

```bash
# Đóng gói code
cd aws_lambda
zip /tmp/lambda.zip lambda_function.py

# Tạo function với timeout 30s
aws lambda create-function \
  --function-name california-housing-api-proxy \
  --runtime python3.11 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::678551739301:role/CaliforniaHousing-LambdaExecutionRole \
  --zip-file fileb:///tmp/lambda.zip \
  --timeout 30 \
  --environment 'Variables={
    ENDPOINT_NAME=california-housing-ep,
    DYNAMODB_TABLE=CaliforniaHousingPredictions,
    REGION=us-east-1
  }'

# Cập nhật code sau khi sửa
zip /tmp/lambda.zip lambda_function.py
aws lambda update-function-code \
  --function-name california-housing-api-proxy \
  --zip-file fileb:///tmp/lambda.zip
```

**Code Lambda** (`aws_lambda/lambda_function.py`):

```python
import json, boto3, uuid, os
from datetime import datetime

ENDPOINT_NAME = os.environ.get("ENDPOINT_NAME", "california-housing-ep")
TABLE_NAME    = os.environ.get("DYNAMODB_TABLE", "CaliforniaHousingPredictions")
REGION        = os.environ.get("REGION", "us-east-1")

sm_runtime = boto3.client("sagemaker-runtime", region_name=REGION)
dynamodb   = boto3.resource("dynamodb", region_name=REGION)

def lambda_handler(event, context):
    path = event.get("rawPath", "/predict")
    body = json.loads(event.get("body", "{}"))

    if path == "/predict":
        # ⚠️ Payload PHẢI là {"instances": [[f1, f2, ...]]} – array format!
        response = sm_runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Body=json.dumps(body)
        )
        result    = json.loads(response["Body"].read().decode())
        predicted = result["predictions"][0]

        pred_id = str(uuid.uuid4())
        dynamodb.Table(TABLE_NAME).put_item(Item={
            "prediction_id":   pred_id,
            "timestamp":       datetime.utcnow().isoformat(),
            "features":        json.dumps(body),
            "predicted_price": str(predicted),
        })

        return {
            "statusCode": 200,
            "headers":    {"Access-Control-Allow-Origin": "*"},
            "body":       json.dumps({"prediction_id": pred_id, "predicted_value": predicted})
        }

    elif path == "/feedback":
        dynamodb.Table(TABLE_NAME).update_item(
            Key={"prediction_id": body.get("prediction_id")},
            UpdateExpression="SET actual_price = :val",
            ExpressionAttributeValues={":val": str(body.get("actual_price"))}
        )
        return {
            "statusCode": 200,
            "headers":    {"Access-Control-Allow-Origin": "*"},
            "body":       json.dumps({"message": "Feedback saved"})
        }
```

---

### 6.3 Tạo API Gateway (HTTP API)

#### 🖥️ Qua Console

1. **API Gateway → Create API**
2. Chọn **HTTP API → Build**
3. **Add integration**:
   - Type: Lambda
   - AWS Region: `us-east-1`
   - Lambda function: `california-housing-api-proxy`
4. **API name**: `california-housing-api`
5. Click **Next**
6. **Routes** – thêm 2 route:
   - `POST /predict` → integration: `california-housing-api-proxy`
   - `POST /feedback` → integration: `california-housing-api-proxy`
7. Click **Next → Next → Create**
8. **Ghi lại Invoke URL**: `https://1modfu9v9k.execute-api.us-east-1.amazonaws.com`

**Cấu hình CORS** (sau khi tạo):
1. API → **CORS → Configure**
2. **Allow origins**: `*`
3. **Allow methods**: `POST, OPTIONS`
4. **Allow headers**: `Content-Type`
5. Click **Save**

#### ⌨️ Qua CLI

```bash
# Tạo HTTP API với CORS
API_ID=$(aws apigatewayv2 create-api \
  --name california-housing-api \
  --protocol-type HTTP \
  --cors-configuration \
    'AllowOrigins=["*"],AllowMethods=["POST","OPTIONS"],AllowHeaders=["Content-Type"]' \
  --query "ApiId" --output text)

echo "API ID: $API_ID"

# Tạo Lambda integration
LAMBDA_ARN="arn:aws:lambda:us-east-1:678551739301:function:california-housing-api-proxy"
INT_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $LAMBDA_ARN \
  --payload-format-version 2.0 \
  --query "IntegrationId" --output text)

# Tạo routes
aws apigatewayv2 create-route --api-id $API_ID \
  --route-key "POST /predict" --target "integrations/$INT_ID"
aws apigatewayv2 create-route --api-id $API_ID \
  --route-key "POST /feedback" --target "integrations/$INT_ID"

# Deploy (auto-deploy stage $default)
aws apigatewayv2 create-stage \
  --api-id $API_ID --stage-name '$default' --auto-deploy

# Cấp quyền Lambda cho API Gateway gọi được
aws lambda add-permission \
  --function-name california-housing-api-proxy \
  --statement-id api-gw-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:678551739301:${API_ID}/*/*"

echo "API URL: https://${API_ID}.execute-api.us-east-1.amazonaws.com"
```

### 6.4 Test End-to-End

```bash
API_URL="https://1modfu9v9k.execute-api.us-east-1.amazonaws.com"

# Test predict
curl -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"instances": [[-122.23, 37.88, 41.0, 880.0, 129.0, 322.0, 126.0, 8.3252, 0]]}'
# → {"prediction_id": "xxx-yyy-zzz", "predicted_value": 425027.58}

# Test feedback (thay PRED_ID bằng id từ bước trên)
curl -X POST "${API_URL}/feedback" \
  -H "Content-Type: application/json" \
  -d '{"prediction_id": "PRED_ID", "actual_price": 430000}'
# → {"message": "Feedback saved"}

# Xem dữ liệu trong DynamoDB
aws dynamodb scan \
  --table-name CaliforniaHousingPredictions \
  --max-items 5 \
  --query "Items[*].{id:prediction_id.S,price:predicted_price.S,ts:timestamp.S}"
```

---

## 7. Khối 6: Frontend React trên S3 + CloudFront

### 7.1 ⚠️ CẢNH BÁO: React Router & Vite trên S3 → Màn Hình Trắng

**Lỗi**: Upload xong lên S3, mở website → **màn hình trắng hoàn toàn**.

**Nguyên nhân 1 – BrowserRouter**: S3 chỉ có `index.html` ở root. Khi refresh tại route `/admin`, S3 tìm file `/admin/index.html` → không tìm thấy → 404 → trắng.

**Nguyên nhân 2 – Vite base path**: Vite mặc định `base: '/'` → JS/CSS load từ `/assets/main.js` (absolute path) → fail trên S3 domain.

**✅ Sửa 4 file trước khi build**:

```jsx
// frontend/src/App.jsx
// ❌ SAI – không dùng BrowserRouter
import { BrowserRouter as Router } from 'react-router-dom';
// ✅ ĐÚNG – dùng HashRouter (URL sẽ thành https://.../#/route)
import { HashRouter as Router } from 'react-router-dom';
```

```js
// frontend/vite.config.js
export default defineConfig({
  plugins: [react()],
  base: './',   // ← THÊM DÒNG NÀY – dùng relative paths
})
```

```env
# frontend/.env.production (tạo file mới)
VITE_API_URL=https://1modfu9v9k.execute-api.us-east-1.amazonaws.com
```

```js
// frontend/src/api/client.js
const API_BASE_URL = import.meta.env.VITE_API_URL
  || "https://1modfu9v9k.execute-api.us-east-1.amazonaws.com";
```

### 7.2 Build Frontend

```bash
cd frontend
npm install        # cài dependencies (lần đầu hoặc khi thêm package)
npm run build      # build production → tạo thư mục dist/

# Kiểm tra cấu trúc dist/ phải như này:
ls dist/
# → assets/  index.html  vite.svg  (không có folder dist/ bên trong)
```

---

### 7.3 ⚠️ CẢNH BÁO: Upload Đúng Cách Lên S3

**Lỗi**: Kéo thả thư mục `dist/` vào S3 → S3 Objects chỉ hiển thị 1 folder tên `dist/` → website không tìm được `index.html` ở bucket root → 404.

#### 🖥️ Qua Console – Cách đúng

1. Vào bucket `california-housing-web-678551739301-us-east-1-an`
2. Click **Upload**
3. **Add files** → chọn `dist/index.html` và các file `.html`, `.ico`, `.txt` trong `dist/`
4. **Add folder** → chọn **folder `assets`** bên TRONG `dist/` (không phải folder `dist/`)
5. ❌ **KHÔNG kéo thả cả folder `dist/`**
6. Click **Upload**

**Kiểm tra**: Nhìn vào bucket root, phải thấy:
```
✅ Đúng:           ❌ Sai:
assets/            dist/
index.html
```

#### ⌨️ Qua CLI – Cách đúng nhất (1 lệnh)

```bash
# Sync NỘI DUNG dist/ vào root bucket
aws s3 sync frontend/dist/ \
  s3://california-housing-web-678551739301-us-east-1-an/ \
  --delete

# Kiểm tra: phải thấy index.html ở root
aws s3 ls s3://california-housing-web-678551739301-us-east-1-an/
# Expected:
#   PRE assets/
#   2026-09-09 ... index.html
```

---

### 7.4 ⚠️ CẢNH BÁO: S3 Website URL Timeout ở Việt Nam

**Lỗi**: `ERR_TIMED_OUT` khi truy cập `http://bucket.s3-website-us-east-1.amazonaws.com`

**Nguyên nhân**: URL website S3 dùng HTTP port 80. ISP Việt Nam block port 80 đến một số AWS endpoints.

**✅ Giải pháp**: Dùng CloudFront (HTTPS port 443 – không bị block).

---

### 7.5 Tạo CloudFront Distribution

#### 🖥️ Qua Console (chi tiết từng bước)

1. **CloudFront → Distributions → Create distribution**

2. **Origin domain**: click dropdown → chọn S3 bucket:
   ```
   california-housing-web-678551739301-us-east-1-an.s3.amazonaws.com
   ```

   > ⚠️ **Nếu lỡ upload cả folder `dist/`**: Sau khi chọn bucket, điền thêm **Origin path**: `/dist`

3. **Origin access**: chọn **Origin access control settings (recommended)**
   - Click **Create new OAC**
   - Name: `california-housing-oac`
   - Click **Create**
   - AWS sẽ hiện banner "You must update the S3 bucket policy" → **Copy policy** (sẽ dán vào S3 sau)

4. **Default cache behavior**:
   - **Viewer protocol policy**: Redirect HTTP to HTTPS
   - **Allowed HTTP methods**: GET, HEAD
   - **Cache policy**: CachingOptimized

5. **Settings**:
   - **Default root object**: `index.html` ← QUAN TRỌNG, không có sẽ 403
   - **Price class**: Use only North America and Europe (rẻ nhất)
   - **Description**: California Housing Web App

6. Click **Create distribution**
   - Chờ **Status: Deploying → Deployed** (~10-15 phút)

7. **Cập nhật S3 Bucket Policy** (bắt buộc khi dùng OAC):
   - S3 → bucket → **Permissions → Bucket policy → Edit**
   - Dán policy vừa copy từ CloudFront (trông như sau):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontServicePrincipal",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::california-housing-web-678551739301-us-east-1-an/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::678551739301:distribution/<DISTRIBUTION_ID>"
      }
    }
  }]
}
```
   - Click **Save changes**

8. Truy cập website qua **CloudFront domain**:
   - `https://xxxxx.cloudfront.net`
   - HashRouter → URL dạng: `https://xxxxx.cloudfront.net/#/`

#### ⌨️ Tạo CloudFront qua CLI

```bash
BUCKET=california-housing-web-678551739301-us-east-1-an

DIST_ID=$(aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "ch-web-2026-09",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "S3Origin",
        "DomainName": "'${BUCKET}'.s3.amazonaws.com",
        "S3OriginConfig": {"OriginAccessIdentity": ""}
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "S3Origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
      "AllowedMethods": {
        "Quantity": 2, "Items": ["HEAD","GET"],
        "CachedMethods": {"Quantity": 2, "Items": ["HEAD","GET"]}
      }
    },
    "DefaultRootObject": "index.html",
    "Enabled": true,
    "Comment": "California Housing Web App",
    "PriceClass": "PriceClass_100"
  }' \
  --query "Distribution.Id" --output text)

echo "Distribution ID: $DIST_ID"

# Lấy CloudFront domain
aws cloudfront get-distribution --id $DIST_ID \
  --query "Distribution.DomainName" --output text

# Chờ deploy xong
aws cloudfront wait distribution-deployed --id $DIST_ID
echo "CloudFront ready!"
```

---

## 8. Khối 7: Monitoring với CloudWatch

### 8.1 Tạo Alarm cho Endpoint Errors

#### 🖥️ Qua Console

1. **CloudWatch → Alarms → Create alarm**
2. Click **Select metric**
3. Tìm: **SageMaker → Endpoint Metrics by Endpoint Name**
4. Chọn: `california-housing-ep / AllTraffic / InvocationModelErrors`
5. Click **Select metric**
6. **Statistic**: Sum | **Period**: 5 minutes
7. **Threshold**: Greater/Equal `5`
8. Click **Next**
9. **Notification**: In alarm → SNS → `alifornia-housing-approval-topic`
10. **Alarm name**: `CaliforniaHousingEndpointErrors`
11. Click **Create alarm**

#### ⌨️ Qua CLI

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "CaliforniaHousingEndpointErrors" \
  --alarm-description "Alert khi endpoint co qua nhieu loi" \
  --metric-name InvocationModelErrors \
  --namespace AWS/SageMaker \
  --dimensions \
    Name=EndpointName,Value=california-housing-ep \
    Name=VariantName,Value=AllTraffic \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:678551739301:alifornia-housing-approval-topic" \
  --treat-missing-data notBreaching
```

### 8.2 Log Groups Quan Trọng

| Service | Log Group | Console path |
|---|---|---|
| Lambda | `/aws/lambda/california-housing-api-proxy` | Lambda → Monitor → View logs in CloudWatch |
| SageMaker Endpoint | `/aws/sagemaker/Endpoints/california-housing-ep` | CloudWatch → Log groups |
| CodeBuild | `/aws/codebuild/california-housing-mlops-build` | CodeBuild → Build history → View logs |
| Pipeline Steps | Tạo động mỗi execution | SageMaker → Pipelines → Executions → node → View logs |

---

## 9. Checklist Sản Xuất

### Bảo mật
- [ ] S3 data bucket: Block all public access ✅
- [ ] API Gateway: Thêm API key hoặc Cognito Authorizer
- [ ] CloudFront: Bật WAF (Web Application Firewall)
- [ ] Lambda: IAM role restricted minimum permissions

### Hiệu suất
- [ ] Serverless Endpoint: Xem xét `ProvisionedConcurrency` nếu cold start > 10s không chấp nhận được
- [ ] DynamoDB: Chuyển sang Provisioned nếu traffic ổn định
- [ ] CloudFront: Bật Gzip/Brotli compression

### Độ tin cậy
- [ ] CloudWatch Alarm cho endpoint errors ✅
- [ ] Lambda: Dead Letter Queue cho failed invocations
- [ ] Backup DynamoDB: Enable Point-in-time recovery

### Chi phí
- [ ] S3 Lifecycle: Archive model artifacts cũ > 90 ngày sang Glacier
- [ ] Tag tất cả resources: `Project=CaliforniaHousing`
- [ ] Bật AWS Budget Alert

---

## 10. Tóm Tắt Lỗi & Cách Khắc Phục

| # | Lỗi | Nguyên nhân | Giải pháp |
|---|-----|-------------|-----------|
| 1 | `SNS:Publish not authorized` trong CodePipeline | Role CodePipeline thiếu quyền SNS | Thêm inline policy `sns:Publish` vào CodePipeline role |
| 2 | `BinaryCondition type mismatch: String vs Float` | Dùng S3Uri trực tiếp trong ConditionStep | Dùng `JsonGet` + `PropertyFile` để extract float |
| 3 | `Network isolation not supported for Serverless` | Console tự bật `EnableNetworkIsolation=True` | Tạo Model qua CLI không có `--enable-network-isolation` |
| 4 | `UnexpectedParameter TrainingPlanArnEquals` | Bug UI AWS Console Create Model dialog | Chọn "Provide model artifacts + image" thay vì "Use model package" |
| 5 | Màn hình trắng trên S3 | `BrowserRouter` + Vite absolute paths | Đổi sang `HashRouter` + `base: './'` trong vite.config.js |
| 6 | S3 Objects hiển thị folder `dist/` | Upload cả folder thay vì nội dung | Upload files bên TRONG `dist/`, hoặc `aws s3 sync frontend/dist/ s3://bucket/` |
| 7 | `ERR_TIMED_OUT` S3 website URL | ISP Việt Nam block HTTP port 80 | Dùng CloudFront (HTTPS port 443) |
| 8 | Frontend gọi `http://localhost:8000` | URL hardcoded từ thời dev local | Sửa `client.js` + dùng env var `VITE_API_URL` |
| 9 | Lambda timeout 3 giây | Default timeout quá ngắn cho Serverless cold start | Tăng Lambda timeout lên 30 giây |
| 10 | Training chạy mỗi lần push code | CodePipeline trigger mọi push | Dùng `git tag v*` + `git describe --tags --exact-match` trong buildspec |

---

## Phụ Lục: Lệnh Kiểm Tra Nhanh

```bash
# Trạng thái endpoint
aws sagemaker describe-endpoint \
  --endpoint-name california-housing-ep \
  --query "{Status:EndpointStatus,Updated:LastModifiedTime}"

# Pipeline executions gần nhất
aws sagemaker list-pipeline-executions \
  --pipeline-name CaliforniaHousingMLOpsPipeline \
  --sort-by CreationTime --sort-order Descending --max-results 5 \
  --query "PipelineExecutionSummaries[*].{Status:PipelineExecutionStatus,Time:StartTime}"

# Model packages trong Registry
aws sagemaker list-model-packages \
  --model-package-group-name CaliforniaHousingPackageGroup \
  --query "ModelPackageSummaryList[*].{Ver:ModelPackageVersion,Status:ModelApprovalStatus}"

# Predictions gần nhất từ DynamoDB
aws dynamodb scan \
  --table-name CaliforniaHousingPredictions \
  --max-items 5 \
  --query "Items[*].{id:prediction_id.S,price:predicted_price.S,ts:timestamp.S}"

# CloudFront distributions
aws cloudfront list-distributions \
  --query "DistributionList.Items[*].{Id:Id,Domain:DomainName,Status:Status}"
```

### Dọn Dẹp Tài Nguyên

```bash
# ⚠️ CẢNH BÁO: Không thể hoàn tác!
aws sagemaker delete-endpoint --endpoint-name california-housing-ep
aws sagemaker delete-endpoint-config --endpoint-config-name california-housing-serverless-cfg
aws sagemaker delete-model --model-name california-housing-model-v1
aws lambda delete-function --function-name california-housing-api-proxy
aws apigatewayv2 delete-api --api-id 1modfu9v9k
aws dynamodb delete-table --table-name CaliforniaHousingPredictions
```

---

*Cập nhật: 09/09/2026 – v2.1 với đầy đủ Console UI + CLI cho mọi bước*
