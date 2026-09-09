import json
import base64
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any

import requests
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.serialization import pkcs12

from app.core.config import settings
from .constant import ResponseStatus, EncryptType
from app.core.logging import logger



# 自定义错误类
class CustomError(Exception):
    def __init__(self, txn_sta: str, message: str):
        self.txn_sta = txn_sta
        self.message = message
        super().__init__(f"Txn Sta: {txn_sta}, Message: {message}")


class CommonRsp:
    def __init__(self, data: Dict[str, Any]):
        self.access_mid: str = data.get("accessMid", "")
        self.version: str = data.get("version", "")
        self.sign_type: str = data.get("signType", "")
        self.sign: str = data.get("sign", "")
        self.encrypt_type: str = data.get("encryptType", "")
        self.encrypt_key: str = data.get("encryptKey", "")
        self.resp_code: str = data.get("respCode", "")
        self.resp_desc: str = data.get("respDesc", "")
        self.resp_time: str = data.get("respTime", "")
        self.biz_data: Any = data.get("bizData", None)


class SandPayClient:
    """
    杉德支付客户端基类
    """
    def __init__(self, config):
        """
        初始化杉德支付客户端
        :param config: 配置字典，应包含以下键：
                       - access_mid: 商户接入号
                       - cert_no: 证书序列号
                       - version: 版本号
                       - private_key: 商户私钥(私钥地址字符串或已加载的PrivateKey对象)
                       - sand_public_key: 杉德公钥(公钥地址字符串或已加载的PublicKey对象)
                       - private_key_password: 商户私钥密码(如果使用PFX证书)
        """
        self.config = config
        self.access_mid = config.get('access_mid')
        self.version = config.get('version')
        self.request_content = None
        self.url = None

        # 加载或设置私钥
        private_key = config.get('private_key')
        if isinstance(private_key, str):
            self.private_key = self._load_pfx_private_key(private_key, config.get('private_key_password'))
        else:
            self.private_key = private_key

        # 加载或设置杉德公钥
        sand_public_key = config.get('sand_public_key')
        if isinstance(sand_public_key, str):
            self.sand_public_key = self._load_cer_public_key(sand_public_key)
        else:
            self.sand_public_key = sand_public_key

    @staticmethod
    def _load_cer_public_key(cer_path: str) -> rsa.RSAPublicKey:
        # 加载CER公钥证书
        try:
            with open(cer_path, 'rb') as cer_file:
                cer_data = cer_file.read()

            # 假设是DER格式的证书（常见于.cer文件）
            # 如果是PEM格式，可以使用 x509.load_pem_x509_certificate
            certificate = x509.load_der_x509_certificate(cer_data)
            public_key = certificate.public_key()
            logger.debug("杉德公钥证书加载成功")

            return public_key
        except Exception as e:
            logger.error(f"加载CER公钥证书时出错: {e}")
            return None

    @staticmethod
    def _load_pfx_private_key(pfx_path: str, password: str) -> rsa.RSAPrivateKey:
        # 加载PFX私钥证书
        try:
            with open(pfx_path, 'rb') as pfx_file:
                pfx_data = pfx_file.read()

            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                pfx_data, password.encode('utf-8'), default_backend()
            )
            logger.debug("商户私钥证书加载成功")

            return private_key
        except Exception as e:
            logger.error(f"加载PFX私钥证书时出错: {e}")
            return None

    @staticmethod
    def _gen_random_string(length=16):
        """
        生成指定长度的随机字符串，包含大小写字母和数字
        :param length: 字符串长度，默认为16
        :return: 随机字符串
        """
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    @staticmethod
    def _aes_encrypt(content, aes_key):
        """
        使用AES算法加密内容 (AES/ECB/PKCS7Padding)
        :param content: 待加密的明文字符串
        :param aes_key: AES密钥字符串
        :return: Base64编码的加密结果
        """
        # 将内容和密钥转换为bytes
        content_bytes = content.encode('utf-8')
        key_bytes = aes_key.encode('utf-8')

        # 创建AES加密器，使用ECB模式
        cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
        encryptor = cipher.encryptor()

        # 应用PKCS7填充
        padder = sym_padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(content_bytes) + padder.finalize()

        # 加密并Base64编码
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(ciphertext).decode('utf-8')

    @staticmethod
    def _aes_decrypt(encrypted_data: str, aes_key: bytes) -> bytes:
        """AES解密"""
        key_bytes = aes_key

        # Base64解码密文
        ciphertext = base64.b64decode(encrypted_data.encode('utf-8'))

        # 创建AES解密器，使用ECB模式
        cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()

        # 解密数据
        decrypted_padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # 去除PKCS7填充
        unpadder = sym_padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

        return decrypted_data.decode('utf-8')

    @staticmethod
    def _rsa_encrypt(data, public_key):
        """
        使用RSA公钥加密数据 (RSA/ECB/PKCS1Padding)
        :param data: 待加密的字符串
        :param public_key: RSA公钥
        :return: Base64编码的加密结果
        """
        data_bytes = data.encode('utf-8')

        # 使用PKCS1v1.5填充进行RSA加密
        ciphertext = public_key.encrypt(
            data_bytes,
            padding.PKCS1v15()
        )
        return base64.b64encode(ciphertext).decode('utf-8')

    @staticmethod
    def _rsa_decrypt(encrypted_data: str, private_key) -> bytes:
        """RSA解密"""
        if isinstance(private_key, str):
            private_key = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend()
            )

        decrypted = private_key.decrypt(
            base64.decodebytes(encrypted_data.encode('utf-8')),
            padding.PKCS1v15()
        )
        return decrypted

    @staticmethod
    def _generate_sign(data, private_key):
        """
        使用SHA256WithRSA算法生成签名
        :param data: 待签名的数据字符串
        :param private_key: 商户私钥
        :return: Base64编码的签名
        """
        data_bytes = data.encode('utf-8')

        # 使用私钥创建签名
        signature = private_key.sign(
            data_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def _get_timestamp():
        """
        获取当前时间戳，格式为yyyyMMddHHmmss
        :return: 时间戳字符串
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def build_request(self, content, encrypt_type="AES"):
        """
        加密、签名接口请求报文并组装公共请求报文
        :param content: 接口请求报文明文
        :param encrypt_type: 加密方式，默认为"AES"
        :return: 组装好的公共请求报文（字典形式）
        :raises: ValueError 当参数不符合要求时
        """
        sign_type = "RSA"

        # 1. 参数校验
        if not content:
            raise ValueError("签名内容为空")
        if encrypt_type != "AES":
            raise ValueError(f"不支持的加密类型: {encrypt_type}")

        # 2. 生成16位随机AES密钥
        aes_key = self._gen_random_string(16)

        # 3. 使用AES加密请求报文明文
        biz_data = self._aes_encrypt(content, aes_key)

        # 4. 使用杉德公钥RSA加密AES密钥
        encrypt_key = self._rsa_encrypt(aes_key, self.sand_public_key)

        # 5. 使用商户私钥对加密后的报文体进行签名
        sign = self._generate_sign(biz_data, self.private_key)

        # 6. 组装公共请求报文
        common_request = {
            "accessMid": self.access_mid,
            "timestamp": self._get_timestamp(),
            "version": self.version,
            "signType": sign_type,
            "sign": sign,
            "encryptType": encrypt_type,
            "encryptKey": encrypt_key,
            "bizData": biz_data
        }

        return common_request

    def build_req_content(self, order_no: str, amount: float, extra_dict: dict=None):
        """
        构建请求报文
        :param order_no: 订单号
        :param amount: 金额
        :return: 请求报文
        """
        pass

    def call(self, order_no: str, amount: float, extra_dict: dict = None):
        """
        调用杉德支付接口
        :param order_no: 订单号
        :param amount: 金额
        :param extra_dict: 额外参数
        :return: 响应报文
        """
        try:
            # 1. 构建请求报文
            req_content = self.build_req_content(order_no, amount, extra_dict=extra_dict)
            req_content_str = json.dumps(req_content, ensure_ascii=False)
            request_data = self.build_request(
                req_content_str,
                "AES"
            )
            headers = {
                "Content-Type": "application/json"
            }

            # 2. 发送请求
            try:
                response = requests.post(self.url, json=request_data, headers=headers)
            except Exception as e:
                logger.error(f"HTTP请求异常: {e}")
                raise CustomError(ResponseStatus.PROCESS.value, f"通讯异常")
            # 处理响应
            if response.status_code != 200:
                raise CustomError(ResponseStatus.PROCESS.value, f"HTTP错误: {response.status_code}")
            # 3. 解析响应
            try:
                resp_bytes = response.json()
            except Exception as e:
                logger.error(f"响应数据解析错误: {e}")
                raise CustomError(ResponseStatus.PROCESS.value, "通道应答解析失败")
            resp_content = resp_bytes
            logger.debug(f"杉德支付响应报文: {resp_content}")
            resp_struct = CommonRsp(resp_content)
            logger.debug(f"杉德支付公共响应: {resp_struct.__dict__}")
            if resp_struct.resp_code != ResponseStatus.SUCCESS.value:
                raise CustomError(resp_struct.resp_code, resp_struct.resp_desc)
            # 验签
            if resp_struct.sign_type != EncryptType.RSA.value:
                raise CustomError(ResponseStatus.PROCESS.value, "签名方式异常")
            if not isinstance(resp_struct.biz_data, str):
                raise CustomError(ResponseStatus.PROCESS.value, "渠道应答报文异常")
            # 4. 验证签名
            if not self.verify_sign(resp_struct.biz_data, resp_struct.sign, resp_struct.sign_type, self.sand_public_key):
                raise ValueError("验签失败")
            if resp_struct.encrypt_type != EncryptType.AES.value:
                raise CustomError(ResponseStatus.PROCESS.value, "应答加密方式不支持")
            # 解密响应数据
            dec_key = self._rsa_decrypt(resp_struct.encrypt_key, self.private_key)
            resp_biz_data = self._aes_decrypt(resp_struct.biz_data, dec_key)

            # 解析业务响应
            rsp_dict = json.loads(resp_biz_data)

            return rsp_dict
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            raise CustomError(ResponseStatus.PROCESS.value, "通道应答解析失败")
        except Exception as e:
            if isinstance(e, CustomError):
                raise e
            logger.error(f"未知错误: {e}")
            raise CustomError(ResponseStatus.PROCESS.value, "渠道结果解析失败")

    @staticmethod
    def verify_sign(content: str, sign: str, sign_type: str, public_key: rsa.RSAPublicKey,
                    charset: str = 'utf-8') -> bool:
        """
        验证签名
        :param content: 响应报文bizData
        :param sign: 响应报文中的sign（Base64编码字符串）
        :param sign_type: 响应报文中的signType，例如"SHA256withRSA"
        :param public_key: 杉德公钥（RSAPublicKey对象）
        :param charset: 编码格式，默认为'utf-8'
        :return: boolean 验签是否成功
        :raises: ValueError, InvalidSignature 等异常
        """
        # 根据sign_type确定哈希算法
        if sign_type == "SHA256withRSA":
            hash_algorithm = hashes.SHA256()
        elif sign_type == "SHA1withRSA":
            hash_algorithm = hashes.SHA1()
        elif sign_type == 'RSA':
            hash_algorithm = hashes.SHA256()
        # 可根据需要添加其他算法，如MD5等
        else:
            raise ValueError(f"Unsupported signType: {sign_type}")

        # 将签名从Base64字符串解码为字节
        signature_bytes = base64.b64decode(sign)

        # 将内容字符串按指定字符集编码为字节
        if charset:
            content_bytes = content.encode(charset)
        else:
            content_bytes = content.encode('utf-8')  # 默认UTF-8

        try:
            # 使用公钥验证签名
            # 注意：这里使用PKCS1v1.5填充，这是Java标准Signature.getInstance(signType)的常见默认方式
            # 如果对方使用的是PSS填充，则需要使用padding.PSS
            public_key.verify(
                signature_bytes,
                content_bytes,
                padding.PKCS1v15(),
                hash_algorithm
                    )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            # 其他异常，如编码错误等，可以选择抛出或处理
            raise e


class AllTradeSandPayClient(SandPayClient):
    """
    全支付收银台客户端

    不支持PC网站端支付
    """
    def __init__(self, config):
        super().__init__(config)
        self.url = 'https://scfp-uat.sand.com.cn/gateway/trade'

    def build_req_content(self, order_id, amount, extra_dict: dict = None):
        """
        构建交易请求报文
        :param order_id: 订单号
        :param amount: 订单金额
        :return: 交易请求内容
        """
        extra_dict = extra_dict or dict()
        description = extra_dict.get("description", "皮皮虾短剧") if extra_dict else "皮皮虾短剧"
        content = dict(
            mid=self.access_mid,
            outOrderNo=order_id,
            description=description,
            goodsClass="99",
            amount=amount,
            funcCodeList=[
                # '02030001',
                # '02040001',
                '02020005'],
            payerInfo=dict(
                payExtra=[
                    # dict(funcCode="02030001"),
                    # dict(funcCode="02040001"),
                    dict(funcCode="02020005"),
                ],
                frontUrl=settings.CALLBACK_BASE_URL,
            ),
            timeOut=(datetime.now() + timedelta(seconds=settings.PAY_TIME_OUT)).strftime("%Y%m%d%H%M%S"),
            notifyUrl=settings.SANDPAY_RECHARGE_CALLBACK_URL,
            riskmgtInfo=dict(
                sourceIp=settings.PAY_SOURCE_IP,
            ),
            sdCashierType="PC",
            metaOption='[{"s":"Android","n":"","id":"","sc":""},{"s":"IOS","n":"","id":"","sc":""}]',

        )

        self.request_content = content
        logger.debug(f"杉德支付请求内容体: {content}")

        return content


class AliQrcodeSandPayClient(SandPayClient):
    def __init__(self, config):
        super().__init__(config)
        self.url = 'https://openapi-uat01.sand.com.cn/v4/sd-payment/api/trans/trans.payment.order.create'

    def build_req_content(self, order_id, amount, extra_dict: dict = None):
        """
        构建交易请求报文
        :param order_id: 订单号
        :param amount: 订单金额
        :return: 交易请求内容
        """
        extra_dict = extra_dict or dict()
        description = extra_dict.get("description", "皮皮虾短剧") if extra_dict else "皮皮虾短剧"
        content = dict(
            outReqTime=datetime.now().strftime("%Y%m%d%H%M%S"),
            mid=self.access_mid,
            outOrderNo=order_id,
            description=description,
            goodsClass="99",
            amount=amount,
            payType="ALIPAY",
            payMode="QR",
            timeOut=(datetime.now() + timedelta(seconds=settings.PAY_TIME_OUT)).strftime("%Y%m%d%H%M%S"),
            notifyUrl=settings.SANDPAY_RECHARGE_CALLBACK_URL,
            riskmgtInfo=dict(
                sourceIp=settings.PAY_SOURCE_IP,
            ),
        )
        self.request_content = content

        logger.debug(f"杉德支付请求内容体: {content}")
        return content


class TencentQrcodeSandPayClient(SandPayClient):
    def __init__(self, config):
        super().__init__(config)
        self.url = 'https://openapi-uat01.sand.com.cn/v4/sd-receipts/api/trans/trans.order.create'

    def build_req_content(self, order_id, amount, extra_dict: dict = None):
        """
        构建交易请求报文
        :param order_id: 订单号
        :param amount: 订单金额
        :return: 交易请求内容
        """
        extra_dict = extra_dict or dict()
        description = extra_dict.get("description", "皮皮虾短剧") if extra_dict else "皮皮虾短剧"
        content = dict(
            marketProduct="QZF",
            outReqTime=datetime.now().strftime("%Y%m%d%H%M%S"),
            mid=self.access_mid,
            outOrderNo=order_id,
            description=description,
            goodsClass="99",
            amount=amount,
            payType="WXPAY",
            payMode="QR",
            timeOut=(datetime.now() + timedelta(seconds=settings.PAY_TIME_OUT)).strftime("%Y%m%d%H%M%S"),
            notifyUrl=settings.SANDPAY_RECHARGE_CALLBACK_URL,
            riskmgtInfo=dict(
                sourceIp=settings.PAY_SOURCE_IP,
            ),
            payerInfo=dict(),
        )
        self.request_content = content

        logger.debug(f"杉德支付请求内容体: {content}")
        return content


class CupQrcodeSandPayClient(SandPayClient):
    def __init__(self, config):
        super().__init__(config)
        self.url = settings.SANDPAY_CUP_QRCODE_URL

    def build_req_content(self, order_id, amount, extra_dict: dict = None):
        """
        构建交易请求报文
        :param order_id: 订单号
        :param amount: 订单金额
        :return: 交易请求内容
        """
        extra_dict = extra_dict or dict()
        description = extra_dict.get("description", "皮皮虾短剧") if extra_dict else "皮皮虾短剧"
        notify_url = extra_dict.get("notify_url", settings.SANDPAY_RECHARGE_CALLBACK_URL)
        content = dict(
            marketProduct="CSDB",
            outReqTime=datetime.now().strftime("%Y%m%d%H%M%S"),
            mid=self.access_mid,
            outOrderNo=order_id,
            description=description,
            goodsClass="99",
            amount=amount,
            payType="CUPPAY",
            payMode="QR",
            payerInfo=dict(),
            timeOut=(datetime.now() + timedelta(seconds=settings.PAY_TIME_OUT)).strftime("%Y%m%d%H%M%S"),
            notifyUrl=notify_url,
            riskmgtInfo=dict(
                sourceIp=settings.PAY_SOURCE_IP,
            ),
        )
        self.request_content = content

        logger.debug(f"杉德支付请求内容体: {content}")
        return content


class PaymentSandPayClient(SandPayClient):
    def __init__(self, config):
        super().__init__(config)
        self.url = 'https://openapi-uat01.sand.com.cn/v4/sd-payment/api/trans/trans.payment.order.create'

    def build_req_content(self, order_no: str, amount: float, extra_dict: dict = None):
        """
        构建交易请求报文
        :param order_no: 订单号
        :param amount: 订单金额
        :return: 交易请求内容
        """
        extra_dict = extra_dict or dict()
        description = extra_dict.get("description", "皮皮虾短剧-提取") if extra_dict else "皮皮虾短剧-提取"
        payeeInfo = dict(
            accType=extra_dict['acc_type'],
            accNo=extra_dict['acc_number'],
            accName=extra_dict['acc_name'],
        )
        if extra_dict['acc_type'] == 'corp_acc':
            payeeInfo['branchCode'] = extra_dict['branch_code']
        if extra_dict.get('phone'):
            payeeInfo['phone'] = extra_dict['phone']

        content = dict(
            mid=self.access_mid,
            outOrderNo=order_no,
            amount=amount,
            payeeInfo=payeeInfo,
            payerInfo=dict(
                sdaccSubId='payment'
            ),
            remark=description,
        )
        self.request_content = content

        logger.debug(f"杉德支付请求内容体: {content}")

        return content


class QueryPaymentStatusSandPayClient(SandPayClient):
    def __init__(self, config):
        super().__init__(config)
        self.url = settings.SANDPAY_PAYMENT_QUERY_URL

    def build_req_content(self, order_no: str, amount: float = None, extra_dict: dict = None):
        """
        构建查询付款状态请求报文
        :param order_no: 订单号
        :param out_req_time: 请求时间(格式: %Y%m%d)
        :return: 查询付款状态请求内容
        """
        extra_dict = extra_dict or dict()
        content = dict(
            mid=self.access_mid,
            outReqDate=extra_dict['out_req_date'],
            outOrderNo=order_no,
        )
        self.request_content = content

        logger.debug(f"杉德支付请求内容体: {content}")

        return content


class QueryQrCodeStatusSandPayClient(SandPayClient):
    def __init__(self, config):
        super().__init__(config)
        self.url = settings.SANDPAY_QRCODE_QUERY_URL

    def build_req_content(self, order_no: str, amount: float = None, extra_dict: dict = None):
        """
        构建查询二维码状态请求报文
        :param order_no: 订单号
        :param amount: 订单金额
        :return: 查询二维码状态请求内容
        """
        extra_dict = extra_dict or dict()
        content = dict(
            marketProduct="CSDB",
            mid=self.access_mid,
            outReqTime=datetime.now().strftime("%Y%m%d%H%M%S"),
            outOrderNo=order_no,
        )
        self.request_content = content

        logger.debug(f"杉德支付请求内容体: {content}")

        return content
