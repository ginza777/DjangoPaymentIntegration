from rest_framework import serializers
from .utils import PaylovMethods
from payment_integrations.payment_model.models import Transaction


class PaylovWithCardSerializer(serializers.Serializer):
    cardNumber = serializers.CharField( required=True)
    expireDate = serializers.CharField( required=True)
    amount = serializers.IntegerField( required=True)

    def validate(self, data):
        # Use this method for any cross-field validation
        card_number = data.get('cardNumber')
        expire_date = data.get('expireDate')
        amount = data.get('amount')

        if len(str(card_number)) > 16 or len(str(card_number)) < 16 or not str(card_number).isdigit():
            raise serializers.ValidationError({"cardNumber": "Card number is not 16 digits"})

        if len(expire_date) != 4:
            raise serializers.ValidationError({"expireDate": "Expire date is not valid, must be 4 digits"})

        elif amount < 1000:
            raise serializers.ValidationError({"amount": "Amount is not valid, must be greater than 1000"})

        return data


class PaylovWithCardConfirmSerializer(serializers.Serializer):
    transactionId = serializers.CharField(max_length=255, required=True)
    otp = serializers.CharField(max_length=255, required=True)
    is_hold = serializers.BooleanField(default=False)


class PaylovSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=PaylovMethods.choices())
    params = serializers.JSONField()


class PaylovLinkSerializer(serializers.Serializer):
    amount = serializers.IntegerField(required=True)


class PaylovLinkStatusSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)

    def validate(self, data):
        print(data)
        print(data['transaction_id'])
        if Transaction.objects.filter(id=data['transaction_id']).exists():
            if Transaction.objects.get(id=data['transaction_id']).total == data['amount']:
                return data
            else:
                print("Amount is not equal")
                raise serializers.ValidationError("Amount is not equal")
        else:
            raise serializers.ValidationError("Transaction not found")
