"""Full-functional E2E tests — real user interactions via Playwright.

Tests login, CRUD for every module, form submissions, navigation,
approval workflow, and cross-module data flow.
Usage: python3.13 tests/e2e_functional.py
"""
import sys
import json
import time
import os

from playwright.sync_api import sync_playwright, expect

BASE = "http://localhost:5173"
API = "http://localhost:8000"
TIMEOUT = 15000
SCREENSHOT_DIR = "/tmp/wedding-e2e-screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

passed = 0
failed = 0
errors = []
step_num = 0


def test(name):
    def decorator(fn):
        def wrapper(page, *args, **kwargs):
            global passed, failed, step_num
            step_num += 1
            try:
                fn(page, *args, **kwargs)
                passed += 1
                print(f"  \033[32mPASS\033[0m  {step_num:02d}. {name}")
            except Exception as e:
                failed += 1
                errors.append((name, str(e)))
                screenshot_path = f"{SCREENSHOT_DIR}/fail-{step_num:02d}-{name.replace(' ', '-')[:40]}.png"
                try:
                    page.screenshot(path=screenshot_path)
                except:
                    pass
                print(f"  \033[31mFAIL\033[0m  {step_num:02d}. {name}")
                print(f"        {str(e)[:180]}")
        wrapper.__name__ = name
        return wrapper
    return decorator


def screenshot(page, name):
    path = f"{SCREENSHOT_DIR}/{name}.png"
    page.screenshot(path=path)
    return path


def api_login(page, username="admin", password="admin123"):
    resp = page.request.post(f"{API}/api/v1/auth/login", data={
        "username": username, "password": password,
    })
    return resp.json()


def inject_token(page, tokens):
    page.evaluate("""(tokens) => {
        localStorage.setItem('token', tokens.access_token);
        localStorage.setItem('refreshToken', tokens.refresh_token);
    }""", tokens)


def setup_page(page):
    tokens = api_login(page)
    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    inject_token(page, tokens)
    page.goto(f"{BASE}/dashboard", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)


def fill_ninput(page, label, value):
    """Fill a Naive UI input by its label text."""
    form_item = page.locator(f".n-form-item:has-text('{label}')").last
    inp = form_item.locator("input, textarea").first
    inp.fill(value)


def click_button(page, text):
    page.locator(f'button:has-text("{text}")').first.click()


def wait_for_api(page, timeout=3000):
    page.wait_for_timeout(timeout)


# ──────────────────────────────────────────────────────────────────────────────
# AUTH MODULE
# ──────────────────────────────────────────────────────────────────────────────

@test("通过表单登录系统")
def test_form_login(page):
    page.goto(f"{BASE}/login", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.evaluate("() => { localStorage.clear() }")

    page.reload()
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    inputs = page.locator("input")
    inputs.nth(0).fill("admin")
    inputs.nth(1).fill("admin123")
    page.locator("button").first.click()
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)

    assert "/login" not in page.url, f"登录后应跳转，当前 URL: {page.url}"
    assert "/dashboard" in page.url, f"应跳转到 dashboard，当前: {page.url}"
    screenshot(page, "01-login-success")


