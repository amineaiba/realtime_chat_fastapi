// Takes the README screenshots from a running app with the demo seed data.
//   docker compose up -d --build
//   docker compose exec backend python -m scripts.seed_demo
//   cd frontend && npx playwright install chromium && node scripts/screenshots.mjs
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";

const APP_URL = process.env.APP_URL ?? "http://localhost:5173";
const OUT = new URL("../../docs/screenshots/", import.meta.url).pathname;
const DESKTOP = { width: 1280, height: 800 };
const MOBILE = { width: 390, height: 844 };

async function login(browser, username, viewport) {
  const context = await browser.newContext({ viewport, colorScheme: "dark" });
  const page = await context.newPage();
  await page.goto(`${APP_URL}/login`);
  await page.getByLabel("Email").fill(`${username}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("Password1");
  await page.locator("button[type=submit]").click();
  await page.waitForURL(`${APP_URL}/`);
  return page;
}

async function openRoom(page, name) {
  await page.getByRole("button", { name: new RegExp(name) }).first().click();
  await page.getByPlaceholder(new RegExp(`Message #?${name}`)).waitFor();
}

async function shot(page, name) {
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}${name}.png` });
  console.log(`saved ${name}.png`);
}

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();

// Login page.
const anon = await (await browser.newContext({ viewport: DESKTOP, colorScheme: "dark" })).newPage();
await anon.goto(`${APP_URL}/login`);
await shot(anon, "login");

// Two users online at once, so presence and typing show up.
const sara = await login(browser, "sara", DESKTOP);
const yacine = await login(browser, "yacine", DESKTOP);

await openRoom(sara, "Backend team");
await openRoom(yacine, "Backend team");
await yacine.getByPlaceholder(/Message #?Backend team/).pressSequentially("Deploying now", { delay: 40 });
await sara.getByText("yacine is typing").waitFor();
await shot(sara, "chat");

await sara.getByRole("button", { name: /members/ }).click();
await shot(sara, "chat-members");
await sara.getByRole("button", { name: /members/ }).click();

await sara.getByRole("button", { name: "Backend team" }).last().click();
await shot(sara, "manage-group");
await sara.keyboard.press("Escape");

await sara.getByLabel("Your profile").click();
await sara.waitForURL(`${APP_URL}/profile`);
await shot(sara, "profile");

// Mobile layout.
const mobile = await login(browser, "lina", MOBILE);
await shot(mobile, "mobile-rooms");
await openRoom(mobile, "Backend team");
await shot(mobile, "mobile-chat");

await browser.close();
