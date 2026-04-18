import fs from 'node:fs'
import path from 'node:path'
import { test, expect } from '@playwright/test'

const baseUrl = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4175'
const imagePath = process.env.E2E_IMAGE ?? '/Users/gimdonghyeon/Downloads/output_746520522.jpg'
const artifactsDir = process.env.E2E_ARTIFACTS_DIR ?? '/Users/gimdonghyeon/Desktop/cscodex/stdev/apps/web/e2e-artifacts'

test.describe.configure({ mode: 'serial' })
test.setTimeout(600000)

test('upload to library flow works end to end', async ({ page }) => {
  fs.mkdirSync(artifactsDir, { recursive: true })

  const consoleErrors = []
  const pageErrors = []
  const requestFailures = []

  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text())
    }
  })

  page.on('pageerror', (error) => {
    pageErrors.push(String(error))
  })

  page.on('requestfailed', (request) => {
    const failureText = request.failure()?.errorText ?? 'failed'
    const url = request.url()
    if (failureText === 'net::ERR_ABORTED' && url.includes('/story-video.mp4')) {
      return
    }
    requestFailures.push(`${request.method()} ${url} :: ${failureText}`)
  })

  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await expect(page.getByRole('heading', { name: '아이들이 세상을 이해하는 방식을 바꿉니다' })).toBeVisible()
  await page.screenshot({ path: path.join(artifactsDir, '01-home.png'), fullPage: true })

  await page.getByRole('button', { name: '일기 올리고 시작하기' }).click()
  await page.waitForURL(/#\/studio\/source/)
  await expect(page.getByText('일기 한 장을 올리고 바로 읽습니다')).toBeVisible()
  await page.screenshot({ path: path.join(artifactsDir, '02-source.png'), fullPage: true })

  await page.locator('input[type="file"]').setInputFiles(imagePath)

  const editor = page.locator('textarea.editor-textarea')
  await page.waitForURL(/#\/studio\/ocr/, { timeout: 60000 })
  await expect(editor).toBeVisible({ timeout: 60000 })
  await expect.poll(async () => (await editor.inputValue()).trim().length, { timeout: 60000 }).toBeGreaterThan(0)
  await page.screenshot({ path: path.join(artifactsDir, '03-ocr.png'), fullPage: true })

  await page.getByRole('button', { name: '탐구 결과 만들기' }).click()
  await page.waitForURL(/#\/studio\/results/)
  await expect(page.getByRole('heading', { name: '오늘의 장면을 과학 질문으로 바꿨습니다' })).toBeVisible()

  await expect
    .poll(async () => {
      const src = await page.locator('video').first().getAttribute('src').catch(() => null)
      return Boolean(src)
    }, { timeout: 420000 })
    .toBeTruthy()

  await expect(page.getByText('생성 완료')).toBeVisible({ timeout: 120000 })
  await expect
    .poll(async () => {
      return page.locator('video').first().evaluate((video) => video.readyState)
    }, { timeout: 30000 })
    .toBeGreaterThanOrEqual(2)
  await page.screenshot({ path: path.join(artifactsDir, '04-results.png'), fullPage: true })

  await page.locator('.result-scene-card-button').first().click()
  await expect(page.getByRole('heading', { name: '현상 요약 더 묻기' })).toBeVisible()
  const initialAssistantBubbleCount = await page.locator('.card-chat-bubble.assistant').count()
  await page.locator('.card-chat-form textarea').fill('안녕')
  await page.getByRole('button', { name: '질문 보내기' }).click()
  await expect
    .poll(async () => await page.locator('.card-chat-bubble.assistant').count(), { timeout: 30000 })
    .toBeGreaterThan(initialAssistantBubbleCount)
  await expect(page.locator('.card-chat-bubble.loading')).toHaveCount(0, { timeout: 30000 })
  await expect
    .poll(async () => await page.locator('.card-chat-bubble.assistant').last().textContent(), { timeout: 30000 })
    .not.toContain('Not Found')
  await expect
    .poll(async () => await page.locator('.card-chat-bubble.assistant').last().textContent(), { timeout: 30000 })
    .not.toContain('지금은 답을 불러오지 못했어요')
  await page.locator('.card-chat-close').click()
  await expect.poll(async () => await page.locator('.card-chat-overlay').count(), { timeout: 10000 }).toBe(0)

  await page.locator('.quiz-choice').first().click()
  await page.getByRole('button', { name: '정답 확인' }).click()
  await expect(page.locator('.challenge-feedback')).toBeVisible()

  const missionAreas = page.locator('.mission-form textarea')
  await missionAreas.nth(0).fill('버찌를 떨어뜨리는 높이를 바꾸면 자국 크기가 달라질 것 같다고 적었다.')
  await missionAreas.nth(1).fill('다음에는 바닥 재질도 함께 비교해 보기로 했다.')
  await page.getByRole('button', { name: '관찰 로그 저장' }).click()
  await expect(page.getByText('버찌를 떨어뜨리는 높이를 바꾸면')).toBeVisible({ timeout: 15000 })

  await page.getByRole('button', { name: '다음 단계' }).click()
  await page.waitForURL(/#\/studio\/library/)
  await expect(page.getByText('최근 결과')).toBeVisible()
  await page.screenshot({ path: path.join(artifactsDir, '05-library.png'), fullPage: true })

  expect(consoleErrors).toEqual([])
  expect(pageErrors).toEqual([])
  expect(requestFailures).toEqual([])
})
