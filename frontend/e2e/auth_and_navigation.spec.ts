import { test, expect } from '@playwright/test'

test.describe('Authentication & Protected Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Clear cookies and local storage before each test
    await page.goto('/login')
    await page.evaluate(() => localStorage.clear())
  })

  test('TC-AUTH-01: Displays login page with official AICTE branding and statutory disclaimers', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('h2')).toContainText('AICTE SENTINEL')
    await expect(page.getByText('Statutory Regulatory Workflow & Compliance Portal')).toBeVisible()
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.getByRole('button', { name: /Authenticate & Access Docket/i })).toBeVisible()
  })

  test('TC-AUTH-02: Rejects invalid credentials with statutory error alert', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('invalid.user@aicte-india.org')
    await page.locator('input[type="password"]').fill('WrongPassword123!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()

    // Error alert must appear
    const alertBox = page.locator('div.bg-rose-50')
    await expect(alertBox).toBeVisible({ timeout: 10000 })
    await expect(alertBox).toContainText(/Authentication failed|Invalid email or password/i)
  })

  test('TC-AUTH-03: Authenticates Institution Admin and lands on Command Center', async ({ page }) => {
    await page.goto('/login')
    
    // Fill credentials for seeded institution signatory
    await page.locator('input[type="email"]').fill('director@ditm-delhi.edu.in')
    await page.locator('input[type="password"]').fill('College@2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()

    // Must navigate to Command Center (/)
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })
    await expect(page.getByText('Dr. Sunita Aggarwal').first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('INSTITUTION_ADMIN').first()).toBeVisible()
  })

  test('TC-AUTH-04: Enforces protected routes by redirecting unauthenticated visits to login', async ({ page }) => {
    // Navigate directly to protected application and compliance routes without auth
    await page.goto('/applications')
    await page.waitForURL('**/login', { timeout: 10000 })
    expect(page.url()).toContain('/login')

    await page.goto('/compliance')
    await page.waitForURL('**/login', { timeout: 10000 })
    expect(page.url()).toContain('/login')

    await page.goto('/audit')
    await page.waitForURL('**/login', { timeout: 10000 })
    expect(page.url()).toContain('/login')
  })

  test('TC-AUTH-05: Logs out cleanly and clears session credentials', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('director@ditm-delhi.edu.in')
    await page.locator('input[type="password"]').fill('College@2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })

    // Click Sign Out
    const signOutBtn = page.getByRole('button', { name: /Sign Out/i })
    await expect(signOutBtn).toBeVisible()
    await signOutBtn.click()

    // Must redirect to /login and clear token
    await page.waitForURL('**/login', { timeout: 10000 })
    const token = await page.evaluate(() => localStorage.getItem('sentinel_token'))
    expect(token).toBeNull()
  })

  test('TC-AUTH-06: Authenticates Regional Officer with supervisory navigation privileges', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('ro.delhi@aicte-india.org')
    await page.locator('input[type="password"]').fill('Regional@2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()

    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })
    await expect(page.getByText('Prof. Anita Deshmukh').first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('REGIONAL_OFFICER')).toBeVisible()

    // Navigate to Statutory Decisions
    await page.getByRole('link', { name: /Statutory Decisions/i }).click()
    await page.waitForURL('**/decisions', { timeout: 10000 })
    await expect(page.getByText(/Statutory Decision/i).first()).toBeVisible()
  })
})
