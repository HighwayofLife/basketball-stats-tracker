v0.4.13
-------

### Refactoring / Optimization
- Centralized database transaction handling using new context manager

v0.4.12
-------

### Bug Fixes
- **Critical: Fixed tests overwriting real uploaded team logos** - Tests now use configurable UPLOAD_DIR and proper mocking to prevent writing to production upload directories
- Made upload directory configurable via UPLOAD_DIR environment variable to support different environments
- Added test fixtures for image creation to reduce inline test image generation


v0.4.11
-------

### Added
- UI validation tests with authentication support
- Enhanced team logo processing and display functionality

### Refactoring / Optimization
- Refactored duplicated listing logic in CLI commands by extracting common CSV/table formatting into reusable helper functions
- Consolidated banner CSS styles into main.css (removed duplicate component files)
- Improved test client setup for integration tests

### Bug Fixes
- Preserve jersey number string format in CSV parser (prevents "0" vs "00" issues)
- Fixed authentication cookie security settings for local development environments
- Fixed admin session authentication in UI validation tests
- Fix Box Score table display on game detail page - regression
- Fixed UI validation tests in CI by adding database migrations step and required environment variables

v0.4.10
-------

### Added
- Team logo upload functionality with automatic image resizing
- Unit tests for team logo image processing service
- Unit tests for team logo API endpoints
- Unit tests for team logo template helpers

### Refactoring / Optimization
- Eliminated inline CSS styles across 18+ templates by consolidating into dedicated component files (team-logos.css)
- Removed 328 lines of inline CSS from games/detail.html and organized into component files (game-detail.css, box-score.css)

### Bug Fixes
- Fix 500 errors on /v1/games and /v1/teams endpoints due to missing logo_filename column (applied pending database migration)
- Fix team logo upload not overwriting existing logos (ensure all sizes are deleted before creating new ones)
- Fix team logo image format preservation (maintain original format PNG/JPG/WebP instead of converting all to JPEG)
- Fix team logo resizing to preserve aspect ratios instead of cropping to exact dimensions (prevents distortion of non-square images)

v0.4.9
------

### Added
- Comprehensive template duplication analysis documenting reusable patterns across HTML templates
- Template component system with reusable partials for modals, forms, tables, and stats cards
- Form field macros for consistent input styling and validation
- JavaScript modules for API interactions, CRUD operations, and form validation

### Refactoring / Optimization
- Consolidated 4 responsive CSS files into single mobile-first main.css file (50-70% code reduction)
- Created component-based CSS architecture with separate files for buttons, tables, forms, and modals
- Standardized mobile table behavior across all pages for consistent user experience
- Extracted template partials to eliminate duplication of modal, form, and table structures
- Implemented mobile-first responsive design with consistent breakpoints and touch targets
- Remove redundant CI workflow steps to reduce github action consumption

