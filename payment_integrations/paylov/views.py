import base64
import uuid

from django.db import transaction as db_transaction
from django.shortcuts import redirect
from drf_yasg.utils import swagger_auto_schema
from payments import FraudStatus
from payments import PaymentStatus
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from payment_integrations.payment_model.models import UserBalanceHistory, PaymentMerchantRequestLog, Provider
from .authentication import CustomBasicAuthentication
from .provider import PaylovProvider
from .serializers import *
from .serializers import PaylovSerializer
from .utils import *
from .utils import PaylovMethods
User=get_user_model()

def redirect_to_mobile_app():
    deep_link_url = "ztyapp://org.uicgroup.zty"  # Mobil ilova uchun deep link URL
    return redirect(deep_link_url)


class PaylovWithCard(GenericAPIView):
    serializer_class = PaylovWithCardSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        # Quyidagi qo'shimcha amallarni bajarish uchun `validated_data` ni ishlatishingiz mumkin
        card_number = validated_data['cardNumber']
        expire_date = validated_data['expireDate']
        amount = validated_data['amount']

        with db_transaction.atomic():
            transaction = Transaction.objects.create(
                user=request.user,
                variant='paylov',
                status=PaymentStatus.WAITING,
                total=amount,
                currency='uzs',
            )
            transaction.save()

        response_data = KarmonPayClient().payment_without_registration(
            cardNumber=card_number,
            expireDate=expire_date,
            amount=amount,
            transaction_id=transaction.id,
            userid=request.user.id
        )

        if response_data and 'result' in response_data and response_data['result'] is not None and 'otpSentPhone' in \
                response_data['result']:
            with db_transaction.atomic():
                transaction.status = PaymentStatus.PREAUTH
                transaction.transaction_id = response_data['result']['transactionId']
                transaction.save()
            message = {
                'message_uz': 'SMS orqali kod yuborildi',
                'message_ru': 'Код был отправлен по СМС',
                'message_en': 'Code was sent by SMS'
            }
            return Response(
                {
                    'zty_response': {
                        'message': message,
                        'transaction_status': 'preauth',
                    },
                    'paylov_response': response_data
                }, status=201)
        else:
            with db_transaction.atomic():
                transaction.status = PaymentStatus.REJECTED
                transaction.fraud_status = FraudStatus.REJECT
                transaction.fraud_message = response_data
                transaction.transaction_id = f"fake--{uuid.uuid4().hex}"
                transaction.save()
            return Response({'zty_response': 'Invalid response data', 'paylov_response': response_data}, status=400)


class PaylovWithCardConfirm(CreateAPIView):
    serializer_class = PaylovWithCardConfirmSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            transaction = Transaction.objects.get(transaction_id=data['transactionId'])
            print("transaction:: ", transaction)
        except Transaction.DoesNotExist:
            return Response({'zty_response': 'Invalid transaction id'}, status=400)
        response_data = KarmonPayClient().payment_without_registration_confirm(
            transactionId=data['transactionId'],
            otp=data['otp'],
            is_hold=data['is_hold'],
        )
        print("response_data:: ", response_data)

        if (
                response_data
                and "result" in response_data
                and response_data["result"] is not None
                and response_data["result"]["transactionId"] == data["transactionId"]
                and response_data["error"] is None
        ):
            with db_transaction.atomic():
                transaction.status = PaymentStatus.CONFIRMED
                transaction.message = response_data
                transaction.save()
            user = User.objects.get(id=request.user.id)
            transaction = transaction
            print('-------------------------------\n\n\n')
            print('user:: ', user)
            print('transaction:: ', transaction)

            with db_transaction.atomic():
                ubh = UserBalanceHistory()
                ubh.amount = transaction.total
                ubh.user = user
                ubh.operation = 1
                ubh.prev_balance = user.amount
                ubh.new_balance = user.amount + float(transaction.total)
                ubh.transaction = transaction
                ubh.title = 'Paylov'
                ubh.save()
                user.amount = user.amount + float(transaction.total)
                user.save()
            return Response({'zty_response': 'transaction is confirmed', 'paylov_response': response_data},
                            status=201)  # You need to create an instance of Response here
        else:
            with db_transaction.atomic():
                transaction.status = PaymentStatus.REJECTED
                transaction.fraud_status = FraudStatus.REJECT
                transaction.fraud_message = response_data
                transaction.save()
            return Response({'zty_response': 'Invalid response data for confirm', 'paylov_response': response_data},
                            status=400)


