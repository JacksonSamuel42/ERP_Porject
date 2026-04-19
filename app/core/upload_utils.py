import uuid
from typing import Optional

import aioboto3
from fastapi import UploadFile

from app.config import settings


class S3UploadUtils:
    @staticmethod
    async def get_s3_session():
        session = aioboto3.Session()
        return session.client(
            's3',
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )

    @staticmethod
    async def save_file(file: UploadFile, folder: str = 'logos') -> str:
        """
        Faz upload direto para o S3 e retorna a URL ou o Path.
        """
        extension = file.filename.split('.')[-1].lower()
        unique_filename = f'{folder}/{uuid.uuid4().hex}.{extension}'

        async with await S3UploadUtils.get_s3_session() as s3:
            content = await file.read()

            await s3.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=unique_filename,
                Body=content,
                ContentType=file.content_type,
            )

        return unique_filename

    @staticmethod
    async def generate_presigned_url(
        file_key: Optional[str], expires_in: int = 3600
    ) -> Optional[str]:
        """
        Gera uma URL temporária. Se não for imagem, força o download.
        """
        if not file_key:
            return None

        image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
        is_image = file_key.lower().endswith(image_extensions)

        async with await S3UploadUtils.get_s3_session() as s3:
            params = {'Bucket': settings.S3_BUCKET_NAME, 'Key': file_key}

            # Se NÃO for imagem, forçamos o "attachment" (download)
            if not is_image:
                filename = file_key.split('/')[-1]
                params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'

            return await s3.generate_presigned_url(
                'get_object', Params=params, ExpiresIn=expires_in
            )

    @staticmethod
    async def delete_file(file_key: str):
        """Remove o ficheiro do S3."""
        async with await S3UploadUtils.get_s3_session() as s3:
            try:
                await s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=file_key)
            except Exception:
                pass
