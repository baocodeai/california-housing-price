import argparse
import os
import boto3
import sagemaker
from sagemaker.model import Model
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn.estimator import SKLearn
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.parameters import ParameterFloat, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

def get_pipeline(
    role: str,
    default_bucket: str,
    pipeline_name: str = "CaliforniaHousingMLOpsPipeline",
    model_package_group_name: str = "CaliforniaHousingPackageGroup",
    base_job_prefix: str = "california-housing"
) -> Pipeline:
    """Định nghĩa toàn bộ đồ thị DAG của SageMaker AI Pipeline."""
    sagemaker_session = sagemaker.Session()

    # 1. Pipeline Parameters
    r2_threshold = ParameterFloat(name="R2Threshold", default_value=0.80)
    input_data_uri = ParameterString(
        name="InputDataUrl",
        default_value=f"s3://{default_bucket}/raw/housing.csv"
    )

    # 2. Step 1: Preprocessing Step
    sklearn_processor = SKLearnProcessor(
        framework_version="1.2-1",
        instance_type="ml.t3.medium",
        instance_count=1,
        base_job_name=f"{base_job_prefix}-prep",
        role=role,
        sagemaker_session=sagemaker_session
    )

    step_process = ProcessingStep(
        name="DataPreprocessing",
        processor=sklearn_processor,
        inputs=[
            ProcessingInput(
                source=input_data_uri,
                destination="/opt/ml/processing/input"
            )
        ],
        outputs=[
            ProcessingOutput(
                output_name="preprocessed_data",
                source="/opt/ml/processing/output"
            )
        ],
        code="aws_sagemaker/steps/preprocessing.py"
    )

    # 3. Step 2: Training Step (Stacking Regressor)
    sklearn_estimator = SKLearn(
        entry_point="train.py",
        source_dir="aws_sagemaker/steps",
        framework_version="1.2-1",
        instance_type="ml.m5.xlarge",
        instance_count=1,
        role=role,
        sagemaker_session=sagemaker_session,
        base_job_name=f"{base_job_prefix}-train",
        hyperparameters={
            "n-estimators": 100,
            "max-depth": 15
        }
    )

    step_train = TrainingStep(
        name="ModelTraining",
        estimator=sklearn_estimator,
        inputs={
            "train": step_process.properties.ProcessingOutputConfig.Outputs[
                "preprocessed_data"
            ].S3Output.S3Uri
        }
    )

    # 4. Step 3: Evaluation Step
    eval_report = PropertyFile(
        name="EvaluationReport",
        output_name="evaluation",
        path="evaluation.json"
    )

    step_eval = ProcessingStep(
        name="ModelEvaluation",
        processor=sklearn_processor,
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model"
            ),
            ProcessingInput(
                source=step_process.properties.ProcessingOutputConfig.Outputs[
                    "preprocessed_data"
                ].S3Output.S3Uri,
                destination="/opt/ml/processing/test"
            )
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                source="/opt/ml/processing/evaluation"
            )
        ],
        code="aws_sagemaker/steps/evaluate.py",
        property_files=[eval_report]
    )

    # 5. Step 4: Model Registration & Condition Step
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
        name=pipeline_name,
        parameters=[r2_threshold, input_data_uri],
        steps=[step_process, step_train, step_eval, step_cond],
        sagemaker_session=sagemaker_session
    )

    return pipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-arn", type=str, required=True, help="SageMaker Execution Role ARN")
    parser.add_argument("--bucket", type=str, required=True, help="S3 bucket name")
    parser.add_argument("--pipeline-name", type=str, default="CaliforniaHousingMLOpsPipeline")
    parser.add_argument("--execute", action="store_true", help="Start execution after upsert")
    args = parser.parse_args()

    print(f"Creating / Updating SageMaker Pipeline '{args.pipeline_name}'...")
    pipeline = get_pipeline(
        role=args.role_arn,
        default_bucket=args.bucket,
        pipeline_name=args.pipeline_name
    )

    pipeline.upsert(role_arn=args.role_arn)
    print("Pipeline upserted successfully!")

    if args.execute:
        print("Triggering pipeline execution...")
        execution = pipeline.start()
        print(f"Execution started! ARN: {execution.arn}")
        print("You can now open SageMaker Studio -> Pipelines to watch it run in real time!")
