"""
azure/training/azure_job.py — Submit training job to Azure ML.

Submits app/training/train_all.py as an Azure ML command job.
Uses azure-ai-ml SDK v1.x with MLflow autologging.
Run this locally or from CI after Phase 5 data pipeline has been running.

Requirements:
    pip install azure-ai-ml azure-identity mlflow

Usage:
    python -m azure.training.azure_job
    python -m azure.training.azure_job --dry-run   (10% of data, for validation)
"""

from __future__ import annotations

import argparse
import logging
import os

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def submit_training_job(
    dry_run: bool = False,
    practice_areas: list[str] | None = None,
) -> str:
    """
    Submit Oracle ML training job to Azure ML.

    Args:
        dry_run:        Use 10% of data for validation runs.
        practice_areas: Optional list of practice areas for targeted retraining.
                        When provided, only those practice areas are retrained.
                        Used by Phase 12 Agent 035 to avoid full retrains.

    Returns:
        Azure ML job name.
    """
    try:
        from azure.ai.ml import MLClient, command
        from azure.ai.ml.entities import Environment, AmlCompute
        from azure.identity import DefaultAzureCredential
    except ImportError as e:
        raise RuntimeError(
            f"azure-ai-ml not installed: {e}. Run: pip install azure-ai-ml azure-identity"
        ) from e

    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    workspace_name = os.environ["AZURE_WORKSPACE_NAME"]
    compute_name = os.environ.get("AZURE_COMPUTE_NAME", "oracle-training-cluster")

    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )

    # Environment: Python 3.12 with all Oracle ML dependencies
    env = Environment(
        image="mcr.microsoft.com/azureml/openmpi4.1.0-cuda11.8-cudnn8-ubuntu22.04:latest",
        conda_file=None,
        pip_requirements=[
            "fastapi==0.115.0",
            "sqlalchemy[asyncio]==2.0.0",
            "asyncpg==0.29.0",
            "motor==3.4.0",
            "xgboost==2.0.3",
            "lightgbm==4.3.0",
            "optuna==3.6.1",
            "scikit-learn==1.4.2",
            "torch==2.3.0",
            "shap==0.45.0",
            "mlxtend==0.23.1",
            "networkx==3.3",
            "pandas==2.2.2",
            "numpy==1.26.4",
            "boto3==1.34.0",
            "joblib==1.4.2",
            "structlog==24.1.0",
        ],
        name="oracle-training-env",
        version="1.0",
    )

    dry_run_flag = "--dry-run" if dry_run else ""
    pa_flag = ""
    if practice_areas:
        pa_list = ",".join(practice_areas)
        pa_flag = f"--practice-areas {pa_list}"

    job = command(
        code="./",   # entire repo — .amlignore excludes frontend
        command=f"python -m app.training.train_all {dry_run_flag} {pa_flag}".strip(),
        environment=env,
        compute=compute_name,
        experiment_name="oracle-ml-training",
        display_name=f"oracle-training{'(dry-run)' if dry_run else ''}",
        environment_variables={
            "DATABASE_URL": "${{secrets.DATABASE_URL}}",
            "MONGODB_URL": "${{secrets.MONGODB_URL}}",
            "SPACES_KEY": "${{secrets.SPACES_KEY}}",
            "SPACES_SECRET": "${{secrets.SPACES_SECRET}}",
            "OUTPUT_DIR": "/tmp/oracle_models",
        },
        instance_count=1,
        distribution=None,
    )

    returned_job = ml_client.jobs.create_or_update(job)
    log.info("Submitted Azure ML job: %s", returned_job.name)
    log.info("Studio URL: %s", returned_job.studio_url)
    if practice_areas:
        log.info("Targeted retraining for practice areas: %s", practice_areas)
    return returned_job.name


def wait_for_completion(job_name: str) -> None:
    """Poll until Azure ML job completes."""
    try:
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential
        import time

        ml_client = MLClient(
            DefaultAzureCredential(),
            subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
            resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
            workspace_name=os.environ["AZURE_WORKSPACE_NAME"],
        )

        while True:
            job = ml_client.jobs.get(job_name)
            status = job.status
            log.info("Job %s status: %s", job_name, status)

            if status in ("Completed", "Failed", "Canceled"):
                if status != "Completed":
                    raise RuntimeError(f"Azure ML job {job_name} ended with status: {status}")
                return

            time.sleep(60)

    except ImportError:
        log.warning("azure-ai-ml not available — cannot poll job status")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--wait", action="store_true", help="Wait for job completion")
    parser.add_argument(
        "--practice-areas",
        type=str,
        default=None,
        help="Comma-separated list of practice areas for targeted retraining (Phase 12)",
    )
    args = parser.parse_args()

    pa_list = args.practice_areas.split(",") if args.practice_areas else None
    job_name = submit_training_job(dry_run=args.dry_run, practice_areas=pa_list)
    if args.wait:
        wait_for_completion(job_name)
