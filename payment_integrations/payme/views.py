import base64
import uuid
from django.utils import timezone

from django.db import transaction
from django.db import transaction as db_transaction
from drf_yasg.utils import swagger_auto_schema
from payments import PaymentStatus as TransactionStatus
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
# Create your views here.
from rest_framework.views import APIView

from payment_integrations.payment_model.models import PaymentMerchantRequestLog, Provider,Transaction
from .serializers import PaymeSerializer
from .utils import PaymeMethods
from core import settings
from . import serializers
from .auth import AUTH_ERROR, authentication
from .provider import PaymeProvider

# for payment log
class PaymentView(APIView):
    TYPE: str = ""
    PROVIDER: str = ""

    @transaction.non_atomic_requests
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


# for payme link
class PaymeLinkAPIView(PaymentView):
    permission_classes = [AllowAny]
    http_method_names = ["post"]
    serializer_class = serializers.PaymeLinkSerializer

    @swagger_auto_schema(request_body=serializers.PaymeLinkSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.transaction_amount = serializer.validated_data["amount"]
        self.provider = Provider.PAYME

        with db_transaction.atomic():
            transaction = Transaction.objects.create(
                variant=Provider.PAYME,
                user=request.user,
                total=self.transaction_amount,
                status=TransactionStatus.WAITING,
                currency='uzs',

            )
            transaction.transaction_id = str(transaction.id)
            transaction.save()

        callback = settings.PROVIDERS["payme"]["callback_url"]
        merchant_id = settings.PROVIDERS["payme"]["merchant_id"]

        params = f"m={merchant_id};ac.order_id={transaction.id};a={self.transaction_amount * 100};c={callback}"
        encode_params = base64.b64encode(params.encode("utf-8"))
        encode_params = str(encode_params, "utf-8")
        payment_url = f"{settings.PROVIDERS[self.provider]['callback_url']}/{encode_params}"

        return Response(dict(result=dict(url=payment_url)))


class PaymeAPIView(PaymentView):
    permission_classes = [AllowAny]
    http_method_names = ["post"]
    authentication_classes = []  # type: ignore
    TYPE = ""
    PROVIDER = Provider.PAYME  # type: ignore

    def __init__(self):
        self.METHODS = {
            PaymeMethods.CHECK_PERFORM_TRANSACTION: self.check_perform_transaction,
            PaymeMethods.CREATE_TRANSACTION: self.create_transaction,
            PaymeMethods.PERFORM_TRANSACTION: self.perform_transaction,
            PaymeMethods.CHECK_TRANSACTION: self.check_transaction,
            PaymeMethods.CANCEL_TRANSACTION: self.cancel_transaction,
        }
        self.params = None
        super(PaymeAPIView, self).__init__()

    @swagger_auto_schema(request_body=PaymeSerializer)
    def post(self, request, *args, **kwargs):
        check = authentication(request)

        if check is False or not check:
            return Response(AUTH_ERROR)

        serializer = PaymeSerializer(data=request.data, many=False)
        serializer.is_valid(raise_exception=True)

        method = serializer.validated_data["method"]
        self.params = serializer.validated_data["params"]
        self.TYPE = method

        with db_transaction.atomic():
            response_data = self.METHODS[method]()

        return Response(response_data)

    def check_perform_transaction(self):

        error, error_message, code = PaymeProvider(self.params).check_perform_transaction()
        if error:
            print(error)
            print(error_message)
            print(code)

            return dict(
                error=dict(
                    code=code,
                    message=error_message,
                    data="transaction not found"
                ))

        user_id = Transaction.objects.get(id=self.params["account"]["order_id"]).user_id

        return dict(
            result=dict(allow=True),
            additional=dict(user_id=user_id)
        )

    def create_transaction(self):
        error, error_message, code = PaymeProvider(self.params).create_transaction()

        # when order is not found
        if error and code == PaymeProvider.ORDER_NOT_FOUND:
            print("order not found view")
            return dict(error=dict(code=code, message=error_message))

        transaction = Transaction.objects.get(
            id=self.params["account"]["order_id"],
            transaction_id=self.params["id"],
            status=TransactionStatus.PREAUTH
        )

        print("transaction  mavjud:", transaction.id, transaction.status)

        if not transaction:
            return dict(error=dict(code=code, message=error_message))

        # when order found and transaction created but error occurred
        if error:
            print("error view")
            transaction.status = TransactionStatus.REJECTED
            transaction.save()
            return dict(error=dict(code=code, message=error_message))

        return dict(
            result=dict(
                create_time=int(transaction.created_at.timestamp() * 1000),
                transaction=transaction.transaction_id,
                state=PaymeProvider.CREATE_TRANSACTION,
            )
        )

    def perform_transaction(self):
        print(100 * '-')
        error, error_message, code = PaymeProvider(self.params).perform_transaction()
        # when order is not found
        if error and (code == PaymeProvider.ORDER_NOT_FOUND or code == PaymeProvider.TRANSACTION_NOT_FOUND):
            print("order not found view3")
            return dict(error=dict(code=code, message=error_message))

        transaction = Transaction.objects.get(transaction_id=self.params["id"], variant=Provider.PAYME)

        # when order found and transaction created but error occurred
        if error:
            print("error view3")
            transaction.status = TransactionStatus.REJECTED
            transaction.save()
            return dict(error=dict(code=code, message=error_message))

        if transaction.status == TransactionStatus.PREAUTH:
            print(100 * '-')
            print("transaction status preauth view3")
            with db_transaction.atomic():
                transaction.status = TransactionStatus.CONFIRMED
                transaction.paid_at = timezone.now()
                transaction.save()

        return dict(
            result=dict(
                transaction=transaction.transaction_id,
                perform_time=int(transaction.paid_at.timestamp() * 1000),
                state=PaymeProvider.CLOSE_TRANSACTION,
            )
        )

    def check_transaction(self):
        error, error_message, code = PaymeProvider(self.params).check_transaction()
        if error:
            return dict(error=dict(code=code, message=error_message))

        transaction = Transaction.objects.get(transaction_id=self.params["id"], variant=Provider.PAYME)
        perform_time = int(transaction.paid_at.timestamp() * 1000) if transaction.paid_at else 0
        cancel_time = int(transaction.cancel_time.timestamp() * 1000) if transaction.cancel_time else 0
        reason = None
        if transaction.status == TransactionStatus.CONFIRMED:
            state = 2

        elif transaction.status == TransactionStatus.REJECTED:
            if perform_time==0:
                state = PaymeProvider.CANCEL_TRANSACTION_CODE
                reason = 3
            else:
                state = PaymeProvider.PERFORM_CANCELED_CODE
                reason = 5
        elif transaction.status == TransactionStatus.PREAUTH:
            state = 1
        elif transaction.status == TransactionStatus.WAITING:
            state = 1

        else:
            state = PaymeProvider.CREATE_TRANSACTION

        return dict(
            result=dict(
                create_time=int(transaction.created_at.timestamp() * 1000),
                perform_time=perform_time,
                cancel_time=cancel_time,
                transaction=str(transaction.transaction_id),
                state=state,
                reason=reason,
            )
        )





    def cancel_transaction(self):
        error, error_message, code = PaymeProvider(self.params).cancel_transaction()
        if error:
            return dict(error=dict(code=code, message=error_message))
        transaction = Transaction.objects.get(transaction_id=self.params["id"], variant=Provider.PAYME)
        state=None
        reason=None
        #state 1
        print("transaction :",transaction.status)
        print("transaction created :",transaction.created_at)
        print("transaction cancel: ",transaction.cancel_time)
        print("transaction paid_at : ",transaction.paid_at)
        print("transaction.status : ",transaction.status)


        if transaction.status == TransactionStatus.REJECTED:
            state=-1
            reason=1

        if transaction.status == TransactionStatus.WAITING:
            transaction.status = TransactionStatus.REJECTED
            transaction.cancel_time = timezone.now()
            transaction.save()
            state=-1
            reason=1

        #state 2
        if transaction.status == TransactionStatus.PREAUTH:
            transaction.status = TransactionStatus.REJECTED
            transaction.cancel_time = timezone.now()
            transaction.save()
            state=2
            reason=1


        perform_time = int(transaction.paid_at.timestamp() * 1000) if transaction.paid_at else 0
        cancel_time = int(transaction.cancel_time.timestamp() * 1000) if transaction.cancel_time else 0
        return dict(
            result=dict(
                create_time=int(transaction.created_at.timestamp() * 1000),
                perform_time=perform_time,
                cancel_time=cancel_time,
                transaction=str(transaction.transaction_id),
                state=state,
                reason=reason,
            )
        )






__all__ = ['PaymentView', 'PaymeAPIView', 'PaymeLinkAPIView']
