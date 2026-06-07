import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Numeric, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    accounts: Mapped[list["Account"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    assets: Mapped[list["Asset"]] = relationship(back_populates="user")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")
    recurring_bills: Mapped[list["RecurringBill"]] = relationship(back_populates="user")
    financial_persona: Mapped[Optional["UserFinancialPersona"]] = relationship(
        back_populates="user", uselist=False
    )


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_type: Mapped[str] = mapped_column(Text, nullable=False)  # bank | credit_card | wallet | cash | loan | mutual_fund | epf | ...
    name: Mapped[str] = mapped_column(Text, nullable=False)
    institution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    loan_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # home | personal | vehicle | education | other
    loan_type_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)  # credit_card only
    sanctioned_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)  # loan only
    interest_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    emi_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    tenure_months: Mapped[Optional[int]] = mapped_column(nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_day: Mapped[Optional[int]] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="INR")
    parent_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True
    )
    account_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # bank only
    ifsc_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # bank only
    branch: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # bank only
    account_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # bank only
    folio_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # MF/RD folio; EPF UAN
    demat_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # stock
    invested_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)  # holdings cost basis
    current_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)  # holdings market value
    investment_mode: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # mutual_fund: one_time | sip
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
    recurring_bills: Mapped[list["RecurringBill"]] = relationship(back_populates="account")
    parent_account: Mapped[Optional["Account"]] = relationship(
        remote_side="Account.id",
        foreign_keys=[parent_account_id],
    )


class RecurringBill(Base):
    """User-defined rent / EMI / subscription-style bills (monthly or weekly)."""

    __tablename__ = "recurring_bills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(Text, nullable=False)  # monthly | weekly
    due_day: Mapped[Optional[int]] = mapped_column(nullable=True)  # 1–31 for monthly
    weekday: Mapped[Optional[int]] = mapped_column(nullable=True)  # 0=Mon .. 6=Sun for weekly
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="recurring_bills")
    account: Mapped["Account"] = relationship(back_populates="recurring_bills")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)  # debit negative, credit positive
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="INR")
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)

    merchant: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")  # import | manual | ai_extracted
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)

    raw_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nw_impact: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    recurring_bill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_bills.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="transactions")
    account: Mapped["Account"] = relationship(back_populates="transactions")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)  # property | mf | stock | gold | other
    name: Mapped[str] = mapped_column(Text, nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    valuation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship(back_populates="assets")


class ImportFingerprint(Base):
    """Store fingerprints of imported transactions to avoid duplicates."""
    __tablename__ = "import_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "fingerprint", name="uq_import_fingerprints_user_fp"),)


class UserFinancialPersona(Base):
    """Per-user copilot profile — preferences and patterns, not financial truth."""

    __tablename__ = "user_financial_personas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    traits: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="financial_persona")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="New Chat")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # 'user' or 'assistant'
    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Store the full JSON AgentResponse generated by the backend
    import sqlalchemy.dialects.postgresql as pg
    agent_response: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
