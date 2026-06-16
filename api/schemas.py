"""Request/Response schemas for API validation."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class RouteRequest(BaseModel):
    """Data Transfer Object (DTO) for the POST /route endpoint.

    Validates the structure and geometric bounds of incoming routing requests.
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
        None,
        alias="lambda",
        description="Uphill penalty factor (for backward compatibility)",
    )
    mode: Optional[str] = Field(
        "time",
        description="Routing weight mode: 'time' (travel time) or 'distance' (shortest path)",
    )
    model_type: Optional[str] = Field(
        "glm",
        alias="model",
        description="Velocity model: 'glm' (default), 'tobler', or 'naismith'",
    )
    ignore_downhill: Optional[bool] = Field(
        False,
        description="Whether to ignore the constant 5km/h downhill speed rule",
    )
    slope_multiplier: Optional[float] = Field(
        None,
        alias="slope_multiplier",
        description="Slope elevation multiplier (e.g. 3.0 for pushing motorbike)",
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
    travel_time: float = Field(..., description="Estimated travel time in seconds")
    slope_characteristics: Dict = Field(..., description="Slope statistics of the path")
    mode: str = Field(..., description="Routing mode used ('time' or 'distance')")
    model_type: str = Field(..., description="Velocity model used")
    ignore_downhill: bool = Field(..., description="Whether downhill speed override was ignored")
    slope_multiplier: float = Field(..., description="Slope multiplier used")
    lambda_value: float = Field(..., description="Lambda value or equivalent fallback")
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
