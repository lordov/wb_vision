from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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


class SalesWBCreate(BaseModel):
    date: datetime
    last_change_date: datetime = Field(..., alias="lastChangeDate")
    warehouse_name: str = Field(..., alias="warehouseName")
    country_name: Optional[str] = Field(None, alias="countryName")
    oblast_okrug_name: Optional[str] = Field(None, alias="oblastOkrugName")
    region_name: str = Field(..., alias="regionName")
    supplier_article: str = Field(..., alias="supplierArticle")
    nm_id: int = Field(..., alias="nmId")
    barcode: str
    category: str
    subject: str
    brand: str
    tech_size: str = Field(..., alias="techSize")
    income_id: Optional[int] = Field(None, alias="incomeID")
    is_supply: Optional[bool] = Field(None, alias="isSupply")
    is_realization: Optional[bool] = Field(None, alias="isRealization")
    total_price: Decimal = Field(..., alias="totalPrice")
    discount_percent: Decimal = Field(..., alias="discountPercent")
    spp: Optional[Decimal] = None
    for_pay: Decimal = Field(..., alias="forPay")
    finished_price: Optional[Decimal] = Field(None, alias="finishedPrice")
    price_with_disc: Decimal = Field(..., alias="priceWithDisc")
    payment_sale_amount: Optional[Decimal] = Field(
        None, alias="paymentSaleAmount")
    sale_id: str = Field(..., alias="saleID")
    sticker: str
    g_number: str = Field(..., alias="gNumber")
    is_cancel: bool = Field(..., alias="isCancel")
    srid: Optional[str] = None
    warehouse_type: Optional[str] = Field(None, alias="warehouseType")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class StocksWBCreate(BaseModel):
    import_date: datetime = Field(..., alias="importDate")
    last_change_date: datetime = Field(..., alias="lastChangeDate")
    supplier_article: str = Field(..., alias="supplierArticle")
    tech_size: str = Field(..., alias="techSize")
    barcode: str
    nm_id: int = Field(..., alias="nmId")
    category: str
    subject: str
    brand: str
    quantity: int
    is_supply: Optional[bool] = Field(None, alias="isSupply")
    is_realization: Optional[bool] = Field(None, alias="isRealization")
    in_way_to_client: Optional[int] = Field(..., alias="inWayToClient")
    in_way_from_client: Optional[int] = Field(..., alias="inWayFromClient")
    quantity_full:int = Field(..., alias="quantityFull")
    warehouse_name: str = Field(..., alias="warehouseName")
    sc_code: Optional[str] = Field(None, alias="SCCode")
    price: Decimal
    discount: Decimal

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True
