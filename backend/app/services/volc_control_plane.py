"""
火山引擎管控面服务

使用 HMAC-SHA256 (AWS SigV4 风格) 签名调用火山引擎 OpenAPI
"""
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote, urlencode

import httpx
from loguru import logger

from app.core.config import settings
from app.enums.user import UserRegion

VOLC_OPENAPI_HOST = "open.volcengineapi.com"
VOLC_REGION = "cn-beijing"
VOLC_SERVICE = "ark"
VOLC_VERSION = "2024-01-01"

# 国际版（BytePlus）
VOLC_OVERSEA_HOST = "ark.ap-southeast-1.byteplusapi.com"
VOLC_OVERSEA_REGION = "ap-southeast-1"
VOLC_OVERSEA_SERVICE = "ark"


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class VolcControlPlane:
    """火山引擎管控面服务（方舟管控面 OpenAPI）

    支持国内（火山引擎）与国际版（BytePlus）两套 endpoint。
    region 取值：
      - UserRegion.DOMESTIC（默认）：火山引擎 open.volcengineapi.com / cn-beijing
      - UserRegion.OVERSEAS：BytePlus ark.ap-southeast-1.byteplusapi.com / ap-southeast-1
    """

    def __init__(self, region: str = UserRegion.DOMESTIC):
        self.region_type = region
        if region == UserRegion.OVERSEAS:
            self.access_key = settings.VOLC_OVERSEA_ACCESSKEY
            self.secret_key = settings.VOLC_OVERSEA_SECRETKEY
            self.host = VOLC_OVERSEA_HOST
            self.region = VOLC_OVERSEA_REGION
            self.service = VOLC_OVERSEA_SERVICE
        else:
            self.access_key = settings.VOLC_ACCESSKEY
            self.secret_key = settings.VOLC_SECRETKEY
            self.host = VOLC_OPENAPI_HOST
            self.region = VOLC_REGION
            self.service = VOLC_SERVICE

    # 不参与签名的 headers
    _UNSIGNED_HEADERS = frozenset({
        "authorization", "content-type", "content-length",
        "user-agent", "presigned-expires", "expect",
    })

    def _sign(self, method: str, query_params: dict, headers: dict, body: str) -> dict:
        """HMAC-SHA256 签名（AWS SigV4 风格）"""
        now = datetime.now(timezone.utc)
        date_stamp = now.strftime("%Y%m%d")
        datetime_stamp = now.strftime("%Y%m%dT%H%M%SZ")

        headers["X-Date"] = datetime_stamp
        headers["Host"] = self.host
        headers["X-Content-Sha256"] = _sha256_hex(body)

        # Canonical query string
        sorted_query = sorted(query_params.items())
        canonical_querystring = "&".join(
            f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in sorted_query
        )

        # Canonical headers — 排除不签名的 headers
        signable = {k: v for k, v in headers.items() if k.lower() not in self._UNSIGNED_HEADERS}
        signed_header_keys = sorted(signable.keys(), key=str.lower)
        canonical_headers = ""
        for k in signed_header_keys:
            canonical_headers += f"{k.lower()}:{signable[k].strip()}\n"
        signed_headers_str = ";".join(k.lower() for k in signed_header_keys)

        # Canonical request
        canonical_request = "\n".join([
            method,
            "/",
            canonical_querystring,
            canonical_headers,
            signed_headers_str,
            _sha256_hex(body),
        ])

        # String to sign
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/request"
        string_to_sign = "\n".join([
            "HMAC-SHA256",
            datetime_stamp,
            credential_scope,
            _sha256_hex(canonical_request),
        ])

        # Signing key
        k_date = _hmac_sha256(self.secret_key.encode("utf-8"), date_stamp)
        k_region = _hmac_sha256(k_date, self.region)
        k_service = _hmac_sha256(k_region, self.service)
        k_signing = _hmac_sha256(k_service, "request")

        # Signature
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization = (
            f"HMAC-SHA256 Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers_str}, Signature={signature}"
        )
        headers["Authorization"] = authorization

        return headers

    def _request(self, action: str, body: dict = None, version: str = None) -> dict:
        """发送火山引擎管控面请求"""
        url = f"https://{self.host}/"
        query_params = {
            "Action": action,
            "Version": version or VOLC_VERSION,
        }
        body_str = json.dumps(body, ensure_ascii=False) if body else ""
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        headers = self._sign("POST", query_params, headers, body_str)

        is_overseas = self.region_type == UserRegion.OVERSEAS
        if is_overseas:
            # 国际版联调用：把实际发送的完整请求参数转 JSON 完整打印
            request_payload = {
                "method": "POST",
                "url": url,
                "query": query_params,
                "headers": headers,
                "body": body,
            }
            logger.info(
                f"[BytePlus] {action} 请求: {json.dumps(request_payload, ensure_ascii=False)}"
            )
        else:
            logger.debug(f"[volc] {action} REQUEST body={body_str[:300]}")

        with httpx.Client(timeout=120) as client:
            resp = client.post(url, params=query_params, content=body_str.encode("utf-8"), headers=headers)
            if resp.status_code >= 400:
                logger.error(
                    f"[{'BytePlus' if is_overseas else 'volc'}] {action} HTTP {resp.status_code}: {resp.text}"
                )
                # 解析响应体里的火山 API 错误（Code/Message），抛带具体原因的异常
                # 否则 raise_for_status 只会得到 "Client error '400 Bad Request'" 这种无信息文本
                api_err = self._extract_api_error(resp)
                if api_err:
                    raise ValueError(f"火山 API 错误: {api_err}")
                resp.raise_for_status()
            result = resp.json()

        if is_overseas:
            # 国际版联调用：把完整响应转 JSON 完整打印
            response_payload = {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body": result,
            }
            logger.info(
                f"[BytePlus] {action} 响应: {json.dumps(response_payload, ensure_ascii=False)}"
            )
        else:
            logger.debug(f"[volc] {action} RESPONSE: {json.dumps(result, ensure_ascii=False)[:500]}")

        # 检查 API 错误（HTTP 200 但业务层报错的情况）
        err = result.get("ResponseMetadata", {}).get("Error")
        if err:
            raise ValueError(f"火山 API 错误: {err.get('Code', '')} - {err.get('Message', '')}")

        return result

    @staticmethod
    def _extract_api_error(resp: httpx.Response) -> Optional[str]:
        """从火山响应里提取 ResponseMetadata.Error 的 Code - Message 文本。
        解析失败时返回 None，由调用方回退到 raise_for_status。
        """
        try:
            body = resp.json()
        except Exception:
            return None
        err = (body or {}).get("ResponseMetadata", {}).get("Error")
        if not err:
            return None
        code = err.get("Code", "")
        message = err.get("Message", "")
        return f"{code} - {message}".strip(" -")

    def create_asset_group(self, name: str) -> str:
        """创建资产组"""
        result = self._request("CreateAssetGroup", body={"Name": name})

        # 从多种可能的响应字段提取 group_id
        group_id = ""
        for path in [
            lambda r: r.get("Result", {}).get("GroupId"),
            lambda r: r.get("Result", {}).get("Id"),
            lambda r: r.get("Result", {}).get("AssetGroupId"),
            lambda r: r.get("GroupId"),
            lambda r: r.get("Id"),
        ]:
            group_id = path(result)
            if group_id:
                break

        if not group_id:
            logger.warning(f"创建资产组响应中未找到 GroupId: {json.dumps(result)[:500]}")
            raise ValueError(f"创建资产组成功但未返回 GroupId")

        logger.info(f"创建火山资产组成功: name={name}, group_id={group_id}")
        return group_id

    def create_asset(self, group_id: str, image_url: str, display_name: str = "", asset_type: str = "Image") -> str:
        """创建素材（支持 Image/Video/Audio）"""
        body = {
            "GroupId": group_id,
            "AssetType": asset_type,
            "Name": display_name,
            "URL": image_url,
        }
        # 国际版（BytePlus）需显式跳过内容审核
        if self.region_type == UserRegion.OVERSEAS:
            body["Moderation"] = {"Strategy": "Skip"}
        result = self._request("CreateAsset", body=body)

        # 从多种可能的响应字段提取 asset_id
        asset_id = ""
        for path in [
            lambda r: r.get("Result", {}).get("Id"),
            lambda r: r.get("Result", {}).get("AssetId"),
            lambda r: r.get("AssetId"),
            lambda r: r.get("Id"),
        ]:
            asset_id = path(result)
            if asset_id:
                break

        if not asset_id:
            logger.warning(f"创建素材响应中未找到 AssetId: {json.dumps(result)[:500]}")
            raise ValueError(f"创建素材成功但未返回 AssetId")

        logger.info(f"创建火山素材成功: display_name={display_name}, asset_id={asset_id}")
        return asset_id

    def sync_project_assets(self, project_id: str, group_id: str, assets: list[dict]) -> list[dict]:
        """批量同步项目资产到火山私域"""
        results = []
        for asset in assets:
            try:
                volc_id = self.create_asset(
                    group_id=group_id,
                    image_url=asset["image_url"],
                    display_name=asset.get("display_name", ""),
                )
                results.append({
                    "asset_id": asset["asset_id"],
                    "volc_private_asset_id": volc_id,
                    "status": "success",
                })
                time.sleep(0.5)
            except Exception as e:
                results.append({
                    "asset_id": asset["asset_id"],
                    "volc_private_asset_id": None,
                    "status": "failed",
                    "error": str(e),
                })
                logger.warning(f"同步资产失败: asset_id={asset['asset_id']}, error={e}")

        logger.info(f"批量同步完成: project_id={project_id}, success={sum(1 for r in results if r['status']=='success')}/{len(results)}")
        return results
