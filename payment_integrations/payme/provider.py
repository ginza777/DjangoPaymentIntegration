from django.utils import timezone
from payment_integrations.payment_model.models import Transaction, Provider
from payments import PaymentStatus as TransactionStatus
class PaymeProvider:
    ORDER_NOT_FOUND = -31050
    ORDER_ALREADY_PAID = -31051
    ORDER_INVALID_PAYMENT_TYPE = -31053
    TRANSACTION_NOT_FOUND = -31003
    INVALID_AMOUNT = -31001
    UNABLE_TO_PERFORM_OPERATION = -31008

    CREATE_TRANSACTION = 1
    CLOSE_TRANSACTION = 2
    CANCEL_TRANSACTION_CODE = -1
    PERFORM_CANCELED_CODE = -2

    ORDER_NOT_FOUND_MESSAGE = {"uz": "Buyurtma topilmadi", "ru": "Заказ не найден", "en": "Order not fond"}
    ORDER_ALREADY_PAID_MESSAGE = {
        "uz": "Buyurtma allaqachon to'langan",
        "ru": "Заказ уже оплачен",
        "en": "Order already paid",
    }
    ORDER_INVALID_PAYMENT_TYPE_MESSAGE = {
        "uz": "To'lov usuli noto'g'ri",
        "ru": "Неверный тип оплаты",
        "en": "Invalid payment type",
    }
    TRANSACTION_NOT_FOUND_MESSAGE = {
        "uz": "Tranzaksiya topilmadi",
        "ru": "Транзакция не найдена",
        "en": "Transaction not found",
    }
    UNABLE_TO_PERFORM_OPERATION_MESSAGE = {
        "uz": "Ushbu amalni bajarib bo'lmaydi",
        "ru": "Невозможно выполнить данную операцию",
        "en": "Unable to perform operation",
    }

    INVALID_AMOUNT_MESSAGE = {"uz": "Miqdori notog'ri", "ru": "Неверная сумма", "en": "Invalid amount"}

    def __init__(self, params):
        self.params = params
        self.code = None
        self.error = None
        self.error_message = None
        self.order = self.get_order()

    def get_order(self):
        print("get_order",self.params.get("account"))
        if not self.params.get("account"):
            return
        try:
            print("get_order",self.params["account"]["order_id"],'\n',Transaction.objects.get(id=self.params["account"]["order_id"]))
            return Transaction.objects.get(id=self.params["account"]["order_id"])
        except Transaction.DoesNotExist:
            print("get_order error",self.params["account"]["order_id"])
            return
        #

    def validate_order(self):
        print("validate_order",self.order)
        if self.order.status == TransactionStatus.CONFIRMED:
            self.error = True
            self.error_message = self.ORDER_ALREADY_PAID_MESSAGE
            self.code = self.ORDER_ALREADY_PAID

    def validate_amount(self, amount):
        print("validate_amount",amount,self.order.total)
        print("validate_amount",self.order.total)
        if amount != self.order.total:
            self.error = True
            self.error_message = self.INVALID_AMOUNT_MESSAGE
            self.code = self.INVALID_AMOUNT

    def check_perform_transaction(self):
        print("check_perform_transaction",self.order)
        self.validate_amount(self.params["amount"] / 100)
        if not self.order:
            print("*order topilmadi*}")
            return True, self.ORDER_NOT_FOUND_MESSAGE, self.ORDER_NOT_FOUND

        if self.order.status == TransactionStatus.CONFIRMED:
            print("*order allaqachon to'langan*}")
            self.error = True
            self.error_message = self.ORDER_ALREADY_PAID_MESSAGE
            self.code = self.ORDER_ALREADY_PAID
            return  self.error, self.error_message, self.code

        if self.order.status != TransactionStatus.WAITING:
            print("*order waiting emas*}")
            self.error = True
            self.error_message = self.ORDER_NOT_FOUND_MESSAGE
            self.code = self.ORDER_NOT_FOUND

            return self.error, self.error_message, self.code



        return self.error, self.error_message, self.code

    def create_transaction(self):
        print("create_transaction",self.order)
        print("amount check")
        self.validate_amount(self.params["amount"] / 100)
        self.validate_order()

        if not self.order:
            print("order topilmadi")
            return True, self.ORDER_NOT_FOUND_MESSAGE, self.ORDER_NOT_FOUND

        _time = timezone.now() - timezone.timedelta(seconds=15)
        print(_time)
        if self.order.id:
            print("if order topildi")
            check_transaction = Transaction.objects.get(id=self.order.id)
            print("check_transaction",check_transaction.id,check_transaction.transaction_id,check_transaction.status,self.params["id"])
        else:
            print("else order topilmadi")
            return True, self.ORDER_NOT_FOUND_MESSAGE, self.ORDER_NOT_FOUND
        print("order:",check_transaction.id,check_transaction.transaction_id,check_transaction.status,self.params["id"])
        print("*"*10)
        print(check_transaction.id)
        print(check_transaction.transaction_id)
        print(check_transaction.status)
        print(self.params["id"])
        print(TransactionStatus.WAITING)
        print("*"*10)

        if str(check_transaction.id)==str(check_transaction.transaction_id) and str(check_transaction.status)==str(TransactionStatus.WAITING) :
            print("1 if ")
            check_transaction.transaction_id=self.params["id"]
            check_transaction.status=TransactionStatus.PREAUTH
            try:
                check_transaction.save()
            except Exception as e:
                print(f"Hata: {e}")
            print("1order:", check_transaction.id, check_transaction.transaction_id, check_transaction.status)
        elif  str(check_transaction.transaction_id)==str(self.params["id"]) and str(check_transaction.status)==str(TransactionStatus.PREAUTH):
            print("2 if ")
            check_transaction.transaction_id=self.params["id"]
            check_transaction.status=TransactionStatus.PREAUTH
            try:
                check_transaction.save()
            except Exception as e:
                print(f"Hata: {e}")
            print("order:", check_transaction.id, check_transaction.transaction_id, check_transaction.status)

        elif str(check_transaction.transaction_id )!= str(self.params["id"]):
            print("3 if ")
            if str(check_transaction.status)==str(TransactionStatus.PREAUTH) or str(check_transaction.status)==str(TransactionStatus.WAITING):
                print("3 if 1")
                return True, self.ORDER_NOT_FOUND_MESSAGE, self.ORDER_NOT_FOUND
            return True, self.ORDER_NOT_FOUND_MESSAGE, self.ORDER_NOT_FOUND

        elif str(check_transaction.transaction_id )== str(self.params["id"]) and str(check_transaction.status)!=str(TransactionStatus.WAITING):
            print("4 if ")
            if check_transaction.status!=TransactionStatus.PREAUTH:
                print("4 if 1")
                return True, self.ORDER_NOT_FOUND, self.ORDER_NOT_FOUND
            return True, self.ORDER_NOT_FOUND, self.ORDER_NOT_FOUND


        return self.error, self.error_message, self.code

    def perform_transaction(self):
        try:
            transaction = Transaction.objects.get(transaction_id=self.params["id"], variant=Provider.PAYME)
        except Transaction.DoesNotExist:
            print("transaction not found4")
            return True, self.TRANSACTION_NOT_FOUND_MESSAGE, self.TRANSACTION_NOT_FOUND
        if transaction.status == TransactionStatus.REJECTED:
            print("transaction status rejected4")
            return True, self.UNABLE_TO_PERFORM_OPERATION, self.UNABLE_TO_PERFORM_OPERATION_MESSAGE
        if self.order and self.order.status == TransactionStatus.PREAUTH:
            print("transaction status preauth4")
            self.order = transaction
            self.validate_order()

        return self.error, self.error_message, self.code

    def check_transaction(self):
        print("check_transaction",self.order)
        try:
            Transaction.objects.get(transaction_id=self.params["id"], variant=Provider.PAYME)
        except Transaction.DoesNotExist:
            return True, self.TRANSACTION_NOT_FOUND_MESSAGE, self.TRANSACTION_NOT_FOUND

        return self.error, self.error_message, self.code


    def cancel_transaction(self):
        print("cancel_transaction",self.order)
        try:
            transaction = Transaction.objects.get(transaction_id=self.params["id"], variant=Provider.PAYME)
        except Transaction.DoesNotExist:
            return True, self.TRANSACTION_NOT_FOUND_MESSAGE, self.TRANSACTION_NOT_FOUND

        if transaction.status == TransactionStatus.CONFIRMED:
            return True, self.UNABLE_TO_PERFORM_OPERATION, self.UNABLE_TO_PERFORM_OPERATION_MESSAGE

        return self.error, self.error_message, self.code

