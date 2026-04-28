"""Request/Response schemas for API validation."""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RouteRequest(BaseModel):
    """Data Transfer Object (DTO) for the POST /route endpoint.
    
    Validates the structure and geometric bounds of incoming routing requests.
    Strict validation at the API boundary prevents processing errors deeper 
    in the routing engine.
    """

    start: List[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Start coordinates [lat, lon]",
        examples=[[-6.9, 112.0]],
    )
    end: List[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="End coordinates [lat, lon]",
        examples=[[-6.95, 112.05]],
    )
    lambda_value: Optional[float] = Field(
        0.0,
        alias="lambda",
        description="Uphill penalty factor (dynamic float value from UI slider)",
    )

    @field_validator("start", "end")
    @classmethod
    def validate_coords(cls, v):
        """Ensure coordinate arrays map to valid geographical points."""
        if len(v) != 2:
            raise ValueError("Coordinates must be formatted as exactly [latitude, longitude]")
        lat, lon = v
        # Validate against standard WGS84 bounds
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be constrained between -90 and 90 degrees")
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be constrained between -180 and 180 degrees")
        return v

    class Config:
        populate_by_name = True


class RouteResponse(BaseModel):
    """POST /route response body."""

    path: List[List[float]] = Field(..., description="List of [lat, lon] waypoints")
    distance: float = Field(..., description="Total distance in meters")
    elevation_gain: float = Field(..., description="Total uphill elevation gain in meters")
    lambda_value: float = Field(..., description="Lambda value used")
    node_count: int = Field(..., description="Number of nodes in path")


class NearestNodeResponse(BaseModel):
    """GET /nearest-node response."""

    node_id: int = Field(..., description="Graph node ID")
    lat: float = Field(..., description="Node latitude")
    lon: float = Field(..., description="Node longitude")


class GraphInfoResponse(BaseModel):
    """GET /graph-info response."""

    node_count: int = Field(..., description="Number of nodes")
    edge_count: int = Field(..., description="Number of edges")
    is_directed: bool = Field(..., description="Whether graph is directed")


