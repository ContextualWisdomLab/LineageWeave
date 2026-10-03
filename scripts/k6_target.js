/** Validate a credential-bearing target before reading any runtime token. */
export function credentialTarget(value, name) {
  const https = /^https:\/\/[^/@\\\s?#]+(?:\/[^\\\s?#]*)?$/i;
  const loopback = /^http:\/\/(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]+)?(?:\/[^\\\s?#]*)?$/i;
  if (!https.test(value) && !loopback.test(value)) {
    throw new Error(`${name} requires HTTPS or HTTP on an exact loopback host`);
  }
  return value;
}
