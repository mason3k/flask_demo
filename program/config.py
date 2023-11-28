from typing import Literal


class Config:
    ROWS_PER_PAGE: int = 3
    DEFAULT_MODE: Literal["offline", "online"] = "offline"
