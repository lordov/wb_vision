from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator, validator

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, validator

class OrderWBCreate(BaseModel):
    date: datetime
    last_change_date: datetime = Field(..., alias="lastChangeDate")
    supplier_article: str = Field(..., alias="supplierArticle")
    tech_size: str = Field(..., alias="techSize")
    barcode: str
    total_price: Decimal = Field(..., alias="totalPrice")
    finished_price: Optional[Decimal] = Field(None, alias="finishedPrice")
    discount_percent: Decimal = Field(..., alias="discountPercent")
    spp: Optional[Decimal] = None
    warehouse_name: str = Field(..., alias="warehouseName")
    region_name: str = Field(..., alias="regionName")
    oblast_okrug_name: Optional[str] = Field(None, alias="oblastOkrugName")
    country_name: Optional[str] = Field(None, alias="countryName")
    income_id: Optional[int] = Field(None, alias="incomeID")
    nm_id: int = Field(..., alias="nmId")
    subject: str
    category: str
    brand: str
    is_cancel: bool = Field(..., alias="isCancel")
    cancel_date: Optional[datetime] = Field(None, alias="cancelDate")
    g_number: str = Field(..., alias="gNumber")
    sticker: str
    srid: Optional[str] = None
    price_with_disc: Optional[Decimal] = Field(None, alias="priceWithDisc")
    is_supply: Optional[bool] = Field(None, alias="isSupply")
    is_realization: Optional[bool] = Field(None, alias="isRealization")
    warehouse_type: Optional[str] = Field(None, alias="warehouseType")

    @field_validator('cancel_date', mode='before')
    @classmethod
    def empty_cancel_date_to_none(cls, v):
        if v in ("0001-01-01T00:00:00", "0001-01-01T00:00:00Z"):
            return None
        return v

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True

