/**
 * E2E test placeholder for switcher grayscale mechanism.
 *
 * M1 第一页迁移时启用，验证 switcher → 跳转 → 回跳完整链路。
 *
 * Items to verify when unskipping:
 * 1. Flask page renders {% block spa_switcher %} with link to /app/<page>
 * 2. Clicking switcher link navigates to SPA page
 * 3. SPA page shows "回到经典版" link when enableBackToClassic={true}
 * 4. Clicking "回到经典版" navigates back to Flask page
 * 5. Telemetry events are emitted for both directions
 */
import { test, expect } from "@playwright/test";

test.skip("switcher: Flask → SPA → back-to-classic roundtrip", async ({ page }) => {
  // Placeholder: enable when M1 first page migration is complete
  // 1. Navigate to Flask page
  // 2. Verify spa_switcher block is visible
  // 3. Click "试试新版 →"
  // 4. Assert SPA page loaded with "回到经典版" link
  // 5. Click "回到经典版"
  // 6. Assert back on Flask page
});