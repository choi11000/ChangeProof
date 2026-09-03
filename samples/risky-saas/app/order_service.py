from dataclasses import dataclass


@dataclass
class Order:
    id: int
    legacy_status: str


def serialize_order(order: Order) -> dict[str, int | str]:
    return {"id": order.id, "status": order.legacy_status}
