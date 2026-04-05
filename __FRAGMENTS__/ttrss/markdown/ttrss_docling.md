<!-- Source: ttrss.xlsx -->
<!-- Converter: docling -->
<!-- Generated: 2026-04-06T00:41:01.362490 -->

| Key Test Scenarios for TTRSS    |
|---------------------------------|

| 1. Feed Management [Core:Feed Management]   |
|---------------------------------------------|

| Subscribe to new feeds (RSS)   |
|--------------------------------|

| Verify feed can be added, fetched, and displayed correctly in the UI.   |
|-------------------------------------------------------------------------|

| Organize feeds with categories and subfolders   |
|-------------------------------------------------|

| Create categories/subfolders, move feeds between them, confirm hierarchy reflects accurately   |
|------------------------------------------------------------------------------------------------|

| Import/Export of OPML   |
|-------------------------|

| Test import of an OPML file: confirm feeds appear; test export: ensure the file contains expected subscriptions   |
|-------------------------------------------------------------------------------------------------------------------|

| 2. Feed Aggregation & Display [Core:Article Handling]   |
|---------------------------------------------------------|

| Pulling updates   |
|-------------------|

| Verify feed polling runs on schedule, fetches new articles, and displays unread items.   |
|------------------------------------------------------------------------------------------|

| Read/Unread toggling, starring, publishing   |
|----------------------------------------------|

| Mark articles read/unread; star and publish them; ensure they land in appropriate sections (e.g., "Starred")   |
|----------------------------------------------------------------------------------------------------------------|

| 3. Navigation & Keyboard Shortcuts [Core:Misc]   |
|--------------------------------------------------|

| Keyboard-based navigation   |
|-----------------------------|

| Use keyboard shortcuts to navigate articles, mark read/star, search, etc., confirming they trigger correctly   |
|----------------------------------------------------------------------------------------------------------------|

| 4. Filters and Content Processing [Core:Article Handling]   |
|-------------------------------------------------------------|

| Article filtering using regex   |
|---------------------------------|

| Set up content filters (e.g., match titles or body, assign tags, delete) and confirm they apply during feed ingestion and live view   |
|---------------------------------------------------------------------------------------------------------------------------------------|

| Filter ordering and complexities   |
|------------------------------------|

| Add multiple filters, reorder them; test inversion flags, multi-rule scenarios, and matching logic   |
|------------------------------------------------------------------------------------------------------|

| 5. Generated Feeds (Export) [Core:Feed Management]   |
|------------------------------------------------------|

| Generate Atom/JSON feeds   |
|----------------------------|

| Create generated feeds (e.g. starred, labels), export as Atom/JSON, confirm URL contains correct parameters and returns expected content   |
|--------------------------------------------------------------------------------------------------------------------------------------------|

| Key regeneration   |
|--------------------|

| Regenerate access key for a feed; test that previous URLs become invalid and new one works   |
|----------------------------------------------------------------------------------------------|

| 6. Plugins & Themes [Core:Misc]   |
|-----------------------------------|

| Installing and enabling plugins   |
|-----------------------------------|

| Install a plugin (e.g., readability, sharing), activate via Preferences, verify function works correctly (e.g., full-article embedding or social sharing)   |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------|

| System vs user plugins   |
|--------------------------|

| Add system-level plugin via PLUGINS config and verify all users have it; test user-level plugin activation separately   |
|-------------------------------------------------------------------------------------------------------------------------|

| Theme functionality   |
|-----------------------|

| Apply a theme (e.g., Feedly-inspired), toggle between light/dark and high‑contrast modes; verify UI layout, mobile responsiveness, plugin compatibility   |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------|

| 7. API & JSON [Core:Misc]   |
|-----------------------------|

| JSON-based API functionality   |
|--------------------------------|

| Use JSON API endpoints to fetch headlines, mark articles read/starred/published, manipulate subscriptions   |
|-------------------------------------------------------------------------------------------------------------|

| 8. Multi-User and User Settings [Core: User Settings]   |
|---------------------------------------------------------|

| Single-user vs multi-user mode   |
|----------------------------------|

| In single-user mode, verify only admin exists; in multi-user (with SINGLE_USER_MODE=false), create users, manage user preferences, verify isolation   |
|-------------------------------------------------------------------------------------------------------------------------------------------------------|

| User-level settings   |
|-----------------------|

| Test per-user preferences: update interval, theme, date format, digest emails, label creation   |
|-------------------------------------------------------------------------------------------------|

| 9. Full-Text, Deduplication, Podcasts [Core: Article Handling]   |
|------------------------------------------------------------------|

| Readability/full content embedding   |
|--------------------------------------|

| Enable embedding via plugins; verify that stubs are replaced by full content   |
|--------------------------------------------------------------------------------|

| Deduplication (including images)   |
|------------------------------------|

| Add duplicate articles (exact and image-based); ensure duplicates are removed or merged   |
|-------------------------------------------------------------------------------------------|

| Podcast enclosure support   |
|-----------------------------|

| Subscribe to a podcast feed; confirm enclosure visible and playable inline   |
|------------------------------------------------------------------------------|

| 10. Search, Labels, Tagging [Core: Article Handling]   |
|--------------------------------------------------------|

| Search functionality   |
|------------------------|

| Perform keyword search within a feed and across feeds; confirm results accuracy   |
|-----------------------------------------------------------------------------------|

| Labels (SQL‑based virtual feeds)   |
|------------------------------------|

| Enable labels, create custom label via SQL, verify label content and behavior   |
|---------------------------------------------------------------------------------|

| Tagging articles   |
|--------------------|

| Tag articles manually or via filter action; verify tag assignment and listing   |
|---------------------------------------------------------------------------------|

