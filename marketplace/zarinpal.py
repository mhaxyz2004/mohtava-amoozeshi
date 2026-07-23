import requests
from django.conf import settings

def initiate_zarinpal_payment(order_id, amount, description):
    """شروع پرداخت درگاه زرین‌پال"""
    
    data = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "amount": int(amount) * 10,  # تبدیل به ریال
        "description": description,
        "metadata": [
            {"key": "order_id", "value": str(order_id)}
        ],
        "callback_url": f"{settings.SITE_URL}/payment/verify/"
    }
    
    try:
        response = requests.post(settings.ZARINPAL_API_URL, json=data)
        result = response.json()
        
        if result.get('data', {}).get('authority'):
            return {
                'success': True,
                'authority': result['data']['authority'],
                'url': f"https://www.zarinpal.com/pg/StartPay/{result['data']['authority']}"
            }
        return {'success': False, 'error': 'خطا در اتصال به زرین‌پال'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def verify_zarinpal_payment(authority, amount):
    """تأیید پرداخت درگاه زرین‌پال"""
    
    data = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "authority": authority,
        "amount": int(amount) * 10
    }
    
    try:
        response = requests.post(settings.ZARINPAL_VERIFY_URL, json=data)
        result = response.json()
        
        if result.get('data', {}).get('code') in [100, 101]:
            return {
                'success': True,
                'ref_id': result['data'].get('ref_id')
            }
        return {'success': False, 'error': 'تأیید ناموفق'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
