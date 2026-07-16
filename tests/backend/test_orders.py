"""
Tests for the orders endpoints, focused on POST /api/orders/restock.
Covers creation, validation errors, lead-time derivation, and filter interaction.
"""
import re
from datetime import datetime

import pytest


@pytest.fixture(autouse=True)
def restore_orders():
    """Restore the in-memory orders list after each test.

    main.py holds a reference to the same list object, so restoration must
    slice-assign rather than rebind the name.
    """
    import mock_data
    original = list(mock_data.orders)
    yield
    mock_data.orders[:] = original


def _restock_payload(**overrides):
    payload = {
        "budget": 20000,
        "items": [{"sku": "WDG-001", "quantity": 450}]
    }
    payload.update(overrides)
    return payload


class TestRestockOrderEndpoints:
    """Tests for POST /api/orders/restock."""

    def test_create_restock_order_success(self, client):
        response = client.post("/api/orders/restock", json=_restock_payload())
        assert response.status_code == 201
        order = response.json()
        assert order["status"] == "Submitted"
        assert order["customer"] == "Internal Restocking"
        assert re.fullmatch(r"ORD-\d{4}-\d{4}", order["order_number"])
        # Server derives pricing from demand data: 450 * 24.99
        assert abs(order["total_value"] - 11245.50) < 0.01
        assert order["items"][0]["unit_price"] == 24.99
        assert order["items"][0]["lead_time_days"] == 7

    def test_created_order_appears_in_get_orders(self, client):
        created = client.post("/api/orders/restock", json=_restock_payload()).json()
        all_orders = client.get("/api/orders").json()
        assert any(o["id"] == created["id"] for o in all_orders)
        single = client.get(f"/api/orders/{created['id']}")
        assert single.status_code == 200
        assert single.json()["order_number"] == created["order_number"]

    def test_expected_delivery_uses_max_lead_time(self, client):
        payload = _restock_payload(items=[
            {"sku": "WDG-001", "quantity": 10},   # 7 day lead time
            {"sku": "BRG-102", "quantity": 10}    # 14 day lead time
        ])
        order = client.post("/api/orders/restock", json=payload).json()
        order_date = datetime.fromisoformat(order["order_date"])
        expected_delivery = datetime.fromisoformat(order["expected_delivery"])
        assert (expected_delivery - order_date).days == 14

    def test_empty_items_422(self, client):
        response = client.post("/api/orders/restock", json=_restock_payload(items=[]))
        assert response.status_code == 422

    def test_budget_nonpositive_422(self, client):
        for budget in (0, -1):
            response = client.post("/api/orders/restock", json=_restock_payload(budget=budget))
            assert response.status_code == 422

    def test_zero_quantity_422(self, client):
        payload = _restock_payload(items=[{"sku": "WDG-001", "quantity": 0}])
        response = client.post("/api/orders/restock", json=payload)
        assert response.status_code == 422

    def test_unknown_sku_400(self, client):
        payload = _restock_payload(items=[{"sku": "NOPE-999", "quantity": 1}])
        response = client.post("/api/orders/restock", json=payload)
        assert response.status_code == 400
        assert "Unknown SKU" in response.json()["detail"]

    def test_total_exceeds_budget_400(self, client):
        payload = _restock_payload(budget=100, items=[{"sku": "WDG-001", "quantity": 450}])
        response = client.post("/api/orders/restock", json=payload)
        assert response.status_code == 400
        assert "exceeds budget" in response.json()["detail"]

    def test_filter_interaction(self, client):
        payload = _restock_payload(warehouse="Tokyo")
        created = client.post("/api/orders/restock", json=payload).json()

        tokyo = client.get("/api/orders?warehouse=Tokyo").json()
        assert any(o["id"] == created["id"] for o in tokyo)

        london = client.get("/api/orders?warehouse=London").json()
        assert not any(o["id"] == created["id"] for o in london)

        submitted = client.get("/api/orders?status=submitted").json()
        assert any(o["id"] == created["id"] for o in submitted)
