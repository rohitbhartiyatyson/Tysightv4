from enum import Enum


class IntentSchema(Enum):
    sales_performance = "sales_performance"
    yoy_performance = "yoy_performance"
    distribution_summary = "distribution_summary"
    pricing_summary = "pricing_summary"
    velocity_summary = "velocity_summary"
    promotion_summary = "promotion_summary"

    @staticmethod
    def names():
        return [i.value for i in IntentSchema]
