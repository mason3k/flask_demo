from typing import Literal


class Config:
    ROWS_PER_PAGE: int = 10
    DEFAULT_MODE: Literal["offline", "online"] = "online"
