from sqlalchemy import Column, BigInteger, TIMESTAMP, String, BOOLEAN, ForeignKey
from db_utils import Base as BaseModel
from db_utils import UUID
import uuid


class Tracker(BaseModel):
    __tablename__ = 'trackers'
    uuid = Column(UUID, nullable=False, unique=True, primary_key=True)
    name = Column(String, nullable=False)
    owner_id = Column(BigInteger, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)

class Notification(BaseModel):
    __tablename__ = 'notifications'
    uuid = Column(UUID, nullable=False, unique=True, primary_key=True, default=uuid.uuid4())
    tracker_uuid = Column(UUID, ForeignKey('trackers.uuid'), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    enable = Column(BOOLEAN, default=True)


class Users(BaseModel):
    __tablename__ = 'users'
    telegram_id = Column(BigInteger, nullable=False, unique=True, primary_key=True)
    action = Column(String)
    state = Column(String)
    created_at = Column(TIMESTAMP, nullable=False)
