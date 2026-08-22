"""Relational metadata store; raw WARC/WACZ bytes are intentionally excluded from the database."""

from __future__ import annotations

try:
    try:
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class PublicObject(Base):
    __tablename__ = "objects"
    object_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    canonical_url: Mapped[str] = mapped_column(Text, unique=True, index=True)
    original_url: Mapped[str] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(String(32), index=True)
    semantic_identifiers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    observations: Mapped[list[Observation]] = relationship(back_populates="object")


class Observer(Base):
    __tablename__ = "observers"
    observer_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    public_key: Mapped[str] = mapped_column(Text, unique=True)
    key_algorithm: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[str] = mapped_column(String(40))
    operator_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    key_status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    replacement_observer_id: Mapped[str | None] = mapped_column(String(96), nullable=True)


class Observation(Base):
    __tablename__ = "observations"
    observation_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    object_id: Mapped[str] = mapped_column(ForeignKey("objects.object_id"), index=True)
    observer_id: Mapped[str] = mapped_column(ForeignKey("observers.observer_id"), index=True)
    captured_at: Mapped[str] = mapped_column(String(40), index=True)
    raw_content_hash: Mapped[str] = mapped_column(String(80), index=True)
    raw_content_reference: Mapped[str] = mapped_column(Text)
    archive_format: Mapped[str] = mapped_column(String(16))
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    object: Mapped[PublicObject] = relationship(back_populates="observations")


class Signature(Base):
    __tablename__ = "signatures"
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.observation_id"), primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(32))
    signature: Mapped[str] = mapped_column(Text)


class TimestampEvidence(Base):
    __tablename__ = "timestamps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.observation_id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class StorageRef(Base):
    __tablename__ = "storage_refs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.observation_id"), index=True)
    backend: Mapped[str] = mapped_column(String(64))
    locator: Mapped[str] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("observation_id", "backend", "locator", name="uq_storage_ref"),)


class LogEntry(Base):
    __tablename__ = "log_entries"
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.observation_id"), primary_key=True)
    log_id: Mapped[str] = mapped_column(String(128))
    leaf_index: Mapped[int] = mapped_column(Integer)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSON)
    proof: Mapped[dict[str, Any]] = mapped_column(JSON)


class Conflict(Base):
    __tablename__ = "conflicts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[str] = mapped_column(ForeignKey("objects.object_id"), index=True)
    observation_a_id: Mapped[str] = mapped_column(ForeignKey("observations.observation_id"))
    observation_b_id: Mapped[str] = mapped_column(ForeignKey("observations.observation_id"))
    classification: Mapped[str] = mapped_column(String(32), index=True)
    is_conflict_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("observation_a_id", "observation_b_id", name="uq_conflict_pair"),)