| 11. Security & Access [Core: Misc]   |
|--------------------------------------|

| SSL/TLS connections   |
|-----------------------|

| Configure via HTTPS; verify secure access to UI and API   |
|-----------------------------------------------------------|

| Authentication for protected feeds   |
|--------------------------------------|

| Add feed requiring Digest/Basic auth and confirm successful fetch with credentials   |
|--------------------------------------------------------------------------------------|

| Feed icons and UI assets   |
|----------------------------|

| Test default vs custom feed icons; replace default and verify rendering   |
|---------------------------------------------------------------------------|

| 12. Preferences   |
|-------------------|
| 13. Localization  |

| Test Coverage Matrix   |
|------------------------|

| Test Category         | Key Scenarios                                       | Core             |    |
|-----------------------|-----------------------------------------------------|------------------|----|
| Feed Management       | Subscribe, categorize, import/export OPML           | Feed Management  | +  |
| Aggregation & Display | Updating, read/unread toggling, starring/publishing | Article Handling |    |
| Navigation & UI       | Keyboard, mobile interface                          | Misc             | +  |
| Filtering             | Regex filters, ordering, complex rule logic         | Article Handling | +  |
| Generated Feeds       | Export, key regeneration                            | Feed Management  | +  |
| Plugins & Themes      | Install, activate, apply themes, plugin behavior    | Misc             | -  |
| API Integration       | JSON API, Google Reader compatibility               | Misc             | +  |
| Multi-user Settings   | User accounts, preferences, isolation               | User Settings    | +  |
| Content Processing    | Full-text, deduplication, podcasts                  | Article Handling | +  |
| Search & Labeling     | Search across feeds, tags, custom labels            | Article Handling | +  |
| Security              | HTTPS access, authenticated feed fetching           | Misc             | +  |

| 2 FE + 1 BE     |
|-----------------|
| Navigation & UI |

| 1+1             |
|-----------------|
| Generated Feeds |

| 1+1             |
|-----------------|
| API Integration |

| Multi-user Settings   |
|-----------------------|

| Feed Management   |
|-------------------|

| Filtering   |
|-------------|

| Aggregation & Display   |
|-------------------------|

| Security   |
|------------|

| Search & Labeling   |
|---------------------|

| Search & Labeling   |
|---------------------|

| User Management Test Cases   |
|------------------------------|

| 1. User Creation   |
|--------------------|

| Create a new user via admin interface (username, password, email) and confirm account is listed under Users.   |
|----------------------------------------------------------------------------------------------------------------|
| Try to create a user with an existing username — expect error: duplicate username.                             |
| Create user with special characters in username/email — ensure proper validation.                              |
| Verify created user can log in and see empty dashboard/feed list by default.                                   |

| 2.User Roles / Permissions   |
|------------------------------|

| Assign admin privileges to a user and verify access to admin functions (user mgmt, system config).                |
|-------------------------------------------------------------------------------------------------------------------|
| Verify a non-admin user cannot access /prefs.php?tab=users or other admin-only pages (returns error or redirect). |
| Downgrade admin to regular user and confirm admin access is revoked.                                              |

| 3. User Authentication   |
|--------------------------|

| Attempt login with correct and incorrect credentials — verify expected success/failure.            |
|----------------------------------------------------------------------------------------------------|
| Verify login/logout flow; check that session is destroyed after logout.                            |
| Test session expiration after inactivity (depends on server config).                               |
| Attempt login with disabled account — verify login is rejected.                                    |
| Brute-force protection: after multiple failed login attempts, ensure throttling or error feedback. |

| 4. User Preferences & Isolation   |
|-----------------------------------|

| Verify that each user has isolated feeds, categories, and settings — changes in one user account don't affect others.   |
|-------------------------------------------------------------------------------------------------------------------------|
| User changes personal preferences (theme, date format, update interval) — verify persistence after logout/login.        |
| User imports OPML — verify feeds appear only for that user.                                                             |
| Confirm starred, published, labeled articles are scoped to the user.                                                    |

| 5. Password Management   |
|--------------------------|

| Admin resets user password — verify that new credentials work and old password fails.   |
|-----------------------------------------------------------------------------------------|
| User changes own password — requires current password and confirmation.                 |
| Try setting weak or blank password — should fail with appropriate validation.           |
| Attempt to change another user’s password as non-admin — should be rejected.            |

| 6. User Deletion & Deactivation   |
|-----------------------------------|

| Admin deletes a user — verify user cannot log in anymore and their data (feeds, starred articles) is deleted or flagged (depending on DB config).   |
|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| Admin disables a user (without deletion) — verify they can't log in, but their data remains intact.                                                 |
| Attempt to delete self as admin — expect warning or prevention.                                                                                     |
| Verify deleting user does not impact global feeds or other user accounts.                                                                           |

| 7. API Access & Tokens   |
|--------------------------|

| Generate an API token/session for a user and verify it allows access to api/index.php.                               |
|----------------------------------------------------------------------------------------------------------------------|
| Revoke token or session and confirm API requests are denied.                                                         |
| Verify user-specific generated feeds (e.g. public.php?op=rss) are only accessible with valid keys or public setting. |

| 8. Security & Access Control   |
|--------------------------------|

| Attempt direct URL access to another user's preferences, labels, or feeds — expect 403 or redirect.   |
|-------------------------------------------------------------------------------------------------------|
| Verify XSS/CSRF protection in user settings forms (e.g., label/tag name input).                       |
| Test login attempts with SQL injection payload — input must be sanitized.                             |
| Ensure that password hashes are securely stored in the DB (e.g., bcrypt/sha256, not plain text).      |