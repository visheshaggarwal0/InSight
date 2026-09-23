import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "InSight Telemetry Intelligence"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    DEFAULT_DATASET: str = "d2c_cosmetics"
    
settings = Settings()