class Replica(Base):
    __tablename__ = "replicas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.observation_id"), index=True)
    peer_id: Mapped[str] = mapped_column(String(256), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class IndependenceProfile(Base):
    __tablename__ = "independence_profiles"
    observer_id: Mapped[str] = mapped_column(ForeignKey("observers.observer_id"), primary_key=True)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Repository:
    def __init__(self, database_url: str = "sqlite:///./oin.db") -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, future=True, connect_args=connect_args)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def save_observation(
        self,
        manifest: dict[str, Any],
        *,
        storage_backend: str,
        storage_locator: str,
        log_proof: dict[str, Any] | None = None,
        timestamp_evidence: dict[str, Any] | None = None,
    ) -> None:
        object_data, observer_data = manifest["object"], manifest["observer"]
        with self.session_factory.begin() as session:
            if not session.get(PublicObject, object_data["object_id"]):
                session.add(PublicObject(
                    object_id=object_data["object_id"], canonical_url=object_data["canonical_url"],
                    original_url=object_data.get("original_url", object_data["canonical_url"]), resource_type=object_data["resource_type"],
                    semantic_identifiers=object_data.get("semantic_identifiers", {}),
                ))
            if not session.get(Observer, observer_data["observer_id"]):
                session.add(Observer(
                    observer_id=observer_data["observer_id"], public_key=observer_data["public_key"],
                    key_algorithm=observer_data["key_algorithm"], created_at=observer_data["created_at"],
                ))
            if session.get(Observation, manifest["observation_id"]):
                return
            observation = Observation(
                observation_id=manifest["observation_id"], object_id=object_data["object_id"], observer_id=observer_data["observer_id"],
                captured_at=manifest["capture"]["captured_at"], raw_content_hash=manifest["content"]["raw_content_hash"],
                raw_content_reference=manifest["content"]["raw_content_reference"], archive_format=manifest["content"]["archive_format"], manifest=manifest,
            )
            session.add(observation)
            session.add(Signature(observation_id=manifest["observation_id"], algorithm="Ed25519", signature=manifest["signature"]["value"]))
            session.add(StorageRef(observation_id=manifest["observation_id"], backend=storage_backend, locator=storage_locator, verified_at=datetime.now(UTC)))
            if timestamp_evidence:
                session.add(
                    TimestampEvidence(
                        observation_id=manifest["observation_id"],
                        kind=timestamp_evidence.get("kind", "unknown"),
                        evidence=timestamp_evidence,
                        verified=timestamp_evidence.get("kind") == "local-declaration",
                    )
                )
            if log_proof:
                session.add(LogEntry(
                    observation_id=manifest["observation_id"], log_id=log_proof["entry"]["log_id"], leaf_index=log_proof["entry"]["leaf_index"],
                    checkpoint=log_proof["checkpoint"], proof=log_proof,
                ))

    def observation(self, observation_id: str) -> Observation | None:
        with self.session_factory() as session:
            return session.get(Observation, observation_id)

    def observations_for_object(self, object_id: str) -> list[Observation]:
        with self.session_factory() as session:
            return list(session.scalars(select(Observation).where(Observation.object_id == object_id).order_by(Observation.captured_at)))

    def storage_ref(self, observation_id: str) -> StorageRef | None:
        with self.session_factory() as session:
            return session.scalar(select(StorageRef).where(StorageRef.observation_id == observation_id).order_by(StorageRef.id))

    def log_proof(self, observation_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            entry = session.get(LogEntry, observation_id)
            return entry.proof if entry else None

    def timestamp_evidence(self, observation_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            evidence = session.scalar(
                select(TimestampEvidence)
                .where(TimestampEvidence.observation_id == observation_id)
                .order_by(TimestampEvidence.id.desc())
            )
            return evidence.evidence if evidence else None

    def list_observation_ids(self) -> list[str]:
        with self.session_factory() as session:
            return list(session.scalars(select(Observation.observation_id).order_by(Observation.captured_at)))

    def record_conflicts(self, object_id: str, candidate: Observation, simultaneous_window_seconds: int = 300) -> list[Conflict]:
        existing = [item for item in self.observations_for_object(object_id) if item.observation_id != candidate.observation_id]
        created: list[Conflict] = []
        with self.session_factory.begin() as session:
            for prior in existing:
                if prior.raw_content_hash == candidate.raw_content_hash:
                    classification, flag = "identical_content", False
                else:
                    a = datetime.fromisoformat(prior.captured_at.replace("Z", "+00:00"))
                    b = datetime.fromisoformat(candidate.captured_at.replace("Z", "+00:00"))
                    seconds = abs((a - b).total_seconds())
                    classification = "observation_divergence" if seconds <= simultaneous_window_seconds else "temporal_variation"
                    flag = classification == "observation_divergence" and prior.observer_id != candidate.observer_id
                first, second = sorted([prior.observation_id, candidate.observation_id])
                exists = session.scalar(select(Conflict).where(Conflict.observation_a_id == first, Conflict.observation_b_id == second))
                if not exists:
                    row = Conflict(object_id=object_id, observation_a_id=first, observation_b_id=second, classification=classification, is_conflict_candidate=flag, details={"window_seconds": simultaneous_window_seconds})
                    session.add(row)
                    created.append(row)
        return created

    def conflicts_for_object(self, object_id: str) -> list[Conflict]:
        with self.session_factory() as session:
            return list(session.scalars(select(Conflict).where(Conflict.object_id == object_id).order_by(Conflict.id)))
