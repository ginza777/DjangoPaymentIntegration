import requests
# import settings
from django.conf import settings

from payment_integrations.payment_model.models import Transaction

class PaylovMethods:
    CHECK_TRANSACTION = "transaction.check"
    PERFORM_TRANSACTION = "transaction.perform"

    @classmethod
    def choices(cls):
        return (
            (cls.CHECK_TRANSACTION, cls.CHECK_TRANSACTION),
            (cls.PERFORM_TRANSACTION, cls.PERFORM_TRANSACTION),
        )


class KarmonPayClient:
    payment_without_registration_url = "https://gw.paylov.uz/merchant/paymentWithoutRegistration/"
    confirm_payment_url = "https://gw.paylov.uz/merchant/confirmPayment/"

    # for Merchant
    ORDER_NOT_FOUND = "303"
    ORDER_ALREADY_PAID = "201"
    INVALID_AMOUNT = "5"
    SERVER_ERROR = "3"
    SUCCESS = "0"

    SUCCESS_STATUS_TEXT = "OK"
    ERROR_STATUS_TEXT = "ERROR"

    def __init__(self, params: dict = None):
        self.headers = {"api-key":settings.PROVIDERS["paylov"]["api_key"]}
        # for merchant
        self.params = params
        self.code = self.SUCCESS
        self.error = False

    def payment_without_registration(self, **kwargs) -> (bool, dict):
        payload = {
            'cardNumber': kwargs.get('cardNumber'),
            'expireDate': kwargs.get('expireDate'),
            'amount': kwargs.get('amount'),
            'account': {
                'transaction_id': kwargs.get('transaction_id'),
                'userid': kwargs.get('userid')
            }

        }
        response = requests.post(self.payment_without_registration_url, headers=self.headers, json=payload)
        print("\n\n\nresponse : ", response.json())
        return response.json()

    def payment_without_registration_confirm(self, **kwargs):
        payload = {
            'transactionId': kwargs.get('transactionId'),
            'otp': kwargs.get('otp'),
            'is_hold': kwargs.get('is_hold'),
        }
        response = requests.post(self.confirm_payment_url, headers=self.headers, json=payload)
        print("\n\n\nresponse : ", response.json())
        return response.json()
