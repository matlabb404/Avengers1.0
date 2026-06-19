from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, Boolean, Time, Date, Enum, UUID, ForeignKey, JSON, UniqueConstraint, Index, Computed
from app.schemas.vendor_Schema import Gender
from app.utils.mixins import TimestampMixin
from sqlalchemy.dialects.postgresql import TSVECTOR
import uuid 
from sqlalchemy.orm import relationship

class Vendor(TimestampMixin, Base):
    __tablename__ = "Vendor"

    vendor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid= True),ForeignKey('users.id'), nullable=False)
    vendor_email = Column(String)
    first_name = Column(String)
    last_name = Column(String, nullable=False)
    house_no= Column(String(50))
    street = Column(String(100), nullable=False)
    city = Column(String, nullable=False)
    state = Column(String(20))
    postal_code = Column(String(10), nullable=False)
    country = Column(String)
    gender = Column(Enum(Gender), default=Gender.Male)
    date_of_birth = Column(Date)
    business_name = Column(String)
    phone_no = Column(String(50))

    # ── Search: weighted full-text vector (generated/STORED) ──────────────
    # business_name (A) > first/last name (B) > city (C). plus trigram indexes
    # on the raw text columns (declared in __table_args__) for typo tolerance.
    search_tsv = Column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('simple', coalesce(business_name, '')), 'A') || "
            "setweight(to_tsvector('simple', coalesce(first_name, '')), 'B') || "
            "setweight(to_tsvector('simple', coalesce(last_name, '')), 'B') || "
            "setweight(to_tsvector('simple', coalesce(city, '')), 'C')",
            persisted=True,
        ),
        nullable=True,
    )

    vendor_details = relationship("Vendor_Details", uselist=False, back_populates="vendor")

    vendor_user = relationship("User", back_populates = "user_vendor")
    
    schedule = relationship("Scheduling_", back_populates = "schedules")

    followers = relationship(
        "Following",
        foreign_keys="Following.vendor_id",
        back_populates="followed_vendor",
        cascade="all, delete-orphan",
    )
    following = relationship(
        "Following",
        foreign_keys="Following.follower_vendor_id",
        back_populates="follower_vendor",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "Comment",
        foreign_keys="Comment.author_vendor_id",
        back_populates="author_vendor",
        cascade="all, delete-orphan",
    )
    likes = relationship(
        "Like",
        foreign_keys="Like.liker_vendor_id",
        back_populates="liker_vendor",
        cascade="all, delete-orphan",
    )

    # ── Search indexes ────────────────────────────────────────────────────
    # GIN over the tsvector (full-text) + GIN trigram over the fuzzy text cols.
    __table_args__ = (
        Index("vendor_search_tsv_gin", "search_tsv", postgresql_using="gin"),
        Index(
            "vendor_business_name_trgm", "business_name",
            postgresql_using="gin", postgresql_ops={"business_name": "gin_trgm_ops"},
        ),
        Index(
            "vendor_city_trgm", "city",
            postgresql_using="gin", postgresql_ops={"city": "gin_trgm_ops"},
        ),
    )

class Vendor_Details(TimestampMixin, Base):
    __tablename__= "Vendor_Details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id_details = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'))
    description = Column(String)
    picture_url = Column(String)
    review = Column(String)

    vendor = relationship("Vendor", back_populates="vendor_details")

class Scheduling_(TimestampMixin, Base):
    __tablename__= "Schedule"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_vendor_id = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'))
    service_id = Column(String, nullable=False, default="all") #"all" or specific service ID
    days = Column(JSON) #day(monday,tuesday) and times worked everyweek
    start_time = Column(Time)
    end_time = Column(Time)
    capacity = Column(Integer)
    interval_minutes = Column(Integer, nullable=False, default=30)  # ✅ Add this
    walk_in_available = Column(Boolean, nullable=False, default=False)  # ✅ Add this


# weekly rules ✅
# working hours ✅
# capacity ✅

    schedules = relationship("Vendor", back_populates = "schedule")
    __table_args__ = (
        # Only one schedule per vendor+service combination
        UniqueConstraint("schedule_vendor_id", "service_id", name="unique_vendor_service_schedule"),
        Index("idx_vendor_service", "schedule_vendor_id", "service_id"),
    )


class ScheduleException(TimestampMixin, Base):
    __tablename__ = "schedule_exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    vendor_id = Column(UUID(as_uuid=True), ForeignKey("Vendor.vendor_id"))

    service_id = Column(String, nullable=False, default="all") #"all" or specific service ID


    date = Column(Date, nullable=False)

    # optional overrides
    is_closed = Column(Boolean, default=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    capacity = Column(Integer, nullable=True)
    reason = Column(String, nullable=True)
    interval_minutes = Column(Integer, nullable=False, default=30)  # ✅ Add this
    walk_in_available = Column(Boolean, nullable=False, default=False)  # ✅ Add this


# Full-day holiday	✅ is_closed=True
# Late opening	✅ override start_time
# Early closing	✅ override end_time
# Special busy day	✅ override capacity
# Multiple exceptions	✅ multiple rows

    vendor = relationship("Vendor")
    __table_args__ = (
        # One exception per vendor+service+date
        UniqueConstraint("vendor_id", "service_id", "date", name="unique_exception_per_service_date"),
        Index("idx_vendor_service_date", "vendor_id", "service_id", "date"),
    )