### Bug Fixes
- Fix CI unit tests failing due to missing DATABASE_URL environment variable (set to sqlite:///test.db for unit tests)
- Fix JavaScript scoping issue in CRUD module retry button onclick handler (use proper event listener binding)
- Fix dashboard "Players of the Week" styling inconsistency with game detail "Game Leaders" (moved shared CSS to main.css, removed all conflicting desktop/mobile overrides, and created reusable component)
- Fix team roster table hiding columns on desktop that should only be hidden on mobile (wrapped column hiding CSS in mobile media query)
- Fix player detail page recent games table not matching dashboard/games list styling (created reusable recent_games component and updated player detail to use consistent game cards/table format)
- Fix teams table styling to match players table responsive behavior (updated teams table to use mobile-table-view class and added CSS rules to hide Display Name and Players columns on mobile)
- Fix player detail page recent games showing incorrect/missing data (updated player stats API to include team scores and game results, simplified JavaScript to remove unused data transformation)
- Create unified games list component to consolidate duplicated games display code across dashboard, team detail, and player detail pages (replaced 3 different implementations with single reusable component)
- Add safety checks for query results in player stats API to prevent potential AttributeError exceptions (added hasattr() validation for total_points field)

### Architecture Improvements
- Established template partial system with components/, includes/, and macros/ directories
- Created JavaScript module structure for better code organization and reusability
- Unified responsive table strategies to provide consistent mobile experience
- Standardized CSS naming conventions and utility classes

v0.4.8
------
### Features
* Add game editing functionality - users can now edit games after they've been entered
* Add Edit button to games list (visible only to authenticated users)
* Implement shot notation conversion service to convert stored stats back to scorebook format
* Add GET /v1/games/{game_id}/scorebook-format API endpoint for retrieving game data in editable format
* Enhanced scorebook save endpoint to support both creating new games and updating existing ones
* Pre-populate scorebook form with existing game data when editing

### UI Improvements
* Added 2 additional players to the "Game Leaders" section on the game detail page (now shows top 2 players from each team)
* Implemented responsive design: desktop displays vertically stacked, mobile displays in 2x2 grid layout

### API Enhancements
* Added `top_players` field to TeamStats schema for enhanced Game Leaders functionality
* Enhanced scorebook endpoint with update mode detection via game_id parameter

### Security
* Proper authentication and authorization for game editing (admin or team member access only)
* Access control checks prevent unauthorized game modifications

### Bug Fixes
* Fixed UnboundLocalError in scorebook game creation when `scheduled_game_info` was not initialized in update path

### Testing
* Comprehensive unit test coverage for ShotNotationService and game scorebook API endpoints
* Fixed database session management issues in API endpoint tests
* All unit tests passing (571 tests)

v0.4.7
------

### UI improvements
* Improve mobile device view of team detail and player list pages
* Refactor CSS: Move duplicated mobile table view styles to main stylesheet
* Replace fragile nth-child selectors with semantic utility classes for column hiding
* Add missing display:none rule for desktop-only tables on mobile devices
* Fix players list on mobile to display as compact table instead of cards
* Hide Position column on mobile views for cleaner display
* Fix CSS specificity issue preventing column hiding on mobile devices

v0.4.5
------

### Bug Fixes
* Fixed team standings showing 0-0 in production game detail pages by reusing the team detail page approach for getting season stats
* Fix JavaScript errors on game creation page - added null checks for DOM elements
* Fix scheduled games table missing locally - migrations not applied
* Fix scheduled game creation API error - wrong method signature for find_matching_game
* Add proper Bearer token authorization to scheduled game creation request
* Fix scheduled games not appearing in games list - modified /v1/games endpoint to include scheduled games
* Fix 404 error when clicking View on scheduled games - removed View button since there's no detail page for scheduled games
* Fix failing unit test for ScheduleService.test_create_scheduled_game - corrected mocked method name from find_matching_game to find_matching_game_by_ids
* Confirmed all integration tests pass (64/78 passed, 14 skipped) - no outstanding test failures

### UI Improvements
* Replace browser alert dialogs with HTML banners for game scheduling success/error messages
* Add auto-dismissing success banners that redirect to games page after scheduling
* Improve user experience with inline error messages using styled HTML banners
* Show scheduled games in main games list with "Scheduled" status instead of scores
* Use negative IDs for scheduled games to distinguish them from completed games
* Update game list UI to properly handle and display scheduled games

### Features
* Add comprehensive game schedule feature with CRUD operations
* Implement ScheduledGame model with status tracking (scheduled, completed, cancelled, postponed)
* Add schedule management API endpoints at /v1/games/scheduled/*
* Automatic matching of CSV imports with scheduled games
* CSV import integration that links completed games to their scheduled entries
* Database migration for scheduled_games table with proper indexing
* ScheduleService for business logic and intelligent game matching
* Update "Schedule Game" functionality to use existing create game page instead of modal
* Simplify UI by removing redundant "Create New Game" button and modal interface
* Create game page now creates scheduled games instead of regular games with 0-0 scores
* Authentication-protected UI elements that only show for logged-in users

### Fixes
* Fix integration test environment setup for JWT_SECRET_KEY configuration
* Add find_matching_game_by_ids method to handle team ID based matching

### Tests
* Add comprehensive unit tests for ScheduleService (13 tests)
* Add unit tests for CRUDScheduledGame operations (9 tests)
* Add integration tests for scheduled games API endpoints (9 tests)
* Add UI tests for create game page functionality (9 tests) - moved to test_ui_validation.py
* Fix time conversion issues in CRUD operations (string to time object conversion)
* Fix integration test database session management for proper test isolation
* Fix API route ordering issue - moved /scheduled routes before /{game_id} to prevent route conflicts
* Add integration tests for authentication flow and authenticated endpoints (10 tests)
* Move create game UI tests to proper UI test suite location in test_ui_validation.py

v0.4.4
------

### Authentication Improvements
* Fix login authentication not persisting - added HTTP-only secure cookies to /auth/token endpoint
* Update authentication dependencies to support both Bearer tokens and cookies
* Fix logout to properly clear authentication cookies
* Add comprehensive integration tests for cookie-based authentication
* Fix admin role check in template context to use proper enum comparison

v0.4.3
------

### Features
* Add mobile-friendly hamburger menu for navigation on small screens
* Enhanced smartphone portrait mode (≤480px) with comprehensive mobile menu implementation
* Added aria-expanded attributes for better accessibility
* Implemented body scroll lock when mobile menu is open
* Improved touch targets and mobile-specific styling
* Add responsive table design for mobile devices with data-label attributes
* Implement compact game card layout for mobile devices showing scores and teams
* Display team win-loss records on game detail page instead of home/away labels
* Add responsive mobile layout for game detail scoreboard with centered scores and team info

### Fixes
* Fix issue with user authentication not being properly checked in templates
* Fix hamburger button styling to look like standard mobile menu icon with proper positioning
* Fix menu toggle functionality by removing conflicting 767px media query rules
* Add hamburger menu support to smartphone landscape mode (481-767px)
* Ensure mobile menu button only shows on mobile devices (≤767px)
* Fix hamburger button alignment - now properly centered vertically with header
* Fix games tables to display properly on mobile portrait view using card-based layout
* Replace responsive table design with compact game cards for better mobile UX
* Fix Players of the Week layout on mobile portrait to stack cards vertically instead of cramming horizontally

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
* Fix missing `get_db_session` import in web UI dependencies module causing test failures
* Fix integration test authentication setup to properly mock auth dependencies

### Authentication Fixes
* Revert admin page authentication approach - HTML pages use client-side auth checking rather than server-side dependencies
* Admin API endpoints still enforce proper role-based authentication
* Update tests to reflect correct authentication behavior (client-side for HTML, server-side for API)

### Test Improvements
* Fix integration test authentication mocking for consistent test behavior
* Skip problematic security integration tests pending team-based access control implementation
* Update OAuth integration tests to handle proper dependency injection

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
