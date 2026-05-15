# Packaging on macOS

The app ships as a native `.app` bundle wrapped in a `.dmg`, built with
[briefcase](https://briefcase.readthedocs.io/). This document covers the
mechanics. The release flow itself runs in CI — see
`.github/workflows/release.yml`.

## Local dry-run

Build the bundle from scratch on your own Mac:

```bash
# 1. Build the frontend and copy it into the backend's static dir.
cd frontend
npm ci
npm run build
cd ..
bash scripts/copy-frontend-dist.sh

# 2. Install briefcase + project deps.
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[build]"

# 3. Create the project skeleton briefcase scaffolds out.
briefcase create macOS --no-input

# 4. Compile the .app.
briefcase build macOS --no-input

# 5. (Optional) Run the .app straight from the build tree.
briefcase run macOS --no-input

# 6. (Optional) Wrap it in a .dmg. Ad-hoc signed — Gatekeeper will warn.
briefcase package macOS --no-input --adhoc-sign
```

The resulting `.app` lives in `backend/build/ra3-inventory/macos/app/`,
and the `.dmg` (when packaged) lands under `backend/dist/`.

## Architecture and minimum OS

| Setting | Value | Source |
|---|---|---|
| Universal binary | x86_64 + arm64 | `tool.briefcase.app.ra3-inventory.macOS.universal_build = true` |
| Minimum macOS | 12.0 (Monterey) | `min_os_version` |
| Python | 3.12, vendored by briefcase | briefcase support package |
| Entitlements | `com.apple.security.network.client = true` | pyproject |

The `network.client` entitlement is **load-bearing**. Without it the
notarized build cannot make outbound TLS connections to the processor —
the LEAP client fails at handshake time. Briefcase's default entitlement
set omits it, so we set it explicitly.

## Signing and notarization (stub — not yet wired)

The current release workflow uses **ad-hoc signing** (`--adhoc-sign`).
That produces a runnable bundle but Gatekeeper will refuse to launch it
on a fresh Mac without the user right-clicking → Open and approving the
warning. Once the project has a real Apple Developer ID Application
identity, the path to a fully-trusted release is:

1. **Provision the identity locally** with Xcode → Certificates.
   Confirm with `security find-identity -v -p codesigning` that the
   identity shows up.
2. **Export it as a `.p12`** and base64-encode it (`base64 -i id.p12 | pbcopy`).
3. **Add three GitHub secrets to the repository:**
   - `MACOS_CERTIFICATE` — base64 of the .p12.
   - `MACOS_CERTIFICATE_PASSWORD` — the .p12 password.
   - `MACOS_NOTARY_PROFILE` — an App-Specific-Password or
     App-Store-Connect API key bundle for `notarytool`.
4. **Replace** the `briefcase package macOS --adhoc-sign` step in
   `.github/workflows/release.yml` with a script that:
   - Imports the cert into a temporary keychain.
   - Runs `briefcase package macOS --identity "Developer ID Application: ..."`.
   - Submits the resulting .dmg to `xcrun notarytool submit --wait`.
   - Staples the ticket: `xcrun stapler staple <dmg>`.

Until that's in place, releases are **for technical users** who are
comfortable bypassing Gatekeeper. The README warns about this.

## Icon

The `icon = "../docs/icon"` line in `backend/pyproject.toml` is commented
out — briefcase falls back to its default Python feather icon. To replace
it:

- Design a 1024×1024 PNG (or commit a multi-resolution `.icns`).
- Save as `docs/icon.png` (or `docs/icon.icns`).
- Uncomment the `icon = "../docs/icon"` line.
- Briefcase auto-converts a PNG to the macOS `.icns` format at build
  time, or uses the `.icns` directly if you commit one.

## CI

Two workflows touch packaging:

- **`ci.yml` → `package-macos`** runs `briefcase create` + `build` on
  every push and PR. It catches "I broke pyproject.toml" or "I added a
  dep briefcase doesn't know how to bundle" before tag time.
- **`release.yml`** runs `briefcase package macOS --adhoc-sign` on every
  `v*` tag push, then uploads the resulting `.dmg` and `.app.zip` to the
  GitHub release page.

`~/.briefcase` is cached between runs in CI; the support-package download
costs ~200 MB on a cold cache and a few seconds on a warm one.
