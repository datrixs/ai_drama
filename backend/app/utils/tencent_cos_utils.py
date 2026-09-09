"""
腾讯对象存储服务工具类
https://cloud.tencent.com/document/product/436/11365
"""
import datetime
import io
import uuid
from typing import List, Optional, Union

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError, CosClientError

from app.core.config import settings


class TencentCosApi:
    client = None

    def __new__(cls, *args, **kwargs):
        if not cls.client:
            cls.client = object.__new__(cls)
        return cls.client

    def __init__(self, bucket_name=settings.TENCENT_COS_BUCKET, domain=settings.TENCENT_COS_DOMAIN):
        self.secret_id = settings.TENCENT_COS_SECRET_ID
        self.secret_key = settings.TENCENT_COS_SECRET_KEY
        self.region = settings.TENCENT_COS_REGION
        self.bucket = bucket_name
        self.domain = domain
        
        # 初始化配置
        config = CosConfig(
            Region=self.region,
            SecretId=self.secret_id,
            SecretKey=self.secret_key,
            Scheme='https'
        )
        self.client = CosS3Client(config)

    def generate_unique_key(
        self, category: str, biz: str, user_id: str, ext: str = "jpg"
    ) -> str:
        date_path = datetime.datetime.now().strftime("%Y%m%d")
        timestamp = int(datetime.datetime.now().timestamp())
        unique_id = uuid.uuid4().hex[:8]
        return f"{category}/{date_path}/{biz}-{user_id}-{timestamp}-{unique_id}.{ext}"


    def exists_bucket(self, bucket_name: str) -> bool:
        """
        判断桶是否存在
        :param bucket_name: 桶名称
        :return: bool
        """
        try:
            self.client.head_bucket(Bucket=bucket_name)
            return True
        except CosServiceError as e:
            return False

    def create_bucket(self, bucket_name: str, is_public: bool = True) -> bool:
        """
        创建桶
        :param bucket_name: 桶名
        :param is_public: 是否公开访问
        :return: bool
        """
        try:
            if self.exists_bucket(bucket_name=bucket_name):
                return False
            
            # 创建桶
            self.client.create_bucket(Bucket=bucket_name)
            
            # 如果设置为公开访问，设置桶策略
            if is_public:
                policy = {
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"qcs": ["*"]},
                            "Action": ["name/cos:GetObject"],
                            "Resource": [f"qcs::cos:{self.region}:uid/*:{bucket_name}/*"]
                        }
                    ],
                    "Version": "2.0"
                }
                self.client.put_bucket_policy(Bucket=bucket_name, Policy=policy)
            
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False

    def get_bucket_list(self) -> List[dict]:
        """
        列出存储桶
        :return: List[dict]
        """
        try:
            response = self.client.list_buckets()
            bucket_list = []
            for bucket in response.get('Buckets', {}).get('Bucket', []):
                bucket_list.append({
                    "bucket_name": bucket['Name'],
                    "create_time": bucket['CreationDate']
                })
            return bucket_list
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return []

    def remove_bucket(self, bucket_name: str) -> bool:
        """
        删除桶
        :param bucket_name: 桶名
        :return: bool
        """
        try:
            self.client.delete_bucket(Bucket=bucket_name)
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False

    def bucket_list_files(self, bucket_name: str, prefix: str = None, max_keys: int = 1000) -> List[str]:
        """
        列出存储桶中所有对象
        :param bucket_name: 桶名
        :param prefix: 前缀
        :param max_keys: 最大返回数量
        :return: List[str]
        """
        file_name_list = []
        try:
            kwargs = {
                'Bucket': bucket_name,
                'MaxKeys': max_keys
            }
            if prefix:
                kwargs['Prefix'] = prefix
            
            response = self.client.list_objects(**kwargs)
            
            for obj in response.get('Contents', []):
                file_name_list.append(obj['Key'])
                print(
                    obj['Key'],
                    obj['LastModified'],
                    obj['ETag'],
                    obj['Size'],
                    obj.get('StorageClass', 'STANDARD')
                )
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
        return file_name_list

    def download_file(self, bucket_name: str, file_key: str, file_path: str) -> bool:
        """
        从bucket下载文件到本地
        :param bucket_name: 桶名
        :param file_key: 文件键
        :param file_path: 本地文件路径
        :return: bool
        """
        try:
            response = self.client.get_object(Bucket=bucket_name, Key=file_key)
            # 循环读取整个流，避免 SDK 单次 read 只返回首个 chunk 导致截断
            body = response['Body']
            with open(file_path, 'wb') as fp:
                while True:
                    chunk = body.read(8192)
                    if not chunk:
                        break
                    fp.write(chunk)
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False

    def download_as_bytes(self, bucket_name: str, file_key: str) -> bytes | None:
        """
        从bucket下载文件内容为 bytes
        :param bucket_name: 桶名
        :param file_key: 文件键
        :return: bytes or None
        """
        try:
            response = self.client.get_object(Bucket=bucket_name, Key=file_key)
            # 循环读取整个流，避免 SDK 单次 read 只返回首个 chunk 导致截断
            body = response['Body']
            chunks: list[bytes] = []
            while True:
                chunk = body.read(8192)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return None

    def download_object_as_bytes(self, file_key: str) -> bytes | None:
        """使用默认桶下载文件内容为 bytes"""
        return self.download_as_bytes(self.bucket, file_key)

    def fget_file(self, bucket_name: str, file_key: str, file_path: str) -> bool:
        """
        下载文件保存到本地（腾讯云COS没有fget_object方法，使用download_file实现）
        :param bucket_name: 桶名
        :param file_key: 文件键
        :param file_path: 本地文件路径
        :return: bool
        """
        return self.download_file(bucket_name, file_key, file_path)

    def copy_file(self, bucket_name: str, source_key: str, dest_key: str) -> bool:
        """
        拷贝文件
        :param bucket_name: 桶名
        :param source_key: 源文件键
        :param dest_key: 目标文件键
        :return: bool
        """
        try:
            copy_source = {
                'Bucket': bucket_name,
                'Key': source_key
            }
            self.client.copy_object(
                Bucket=bucket_name,
                Key=dest_key,
                CopySource=copy_source
            )
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False

    def upload_file(self, bucket_name: str, file_key: str, file_path: Union[str, bytes, io.BytesIO], 
                   content_type: str = "image/jpeg") -> bool:
        """
        上传文件
        :param bucket_name: 桶名
        :param file_key: 文件键
        :param file_path: 本地文件路径或bytes或BytesIO
        :param content_type: 文件类型
        :return: bool
        """
        try:
            if isinstance(file_path, str):
                # 本地文件路径
                with open(file_path, 'rb') as fp:
                    file_data = fp.read()
            elif isinstance(file_path, bytes):
                # bytes数据
                file_data = file_path
            elif isinstance(file_path, io.BytesIO):
                # BytesIO对象
                file_data = file_path.getvalue()
            else:
                raise ValueError("不支持的file_path类型")
            
            self.client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=file_data,
                ContentType=content_type
            )
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False

    def upload_object(self, file_data: Union[str, bytes, io.BytesIO], file_key: str,
                      content_type: str = "image/jpeg") -> bool:
        return self.upload_file(self.bucket, file_key, file_data, content_type=content_type)

    def fput_file(self, bucket_name: str, file_key: str, file_path: str) -> bool:
        """
        上传本地文件
        :param bucket_name: 桶名
        :param file_key: 文件键
        :param file_path: 本地文件路径
        :return: bool
        """
        return self.upload_file(bucket_name, file_key, file_path)

    def stat_object(self, bucket_name: str, file_key: str) -> Optional[dict]:
        """
        获取文件元数据
        :param bucket_name: 桶名
        :param file_key: 文件键
        :return: dict or None
        """
        try:
            response = self.client.head_object(Bucket=bucket_name, Key=file_key)
            print(f"文件键: {file_key}")
            print(f"最后修改时间: {response.get('LastModified')}")
            print(f"ETag: {response.get('ETag')}")
            print(f"文件大小: {response.get('Content-Length')}")
            print(f"内容类型: {response.get('Content-Type')}")
            print(f"存储类型: {response.get('x-cos-storage-class', 'STANDARD')}")
            return response
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return None

    def remove_file(self, bucket_name: str, file_key: str) -> bool:
        """
        移除单个文件
        :param bucket_name: 桶名
        :param file_key: 文件键
        :return: bool
        """
        try:
            self.client.delete_object(Bucket=bucket_name, Key=file_key)
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False

    def remove_files(self, bucket_name: str, file_keys: List[str]) -> bool:
        """
        删除多个文件
        :param bucket_name: 桶名
        :param file_keys: 文件键列表
        :return: bool
        """
        try:
            objects = [{'Key': key} for key in file_keys]
            self.client.delete_objects(
                Bucket=bucket_name,
                Delete={'Object': objects}
            )
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False

    def presigned_get_file(self, bucket_name: str, file_key: str, days: int = 7) -> Optional[str]:
        """
        生成一个http GET操作的预签名URL
        :param bucket_name: 桶名
        :param file_key: 文件键
        :param days: 有效期天数
        :return: str or None
        """
        try:
            url = self.client.get_presigned_download_url(
                Bucket=bucket_name,
                Key=file_key,
                Expired=days * 24 * 3600
            )
            return url
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return None

    def get_file_url(self, bucket_name: str, file_key: str) -> str:
        """
        获取文件的访问URL
        :param bucket_name: 桶名
        :param file_key: 文件键
        :return: str
        """
        if self.domain:
            # return f"https://{self.domain}/{file_key}"
            return f"{self.domain}/{file_key}"
        else:
            return f"https://{bucket_name}.cos.{self.region}.myqcloud.com/{file_key}"

    def get_bucket_lifecycle(self, bucket_name: str) -> Optional[dict]:
        """
        获取桶生命周期配置
        :param bucket_name: 桶名
        :return: dict or None
        """
        try:
            response = self.client.get_bucket_lifecycle(Bucket=bucket_name)
            return response
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return None

    def set_bucket_expiry_day(self, bucket_name: str, days: int) -> bool:
        """
        设置桶生命周期规则（文件过期天数）
        :param bucket_name: 桶名
        :param days: 过期天数
        :return: bool
        """
        try:
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'expire_rule',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'Expiration': {'Days': days}
                    }
                ]
            }
            self.client.put_bucket_lifecycle(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False

    def delete_bucket_lifecycle(self, bucket_name: str) -> bool:
        """
        删除桶生命周期配置
        :param bucket_name: 桶名
        :return: bool
        """
        try:
            self.client.delete_bucket_lifecycle(Bucket=bucket_name)
            return True
        except (CosServiceError, CosClientError) as e:
            print(f"[error]: {e}")
            return False
            
    def generate_presigned_put_url(
        self,
        key: str,
        content_type: str = "image/jpeg",
        expires: int = 600,
    ) -> str:
        """生成预签名 PUT URL，供前端直传 COS"""
        return self.client.get_presigned_url(
            Method="PUT",
            Bucket=self.bucket,
            Key=key,
            Expired=expires,
            Headers={"Content-Type": content_type},
        )

    def get_signed_url(self, key: str, expires: int = 7200) -> str:
        return self.client.get_presigned_url(
            Method="GET",
            Bucket=self.bucket,
            Key=key,
            Expired=expires,
        )

    def key_to_url(self, key: str) -> str:
        return self.get_signed_url(key)

    def get_permanent_url(self, key: str) -> str:
        """获取永久访问 URL（key + domain，不含签名参数）"""
        return self.get_file_url(self.bucket, key)

    def url_to_key(self, url_or_key: str | None) -> str | None:
        """将 COS URL（永久或带签名）转为 key。非 http 输入视为已是 key 原样返回。"""
        if not url_or_key:
            return None
        if not url_or_key.startswith("http"):
            return url_or_key
        from urllib.parse import urlparse
        parsed = urlparse(url_or_key)
        key = parsed.path.lstrip("/")
        return key if key else url_or_key

    def presigned_url_to_key(self, url_or_key: str | None) -> str | None:
        """兼容旧调用，等价于 url_to_key"""
        return self.url_to_key(url_or_key)

    def _is_cos_url(self, url: str | None) -> bool:
        """判断 URL 是否属于当前配置的 COS 域名"""
        if not url or not url.startswith("http") or not self.domain:
            return False
        domain_clean = self.domain.replace("https://", "").replace("http://", "").rstrip("/")
        return domain_clean in url

    def to_signed(self, url_or_key: str | None, allow_external: bool = False) -> str | None:
        """将永久 URL 或 COS key 转为签名 URL(用于响应给前端展示)

        Args:
            url_or_key: COS 永久 URL / 签名 URL / key
            allow_external: True 时,如果 URL 不属于 COS 域名(如第三方在线 URL),
                            原样返回不签名。用于 is_local_upload=False 的场景。

        - key: 直接签名
        - COS 签名/永久 URL: 提取 key 后(重新)签名
        - 外部 URL 且 allow_external=True: 原样返回
        - 外部 URL 且 allow_external=False: 尽力提取 path 当 key 签名(旧行为)
        """
        if not url_or_key:
            return url_or_key
        if not url_or_key.startswith("http"):
            return self.get_signed_url(url_or_key)
        if allow_external and not self._is_cos_url(url_or_key):
            return url_or_key
        key = self.url_to_key(url_or_key)
        if key and key != url_or_key:
            return self.get_signed_url(key)
        return url_or_key

    def to_permanent(self, url_or_key: str | None) -> str | None:
        """将签名 URL 转为永久 URL(用于存储到数据库,去掉签名参数)

        非签名 URL(永久/key)原样返回(已是永久形式)。
        """
        if not url_or_key:
            return url_or_key
        key = self.url_to_key(url_or_key)
        if key and key != url_or_key:
            return self.get_permanent_url(key)
        return url_or_key

    def sign_urls_in_json(self, data, keys=("url", "image_url", "thumbnail_url", "cover_url")):
        """递归把 JSON 中指定 key 的永久 COS URL 转签名 URL（2h TTL）

        数据库中存永久 URL（无签名），返回前端 / WS 推送前需追加临时签名参数。
        Asset:// 资产引用、外部 URL（非 COS）、空值原样保留。
        """
        if isinstance(data, dict):
            out = {}
            for k, v in data.items():
                if k in keys and isinstance(v, str) and v:
                    if v.startswith("Asset://") or not v.startswith("http"):
                        out[k] = v
                    else:
                        out[k] = self.to_signed(v, allow_external=True) or v
                else:
                    out[k] = self.sign_urls_in_json(v, keys)
            return out
        if isinstance(data, list):
            return [self.sign_urls_in_json(x, keys) for x in data]
        return data

cos_client = TencentCosApi()
