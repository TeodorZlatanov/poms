from pydantic import BaseModel


class LineItem(BaseModel):
    description: str
    sku: str | None = None
    quantity: int
    unit_price: float | None = None


class VendorInfo(BaseModel):
    name: str
    contact: str | None = None


class RequesterInfo(BaseModel):
    name: str | None = None
    department: str | None = None


class PurchaseOrderExtraction(BaseModel):
    """Structured data extracted from a purchase order document."""

    po_number: str | None = None
    po_date: str | None = None
    vendor: VendorInfo
    requester: RequesterInfo | None = None
    line_items: list[LineItem]
    total_amount: float | None = None
    currency: str | None = None
    delivery_date: str | None = None
    payment_terms: str | None = None
