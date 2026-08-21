const { sanitizeReturnUrl } = require("../safeReturnUrl.ts");

const testVectors = [
  // VALID
  { input: "/", expected: "/" },
  { input: "/articles/foo", expected: "/articles/foo" },
  { input: "/articles/foo?ref=hero", expected: "/articles/foo?ref=hero" },
  { input: "/articles/foo#comments", expected: "/articles/foo#comments" },
  { input: "/news", expected: "/news" },
  { input: "/news?category=ai", expected: "/news?category=ai" },

  // INVALID (must return "/")
  { input: "https://evil.com", expected: "/" },
  { input: "http://evil.com", expected: "/" },
  { input: "//evil.com", expected: "/" },
  { input: "///evil.com", expected: "/" },
  { input: "https://evil.com/path", expected: "/" },
  { input: "//evil.com/path", expected: "/" },
  { input: "javascript:alert(1)", expected: "/" },
  { input: "data:text/html,<h1>phish</h1>", expected: "/" },
  { input: "\\evil.com", expected: "/" },
  { input: "/\\evil.com", expected: "/" },
  { input: "%2F%2Fevil.com", expected: "/" },
  { input: "https:%2F%2Fevil.com", expected: "/" },
  { input: "", expected: "/" },
  { input: null, expected: "/" },
  { input: undefined, expected: "/" },
];

let failed = 0;
for (const tc of testVectors) {
  const actual = sanitizeReturnUrl(tc.input);
  if (actual !== tc.expected) {
    console.error(`FAIL: input=${JSON.stringify(tc.input)} -> expected=${JSON.stringify(tc.expected)}, got=${JSON.stringify(actual)}`);
    failed++;
  } else {
    console.log(`PASS: input=${JSON.stringify(tc.input)} -> ${JSON.stringify(actual)}`);
  }
}

if (failed > 0) {
  console.error(`\n${failed} test(s) failed!`);
  process.exit(1);
} else {
  console.log(`\nAll ${testVectors.length} returnUrl sanitization tests PASSED!`);
}
