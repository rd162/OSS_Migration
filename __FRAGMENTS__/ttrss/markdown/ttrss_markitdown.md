<!-- Source: ttrss.xlsx -->
<!-- Converter: markitdown -->
<!-- Generated: 2026-04-06T00:40:56.831445 -->

## Key Test Scenarios
| Key Test Scenarios for TTRSS | Unnamed: 1 | Unnamed: 2 |
| --- | --- | --- |
| NaN | NaN | NaN |
| 1. Feed Management [Core:Feed Management] | NaN | NaN |
| NaN | Subscribe to new feeds (RSS) | NaN |
| NaN | NaN | Verify feed can be added, fetched, and displayed correctly in the UI. |
| NaN | Organize feeds with categories and subfolders | NaN |
| NaN | NaN | Create categories/subfolders, move feeds between them, confirm hierarchy reflects accurately |
| NaN | Import/Export of OPML | NaN |
| NaN | NaN | Test import of an OPML file: confirm feeds appear; test export: ensure the file contains expected subscriptions |
| 2. Feed Aggregation & Display [Core:Article Handling] | NaN | NaN |
| NaN | Pulling updates | NaN |
| NaN | NaN | Verify feed polling runs on schedule, fetches new articles, and displays unread items. |
| NaN | Read/Unread toggling, starring, publishing | NaN |
| NaN | NaN | Mark articles read/unread; star and publish them; ensure they land in appropriate sections (e.g., "Starred") |
| 3. Navigation & Keyboard Shortcuts [Core:Misc] | NaN | NaN |
| NaN | Keyboard-based navigation | NaN |
| NaN | NaN | Use keyboard shortcuts to navigate articles, mark read/star, search, etc., confirming they trigger correctly |
| 4. Filters and Content Processing [Core:Article Handling] | NaN | NaN |
| NaN | Article filtering using regex | NaN |
| NaN | NaN | Set up content filters (e.g., match titles or body, assign tags, delete) and confirm they apply during feed ingestion and live view |
| NaN | Filter ordering and complexities | NaN |
| NaN | NaN | Add multiple filters, reorder them; test inversion flags, multi-rule scenarios, and matching logic |
| 5. Generated Feeds (Export) [Core:Feed Management] | NaN | NaN |
| NaN | Generate Atom/JSON feeds | NaN |
| NaN | NaN | Create generated feeds (e.g. starred, labels), export as Atom/JSON, confirm URL contains correct parameters and returns expected content |
| NaN | Key regeneration | NaN |
| NaN | NaN | Regenerate access key for a feed; test that previous URLs become invalid and new one works |
| 6. Plugins & Themes [Core:Misc] | NaN | NaN |
| NaN | Installing and enabling plugins | NaN |
| NaN | NaN | Install a plugin (e.g., readability, sharing), activate via Preferences, verify function works correctly (e.g., full-article embedding or social sharing) |
| NaN | System vs user plugins | NaN |
| NaN | NaN | Add system-level plugin via PLUGINS config and verify all users have it; test user-level plugin activation separately |
| NaN | Theme functionality | NaN |
| NaN | NaN | Apply a theme (e.g., Feedly-inspired), toggle between light/dark and high‑contrast modes; verify UI layout, mobile responsiveness, plugin compatibility |
| 7. API & JSON [Core:Misc] | NaN | NaN |
| NaN | JSON-based API functionality | NaN |
| NaN | NaN | Use JSON API endpoints to fetch headlines, mark articles read/starred/published, manipulate subscriptions |
| 8. Multi-User and User Settings [Core: User Settings] | NaN | NaN |
| NaN | Single-user vs multi-user mode | NaN |
| NaN | NaN | In single-user mode, verify only admin exists; in multi-user (with SINGLE\_USER\_MODE=false), create users, manage user preferences, verify isolation |
| NaN | User-level settings | NaN |
| NaN | NaN | Test per-user preferences: update interval, theme, date format, digest emails, label creation |
| 9. Full-Text, Deduplication, Podcasts [Core: Article Handling] | NaN | NaN |
| NaN | Readability/full content embedding | NaN |
| NaN | NaN | Enable embedding via plugins; verify that stubs are replaced by full content |
| NaN | Deduplication (including images) | NaN |
| NaN | NaN | Add duplicate articles (exact and image-based); ensure duplicates are removed or merged |
| NaN | Podcast enclosure support | NaN |
| NaN | NaN | Subscribe to a podcast feed; confirm enclosure visible and playable inline |
| 10. Search, Labels, Tagging [Core: Article Handling] | NaN | NaN |
| NaN | Search functionality | NaN |
| NaN | NaN | Perform keyword search within a feed and across feeds; confirm results accuracy |
| NaN | Labels (SQL‑based virtual feeds) | NaN |
| NaN | NaN | Enable labels, create custom label via SQL, verify label content and behavior |
| NaN | Tagging articles | NaN |
| NaN | NaN | Tag articles manually or via filter action; verify tag assignment and listing |
| 11. Security & Access [Core: Misc] | NaN | NaN |
| NaN | SSL/TLS connections | NaN |
| NaN | NaN | Configure via HTTPS; verify secure access to UI and API |
| NaN | Authentication for protected feeds | NaN |
| NaN | NaN | Add feed requiring Digest/Basic auth and confirm successful fetch with credentials |
| NaN | Feed icons and UI assets | NaN |
| NaN | NaN | Test default vs custom feed icons; replace default and verify rendering |
| 12. Preferences | NaN | NaN |
| 13. Localization | NaN | NaN |

