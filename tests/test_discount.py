# -*- coding: utf-8 -*-
"""
Discount engine tests
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_discount_levels():
    """Test all discount levels 10,20,30,40,60"""
    from services.discount_engine import DiscountEngine
    from services.product_service import ProductService
    
    de = DiscountEngine()
    ps = ProductService()
    
    # Create product
    prod = ps.create_product(
        name="TestProdDisc",
        normal_price=100.0,
        minimum_price=40.0
    )
    if prod is None:
        prods = ps.get_all_products()
        prod = next((p for p in prods if p["name"] == "TestProdDisc"), None)
    pid = prod["id"]
    
    # 10%
    res = de.validate_discount(pid, 10)
    assert res["valid"] is True
    
    # 20%
    res = de.validate_discount(pid, 20)
    assert res["valid"] is True
    
    # 30%
    res = de.validate_discount(pid, 30)
    assert res["valid"] is True
    
    # 40%
    res = de.validate_discount(pid, 40)
    assert res["valid"] is True
    
    # 60%
    res = de.validate_discount(pid, 60)
    assert res["valid"] is True
    assert res.get("is_final_offer") is True
    
    ps.delete_product(pid)


def test_discount_rejections():
    """Test rejection cases"""
    from services.discount_engine import DiscountEngine
    from services.product_service import ProductService
    
    de = DiscountEngine()
    ps = ProductService()
    
    prod = ps.create_product(
        name="TestProdDisc2",
        normal_price=100.0,
        minimum_price=40.0
    )
    if prod is None:
        prods = ps.get_all_products()
        prod = next((p for p in prods if p["name"] == "TestProdDisc2"), None)
    pid = prod["id"]
    
    # %61 reject
    res = de.validate_discount(pid, 61)
    assert res["valid"] is False
    
    # %100 reject
    res = de.validate_discount(pid, 100)
    assert res["valid"] is False
    
    # Minimum price below
    res = de.validate_discount(pid, 70)  # 30 < 40
    assert res["valid"] is False
    
    # Undefined code
    res = de.validate_discount(pid, 10, discount_code="UNKNOWN")
    assert res["valid"] is False
    
    ps.delete_product(pid)


def test_60_is_final():
    """%60 sonrası yeni indirim → reject"""
    from services.discount_engine import DiscountEngine
    from services.product_service import ProductService
    
    de = DiscountEngine()
    ps = ProductService()
    
    prod = ps.create_product(
        name="TestProdDisc3",
        normal_price=100.0,
        minimum_price=40.0
    )
    if prod is None:
        prods = ps.get_all_products()
        prod = next((p for p in prods if p["name"] == "TestProdDisc3"), None)
    pid = prod["id"]
    
    # After 60% (has final offer)
    res = de.validate_discount(pid, 60)
    assert res["valid"] is True
    assert res.get("is_final_offer") is True
    
    # Now try another discount - has final offer true
    res2 = de.validate_discount(pid, 10, has_final_offer=True)
    assert res2["valid"] is False
    
    ps.delete_product(pid)


def test_discount_code_valid():
    """Test valid discount code"""
    from services.discount_engine import DiscountEngine
    from services.product_service import ProductService
    
    de = DiscountEngine()
    ps = ProductService()
    
    prod = ps.create_product(
        name="TestProdDisc4",
        normal_price=100.0,
        minimum_price=40.0,
        discount_codes=[
            {"code": "ABC10", "discount_percent": 10},
            {"code": "ABC20", "discount_percent": 20},
            {"code": "ABC30", "discount_percent": 30},
            {"code": "ABC40", "discount_percent": 40},
            {"code": "ABC60", "discount_percent": 60},
        ]
    )
    if prod is None:
        prods = ps.get_all_products()
        prod = next((p for p in prods if p["name"] == "TestProdDisc4"), None)
    pid = prod["id"]
    
    res = de.validate_discount(pid, 10, discount_code="ABC10")
    assert res["valid"] is True
    
    res = de.validate_discount(pid, 60, discount_code="ABC60")
    assert res["valid"] is True
    
    # Wrong code match
    res = de.validate_discount(pid, 20, discount_code="ABC10")
    assert res["valid"] is False
    
    ps.delete_product(pid)