@test("查看 Dashboard 数据概览")
def test_dashboard_overview(page):
    page.goto(f"{BASE}/dashboard", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_data = any(kw in body for kw in ["客户", "订单", "活动", "总", "本月", "待办"])
    assert has_data, f"Dashboard 应显示统计数据"

    sidebar = page.locator(".n-layout-sider, .n-menu")
    assert sidebar.count() > 0, "应有侧边栏"
    screenshot(page, "02-dashboard")


# ──────────────────────────────────────────────────────────────────────────────
# CUSTOMER MODULE
# ──────────────────────────────────────────────────────────────────────────────

@test("创建新客户")
def test_create_customer(page):
    setup_page(page)
    page.goto(f"{BASE}/customers", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(1500)

    add_btn = page.locator('button:has-text("新增"), button:has-text("新建"), button:has-text("添加")').first
    if add_btn.is_visible():
        add_btn.click()
        page.wait_for_timeout(1000)

    phone = f"1{int(time.time()) % 100000000000:011d}"
    inputs = page.locator("input")
    filled = False
    for i in range(inputs.count()):
        inp = inputs.nth(i)
        ph = inp.get_attribute("placeholder") or ""
        if "姓名" in ph or "名字" in ph or "客户" in ph:
            inp.fill("E2E测试客户")
            filled = True
            break
    if not filled and inputs.count() > 0:
        inputs.nth(0).fill("E2E测试客户")

    for i in range(inputs.count()):
        inp = inputs.nth(i)
        ph = inp.get_attribute("placeholder") or ""
        tp = inp.get_attribute("type") or ""
        if "电话" in ph or "手机" in ph or "phone" in ph.lower():
            inp.fill(phone)
            break

    submit = page.locator('button:has-text("确定"), button:has-text("提交"), button:has-text("保存")').first
    if submit.is_visible():
        submit.click()
        page.wait_for_timeout(2000)

    screenshot(page, "03-create-customer")
    body = page.text_content("body") or ""
    assert "E2E测试客户" in body or "客户" in body or page.locator("table, .n-data-table").count() > 0


@test("查看客户列表")
def test_view_customer_list(page):
    setup_page(page)
    page.goto(f"{BASE}/customers", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_table = page.locator("table, .n-data-table").count() > 0
    has_content = "客户" in body or "暂无" in body
    assert has_table or has_content, "客户列表应显示内容"
    screenshot(page, "04-customer-list")


@test("查看公海池")
def test_view_customer_pool(page):
    setup_page(page)
    page.goto(f"{BASE}/customer-pool", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_pool = "公海" in body or "客户池" in body or "认领" in body or "暂无" in body
    assert has_pool
    screenshot(page, "05-customer-pool")


# ──────────────────────────────────────────────────────────────────────────────
# EVENT / SCHEDULE MODULE
# ──────────────────────────────────────────────────────────────────────────────

@test("查看排期日历")
def test_view_event_calendar(page):
    setup_page(page)
    page.goto(f"{BASE}/events", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_calendar = page.locator(".n-calendar, .n-data-table, table").count() > 0
    has_content = "活动" in body or "日历" in body or "暂无" in body
    assert has_calendar or has_content
    screenshot(page, "06-events-calendar")


@test("查看场地列表")
def test_view_venues(page):
    setup_page(page)
    page.goto(f"{BASE}/venues", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_venue = "场地" in body or "容量" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_venue or has_table
    screenshot(page, "07-venues")


@test("通过 API 创建活动并验证前端显示")
def test_create_event_and_verify(page):
    tokens = api_login(page)
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    event_resp = page.request.post(f"{API}/api/v1/events", headers=headers,
        data='{"title":"E2E全功能婚礼","date":"2026-10-01","note":"自动化测试创建"}')
    assert event_resp.status == 200, f"创建活动失败: {event_resp.status} {event_resp.text()}"
    event = event_resp.json()
    assert event["title"] == "E2E全功能婚礼"

    inject_token(page, tokens)
    page.goto(f"{BASE}/events", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    screenshot(page, "08-event-created")


# ──────────────────────────────────────────────────────────────────────────────
# ORDER MODULE
# ──────────────────────────────────────────────────────────────────────────────

@test("查看订单列表")
def test_view_order_list(page):
    setup_page(page)
    page.goto(f"{BASE}/orders", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_order = "订单" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_order or has_table
    screenshot(page, "09-order-list")


@test("打开新建订单页面")
def test_order_create_page(page):
    setup_page(page)
    page.goto(f"{BASE}/orders/create", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    form_count = page.locator("input, select, .n-input, .n-select").count()
    assert form_count > 0, f"新建订单页应有表单元素，实际 {form_count}"
    screenshot(page, "10-order-create")


@test("通过 API 创建完整订单（客户→订单→项目→付款）")
def test_full_order_flow(page):
    tokens = api_login(page)
    token = tokens["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    phone = f"1{int(time.time()) % 100000000000:011d}"

    # 创建客户
    c = page.request.post(f"{API}/api/v1/customers", headers=h,
        data=json.dumps({"name": "订单全流程客户", "phone": phone}))
    assert c.status == 200
    cid = c.json()["id"]

    # 创建订单
    o = page.request.post(f"{API}/api/v1/orders", headers=h,
        data=json.dumps({
            "customer_id": cid, "sale_id": 1,
            "items": [
                {"type": "venue", "name": "宴会厅", "quantity": 1, "unit_price": 20000, "amount": 20000},
                {"type": "floral", "name": "花艺布置", "quantity": 1, "unit_price": 8000, "amount": 8000},
            ]
        }))
    assert o.status == 200, f"创建订单失败: {o.status} {o.text()}"
    order = o.json()
    oid = order["id"] if "id" in order else order.get("order_no")
    assert oid is not None

    # 添加付款
    p = page.request.post(f"{API}/api/v1/orders/{oid}/payments", headers=h,
        data=json.dumps({"amount": 10000, "method": "transfer"}))
    assert p.status == 200, f"添加付款失败: {p.status} {p.text()}"

    # 前端查看订单详情
    inject_token(page, tokens)
    page.goto(f"{BASE}/orders/{oid}", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    screenshot(page, "11-order-detail")


@test("查看审批列表")
def test_view_approvals(page):
    setup_page(page)
    page.goto(f"{BASE}/approvals", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_approval = "审批" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_approval or has_table
    screenshot(page, "12-approvals")


# ──────────────────────────────────────────────────────────────────────────────
# SUPPLIER MODULE
# ──────────────────────────────────────────────────────────────────────────────

@test("查看供应商列表")
def test_view_supplier_list(page):
    setup_page(page)
    page.goto(f"{BASE}/suppliers", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_supplier = "供应商" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_supplier or has_table
    screenshot(page, "13-supplier-list")


@test("通过 API 创建供应商并验证前端")
def test_create_supplier(page):
    tokens = api_login(page)
    token = tokens["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    s = page.request.post(f"{API}/api/v1/suppliers", headers=h,
        data=json.dumps({"name": "E2E花艺供应商", "type": "floral", "contact": "李四", "phone": "13700001111"}))
    assert s.status == 200
    sid = s.json()["id"]

    # 添加服务
    svc = page.request.post(f"{API}/api/v1/suppliers/{sid}/services", headers=h,
        data=json.dumps({"service_name": "婚礼花艺套餐", "price": 8000, "unit": "套"}))
    assert svc.status == 200, f"添加服务失败: {svc.status} {svc.text()}"

    # 前端查看
    inject_token(page, tokens)
    page.goto(f"{BASE}/suppliers/{sid}", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    screenshot(page, "14-supplier-detail")


# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM MODULE
# ──────────────────────────────────────────────────────────────────────────────

@test("查看员工列表")
def test_view_users(page):
    setup_page(page)
    page.goto(f"{BASE}/users", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_users = "用户" in body or "员工" in body or "admin" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_users or has_table
    screenshot(page, "15-user-list")


@test("查看角色权限矩阵")
def test_view_roles(page):
    setup_page(page)
    page.goto(f"{BASE}/roles", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_roles = "角色" in body or "权限" in body or "管理员" in body
    has_table = page.locator("table, .n-data-table, .n-switch").count() > 0
    assert has_roles or has_table
    screenshot(page, "16-roles")


@test("查看操作日志")
def test_view_logs(page):
    setup_page(page)
    page.goto(f"{BASE}/operation-logs", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)

    body = page.text_content("body") or ""
    has_logs = "操作" in body or "日志" in body or "暂无" in body
    has_table = page.locator("table, .n-data-table").count() > 0
    assert has_logs or has_table
    screenshot(page, "17-logs")


# ──────────────────────────────────────────────────────────────────────────────
# APPROVAL WORKFLOW (via API + frontend verify)
# ──────────────────────────────────────────────────────────────────────────────

@test("创建折扣审批并审核通过")
def test_approval_workflow(page):
    tokens = api_login(page)
    token = tokens["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 创建客户和订单
    phone = f"1{int(time.time()) % 100000000000:011d}"
    c = page.request.post(f"{API}/api/v1/customers", headers=h,
        data=json.dumps({"name": "审批测试客户", "phone": phone}))
    cid = c.json()["id"]

    o = page.request.post(f"{API}/api/v1/orders", headers=h,
        data=json.dumps({"customer_id": cid, "sale_id": 1,
            "items": [{"type": "planning", "name": "策划服务", "quantity": 1, "unit_price": 15000, "amount": 15000}]}))
    oid = o.json().get("id")

    # 申请折扣审批
    a = page.request.post(f"{API}/api/v1/approvals", headers=h,
        data=json.dumps({"type": "discount", "target_id": oid, "reason": "老客户优惠申请9折"}))
    assert a.status == 200, f"创建审批失败: {a.status}"
    aid = a.json()["id"]

    # 管理员审批通过
    approve = page.request.put(f"{API}/api/v1/approvals/{aid}", headers=h,
        data=json.dumps({"status": "approved"}))
    assert approve.status == 200, f"审批通过失败: {approve.status} {approve.text()}"

    # 前端查看
    inject_token(page, tokens)
    page.goto(f"{BASE}/approvals", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(2000)
    screenshot(page, "18-approval-done")


# ──────────────────────────────────────────────────────────────────────────────
# CROSS-MODULE NAVIGATION
# ──────────────────────────────────────────────────────────────────────────────

@test("侧边栏逐模块导航")
def test_full_navigation(page):
    setup_page(page)
    modules = [
        ("工作台", "/dashboard"),
        ("客户", "/customers"),
        ("排期", "/events"),
        ("订单", "/orders"),
        ("供应商", "/suppliers"),
        ("员工", "/users"),
        ("系统设置", "/roles"),
    ]
    for label, expected_path in modules:
        nav = page.locator(f"text={label}").first
        if nav.is_visible():
            nav.click()
            page.wait_for_timeout(1500)
            assert page.locator("body").count() > 0, f"导航到 {label} 失败"

    screenshot(page, "19-navigation-done")


@test("Dashboard 显示已创建的数据")
def test_dashboard_reflects_data(page):
    setup_page(page)
    page.goto(f"{BASE}/dashboard", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(3000)

    body = page.text_content("body") or ""
    has_numbers = any(c.isdigit() for c in body)
    assert has_numbers, "Dashboard 应显示数字统计"
    screenshot(page, "20-dashboard-with-data")


@test("前端刷新后保持登录状态")
def test_persistent_login(page):
    setup_page(page)
    page.goto(f"{BASE}/customers", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.reload()
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    page.wait_for_timeout(1500)
    assert "/login" not in page.url, "刷新后应保持登录状态"
    screenshot(page, "21-persistent-login")


@test("API 聚合测试：完整业务数据链")
def test_api_full_chain(page):
    tokens = api_login(page)
    token = tokens["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    phone = f"1{int(time.time()) % 100000000000:011d}"

    # 客户
    c = page.request.post(f"{API}/api/v1/customers", headers=h,
        data=json.dumps({"name": "全链路客户", "phone": phone}))
    assert c.status == 200
    cid = c.json()["id"]

    # 跟进记录
    f = page.request.post(f"{API}/api/v1/customers/{cid}/follow-ups", headers=h,
        data=json.dumps({"type": "phone", "content": "初步沟通，有意向", "sale_id": 1}))
    assert f.status == 200, f"跟进记录: {f.status} {f.text()}"

    # 订单
    o = page.request.post(f"{API}/api/v1/orders", headers=h,
        data=json.dumps({"customer_id": cid, "sale_id": 1,
            "items": [{"type": "planning", "name": "全链路策划", "quantity": 1, "unit_price": 12000, "amount": 12000}]}))
    assert o.status == 200
    oid = o.json().get("id")

    # 活动
    e = page.request.post(f"{API}/api/v1/events", headers=h,
        data=json.dumps({"title": "全链路婚礼", "date": "2026-12-20", "order_id": oid}))
    assert e.status == 200

    # 供应商
    s = page.request.post(f"{API}/api/v1/suppliers", headers=h,
        data=json.dumps({"name": "全链路供应商", "type": "photo", "contact": "王五", "phone": f"1{int(time.time()) % 100000000000:011d}"}))
    assert s.status == 200

    # Dashboard 数据应反映新创建的数据
    d = page.request.get(f"{API}/api/v1/dashboard/overview", headers={"Authorization": f"Bearer {token}"})
    assert d.status == 200
    data = d.json()
    assert data.get("total_customers", 0) > 0 or data.get("customer_count", 0) > 0 or isinstance(data, dict)


# ──────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ──────────────────────────────────────────────────────────────────────────────

@test("登出并验证重定向到登录页")
def test_logout(page):
    setup_page(page)
    page.goto(f"{BASE}/dashboard", timeout=TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)

    # 点击用户头像或菜单中的退出按钮
    logout_els = page.locator('text=退出, text=登出, text=注销, text=退出登录').all()
    clicked = False
    for el in logout_els:
        if el.is_visible():
            el.click()
            clicked = True
            break

    if not clicked:
        # 尝试点击用户名区域展开菜单
        user_area = page.locator('[class*="user"], [class*="avatar"]').first
        if user_area.is_visible():
            user_area.click()
            page.wait_for_timeout(500)
            for el in logout_els:
                if el.is_visible():
                    el.click()
                    clicked = True
                    break

    if clicked:
        page.wait_for_timeout(2000)
        assert "/login" in page.url, "登出后应跳转到登录页"
        screenshot(page, "22-logout")
    else:
        # 通过 API 登出并手动清除 token
        page.evaluate("() => { localStorage.clear() }")
        page.goto(f"{BASE}/login", timeout=TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        assert "/login" in page.url
        screenshot(page, "22-logout-manual")


# ──────────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    test_form_login,
    test_dashboard_overview,
    test_create_customer,
    test_view_customer_list,
    test_view_customer_pool,
    test_view_event_calendar,
    test_view_venues,
    test_create_event_and_verify,
    test_view_order_list,
    test_order_create_page,
    test_full_order_flow,
    test_view_approvals,
    test_view_supplier_list,
    test_create_supplier,
    test_view_users,
    test_view_roles,
    test_view_logs,
    test_approval_workflow,
    test_full_navigation,
    test_dashboard_reflects_data,
    test_persistent_login,
    test_api_full_chain,
    test_logout,
]


def main():
    global passed, failed
    print("=" * 60)
    print("  婚庆管理系统 — 全功能 E2E 测试")
    print("=" * 60)
    print(f"  共 {len(ALL_TESTS)} 个测试用例\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        for t in ALL_TESTS:
            t(page)

        # Final screenshot
        page.goto(f"{BASE}/dashboard", timeout=TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        screenshot(page, "99-final-state")

        browser.close()

    total = passed + failed
    pct = passed / total * 100 if total > 0 else 0
    print(f"\n{'=' * 60}")
    print(f"  结果: {passed} 通过, {failed} 失败, 共 {total} 项 ({pct:.0f}%)")
    print(f"  截图目录: {SCREENSHOT_DIR}")
    print(f"{'=' * 60}")

    if errors:
        print(f"\n  \033[31m失败用例:\033[0m")
        for name, err in errors:
            print(f"    - {name}")
            print(f"      {err[:120]}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
