# -*- coding: utf-8 -*-
"""
云存储模块：支持腾讯云 COS 和阿里云 OSS
"""

import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from config import COS_CONFIG

logger = logging.getLogger(__name__)


class CloudStorageBase:
    """云存储基类"""

    def upload_file(self, local_path: Path, cloud_path: str) -> bool:
        raise NotImplementedError

    def download_file(self, cloud_path: str, local_path: Path) -> bool:
        raise NotImplementedError

    def delete_file(self, cloud_path: str) -> bool:
        raise NotImplementedError

    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_file_url(self, cloud_path: str, expires: int = 3600) -> str:
        raise NotImplementedError

    def file_exists(self, cloud_path: str) -> bool:
        raise NotImplementedError


class TencentCOSStorage(CloudStorageBase):
    """腾讯云 COS 存储"""

    def __init__(self, config: Dict[str, Any]):
        self.secret_id = config.get("secret_id", "")
        self.secret_key = config.get("secret_key", "")
        self.region = config.get("region", "ap-guangzhou")
        self.bucket = config.get("bucket", "")
        self.prefix = config.get("prefix", "materials/")
        
        self._client = None

    def _get_client(self):
        """延迟初始化 COS 客户端"""
        if self._client is None:
            try:
                from qcloud_cos import CosConfig, CosS3Client
                
                if not self.secret_id or not self.secret_key:
                    raise ValueError("腾讯云 COS secret_id 和 secret_key 必须配置")
                if not self.bucket:
                    raise ValueError("腾讯云 COS bucket 必须配置")
                
                config = CosConfig(
                    Region=self.region,
                    SecretId=self.secret_id,
                    SecretKey=self.secret_key,
                )
                self._client = CosS3Client(config)
                logger.info(f"✅ 腾讯云 COS 客户端初始化成功，区域: {self.region}，Bucket: {self.bucket}")
            except ImportError:
                logger.warning("⚠️  未安装 qcloud_cos SDK，将使用模拟模式（仅本地存储）")
                self._client = None

    def upload_file(self, local_path: Path, cloud_path: str) -> bool:
        """上传文件到腾讯云 COS"""
        self._get_client()
        
        if self._client is None:
            # 模拟模式：仅返回成功，不做实际上传
            logger.warning(f"⚠️  模拟模式：跳过实际上传 {local_path} -> {cloud_path}")
            return True
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            self._client.put_object_from_local_file(
                Bucket=self.bucket,
                LocalFilePath=str(local_path),
                Key=full_cloud_path,
            )
            logger.info(f"✅ 文件上传成功：{local_path} -> cos://{self.bucket}/{full_cloud_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 文件上传失败：{e}")
            return False

    def download_file(self, cloud_path: str, local_path: Path) -> bool:
        """从腾讯云 COS 下载文件"""
        self._get_client()
        
        if self._client is None:
            logger.warning(f"⚠️  模拟模式：跳过下载 {cloud_path} -> {local_path}")
            return True
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._client.download_file(
                Bucket=self.bucket,
                Key=full_cloud_path,
                DestFilePath=str(local_path),
            )
            logger.info(f"✅ 文件下载成功：cos://{self.bucket}/{full_cloud_path} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 文件下载失败：{e}")
            return False

    def delete_file(self, cloud_path: str) -> bool:
        """删除腾讯云 COS 文件"""
        self._get_client()
        
        if self._client is None:
            logger.warning(f"⚠️  模拟模式：跳过删除 {cloud_path}")
            return True
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            self._client.delete_object(
                Bucket=self.bucket,
                Key=full_cloud_path,
            )
            logger.info(f"✅ 文件删除成功：cos://{self.bucket}/{full_cloud_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 文件删除失败：{e}")
            return False

    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出云端文件"""
        self._get_client()
        
        if self._client is None:
            return []
        
        try:
            search_prefix = f"{self.prefix}{prefix}" if prefix else self.prefix
            response = self._client.list_objects(
                Bucket=self.bucket,
                Prefix=search_prefix,
            )
            
            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    files.append({
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                        "etag": obj["ETag"],
                    })
            return files
        except Exception as e:
            logger.error(f"❌ 列出文件失败：{e}")
            return []

    def get_file_url(self, cloud_path: str, expires: int = 3600) -> str:
        """获取文件访问 URL（预签名链接）"""
        self._get_client()
        
        if self._client is None:
            return f"/uploads/{cloud_path}"
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            # 生成预签名 URL，有效期 1 小时
            url = self._client.get_presigned_download_url(
                Bucket=self.bucket,
                Key=full_cloud_path,
                Expired=expires,
            )
            return url
        except Exception as e:
            logger.error(f"❌ 生成预签名 URL 失败：{e}")
            return f"/uploads/{cloud_path}"

    def file_exists(self, cloud_path: str) -> bool:
        """检查文件是否存在"""
        self._get_client()
        
        if self._client is None:
            return False
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            self._client.head_object(
                Bucket=self.bucket,
                Key=full_cloud_path,
            )
            return True
        except Exception:
            return False


class AliyunOSSStorage(CloudStorageBase):
    """阿里云 OSS 存储"""

    def __init__(self, config: Dict[str, Any]):
        self.access_key_id = config.get("access_key_id", "")
        self.access_key_secret = config.get("access_key_secret", "")
        self.endpoint = config.get("endpoint", "oss-cn-hangzhou.aliyuncs.com")
        self.bucket = config.get("bucket", "")
        self.prefix = config.get("prefix", "materials/")
        
        self._client = None

    def _get_client(self):
        """延迟初始化 OSS 客户端"""
        if self._client is None:
            try:
                import oss2
                
                if not self.access_key_id or not self.access_key_secret:
                    raise ValueError("阿里云 OSS access_key_id 和 access_key_secret 必须配置")
                if not self.bucket:
                    raise ValueError("阿里云 OSS bucket 必须配置")
                
                auth = oss2.Auth(self.access_key_id, self.access_key_secret)
                self._client = oss2.Bucket(auth, self.endpoint, self.bucket)
                logger.info(f"✅ 阿里云 OSS 客户端初始化成功，端点: {self.endpoint}，Bucket: {self.bucket}")
            except ImportError:
                logger.warning("⚠️  未安装 oss2 SDK，将使用模拟模式（仅本地存储）")
                self._client = None

    def upload_file(self, local_path: Path, cloud_path: str) -> bool:
        """上传文件到阿里云 OSS"""
        self._get_client()
        
        if self._client is None:
            logger.warning(f"⚠️  模拟模式：跳过实际上传 {local_path} -> {cloud_path}")
            return True
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            result = self._client.put_object_from_file(
                key=full_cloud_path,
                filename=str(local_path),
            )
            if result.status == 200:
                logger.info(f"✅ 文件上传成功：{local_path} -> oss://{self.bucket}/{full_cloud_path}")
                return True
            else:
                logger.error(f"❌ 文件上传失败，状态码: {result.status}")
                return False
        except Exception as e:
            logger.error(f"❌ 文件上传失败：{e}")
            return False

    def download_file(self, cloud_path: str, local_path: Path) -> bool:
        """从阿里云 OSS 下载文件"""
        self._get_client()
        
        if self._client is None:
            logger.warning(f"⚠️  模拟模式：跳过下载 {cloud_path} -> {local_path}")
            return True
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            result = self._client.get_object_to_file(
                key=full_cloud_path,
                filename=str(local_path),
            )
            if result.status == 200:
                logger.info(f"✅ 文件下载成功：oss://{self.bucket}/{full_cloud_path} -> {local_path}")
                return True
            else:
                logger.error(f"❌ 文件下载失败，状态码: {result.status}")
                return False
        except Exception as e:
            logger.error(f"❌ 文件下载失败：{e}")
            return False

    def delete_file(self, cloud_path: str) -> bool:
        """删除阿里云 OSS 文件"""
        self._get_client()
        
        if self._client is None:
            logger.warning(f"⚠️  模拟模式：跳过删除 {cloud_path}")
            return True
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            result = self._client.delete_object(full_cloud_path)
            if result.status == 204:
                logger.info(f"✅ 文件删除成功：oss://{self.bucket}/{full_cloud_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 文件删除失败：{e}")
            return False

    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出云端文件"""
        self._get_client()
        
        if self._client is None:
            return []
        
        try:
            search_prefix = f"{self.prefix}{prefix}" if prefix else self.prefix
            files = []
            
            for obj in oss2.ObjectIterator(self._client, prefix=search_prefix):
                files.append({
                    "key": obj.key,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })
            return files
        except Exception as e:
            logger.error(f"❌ 列出文件失败：{e}")
            return []

    def get_file_url(self, cloud_path: str, expires: int = 3600) -> str:
        """获取文件访问 URL（预签名链接）"""
        self._get_client()
        
        if self._client is None:
            return f"/uploads/{cloud_path}"
        
        try:
            from datetime import timedelta
            full_cloud_path = f"{self.prefix}{cloud_path}"
            url = self._client.sign_url("GET", full_cloud_path, expires)
            return url
        except Exception as e:
            logger.error(f"❌ 生成预签名 URL 失败：{e}")
            return f"/uploads/{cloud_path}"

    def file_exists(self, cloud_path: str) -> bool:
        """检查文件是否存在"""
        self._get_client()
        
        if self._client is None:
            return False
        
        try:
            full_cloud_path = f"{self.prefix}{cloud_path}"
            return self._client.object_exists(full_cloud_path)
        except Exception:
            return False


