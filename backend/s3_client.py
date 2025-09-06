import boto3
from botocore.client import Config
from .config import get_settings

settings = get_settings()

s3_client = boto3.client(
    's3',
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    config=Config(signature_version='s3v4')
)


def upload_file_to_s3(file, obj_name):

    return s3_client.upload_fileobj(file, settings.s3_bucket_name, obj_name)


def create_presigned_url(obj_name, expiration=3600):

    s3_public_client = boto3.client(
        's3',
        endpoint_url=settings.s3_public_url, 
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version='s3v4')
    )

    
    url = s3_public_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.s3_bucket_name, 'Key': obj_name},
        ExpiresIn=expiration
    )
    
    return url


def delete_file_from_s3(obj_name: str):

    s3_client.delete_object(
        Bucket=settings.s3_bucket_name,
        Key=obj_name
    )