class PaylovLink(GenericAPIView):
    serializer_class = PaylovLinkSerializer

    """
    amount  - amount of transaction
    """

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with db_transaction.atomic():
            transaction = Transaction.objects.create(
                variant='paylov',
                user=request.user,
                total=serializer.validated_data['amount'],
                status=PaymentStatus.WAITING,
                currency='uzs',
            )
            transaction_id = transaction.id
            transaction.save()
        amount = int(serializer.validated_data['amount'])
        merchant_id = settings.PROVIDERS["paylov"]["merchant_id"]
        query = (f"merchant_id={merchant_id}&amount={amount}&account.userid={request.user.id}"
                 f"&account.transaction_id={transaction.id}")
        encode_params = base64.b64encode(query.encode("utf-8"))
        encode_params = str(encode_params, "utf-8")
        base_link = "https://my.paylov.uz/checkout/create"
        url = f"{base_link}/{encode_params}"
        print(url)

        return Response(status=200, data={
            'url': url,
            'transaction_id': transaction.id,
            'amount': amount,
        })


class PaylovLinkStatus(GenericAPIView):
    serializer_class = PaylovLinkStatusSerializer
    queryset = Transaction.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        print(serializer.validated_data)
        transaction = Transaction.objects.get(id=serializer.validated_data['transaction_id'])
        if transaction.status == PaymentStatus.WAITING:
            return Response({'zty_response': 'transaction is waiting', 'status': 'in progress'}, status=400)
        if transaction.status == PaymentStatus.PREAUTH:
            return Response({'zty_response': 'transaction is preauth', 'status': 'in progress'}, status=400)
        if transaction.status == PaymentStatus.CONFIRMED:
            return Response({'zty_response': 'transaction is confirmed'''}, status=200)
        if transaction.status == PaymentStatus.REJECTED:
            return Response({'zty_response': 'transaction is rejcted'}, status=400)


################################################

class PaymentView(APIView):
    authentication_classes = [
        CustomBasicAuthentication.from_settings(
            settings.PROVIDERS["paylov"]["username"], settings.PROVIDERS["paylov"]["password"]
        )
    ]
    TYPE: str = ""
    PROVIDER: str = ""

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        PaymentMerchantRequestLog.objects.create(
            header=self.request.headers,
            body=self.request.data,
            method=self.request.method,
            type=self.TYPE,
            response=response.data,
            response_status_code=response.status_code,
            provider=self.PROVIDER,
        )
        return response


class PaylovAPIView(PaymentView):
    TYPE = ""
    PROVIDER = Provider.PAYLOV  # type: ignore

    def __init__(self):
        self.METHODS = {
            PaylovMethods.CHECK_TRANSACTION: self.check,
            PaylovMethods.PERFORM_TRANSACTION: self.perform,
        }
        self.params = None
        self.amount = None
        super(PaylovAPIView, self).__init__()

    @swagger_auto_schema(request_body=PaylovSerializer)
    def post(self, request, *args, **kwargs):
        serializer = PaylovSerializer(data=request.data, many=False)
        serializer.is_valid(raise_exception=True)
        method = serializer.validated_data["method"]
        self.params = serializer.validated_data["params"]
        self.TYPE = method

        print("method", method)
        print("self.params", self.params)

        with db_transaction.atomic():
            response_data = self.METHODS[method]()
            print("response_data", response_data)

        if isinstance(response_data, dict):
            response_data.update({"jsonrpc": "2.0", "id": request.data.get("id", None)})

        return Response(response_data)

    def check(self):
        error, code = PaylovProvider(self.params).check()
        if error:
            return dict(result=dict(status=code, statusText=PaylovProvider.ERROR_STATUS_TEXT))
        return dict(result=dict(status=code, statusText=PaylovProvider.SUCCESS_STATUS_TEXT))

    def perform(self):
        error, code = PaylovProvider(self.params).perform()
        # when order is not found
        if error and code == PaylovProvider.ORDER_NOT_FOUND:
            redirect_to_mobile_app()
            return dict(result=dict(status=code, statusText=PaylovProvider.ERROR_STATUS_TEXT))

        redirect_to_mobile_app()
        return dict(result=dict(status=code, statusText=PaylovProvider.SUCCESS_STATUS_TEXT))
