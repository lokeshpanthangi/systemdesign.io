from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    """User model for authenticated requests"""
    id: str  # email address (used as user_id in database)
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
