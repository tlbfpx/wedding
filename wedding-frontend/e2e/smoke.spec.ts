import { test, expect } from '@playwright/test'

test.describe('婚庆管理系统 E2E 测试', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173')
    await page.waitForLoadState('networkidle')
  })

  async function login(page: any) {
    await page.locator('input[placeholder="请输入用户名"]').fill('admin')
    await page.locator('input[placeholder="请输入密码"]').fill('admin123')
    await page.locator('button:has-text("登录")').click()
    await page.waitForTimeout(3000)
  }

  test('首页加载', async ({ page }) => {
    await expect(page).toHaveTitle(/.*/)
    await expect(page.locator('body')).toBeVisible()
  })

  test('健康检查端点', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/health')
    expect(response.ok()).toBeTruthy()
    const json = await response.json()
    expect(json.status).toBe('ok')
  })

  test('API文档可访问', async ({ page }) => {
    await page.goto('http://localhost:8000/api/docs')
    await expect(page.locator('body')).toBeVisible()
  })

  test('健康检查端点响应时间', async ({ request }) => {
    const start = Date.now()
    await request.get('http://localhost:8000/api/v1/health')
    const duration = Date.now() - start
    expect(duration).toBeLessThan(5000)
  })

  test('登录功能 - 成功', async ({ page }) => {
    await login(page)
    // 验证登录成功：登录按钮消失或URL变化
    const loginButton = page.locator('button:has-text("登录")')
    const url = page.url()
    // 如果URL包含dashboard或customers等页面，或者登录按钮消失，说明登录成功
    const loggedIn = url.includes('dashboard') || url.includes('customer') || url.includes('order') || !(await loginButton.isVisible().catch(() => true))
    expect(loggedIn).toBeTruthy()
  })

  test('登录失败 - 错误提示', async ({ page }) => {
    await page.locator('input[placeholder="请输入用户名"]').fill('wrong')
    await page.locator('input[placeholder="请输入密码"]').fill('wrong123')
    await page.locator('button:has-text("登录")').click()
    await page.waitForTimeout(1000)
    // 登录按钮仍然可见，说明还在登录页
    await expect(page.locator('button:has-text("登录")')).toBeVisible()
  })

  test('CSRF端点可用', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/auth/csrf')
    expect(response.ok()).toBeTruthy()
    const json = await response.json()
    expect(json.csrf_token).toBeDefined()
    expect(json.csrf_token.length).toBeGreaterThan(16)
  })

  test('Metrics端点返回Prometheus格式', async ({ request }) => {
    const response = await request.get('http://localhost:8000/metrics')
    expect(response.ok()).toBeTruthy()
    const text = await response.text()
    expect(text).toContain('http_requests_total')
  })

  test('Ready端点返回服务状态', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/ready')
    expect(response.ok()).toBeTruthy()
    const json = await response.json()
    expect(json.services).toBeDefined()
    expect(json.services.redis).toBeDefined()
  })
})