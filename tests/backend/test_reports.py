"""
Tests for the reports endpoints, including the filter support that lets the
Reports page respond to the global filter bar.
"""


class TestReportsEndpoints:
    """Tests for /api/reports/quarterly and /api/reports/monthly-trends."""

    def test_get_quarterly_reports(self, client):
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        for key in ("quarter", "total_orders", "total_revenue", "avg_order_value", "fulfillment_rate"):
            assert key in first

    def test_get_monthly_trends(self, client):
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for key in ("month", "order_count", "revenue"):
            assert key in data[0]

    def test_quarterly_warehouse_filter_reduces_orders(self, client):
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get("/api/reports/quarterly?warehouse=Tokyo").json()
        total_all = sum(q["total_orders"] for q in unfiltered)
        total_tokyo = sum(q["total_orders"] for q in filtered)
        # Filtering to one warehouse must not increase the order count, and (given
        # the seed data has multiple warehouses) should strictly reduce it.
        assert 0 < total_tokyo < total_all

    def test_monthly_trends_status_filter(self, client):
        filtered = client.get("/api/reports/monthly-trends?status=Delivered").json()
        # Every counted order was Delivered, so delivered_count equals order_count per month.
        for month in filtered:
            assert month["delivered_count"] == month["order_count"]

    def test_filter_matching_nothing_returns_empty(self, client):
        data = client.get("/api/reports/quarterly?warehouse=Nowhere").json()
        assert data == []
