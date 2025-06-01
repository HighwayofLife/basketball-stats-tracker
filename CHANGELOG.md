v0.4.2
------

### Code Quality Improvements
* Fix all ruff lint validation errors and warnings across the app folder
* Add B008 to ruff ignore list for valid FastAPI Depends() patterns
* Fix B904 errors - add proper exception chaining with 'from e' or 'from None'
* Fix E712 errors - replace `== True` comparisons with direct boolean checks
* Fix line length violations and simplify code patterns

### Bug Fixes  
* Fix player stats API endpoint to return season_stats when no active season exists
* Update player stats endpoint to fall back to most recent season stats if no active season

### Authentication Fixes
* Revert admin page authentication approach - HTML pages use client-side auth checking rather than server-side dependencies
* Admin API endpoints still enforce proper role-based authentication
* Update tests to reflect correct authentication behavior (client-side for HTML, server-side for API)

v0.4.1
------

### Fixes
* Logging out now actually logs out the user
* Fix player season stats endpoint to use active season instead of hardcoded "2024-2025"
* Fix inconsistency between player and team season stats - both now use SeasonStatsService with proper season lookup
* Fix SeasonStatsService to use actual Season table date ranges instead of hardcoded date calculations
* Fix linting issues in tests and main app

v0.4.0
------
### Features
* Add team statistics and team season statistics

### API Improvements
* Replace generic dict[str, Any] response models with explicit Pydantic schemas in teams router for better type safety and API documentation
* Add TeamBasicResponse, RosterPlayer, TeamWithRosterResponse, and DeletedTeamResponse schemas

### Security Fixes
* Fix missing authentication on admin pages - added require_admin dependency to /admin/users and /admin/seasons endpoints

### Test Infrastructure Improvements
* Fix circular import issues and resolve 18 failing unit tests
* Improve test pass rate from 96% to 100% (516 passed, 5 skipped)


v0.3.0
------

### Features
* Introduce user authentication and authorization with JWT tokens
* Add Google OAuth 2.0 integration for user login
* Implement role-based access control (Admin, User)
* Add team-based data access restrictions
* Create user management and account pages
* Create a default admin using a secure password from env

### Changes
* Enhance security with mandatory JWT secret key validation
* Add OAuth provider fields to user model
* Implement comprehensive authentication middleware
* Github action now just uploads and reloads the app/image, no longer overrides terraform configs

### Fixes
* Fix test command to fail fast instead of continuing on errors

### Documentation / Tests
* Add comprehensive authentication test suite
* Create security integration tests
* Add FastAPI startup validation tests

v0.2.0
------
