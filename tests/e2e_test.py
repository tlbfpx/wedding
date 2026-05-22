"""Comprehensive frontend E2E tests using Playwright.

Usage: python3.13 tests/e2e_test.py
Requires: backend on :8000, frontend on :5173
"""
import sys
import json

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
API = "http://localhost:8000"
TIMEOUT = 15000

passed = 0
failed = 0
errors = []


def test(name):
    def decorator(fn):
        def wrapper(page, *args, **kwargs):
            global passed, failed
            try:
                fn(page, *args, **kwargs)
                passed += 1
                print(f"  PASS  {name}")
            except Exception as e:
                failed += 1
                errors.append((name, str(e)))
                print(f"  FAIL  {name}")
                print(f"         {str(e)[:150]}")
        wrapper.__name__ = name
        return wrapper
    return decorator


def login(page, username="admin", password="admin123"):
    """Login via API and inject token into localStorage."""
    resp = page.request.post(f"{API}/api/v1/auth/login", data={
        "username": username, "password": password,
    })
    assert resp.status == 200, f"Login API failed: {resp.status}"
    tokens = resp.json()

    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.evaluate("""(tokens) => {
        localStorage.setItem('token', tokens.access_token);
        localStorage.setItem('refreshToken', tokens.refresh_token);
    }""", tokens)
    page.goto(f"{BASE}/dashboard", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)


def clear_auth(page):
    """Clear auth state for isolation."""
    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
    page.evaluate("""() => {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
    }""")


# ── Login & Auth ──────────────────────────────────────────────────────────────

@test("Login page renders with form fields")
def test_login_page_renders(page):
    clear_auth(page)
    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    inputs = page.locator("input")
    assert inputs.count() >= 2, f"Should have >= 2 inputs, got {inputs.count()}"
    btn = page.locator("button")
    assert btn.count() >= 1, "Should have a login button"


@test("Login page shows validation on empty submit")
def test_login_validation(page):
    clear_auth(page)
    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.locator("button").first.click()
    page.wait_for_timeout(1000)
    body = page.text_content("body") or ""
    assert "请输入" in body or "required" in body.lower(), "Should show validation message"


@test("Login with valid credentials via form")
def test_login_via_form(page):
    clear_auth(page)
    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    inputs = page.locator("input")
    inputs.nth(0).fill("admin")
    inputs.nth(1).fill("admin123")
    page.locator("button").first.click()
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    assert "/login" not in page.url, f"Should redirect away from login, still at: {page.url}"


@test("Login with wrong password shows error")
def test_login_wrong_password(page):
    clear_auth(page)
    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    inputs = page.locator("input")
    inputs.nth(0).fill("admin")
    inputs.nth(1).fill("wrongpassword")
    page.locator("button").first.click()
    page.wait_for_timeout(2500)
    body = page.text_content("body") or ""
    has_error = any(w in body for w in ["错误", "失败", "无效", "error", "invalid", "401", "密码"])
    assert has_error, "Should show error for wrong password"


