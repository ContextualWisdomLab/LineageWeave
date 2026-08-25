# Unreleased — OIDC return context is restored before redirect

## Fixed

- The login action now uses the bounded OIDC return-URL helper and persists its
  fallback before redirecting. This restores the tested deep-link contract and
  removes the unused-import TypeScript build failure delivered on `main`.
