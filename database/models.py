# -*- coding: utf-8 -*-
"""
Database models for Sales.aii
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Index, Numeric
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Product(Base):
    """Product model"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    normal_price = Column(Numeric(10, 2), nullable=True)  # Store safely
    minimum_price = Column(Numeric(10, 2), nullable=True)
    shopier_url = Column(String(500), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    offers = relationship("Offer", back_populates="product")
    sales = relationship("Sale", back_populates="product")
    discount_codes = relationship("DiscountCode", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_products_active', 'active'),
    )


class DiscountCode(Base):
    """Product-based discount codes"""
    __tablename__ = "discount_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(100), nullable=False)
    discount_percent = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    difficulty = Column(String(50), nullable=True)  # easy, normal, hard, very_hard
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="discount_codes")

    __table_args__ = (
        Index('ix_discount_codes_product_id', 'product_id'),
        Index('ix_discount_codes_code', 'code'),
        Index('ix_discount_codes_active', 'active'),
    )


class Lead(Base):
    """Lead/Customer model"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    platform = Column(String(100), nullable=False)  # reddit, github, etc.
    platform_id = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    profile_url = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=True)
    need = Column(String(255), nullable=True)
    need_description = Column(Text, nullable=True)
    suggested_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    lead_quality = Column(String(50), nullable=True)  # high, medium, low
    status = Column(String(50), default="new")  # new, contacted, qualified, disqualified
    score = Column(Float, default=0.0)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON or comma-separated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="lead")
    sales = relationship("Sale", back_populates="lead")
    suggested_product = relationship("Product", foreign_keys=[suggested_product_id])

    __table_args__ = (
        Index('ix_leads_platform', 'platform'),
        Index('ix_leads_username', 'username'),
        Index('ix_leads_status', 'status'),
        Index('ix_leads_platform_username', 'platform', 'username', unique=False),
    )


class Conversation(Base):
    """Conversation model"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    agent_type = Column(String(50), nullable=True)  # lead, sales, support
    platform = Column(String(100), nullable=False)
    platform_convo_id = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    status = Column(String(50), default="active")  # active, closed, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = relationship("Lead", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="conversation")

    __table_args__ = (
        Index('ix_conversations_lead_id', 'lead_id'),
        Index('ix_conversations_status', 'status'),
    )


class Message(Base):
    """Message model"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(50), nullable=False)  # user, agent, system
    content = Column(Text, nullable=False)
    platform = Column(String(100), nullable=True)
    message_type = Column(String(50), nullable=True)  # text, offer, image
    status = Column(String(50), default="pending")  # pending, sent, failed
    approved = Column(Boolean, default=True)
    sent = Column(Boolean, default=False)
    external_message_id = Column(String(255), nullable=True)
    external_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index('ix_messages_conversation_id', 'conversation_id'),
        Index('ix_messages_sent', 'sent'),
    )


class Offer(Base):
    """Offer model"""
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    discount_percent = Column(Float, nullable=True)
    discount_code = Column(String(100), nullable=True)
    original_price = Column(Numeric(10, 2), nullable=True)
    final_price = Column(Numeric(10, 2), nullable=True)
    is_final_offer = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="offers")
    product = relationship("Product", back_populates="offers")

    __table_args__ = (
        Index('ix_offers_conversation_id', 'conversation_id'),
    )


class Sale(Base):
    """Sales model"""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=True)
    discount_percent = Column(Float, nullable=True)
    final_price = Column(Numeric(10, 2), nullable=True)
    payment_status = Column(String(50), default="pending")  # pending, paid, refunded, cancelled
    shopier_reference = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="sales")
    conversation = relationship("Conversation")
    product = relationship("Product", back_populates="sales")

    __table_args__ = (
        Index('ix_sales_lead_id', 'lead_id'),
        Index('ix_sales_payment_status', 'payment_status'),
    )


class Settings(Base):
    """Settings model"""
    __tablename__ = "settings"

    key = Column(String(255), primary_key=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Log(Base):
    """Logs model"""
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(50), nullable=False)
    module = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_logs_level', 'level'),
        Index('ix_logs_created_at', 'created_at'),
    )


class Integration(Base):
    """Integration config model"""
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    platform = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=False)
    config = Column(Text, nullable=True)  # JSON config
    status = Column(String(50), default="disconnected")  # connected, disconnected, error
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityLog(Base):
    """Activity log model"""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_type = Column(String(50), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(50), default="success")  # success, error, warning
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_activity_logs_created_at', 'created_at'),
    )
