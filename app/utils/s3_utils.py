"""AWS S3 utilities para SkyPulse Phase 3.

Este módulo implementa configuración de S3 Bucket Keys según documentación AWS:
https://docs.aws.amazon.com/AmazonS3/latest/userguide/configuring-bucket-key-object.html
"""

import os
from typing import Dict, Any, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class S3BucketKeyManager:
    """Gestiona la configuración de S3 Bucket Keys para SkyPulse."""

    def __init__(self):
        """Inicializar el gestor de S3 Bucket Keys."""
        self.bucket_key_enabled = (
            os.getenv("AWS_S3_BUCKET_KEY_ENABLED", "true").lower() == "true"
        )
        self.encryption_key_id = os.getenv("AWS_S3_ENCRYPTION_KEY_ID", "alias/aws/s3")

        # Configuración de cliente S3 con optimización para Bucket Keys
        self.s3_config = Config(
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-west-2"),
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "adaptive"},
            max_pool_connections=50,  # Optimizado para múltiples requests
        )

        self.s3_client = self._initialize_s3_client()

    def _initialize_s3_client(self) -> Optional[boto3.client]:
        """Inicializar cliente S3 con soporte para Bucket Keys."""
        try:
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

            if aws_access_key and aws_secret_key:
                # Cliente con credenciales explícitas
                client = boto3.client(
                    "s3",
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    config=self.s3_config,
                )
                logger.info("Cliente S3 configurado con credenciales explícitas")
            else:
                # Cliente sin credenciales (acceso anónimo para Open Data)
                client = boto3.client("s3", config=self.s3_config)
                logger.info("Cliente S3 configurado para acceso anónimo (Open Data)")

            return client

        except Exception as e:
            logger.error(f"Error inicializando cliente S3: {e}")
            return None

    def get_bucket_key_headers(self) -> Dict[str, Any]:
        """
        Obtener headers para S3 Bucket Keys según documentación AWS.

        Returns:
            Diccionario con headers para S3 Bucket Keys
        """
        headers = {}

        if self.bucket_key_enabled and self.s3_client:
            # Header principal para habilitar Bucket Keys a nivel de objeto
            headers["x-amz-server-side-encryption-bucket-key-enabled"] = "true"

            # Si se necesita encriptación KMS adicional
            if self.encryption_key_id:
                headers.update(
                    {
                        "x-amz-server-side-encryption": "aws:kms",
                        "x-amz-server-side-encryption-aws-kms-key-id": self.encryption_key_id,
                    }
                )

            logger.debug("Headers S3 Bucket Keys configurados")

        return headers

    def put_object_with_bucket_key(
        self, bucket: str, key: str, body: Any, content_type: Optional[str] = None
    ) -> bool:
        """
        Subir objeto con S3 Bucket Keys habilitados.

        Args:
            bucket: Nombre del bucket S3
            key: Clave (ruta) del objeto
            body: Contenido del objeto
            content_type: Tipo de contenido (opcional)

        Returns:
            True si exitoso, False si hay error
        """
        if not self.s3_client:
            logger.error("Cliente S3 no disponible")
            return False

        try:
            # Preparar parámetros para PutObject con Bucket Keys
            put_params = {"Bucket": bucket, "Key": key, "Body": body}

            # Agregar headers de Bucket Keys
            bucket_key_headers = self.get_bucket_key_headers()
            put_params.update(bucket_key_headers)

            # Agregar content type si se proporciona
            if content_type:
                put_params["ContentType"] = content_type

            # Ejecutar PutObject con Bucket Keys
            response = self.s3_client.put_object(**put_params)

            logger.info(
                f"Objeto subido exitosamente con Bucket Keys: s3://{bucket}/{key}"
            )
            return True

        except ClientError as e:
            logger.error(f"Error subiendo objeto con Bucket Keys: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en put_object_with_bucket_key: {e}")
            return False

    def get_object_metadata(self, bucket: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Obtener metadata de objeto incluyendo estado de Bucket Keys.

        Args:
            bucket: Nombre del bucket S3
            key: Clave (ruta) del objeto

        Returns:
            Metadata del objeto o None si hay error
        """
        if not self.s3_client:
            logger.error("Cliente S3 no disponible")
            return None

        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=key)

            metadata = {
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "content_type": response.get("ContentType"),
                "etag": response.get("ETag"),
                "bucket_key_enabled": response.get(
                    "x-amz-server-side-encryption-bucket-key-enabled", "false"
                ),
                "encryption": response.get("x-amz-server-side-encryption", "None"),
                "storage_class": response.get("StorageClass", "STANDARD"),
            }

            logger.debug(f"Metadata obtenida para s3://{bucket}/{key}: {metadata}")
            return metadata

        except ClientError as e:
            logger.error(f"Error obteniendo metadata: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en get_object_metadata: {e}")
            return None

    def test_bucket_access(self, bucket: str) -> bool:
        """
        Probar acceso al bucket y verificar soporte para Bucket Keys.

        Args:
            bucket: Nombre del bucket a probar

        Returns:
            True si el acceso es exitoso, False si hay error
        """
        if not self.s3_client:
            logger.error("Cliente S3 no disponible para test de bucket")
            return False

        try:
            # Verificar si el bucket existe y es accesible
            self.s3_client.head_bucket(Bucket=bucket)
            logger.info(f"Acceso exitoso al bucket: {bucket}")

            # Verificar región del bucket
            location = self.s3_client.get_bucket_location(Bucket=bucket)
            bucket_region = location.get("LocationConstraint") or "us-east-1"
            logger.info(f"Bucket {bucket} en región: {bucket_region}")

            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.error(f"Bucket {bucket} no encontrado")
            elif error_code == "403":
                logger.error(f"Acceso denegado al bucket {bucket}")
            else:
                logger.error(f"Error accediendo bucket {bucket}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en test_bucket_access: {e}")
            return False


# Instancia global del gestor de S3 Bucket Keys
s3_bucket_manager = S3BucketKeyManager()
