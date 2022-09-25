from sqlalchemy import Column, BigInteger, TIMESTAMP, Text, BOOLEAN, ForeignKey
from db_utils import Base as BaseModel
from db_utils import UUID
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class Tracker(BaseModel):
    __tablename__ = 'trackers'
    uuid = Column(UUID, nullable=False, unique=True, primary_key=True)
    name = Column(Text, nullable=False)
    owner_id = Column(BigInteger, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)


# class Request(BaseModel):
#     __tablename__ = 'requests'
#     uuid = Column(UUID, nullable=False, unique=True, primary_key=True, default=uuid.uuid4())
#     ip = Column(Text, nullable=False)
#     useragent = Column(Text, nullable=True)
#     from_mask = Column(Text, nullable=False)
#     mask_owner = Column(Text, nullable=False)
#     url = Column(Text, nullable=True)
#     tracker_uuid = Column(UUID, ForeignKey('trackers.uuid'), nullable=False)
#     at = Column(TIMESTAMP, nullable=False)


class Notification(BaseModel):
    __tablename__ = 'notifications'
    uuid = Column(UUID, nullable=False, unique=True, primary_key=True, default=generate_uuid())
    tracker_uuid = Column(UUID, ForeignKey('trackers.uuid'), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    enable = Column(BOOLEAN, default=True)


class Users(BaseModel):
    __tablename__ = 'users'
    telegram_id = Column(BigInteger, nullable=False, unique=True, primary_key=True)
    action = Column(Text)
    state = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False)