## Test Coverage Matrix
| Test Coverage Matrix | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 |
| --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN |
| Test Category | Key Scenarios | Core | NaN | NaN | NaN |
| Feed Management | Subscribe, categorize, import/export OPML | Feed Management | + | NaN | NaN |
| Aggregation & Display | Updating, read/unread toggling, starring/publishing | Article Handling | NaN | NaN | NaN |
| Navigation & UI | Keyboard, mobile interface | Misc | + | NaN | NaN |
| Filtering | Regex filters, ordering, complex rule logic | Article Handling | + | NaN | NaN |
| Generated Feeds | Export, key regeneration | Feed Management | + | NaN | NaN |
| Plugins & Themes | Install, activate, apply themes, plugin behavior | Misc | - | NaN | NaN |
| API Integration | JSON API, Google Reader compatibility | Misc | + | NaN | NaN |
| Multi-user Settings | User accounts, preferences, isolation | User Settings | + | NaN | NaN |
| Content Processing | Full-text, deduplication, podcasts | Article Handling | + | NaN | NaN |
| Search & Labeling | Search across feeds, tags, custom labels | Article Handling | + | NaN | NaN |
| Security | HTTPS access, authenticated feed fetching | Misc | + | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | 2 FE + 1 BE | NaN | 1+1 | NaN | 1+1 |
| NaN | Navigation & UI | NaN | Generated Feeds | NaN | API Integration |
| NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | Multi-user Settings | NaN | Feed Management | NaN | Filtering |
| NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | Aggregation & Display | NaN | Security | NaN | Search & Labeling |
| NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | Search & Labeling |

## User Management
| User Management Test Cases | Unnamed: 1 |
| --- | --- |
| NaN | NaN |
| 1. User Creation | NaN |
| NaN | Create a new user via admin interface (username, password, email) and confirm account is listed under Users. |
| NaN | Try to create a user with an existing username — expect error: duplicate username. |
| NaN | Create user with special characters in username/email — ensure proper validation. |
| NaN | Verify created user can log in and see empty dashboard/feed list by default. |
| 2.User Roles / Permissions | NaN |
| NaN | Assign admin privileges to a user and verify access to admin functions (user mgmt, system config). |
| NaN | Verify a non-admin user cannot access /prefs.php?tab=users or other admin-only pages (returns error or redirect). |
| NaN | Downgrade admin to regular user and confirm admin access is revoked. |
| 3. User Authentication | NaN |
| NaN | Attempt login with correct and incorrect credentials — verify expected success/failure. |
| NaN | Verify login/logout flow; check that session is destroyed after logout. |
| NaN | Test session expiration after inactivity (depends on server config). |
| NaN | Attempt login with disabled account — verify login is rejected. |
| NaN | Brute-force protection: after multiple failed login attempts, ensure throttling or error feedback. |
| 4. User Preferences & Isolation | NaN |
| NaN | Verify that each user has isolated feeds, categories, and settings — changes in one user account don't affect others. |
| NaN | User changes personal preferences (theme, date format, update interval) — verify persistence after logout/login. |
| NaN | User imports OPML — verify feeds appear only for that user. |
| NaN | Confirm starred, published, labeled articles are scoped to the user. |
| 5. Password Management | NaN |
| NaN | Admin resets user password — verify that new credentials work and old password fails. |
| NaN | User changes own password — requires current password and confirmation. |
| NaN | Try setting weak or blank password — should fail with appropriate validation. |
| NaN | Attempt to change another user’s password as non-admin — should be rejected. |
| 6. User Deletion & Deactivation | NaN |
| NaN | Admin deletes a user — verify user cannot log in anymore and their data (feeds, starred articles) is deleted or flagged (depending on DB config). |
| NaN | Admin disables a user (without deletion) — verify they can't log in, but their data remains intact. |
| NaN | Attempt to delete self as admin — expect warning or prevention. |
| NaN | Verify deleting user does not impact global feeds or other user accounts. |
| 7. API Access & Tokens | NaN |
| NaN | Generate an API token/session for a user and verify it allows access to api/index.php. |
| NaN | Revoke token or session and confirm API requests are denied. |
| NaN | Verify user-specific generated feeds (e.g. public.php?op=rss) are only accessible with valid keys or public setting. |
| 8. Security & Access Control | NaN |
| NaN | Attempt direct URL access to another user's preferences, labels, or feeds — expect 403 or redirect. |
| NaN | Verify XSS/CSRF protection in user settings forms (e.g., label/tag name input). |
| NaN | Test login attempts with SQL injection payload — input must be sanitized. |
| NaN | Ensure that password hashes are securely stored in the DB (e.g., bcrypt/sha256, not plain text). |