## 1.4.5

### Fixed
- Safari no longer suggests saving or updating passwords on both the setup screen and the settings page — password fields now use a text input with CSS masking to avoid browser credential detection

## 1.4.4

### Fixed
- Safari no longer suggests saving or updating passwords when entering Bring! credentials

## 1.4.3

### Fixed
- Horizontal scroll no longer possible on mobile — `overflow-x: hidden` now explicitly set on `.content`

## 1.4.2

### Fixed
- "Aktualisieren" button in the list select row now matches the select field height exactly
- Removed `max-width: 900px` from `.main` — content expands to fill available width when the sidebar is collapsed on desktop

## 1.4.1

### Fixed
- "Jetzt synchronisieren" button on mobile shows icon only — text hidden to prevent topbar overflow

## 1.4.0

### Changed
- Replaced Gunicorn with Waitress as WSGI server — single process with 2 threads instead of master + worker fork; saves ~10–20 MB RAM in idle
- Added `gc.collect()` after each sync cycle in the daemon to return memory to the OS after processing

### Removed
- `gunicorn` dependency replaced by `waitress>=3.0.0`

## 1.3.2

### Fixed
- Bring! logo now visible in the topbar on mobile (was only inside the hidden sidebar)

## 1.3.1

### Fixed
- Mobile article grid reduced from 4 to 3 columns so section labels no longer overflow
- Topbar is now sticky on mobile — stays visible while scrolling
- List select field fills full width on mobile, matching email/password field size

## 1.3.0

### Added
- Settings page auto-loads available Bring! lists in the background on open when credentials are already saved
- README.md for the GitHub repository

### Changed
- "Listen laden" button label changes to "Aktualisieren" after initial auto-load
- Silent auto-fetch: errors suppressed on automatic background load

## 1.2.1

### Changed
- Web UI uses the colored `bring-logo.svg` everywhere instead of gray inline SVG
- Added Flask route `/bring-logo.svg` with correct MIME type

## 1.2.0

### Added
- Mobile-responsive UI — sidebar becomes a slide-in overlay on small screens
- Sidebar toggle button in topbar: collapses to icon-only on desktop, hamburger on mobile
- Desktop sidebar collapse state persisted in `localStorage`
- `DOCS.md` and `CHANGELOG.md`

### Changed
- List picker in Settings replaced with a native `<select>` dropdown
- "Save & sync" button moved to a standalone footer row below all settings cards
- `autocomplete="off"` on email, `autocomplete="new-password"` on password field
- `config.yaml`: added `startup: application` and `boot: auto`

## 1.1.0

### Added
- Support for multiple TRMNL webhook URLs
- Section/category mapping: items grouped by Bring! store sections
- `load_catalog_sections` in `bring_api.py`

### Fixed
- Encoding-aware `sections_map` for special characters in item IDs
- Icon resolution fallback returns default icon when normalized name is empty

## 1.0.0

### Added
- Initial Home Assistant add-on release
- Bring! API integration with product icons
- TRMNL Custom Plugin webhook push
- Poll loop with configurable intervals and MD5 change detection
- Web UI via HA Ingress: Dashboard, Settings, Logs
- First-run setup wizard
