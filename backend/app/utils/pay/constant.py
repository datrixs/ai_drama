from enum import Enum


class ResponseStatus(Enum):
    SUCCESS = "success"
    FAIL = "fail"
    PROCESS = "process"
    ACCEPT = "accept"
    REJECT = "reject"
    UNPAID = "unpaid"
    PAID = "paid"


class EncryptType(Enum):
    AES = "AES"
    RSA = "RSA"
