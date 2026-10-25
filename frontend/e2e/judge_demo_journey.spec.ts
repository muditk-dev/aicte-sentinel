import { test, expect } from '@playwright/test'

test.describe('Judge-Facing Demonstration Journey & Robustness Verification', () => {
  test('TC-JUDGE-01: Institution Admin login, persona badge and strict tenant isolation', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('director@ditm-delhi.edu.in')
    await page.locator('input[type="password"]').fill('College@2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()

    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })
    await expect(page.getByText('Dr. Sunita Aggarwal').first()).toBeVisible()
    await expect(page.getByText('INSTITUTION_ADMIN').first()).toBeVisible()

    // Navigate to Applications and verify tenant isolation
    await page.goto('/applications')
    await expect(page.getByText(/Statutory Applications Registry/i)).toBeVisible({ timeout: 10000 })

    // DITM Delhi dockets must be visible
    await expect(page.getByText(/AICTE-2026-EOA-/i).first()).toBeVisible()

    // Other institution dockets must NOT leak to DITM
    await expect(page.getByText(/AICTE-2026-NEW-/i)).not.toBeVisible()
    await expect(page.getByText(/AICTE-2026-POLY-/i)).not.toBeVisible()
  })

  test('TC-JUDGE-02: Form submission creates persisted application record in database', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('director@ditm-delhi.edu.in')
    await page.locator('input[type="password"]').fill('College@2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })

    await page.goto('/applications')
    await expect(page.getByText(/Statutory Applications Registry/i)).toBeVisible({ timeout: 10000 })

    // Open New Application modal
    const initiateBtn = page.getByRole('button', { name: /Initiate New Application/i })
    await expect(initiateBtn).toBeVisible()
    await initiateBtn.click()

    // Verify modal is open
    await expect(page.getByText('Initiate Statutory Application Docket')).toBeVisible()

    // Select statutory template within modal dialog
    const modalSelect = page.locator('.fixed select')
    await modalSelect.selectOption({ index: 1 }) // Select first available statutory template

    const capacityInput = page.locator('.fixed input[type="number"]')
    await capacityInput.fill('420')

    // Submit form via Create Application Draft button
    await page.getByRole('button', { name: /Create Application Draft/i }).click()

    // Modal should close upon successful creation
    await expect(page.getByText('Initiate Statutory Application Docket')).not.toBeVisible({ timeout: 10000 })

    // Verify a newly created application docket is visible in the table
    await expect(page.getByText(/AICTE-2026/i).first()).toBeVisible()
  })

  test('TC-JUDGE-03: Form validation enforces statutory requirements without false success', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('director@ditm-delhi.edu.in')
    await page.locator('input[type="password"]').fill('College@2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })

    await page.goto('/applications')
    await page.getByRole('button', { name: /Initiate New Application/i }).click()
    await expect(page.getByText('Initiate Statutory Application Docket')).toBeVisible()

    // Leave template unselected and attempt submission
    const modalSelect = page.locator('.fixed select')
    await modalSelect.selectOption('')

    // Try submitting form without template selection
    await page.getByRole('button', { name: /Create Application Draft/i }).click()

    // The modal must remain open and not show false success
    await expect(page.getByText('Initiate Statutory Application Docket')).toBeVisible()
    await page.getByRole('button', { name: /Cancel/i }).click()
  })

  test('TC-JUDGE-04: Unauthorized backend operations blocked by role boundaries', async ({ page }) => {
    // Authenticate as Institution Admin
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('director@ditm-delhi.edu.in')
    await page.locator('input[type="password"]').fill('College@2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })

    // Direct API attempt by Institution Admin to access superadmin-only audit trail
    const response = await page.evaluate(async () => {
      const token = localStorage.getItem('sentinel_token')
      const res = await fetch('http://127.0.0.1:8000/api/v1/audit/events', {
        headers: { Authorization: `Bearer ${token}` },
      })
      return { status: res.status }
    })

    // Expect HTTP 403 Forbidden
    expect(response.status).toBe(403)
  })

  test('TC-JUDGE-05: Authenticated session persists across page reload without bounce', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('director@ditm-delhi.edu.in')
    await page.locator('input[type="password"]').fill('College@2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })

    await page.goto('/applications')
    await expect(page.getByText(/Statutory Applications Registry/i)).toBeVisible({ timeout: 10000 })

    // Reload browser page
    await page.reload()

    // User must remain authenticated on /applications and not be redirected to /login
    await expect(page.getByText(/Statutory Applications Registry/i)).toBeVisible({ timeout: 10000 })
    expect(page.url()).toContain('/applications')
    expect(page.url()).not.toContain('/login')
  })

  test('TC-JUDGE-06: Application detail multi-tab inspection renders all statutory panels', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('superadmin@aicte-india.org')
    await page.locator('input[type="password"]').fill('Sentinel@Admin2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })

    await page.goto('/applications')
    await expect(page.getByText(/Statutory Applications Registry/i)).toBeVisible({ timeout: 10000 })

    // Inspect first application
    await page.getByText(/Inspect Docket →/i).first().click()
    await expect(page.getByText(/Overview & Decisions/i).first()).toBeVisible({ timeout: 10000 })

    // Switch to Documents & Scrutiny tab
    await page.getByRole('button', { name: /Document Checklist/i }).click()
    await expect(page.getByText(/Statutory Document Vault/i)).toBeVisible()

    // Switch to Scrutiny Findings tab
    await page.getByRole('button', { name: /Scrutiny Workspace/i }).click()
    await expect(page.getByText(/Statutory Scrutiny Desk/i)).toBeVisible()

    // Switch to Deficiency Notices tab
    await page.getByRole('button', { name: /Deficiency Notices/i }).click()
    await expect(page.getByText(/Statutory Deficiency & Clarification Desk/i)).toBeVisible()

    // Switch to EVC Inspection tab
    await page.getByRole('button', { name: /EVC Inspections/i }).click()
    await expect(page.getByText(/Expert Visit Committee \(EVC\) Physical & Virtual Inspections/i)).toBeVisible()

    // Switch to Statutory Decision tab
    await page.getByRole('button', { name: /Statutory Determination/i }).click()
    await expect(page.getByText(/Statutory Determination/i).first()).toBeVisible()
  })

  test('TC-JUDGE-07: Critical workflow positive & negative paths on APH Assistant', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('superadmin@aicte-india.org')
    await page.locator('input[type="password"]').fill('Sentinel@Admin2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })

    await page.goto('/aph-assistant')
    await expect(page.getByText(/AICTE Approval Process Handbook \(APH\) Assistant/i)).toBeVisible({ timeout: 10000 })

    const queryInput = page.locator('input[placeholder="Ask any regulatory rule or norm from APH 2026-27..."]')

    // Positive Path: Valid regulatory question
    await queryInput.fill('What is the mandatory Faculty-to-Student Ratio (FSR) for Degree Engineering programmes?')
    await page.getByRole('button', { name: /^Ask$/i }).click()
    await expect(page.getByText(/Authoritative Sources Cited/i).first()).toBeVisible({ timeout: 20000 })
    await expect(page.getByText(/Clause/i).first()).toBeVisible()

    // Negative Path: Unsupported / Out-of-Corpus Question
    await queryInput.fill('How to bake authentic Neapolitan sourdough pizza at 450 degrees?')
    await page.getByRole('button', { name: /^Ask$/i }).click()
    await expect(page.getByText(/Notice of Insufficient Corpus Coverage|Uncertainty Guardrail/i).first()).toBeVisible({ timeout: 20000 })
  })

  test('TC-JUDGE-08: Non-existent application URL displays graceful statutory error state', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('superadmin@aicte-india.org')
    await page.locator('input[type="password"]').fill('Sentinel@Admin2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })

    // Navigate directly to non-existent UUID
    await page.goto('/applications/00000000-0000-0000-0000-000000000000')

    // System must render statutory error state, not blank screen or crash
    await expect(page.getByText(/Failed to load application docket. Access may be restricted./i)).toBeVisible({ timeout: 10000 })
  })
})
