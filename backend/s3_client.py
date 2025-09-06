import boto3
from botocore.client import Config
from io import BytesIO


from .config import Settings


def get_s3_client(settings: Settings):

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )


def upload_file_to_s3(settings: Settings, file_obj, object_name: str):

    s3_client = get_s3_client(settings)
    s3_client.upload_fileobj(file_obj, settings.s3_bucket_name, object_name)


def delete_file_from_s3(settings: Settings, object_name: str):

    s3_client = get_s3_client(settings)
    s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=object_name)


def download_file_from_s3(settings: Settings, object_name: str) -> BytesIO | None:

    s3_client = get_s3_client(settings)

    try:
        file_stream = BytesIO()
        s3_client.download_fileobj(settings.s3_bucket_name, object_name, file_stream)
        file_stream.seek(0)
        return file_stream
    except Exception as e:
        print(f"Ошибка при скачивании {object_name}: {e}")
        return None


def create_presigned_url(
    settings: Settings, object_name: str, expiration: int = 3600
) -> str:

    public_s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_public_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )

    url = public_s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": object_name},
        ExpiresIn=expiration,
    )
    return url
