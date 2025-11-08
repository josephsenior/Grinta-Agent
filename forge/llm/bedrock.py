"""Helpers for discovering AWS Bedrock foundation models and sanitizing model lists."""

import boto3

from forge.core.logger import forge_logger as logger


def list_foundation_models(aws_region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> list[str]:
    """List available AWS Bedrock foundation models.
    
    Args:
        aws_region_name: AWS region
        aws_access_key_id: AWS access key
        aws_secret_access_key: AWS secret key
        
    Returns:
        List of model IDs prefixed with "bedrock/", empty on error

    """
    try:
        client = boto3.client(
            service_name="bedrock",
            region_name=aws_region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        foundation_models_list = client.list_foundation_models(byOutputModality="TEXT", byInferenceType="ON_DEMAND")
        model_summaries = foundation_models_list["modelSummaries"]
        return ["bedrock/" + model["modelId"] for model in model_summaries]
    except Exception as err:
        logger.warning(
            "%s. Please config AWS_REGION_NAME AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY if you want use bedrock model.",
            err,
        )
        return []


def remove_error_modelId(model_list: list[str]) -> list[str]:
    """Remove Bedrock models from model list (error handling fallback).
    
    Args:
        model_list: List of model IDs
        
    Returns:
        List with Bedrock models filtered out

    """
    return list(filter(lambda m: not m.startswith("bedrock"), model_list))
