class PaymeMethods:
    CHECK_PERFORM_TRANSACTION = "CheckPerformTransaction"
    CREATE_TRANSACTION = "CreateTransaction"
    PERFORM_TRANSACTION = "PerformTransaction"
    CHECK_TRANSACTION = "CheckTransaction"
    CANCEL_TRANSACTION = "CancelTransaction"

    @classmethod
    def choices(cls):
        return (
            (cls.CHECK_PERFORM_TRANSACTION, cls.CHECK_PERFORM_TRANSACTION),
            (cls.CREATE_TRANSACTION, cls.CREATE_TRANSACTION),
            (cls.PERFORM_TRANSACTION, cls.PERFORM_TRANSACTION),
            (cls.CHECK_TRANSACTION, cls.CHECK_TRANSACTION),
            (cls.CANCEL_TRANSACTION, cls.CANCEL_TRANSACTION),
        )
