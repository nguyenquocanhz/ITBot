# SePay Payment Gateway SDK for Python

Official Python library for integrating [SePay Payment Gateway](https://sepay.vn).

## Installation

Install using pip:

```bash
pip install sepay-pg
```

## Quick Start

### Initialize Client

```python
from sepay_pg import SePayClient

sepay = SePayClient(
    merchant_id="YOUR_MERCHANT_ID",
    secret_key="YOUR_MERCHANT_SECRET_KEY",
    env="sandbox" # or "production"
)
```

### Generate Checkout Parameters

```python
order_data = {
    'order_invoice_number': 'INV-123456',
    'order_amount': 100000, # 100,000 VND
    'order_description': 'Test payment description',
    'success_url': 'https://yourwebsite.com/payment/success',
    'error_url': 'https://yourwebsite.com/payment/error',
    'cancel_url': 'https://yourwebsite.com/payment/cancel'
}

checkout_fields = sepay.generate_checkout_data(order_data)

# Resulting dictionary contains all required fields including merchant and signature:
# print(checkout_fields['signature'])
```

### Verify Webhook IPN Signature

```python
# Verify signature header from SePay webhook post request
is_valid = sepay.verify_webhook_signature(
    signature_header=request.headers.get('x-sepay-signature'),
    raw_payload=request.data # raw request body bytes
)
```

### API Queries

```python
# Get order details
order = sepay.get_order("INV-123456")

# Get transactions history
transactions = sepay.get_transactions({"limit": 10})
```

## License

This project is licensed under the MIT License.
