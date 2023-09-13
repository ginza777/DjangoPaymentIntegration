from payments import PaymentStatus
from django.contrib.auth import get_user_model
from payment_integrations.payment_model.models import UserBalanceHistory,Transaction
from django.db import transaction as db_transaction


User=get_user_model()
class PaylovProvider:
    ORDER_NOT_FOUND = "303"
    ORDER_ALREADY_PAID = "201"
    INVALID_AMOUNT = "5"
    SERVER_ERROR = "3"

    SUCCESS = "0"
    SUCCESS_STATUS_TEXT = "OK"
    ERROR_STATUS_TEXT = "ERROR"

    def __init__(self, params):
        self.params = params
        self.code = self.SUCCESS
        self.error = False
        self.transaction = self.get_transaction()

    def check(self):
        if not self.transaction:
            return True, self.ORDER_NOT_FOUND
        if self.transaction.status != PaymentStatus.WAITING:
            return True, self.SERVER_ERROR
        if self.transaction.total != self.params["amount"]:
            return True, self.INVALID_AMOUNT
        with db_transaction.atomic():
            self.transaction.status = PaymentStatus.PREAUTH
            self.transaction.save()
        if self.transaction.status != PaymentStatus.PREAUTH:
            return True, self.SERVER_ERROR
        return self.error, self.code

    def perform(self):
        if not self.params.get("account"):
            return
        if not self.params.get("amount"):
            return
        try:
            user = User.objects.get(id=self.params["account"]["userid"])
            transaction = Transaction.objects.get(
                user=user,
                id=self.params["account"]["transaction_id"]
            )

            if transaction.status == PaymentStatus.WAITING:
                return True, self.SERVER_ERROR

            if transaction.status != PaymentStatus.PREAUTH:
                return True, self.ORDER_NOT_FOUND

            if transaction.total != self.params["amount"]:
                return True, self.ORDER_NOT_FOUND

            if transaction.status == PaymentStatus.PREAUTH:
                with db_transaction.atomic():
                    transaction.status = PaymentStatus.CONFIRMED
                    transaction.transaction_id = self.params["transaction_id"]
                    transaction.save()

                # for balance
                transaction = transaction
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

            if transaction.status != PaymentStatus.CONFIRMED:
                return True, self.SERVER_ERROR


        except Transaction.DoesNotExist:
            return True, self.ORDER_NOT_FOUND

        return self.error, self.code

    def get_transaction(self):
        if not self.params.get("account"):
            return
        if not self.params.get("amount"):
            return
        try:
            user = User.objects.get(id=self.params["account"]["userid"])
            transaction = Transaction.objects.get(
                user=user,
                id=self.params["account"]["transaction_id"]
            )
            return transaction
        except Transaction.DoesNotExist:
            return
