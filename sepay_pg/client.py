# -*- coding: utf-8 -*-
# SDK Cổng thanh toán SePay (client.py)
# Hỗ trợ ký số hóa đơn Checkout, xác thực IPN/Webhook và gọi các API truy vấn của SePay.

import hmac
import hashlib
import base64
import requests
from typing import Dict, Any, Optional

class SePayClient:
    """SePay Payment Gateway SDK Client for Python"""

    def __init__(self, merchant_id: str, secret_key: str, env: str = "production"):
        """
        Khởi tạo Client kết nối SePay
        :param merchant_id: ID Merchant được cấp bởi SePay
        :param secret_key: Secret Key bảo mật được cấp bởi SePay
        :param env: Môi trường hoạt động ('sandbox' hoặc 'production')
        """
        self.merchant_id = merchant_id
        self.secret_key = secret_key
        self.env = env.lower().strip()

        # Cấu hình API URLs
        if self.env == "sandbox":
            self.api_url = "https://pgapi-sandbox.sepay.vn"
            self.checkout_url = "https://pay-sandbox.sepay.vn/v1/checkout/init"
        else:
            self.api_url = "https://pgapi.sepay.vn"
            self.checkout_url = "https://pay.sepay.vn/v1/checkout/init"

    def sign_fields(self, fields: Dict[str, Any]) -> str:
        """
        Sinh chữ ký số bảo mật (signature) từ các tham số đơn hàng theo chuẩn hóa của SePay
        :param fields: Từ điển chứa các thông tin đơn hàng cần ký
        :return: Chuỗi mã hóa Base64 của chữ ký số
        """
        # Thứ tự bắt buộc các trường cần ký theo tài liệu API của SePay
        signed_keys = [
            'merchant', 'operation', 'payment_method', 'order_amount', 'currency',
            'order_invoice_number', 'order_description', 'customer_id',
            'success_url', 'error_url', 'cancel_url'
        ]

        signed_pairs = []
        for key in signed_keys:
            if key in fields and fields[key] is not None:
                signed_pairs.append(f"{key}={fields[key]}")

        # Nối các trường lại bằng dấu phẩy
        raw_string = ",".join(signed_pairs)

        # Tạo chữ ký HMAC-SHA256
        hmac_digest = hmac.new(
            self.secret_key.encode("utf-8"),
            raw_string.encode("utf-8"),
            hashlib.sha256
        ).digest()

        # Mã hóa Base64 kết quả băm
        return base64.b64encode(hmac_digest).decode("utf-8")

    def generate_checkout_data(self, order_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Chuẩn bị đầy đủ các trường dữ liệu để submit Form Checkout gửi lên SePay
        :param order_data: Từ điển chứa thông tin đơn hàng (order_amount, success_url,...)
        :return: Từ điển đã điền merchant_id và chữ ký bảo mật signature hợp lệ
        """
        fields = {
            'merchant': self.merchant_id,
            'currency': order_data.get('currency', 'VND'),
            'order_amount': str(order_data.get('order_amount', 0)),
            'operation': order_data.get('operation', 'PURCHASE'),
            'payment_method': order_data.get('payment_method', 'BANK_TRANSFER'),
            'order_description': order_data.get('order_description', ''),
            'order_invoice_number': order_data.get('order_invoice_number', ''),
            'customer_id': order_data.get('customer_id', ''),
            'success_url': order_data.get('success_url', ''),
            'error_url': order_data.get('error_url', ''),
            'cancel_url': order_data.get('cancel_url', ''),
        }

        # Bổ sung các trường tùy chọn/dữ liệu mở rộng khác nếu có
        for k, v in order_data.items():
            if k not in fields and v is not None:
                fields[k] = str(v)

        # Tính toán chữ ký số bảo mật
        fields['signature'] = self.sign_fields(fields)
        return fields

    def verify_webhook_signature(self, signature_header: str, raw_payload: bytes) -> bool:
        """
        Xác minh tính đúng đắn của chữ ký gửi kèm Webhook IPN từ SePay
        :param signature_header: Chuỗi chữ ký nhận được trong Header yêu cầu (ví dụ: x-sepay-signature)
        :param raw_payload: Payload JSON thô dưới dạng byte nhận từ Webhook
        :return: True nếu chữ ký hợp lệ, ngược lại là False
        """
        try:
            expected = hmac.new(
                self.secret_key.encode("utf-8"),
                raw_payload,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature_header)
        except Exception:
            return False

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Truy vấn thông tin chi tiết một đơn hàng trên cổng SePay (Gọi API)
        :param order_id: ID đơn hàng của SePay hoặc ID hóa đơn của bạn
        :return: Từ điển JSON trả về từ API SePay
        """
        url = f"{self.api_url}/v1/orders/{order_id}"
        response = requests.get(
            url,
            auth=(self.merchant_id, self.secret_key)
        )
        response.raise_for_status()
        return response.json()

    def get_transactions(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Truy vấn danh sách lịch sử các giao dịch thanh toán chuyển khoản nhận được (Gọi API)
        :param filters: Từ điển lọc kết quả (Ví dụ: limit, offset, transaction_date,...)
        :return: Danh sách giao dịch từ API SePay
        """
        url = f"{self.api_url}/v1/transactions"
        response = requests.get(
            url,
            params=filters,
            auth=(self.merchant_id, self.secret_key)
        )
        response.raise_for_status()
        return response.json()
