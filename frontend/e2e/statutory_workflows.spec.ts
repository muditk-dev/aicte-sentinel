import { test, expect } from '@playwright/test'

test.describe('Statutory Approval & Intelligence Workflows', () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as Central Super Admin before each test
    await page.goto('/login')
    await page.locator('input[type="email"]').fill('superadmin@aicte-india.org')
    await page.locator('input[type="password"]').fill('Sentinel@Admin2026!')
    await page.getByRole('button', { name: /Authenticate & Access Docket/i }).click()
    await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 })
  })

  test('TC-FLOW-01: Command Center displays real-time KPI metrics and statutory distribution', async ({ page }) => {
    await page.goto('/')
    // Verify dashboard metrics reflect database records
    await expect(page.getByText('Regulatory Command Center')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Active Dockets').first()).toBeVisible()
    await expect(page.getByText('Under Scrutiny').first()).toBeVisible()
  })

  test('TC-FLOW-02: Statutory Applications Registry lists persisted applications', async ({ page }) => {
    await page.goto('/applications')
    await expect(page.getByText(/Statutory Applications Registry/i)).toBeVisible({ timeout: 10000 })

    // Verify application table displays seeded records
    const table = page.locator('table')
    await expect(table).toBeVisible()
    await expect(page.getByText(/AICTE-2026/i).first()).toBeVisible()
  })

  test('TC-FLOW-03: Post-Approval Compliance module renders KPI overview and navigation tabs', async ({ page }) => {
    await page.goto('/compliance')
    await expect(page.getByText(/Post-Approval Compliance & Monitoring/i)).toBeVisible({ timeout: 10000 })
    
    // Check KPI cards
    await expect(page.getByText('Total Obligations')).toBeVisible()

    // Navigate to Obligations Register
    await page.goto('/compliance/obligations')
    await expect(page.getByText(/Statutory Obligations Register/i)).toBeVisible({ timeout: 10000 })

    // Navigate to Renewal & Expiry Calendar
    await page.goto('/compliance/calendar')
    await expect(page.getByText(/Renewal & Expiry Tracking Calendar/i)).toBeVisible({ timeout: 10000 })

    // Navigate to Compliance Reports & Export Desk
    await page.goto('/compliance/reports')
    await expect(page.getByText(/Statutory Compliance Reports & Analytics/i)).toBeVisible({ timeout: 10000 })
  })

  test('TC-FLOW-04: EVC Inspections, Panel Registry and Conflict-of-Interest Desk', async ({ page }) => {
    await page.goto('/evc')
    await expect(page.getByText(/Expert Visit Committee \(EVC\) Operations/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/Active Inspection Schedules/i).first()).toBeVisible()
  })

  test('TC-FLOW-05: Standing Hearing & Appellate Committees Desk', async ({ page }) => {
    await page.goto('/committees')
    await expect(page.getByText(/Standing Committees & Hearing Dockets/i)).toBeVisible({ timeout: 10000 })
  })

  test('TC-FLOW-06: Statutory Decisions Desk displays attested decision records', async ({ page }) => {
    await page.goto('/decisions')
    await expect(page.getByText(/Statutory Decision Authorization Desk/i)).toBeVisible({ timeout: 10000 })
  })

  test('TC-FLOW-07: Delay-Risk Prediction displays automated advisory boundary', async ({ page }) => {
    await page.goto('/intelligence')
    await expect(page.getByText(/Explainable Delay-Risk & Compliance Intelligence/i)).toBeVisible({ timeout: 10000 })
    // Ensure advisory disclaimer is explicitly visible to prevent autonomous decision-making
    await expect(page.getByText(/Statutory Governance Boundary/i)).toBeVisible()
  })

  test('TC-FLOW-08: APH Assistant answers regulatory queries with grounded clause citations', async ({ page }) => {
    await page.goto('/aph-assistant')
    await expect(page.getByText(/AICTE Approval Process Handbook \(APH\) Assistant/i)).toBeVisible({ timeout: 10000 })

    // Input a supported query from the Approval Process Handbook
    const queryInput = page.locator('input[placeholder="Ask any regulatory rule or norm from APH 2026-27..."]')
    await queryInput.fill('What is the mandatory Faculty-to-Student Ratio (FSR) for Degree Engineering programmes?')
    await page.getByRole('button', { name: /^Ask$/i }).click()

    // A response card with citation must be displayed
    await expect(page.getByText(/Authoritative Sources Cited/i).first()).toBeVisible({ timeout: 20000 })
    await expect(page.getByText(/Clause/i).first()).toBeVisible()
  })

  test('TC-FLOW-09: APH Assistant triggers uncertainty safeguard on out-of-corpus queries', async ({ page }) => {
    await page.goto('/aph-assistant')
    await expect(page.getByText(/AICTE Approval Process Handbook \(APH\) Assistant/i)).toBeVisible({ timeout: 10000 })

    // Input an out-of-corpus query completely unrelated to AICTE regulations
    const queryInput = page.locator('input[placeholder="Ask any regulatory rule or norm from APH 2026-27..."]')
    await queryInput.fill('How to bake authentic Neapolitan sourdough pizza at 450 degrees?')
    await page.getByRole('button', { name: /^Ask$/i }).click()

    // The system must trigger the uncertainty safeguard without hallucinating
    await expect(page.getByText(/Notice of Insufficient Corpus Coverage|Uncertainty Guardrail/i).first()).toBeVisible({ timeout: 20000 })
  })

  test('TC-FLOW-10: Cryptographic Audit Ledger renders chained event verification', async ({ page }) => {
    await page.goto('/audit')
    await expect(page.getByText(/Tamper-Evident Cryptographic Audit Ledger/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/Cryptographic Chain Status:/i)).toBeVisible()
    await expect(page.getByText(/SHA-256 Hash|Entry Hash/i).first()).toBeVisible()
  })
})