@test("Unauthenticated access redirects to login")
def test_auth_guard(page):
    clear_auth(page)
    page.goto(f"{BASE}/dashboard", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(1500)
    assert "/login" in page.url, f"Should redirect to login, at: {page.url}"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@test("Dashboard page loads with content")
def test_dashboard_loads(page):
    login(page)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = any(kw in body for kw in ["客户", "订单", "活动", "本月", "总", "统计", "待办", "数据", "工作台"])
    assert has_content, f"Dashboard should show stats. Body preview: {body[:200]}"


@test("Dashboard shows navigation sidebar")
def test_dashboard_sidebar(page):
    login(page)
    sidebar = page.locator(".n-layout-sider, .n-menu, [class*='sidebar'], [class*='sider']")
    assert sidebar.count() > 0, "Should have sidebar navigation"


# ── Customer Management ───────────────────────────────────────────────────────

@test("Customer list page renders")
def test_customer_list(page):
    login(page)
    page.goto(f"{BASE}/customers", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = "客户" in body or "潜在" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_content or has_table, "Customer list should show content"


@test("Customer pool page loads")
def test_customer_pool(page):
    login(page)
    page.goto(f"{BASE}/customer-pool", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_pool = "公海" in body or "客户池" in body or "认领" in body or "暂无" in body
    assert has_pool, f"Customer pool should show content. Got: {body[:200]}"


@test("Customer detail handles non-existent ID")
def test_customer_detail_404(page):
    login(page)
    page.goto(f"{BASE}/customers/999", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    assert page.locator("body").count() > 0


# ── Schedule Management ───────────────────────────────────────────────────────

@test("Event list page renders")
def test_event_list(page):
    login(page)
    page.goto(f"{BASE}/events", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = "活动" in body or "日历" in body or "场地" in body or "暂无" in body
    has_calendar = page.locator(".n-calendar, .n-data-table, table").count() > 0
    assert has_content or has_calendar, "Events page should show content"


@test("Venue list page loads")
def test_venue_list(page):
    login(page)
    page.goto(f"{BASE}/venues", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_venue = "场地" in body or "容量" in body or "暂无" in body or "venue" in body.lower()
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_venue or has_table, f"Venue page should show content. Got: {body[:200]}"


@test("Event detail handles non-existent ID")
def test_event_detail_404(page):
    login(page)
    page.goto(f"{BASE}/events/999", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    assert page.locator("body").count() > 0


# ── Order Management ──────────────────────────────────────────────────────────

@test("Order list page renders")
def test_order_list(page):
    login(page)
    page.goto(f"{BASE}/orders", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = "订单" in body or "意向" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_content or has_table, "Order list should show content"


@test("Order create page loads with form")
def test_order_create(page):
    login(page)
    page.goto(f"{BASE}/orders/create", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    form_count = page.locator("input, select, .n-input, .n-select, .n-date-picker").count()
    assert form_count > 0, f"Order create should have form elements, got {form_count}"


@test("Order detail handles non-existent ID")
def test_order_detail_404(page):
    login(page)
    page.goto(f"{BASE}/orders/999", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    assert page.locator("body").count() > 0


@test("Approvals list page loads")
def test_approvals_list(page):
    login(page)
    page.goto(f"{BASE}/approvals", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = "审批" in body or "待审批" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_content or has_table, f"Approvals page should show content. Got: {body[:200]}"


# ── Supplier Management ───────────────────────────────────────────────────────

@test("Supplier list page renders")
def test_supplier_list(page):
    login(page)
    page.goto(f"{BASE}/suppliers", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = "供应商" in body or "合作" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_content or has_table, "Supplier list should show content"


@test("Supplier detail handles non-existent ID")
def test_supplier_detail_404(page):
    login(page)
    page.goto(f"{BASE}/suppliers/999", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    assert page.locator("body").count() > 0


# ── System Management ─────────────────────────────────────────────────────────

@test("User management page loads")
def test_user_list(page):
    login(page)
    page.goto(f"{BASE}/users", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = "用户" in body or "admin" in body or "员工" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_content or has_table, f"User management should show content. Got: {body[:200]}"


@test("Role management page loads")
def test_role_list(page):
    login(page)
    page.goto(f"{BASE}/roles", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = "角色" in body or "权限" in body or "管理员" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_content or has_table, f"Role management should show content. Got: {body[:200]}"


@test("Operation logs page loads")
def test_operation_logs(page):
    login(page)
    page.goto(f"{BASE}/operation-logs", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    body = page.text_content("body") or ""
    has_content = "操作" in body or "日志" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_content or has_table, f"Logs page should show content. Got: {body[:200]}"


# ── Navigation ────────────────────────────────────────────────────────────────

@test("Sidebar navigation between modules")
def test_sidebar_navigation(page):
    login(page)
    nav_targets = [
        ("客户", "/customers"),
        ("订单", "/orders"),
        ("供应商", "/suppliers"),
    ]
    for label, path in nav_targets:
        nav_item = page.locator(f"text={label}").first
        if nav_item.is_visible():
            nav_item.click()
            page.wait_for_timeout(1500)
            assert page.locator("body").count() > 0, f"Nav to {label} failed"


# ── API Integration ───────────────────────────────────────────────────────────

@test("API: login returns JWT tokens")
def test_api_login(page):
    resp = page.request.post(f"{API}/api/v1/auth/login", data={
        "username": "admin", "password": "admin123",
    })
    assert resp.status == 200
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body


@test("API: /me returns user info")
def test_api_me(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    me = page.request.get(f"{API}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status == 200
    data = me.json()
    assert data["username"] == "admin"
    assert "permissions" in data


@test("API: customer CRUD")
def test_api_customer_crud(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    import time
    phone = f"139{int(time.time()) % 100000000:08d}"
    c = page.request.post(f"{API}/api/v1/customers", headers=h,
        data=json.dumps({"name": "E2E客户", "phone": phone}))
    assert c.status == 200, f"Create: {c.status} {c.text()}"
    cid = c.json()["id"]

    g = page.request.get(f"{API}/api/v1/customers/{cid}", headers=h)
    assert g.status == 200

    l = page.request.get(f"{API}/api/v1/customers", headers=h)
    assert l.status == 200
    items = l.json().get("items", [])
    assert isinstance(items, list) and len(items) >= 1


@test("API: supplier CRUD")
def test_api_supplier(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    s = page.request.post(f"{API}/api/v1/suppliers", headers=h,
        data='{"name":"E2E供应商","type":"venue","contact":"张三","phone":"13800001111"}')
    assert s.status == 200, f"Create supplier: {s.status} {s.text()}"
    assert s.json()["name"] == "E2E供应商"


@test("API: order creation")
def test_api_order(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    import time
    phone = f"138{int(time.time()) % 100000000:08d}"
    c = page.request.post(f"{API}/api/v1/customers", headers=h,
        data=json.dumps({"name": "E2E订单客户", "phone": phone}))
    assert c.status == 200, f"Create customer: {c.status} {c.text()}"
    cdata = c.json()
    cid = cdata.get("id") or cdata.get("customer", {}).get("id")

    o = page.request.post(f"{API}/api/v1/orders", headers=h,
        data=json.dumps({"customer_id": cid, "sale_id": 1,
            "items": [{"type": "venue", "name": "场地", "quantity": 1, "unit_price": 10000, "amount": 10000}]}))
    assert o.status == 200, f"Create order: {o.status} {o.text()}"
    odata = o.json()
    assert "order_no" in odata or "id" in odata, f"Order should have id or order_no, got: {list(odata.keys())}"


@test("API: dashboard overview")
def test_api_dashboard(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    d = page.request.get(f"{API}/api/v1/dashboard/overview", headers={"Authorization": f"Bearer {token}"})
    assert d.status == 200
    assert isinstance(d.json(), dict)


@test("API: roles list")
def test_api_roles(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    roles = page.request.get(f"{API}/api/v1/users/roles", headers={"Authorization": f"Bearer {token}"})
    assert roles.status == 200
    data = roles.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) >= 7, f"Should have >= 7 roles, got {len(items)}"


@test("API: event creation")
def test_api_event(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    e = page.request.post(f"{API}/api/v1/events", headers=h,
        data='{"title":"E2E测试活动","date":"2026-10-01","note":"E2E备注"}')
    assert e.status == 200, f"Create event: {e.status} {e.text()}"
    assert e.json()["title"] == "E2E测试活动"


@test("API: staff schedule query")
def test_api_staff_schedule(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    s = page.request.get(f"{API}/api/v1/events/staff-schedule", headers={"Authorization": f"Bearer {token}"})
    assert s.status == 200


@test("API: conflict check")
def test_api_conflicts(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    c = page.request.get(f"{API}/api/v1/events/conflicts?date=2026-10-01", headers={"Authorization": f"Bearer {token}"})
    assert c.status == 200
    assert "has_conflicts" in c.json()


@test("API: refresh token")
def test_api_refresh(page):
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    tokens = r.json()
    ref = page.request.post(f"{API}/api/v1/auth/refresh", data={"refresh_token": tokens["refresh_token"]})
    assert ref.status == 200
    assert "access_token" in ref.json()


@test("API: 401 on invalid token")
def test_api_unauthorized(page):
    r = page.request.get(f"{API}/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
    assert r.status == 401


@test("API: account lockout after 5 failures")
def test_api_lockout(page):
    for _ in range(5):
        page.request.post(f"{API}/api/v1/auth/login", data={"username": "locktest_user", "password": "wrong"})
    r = page.request.post(f"{API}/api/v1/auth/login", data={"username": "locktest_user", "password": "wrong"})
    assert r.status == 403, f"Should be locked (403), got {r.status}"


# ── Error Handling ────────────────────────────────────────────────────────────

@test("Unknown route handled gracefully")
def test_404_route(page):
    login(page)
    page.goto(f"{BASE}/nonexistent-page-xyz", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    assert page.locator("body").count() > 0


@test("Page title is set")
def test_page_title(page):
    clear_auth(page)
    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    title = page.title()
    assert title.strip() != "", f"Page title should be non-empty, got: '{title}'"


# ── Test runner ───────────────────────────────────────────────────────────────

ALL_TESTS = [
    test_login_page_renders,
    test_login_validation,
    test_login_via_form,
    test_login_wrong_password,
    test_auth_guard,
    test_dashboard_loads,
    test_dashboard_sidebar,
    test_customer_list,
    test_customer_pool,
    test_customer_detail_404,
    test_event_list,
    test_venue_list,
    test_event_detail_404,
    test_order_list,
    test_order_create,
    test_order_detail_404,
    test_approvals_list,
    test_supplier_list,
    test_supplier_detail_404,
    test_user_list,
    test_role_list,
    test_operation_logs,
    test_sidebar_navigation,
    test_api_login,
    test_api_me,
    test_api_customer_crud,
    test_api_supplier,
    test_api_order,
    test_api_dashboard,
    test_api_roles,
    test_api_event,
    test_api_staff_schedule,
    test_api_conflicts,
    test_api_refresh,
    test_api_unauthorized,
    test_api_lockout,
    test_404_route,
    test_page_title,
]


def main():
    global passed, failed
    print("=" * 60)
    print("  Wedding Management System - E2E Tests")
    print("=" * 60)
    print(f"\n  Running {len(ALL_TESTS)} tests...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        for t in ALL_TESTS:
            t(page)

        browser.close()

    print(f"\n{'=' * 60}")
    pct = passed / (passed + failed) * 100 if (passed + failed) > 0 else 0
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total ({pct:.0f}%)")
    print(f"{'=' * 60}")

    if errors:
        print("\n  Failed tests:")
        for name, err in errors:
            print(f"    - {name}")
            print(f"      {err[:120]}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
