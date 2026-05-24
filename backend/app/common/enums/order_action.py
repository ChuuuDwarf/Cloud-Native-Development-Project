from enum import StrEnum


class OrderAction(StrEnum):
    SUBMIT = "submit"
    CANCEL = "cancel"
    APPROVE = "approve"
    RETURN = "return"
    REJECT = "reject"
    CONFIRM_DELIVERY = "confirm_delivery"
    CONFIRM_RECEIVED = "confirm_received"
    READY_FOR_PICKUP = "ready_for_pickup"
    CLOSE = "close"
