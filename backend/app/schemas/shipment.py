from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class LocationSchema(BaseModel):
    name: str
    latitude: float
    longitude: float
    facilityType: Optional[str] = "destination"


class ProductSchema(BaseModel):
    id: UUID
    name: str
    category: str
    safeTempMin: float
    safeTempMax: float
    criticalTempMax: float
    temperatureSensitivity: str
    shelfLifeHours: float


class ShipmentResponse(BaseModel):
    id: UUID
    shipmentCode: str
    productName: str
    productCategory: str
    vehicleNumber: str
    origin: LocationSchema
    destination: LocationSchema
    currentLat: Optional[float]
    currentLng: Optional[float]
    temperature: float
    humidity: float
    speed: float
    doorOpen: bool
    coolingPower: int
    battery: float
    status: str
    riskScore: int
    riskLevel: str
    plannedEtaMinutes: int
    currentEtaMinutes: int
    delayMinutes: int
    estimatedCargoValue: float
    safeMinTemp: float
    safeMaxTemp: float
    remainingSafeLifeMinutes: Optional[int]


class ShipmentCreate(BaseModel):
    shipmentCode: str
    productName: str
    vehicleNumber: str
    originName: str
    originLat: float
    originLng: float
    destinationName: str
    destinationLat: float
    destinationLng: float
    plannedEtaMinutes: int
    estimatedCargoValue: float
    safeMinTemp: float
    safeMaxTemp: float
