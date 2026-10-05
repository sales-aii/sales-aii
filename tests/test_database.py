# -*- coding: utf-8 -*-
"""
Database CRUD tests
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_database_initialization():
    """Test database initialization"""
    from database.database import db
    assert db is not None


def test_product_crud():
    """Test product CRUD operations"""
    from services.product_service import ProductService
    
    service = ProductService()
    # Create
    product = service.create_product(
        name="Test Product",
        description="Test Description",
        normal_price=100.00,
        minimum_price=80.00,
        shopier_url="https://example.com",
        active=True
    )
    assert product is not None
    assert product["name"] == "Test Product"
    
    product_id = product["id"]
    
    # Read
    retrieved = service.get_product(product_id)
    assert retrieved is not None
    assert retrieved["id"] == product_id
    
    # Update
    updated = service.update_product(product_id, description="Updated desc")
    assert updated is True
    
    # Get all
    all_products = service.get_all_products()
    assert len(all_products) >= 1
    
    # Get active
    active = service.get_active_products()
    assert len(active) >= 1
    
    # Delete
    deleted = service.delete_product(product_id)
    assert deleted is True


def test_lead_crud():
    """Test lead CRUD operations"""
    from services.lead_service import LeadService
    
    service = LeadService()
    # Create
    lead = service.create_lead(
        platform="reddit",
        username="testuser",
        need="Need test",
        need_description="Desc",
        lead_quality="high",
        status="new"
    )
    assert lead is not None
    assert lead["username"] == "testuser"
    assert lead["platform"] == "reddit"
    
    lead_id = lead["id"]
    
    # Read
    retrieved = service.get_lead(lead_id)
    assert retrieved is not None
    
    # Update
    updated = service.update_lead(lead_id, status="contacted")
    assert updated is True
    
    # Get all
    all_leads = service.get_all_leads()
    assert len(all_leads) >= 1
    
    # Duplicate check
    lead2 = service.create_lead(platform="reddit", username="testuser")
    # Should not create duplicate or return None - returns existing
    assert lead2 is not None
    
    # Delete
    deleted = service.delete_lead(lead_id)
    assert deleted is True


def test_conversation_crud():
    """Test conversation CRUD operations"""
    from services.lead_service import LeadService
    from repositories.conversation_repository import ConversationRepository
    from database.database import db
    
    lead_service = LeadService()
    conv_repo = ConversationRepository()
    
    # Create lead first
    lead = lead_service.create_lead(platform="github", username="convuser")
    lead_id = lead["id"]
    
    with db.session_scope() as session:
        # Create
        conv = conv_repo.create(
            session,
            lead_id=lead_id,
            platform="github",
            status="active"
        )
        assert conv is not None
        conv_id = conv.id
        
        # Read
        retrieved = conv_repo.get_by_id(session, conv_id)
        assert retrieved is not None
        
        # Update
        updated = conv_repo.update(session, conv, status="closed")
        assert updated.status == "closed"
    
    # Cleanup
    lead_service.delete_lead(lead_id)


def test_message_crud():
    """Test message CRUD operations"""
    from services.lead_service import LeadService
    from repositories.conversation_repository import ConversationRepository
    from repositories.message_repository import MessageRepository
    from database.database import db
    
    lead_service = LeadService()
    conv_repo = ConversationRepository()
    msg_repo = MessageRepository()
    
    lead = lead_service.create_lead(platform="reddit", username="msguser")
    lead_id = lead["id"]
    
    with db.session_scope() as session:
        conv = conv_repo.create(session, lead_id=lead_id, platform="reddit", status="active")
        conv_id = conv.id
        
        msg = msg_repo.create(
            session,
            conversation_id=conv_id,
            sender="user",
            content="Hello",
            message_type="text"
        )
        assert msg is not None
        msg_id = msg.id
        
        retrieved = msg_repo.get_by_id(session, msg_id)
        assert retrieved is not None
        
        msgs = msg_repo.get_by_conversation_id(session, conv_id)
        assert len(msgs) >= 1
    
    lead_service.delete_lead(lead_id)


def test_offer_crud():
    """Test offer CRUD operations"""
    from services.lead_service import LeadService
    from services.product_service import ProductService
    from repositories.conversation_repository import ConversationRepository
    from repositories.offer_repository import OfferRepository
    from database.database import db
    
    lead_service = LeadService()
    prod_service = ProductService()
    conv_repo = ConversationRepository()
    offer_repo = OfferRepository()
    
    lead = lead_service.create_lead(platform="reddit", username="offeruser")
    lead_id = lead["id"]
    
    prod = prod_service.create_product(name="OfferProd", normal_price=100)
    if prod is None:
        products = prod_service.get_all_products()
        prod = next((p for p in products if p["name"] == "OfferProd"), None)
    assert prod is not None
    prod_id = prod["id"]
    
    with db.session_scope() as session:
        conv = conv_repo.create(session, lead_id=lead_id, platform="reddit")
        conv_id = conv.id
        
        offer = offer_repo.create(
            session,
            conversation_id=conv_id,
            product_id=prod_id,
            discount_percent=10,
            final_price=90
        )
        assert offer is not None
    
    lead_service.delete_lead(lead_id)
    prod_service.delete_product(prod_id)


def test_sales_crud():
    """Test sales CRUD operations"""
    from services.lead_service import LeadService
    from services.product_service import ProductService
    from repositories.sale_repository import SaleRepository
    from database.database import db
    
    lead_service = LeadService()
    prod_service = ProductService()
    sale_repo = SaleRepository()
    
    lead = lead_service.create_lead(platform="reddit", username="saleuser")
    lead_id = lead["id"]
    
    prod = prod_service.create_product(name="SaleProd", normal_price=200)
    if prod is None:
        products = prod_service.get_all_products()
        prod = next((p for p in products if p["name"] == "SaleProd"), None)
    assert prod is not None
    prod_id = prod["id"]
    
    with db.session_scope() as session:
        sale = sale_repo.create(
            session,
            lead_id=lead_id,
            product_id=prod_id,
            original_price=200,
            discount_percent=20,
            final_price=160,
            payment_status="pending"
        )
        assert sale is not None
    
    lead_service.delete_lead(lead_id)
    prod_service.delete_product(prod_id)


def test_settings_crud():
    """Test settings CRUD operations"""
    from repositories.settings_repository import SettingsRepository
    from database.database import db
    
    repo = SettingsRepository()
    
    with db.session_scope() as session:
        # Set
        s = repo.set(session, "test_key", "test_value")
        assert s is not None
        
        # Get
        val = repo.get_value(session, "test_key")
        assert val == "test_value"
        
        # Update
        s2 = repo.set(session, "test_key", "updated")
        assert s2.value == "updated"
        
        # Get with default
        val2 = repo.get_value(session, "nonexistent", "default")
        assert val2 == "default"
        
        # Delete
        deleted = repo.delete(session, "test_key")
        assert deleted is True