class LocalStorage:
    """本地存储（用于测试或不启用云存储的场景）"""

    def __init__(self, uploads_dir: Path):
        self.uploads_dir = uploads_dir

    def upload_file(self, local_path: Path, cloud_path: str) -> bool:
        """本地存储：直接将文件移动到 uploads 目录"""
        try:
            target_path = self.uploads_dir / cloud_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果文件已存在，先删除
            if target_path.exists():
                target_path.unlink()
            
            # 复制文件到目标位置
            import shutil
            shutil.copy2(str(local_path), str(target_path))
            logger.info(f"✅ 文件已保存到本地：{target_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 本地文件保存失败：{e}")
            return False

    def download_file(self, cloud_path: str, local_path: Path) -> bool:
        """从本地下载"""
        try:
            source_path = self.uploads_dir / cloud_path
            if source_path.exists():
                local_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(str(source_path), str(local_path))
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 本地文件下载失败：{e}")
            return False

    def delete_file(self, cloud_path: str) -> bool:
        """删除本地文件"""
        try:
            file_path = self.uploads_dir / cloud_path
            if file_path.exists():
                file_path.unlink()
                logger.info(f"✅ 本地文件已删除：{file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 本地文件删除失败：{e}")
            return False

    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出本地文件"""
        try:
            search_path = self.uploads_dir / prefix if prefix else self.uploads_dir
            files = []
            if search_path.exists() and search_path.is_dir():
                for f in search_path.rglob("*"):
                    if f.is_file():
                        files.append({
                            "key": str(f.relative_to(self.uploads_dir)),
                            "size": f.stat().st_size,
                            "last_modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        })
            return files
        except Exception as e:
            logger.error(f"❌ 列出本地文件失败：{e}")
            return []

    def get_file_url(self, cloud_path: str, expires: int = 3600) -> str:
        """获取本地文件访问 URL"""
        return f"/uploads/{cloud_path}"

    def file_exists(self, cloud_path: str) -> bool:
        """检查本地文件是否存在"""
        return (self.uploads_dir / cloud_path).exists()


def get_storage() -> CloudStorageBase:
    """获取存储实例"""
    config = COS_CONFIG
    
    if not config.get("enabled", False):
        from config import UPLOADS_DIR
        logger.info("📁 使用本地存储模式")
        return LocalStorage(UPLOADS_DIR)
    
    provider = config.get("provider", "tencent")
    
    if provider == "tencent":
        logger.info("☁️  使用腾讯云 COS 存储")
        return TencentCOSStorage(config.get("tencent", {}))
    elif provider == "aliyun":
        logger.info("☁️  使用阿里云 OSS 存储")
        return AliyunOSSStorage(config.get("aliyun", {}))
    else:
        raise ValueError(f"不支持的云存储提供商：{provider}")


# 全局存储实例
_storage = None


def get_storage_instance() -> CloudStorageBase:
    """获取全局存储实例（单例）"""
    global _storage
    if _storage is None:
        _storage = get_storage()
    return _storage
