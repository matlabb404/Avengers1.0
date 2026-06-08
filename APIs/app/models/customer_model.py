
from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date,DateTime, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.utils.mixins import TimestampMixin
import uuid

class customer(TimestampMixin, Base):
    __tablename__ = "customer"

    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid= True),ForeignKey('users.id'), nullable=False)
    name = Column(String(25))
    address_1 = Column(String(100), nullable=False)
    address_2 = Column(String(100))
    city = Column(String, nullable=False)
    post_code = Column(String(10), nullable=False)
    country = Column(String)
    date_of_birth = Column(Date)


#relationship wit user
    customer_user = relationship("User", back_populates = "user_customer")

    following = relationship(
        "Following",
        foreign_keys="Following.follower_customer_id",
        back_populates="follower_customer",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "Comment",
        foreign_keys="Comment.author_customer_id",
        back_populates="author_customer",
        cascade="all, delete-orphan",
    )
    likes = relationship(
        "Like",
        foreign_keys="Like.liker_customer_id",
        back_populates="liker_customer",
        cascade="all, delete-orphan",
    )
