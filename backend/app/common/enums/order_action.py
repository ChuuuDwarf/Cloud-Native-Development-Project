from enum import Enum


class OrderAction(str, Enum):
    SUBMIT = "submit"
    CANCEL = "cancel"
    APPROVE = "approve"
    RETURN = "return"
    REJECT = "reject"
    CONFIRM_DELIVERY = "confirm_delivery"
    CONFIRM_RECEIVED = "confirm_received"
    READY_FOR_PICKUP = "ready_for_pickup"
    CLOSE = "close"
