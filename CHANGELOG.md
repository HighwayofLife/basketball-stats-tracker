v0.6.2
------

### Added
- Awards Showcase page with comprehensive awards display
- Season filter dropdown for viewing awards by specific season
- Awards summary statistics showing total awards and unique players
- Awards link in main navigation menu
- Awards button in Players tab for quick access

### API Enhancements
- Added `/awards` page endpoint for awards showcase
- Added `/v1/awards` endpoint with season filtering support
- Added `/v1/awards/{season}` endpoint for season-specific awards
- Added `/v1/awards/stats/summary` endpoint for awards statistics

### Testing
- Added comprehensive unit tests for awards router endpoints

v0.6.1
------

### Added
- New season awards: Curry Wannabe (most 3-pointers made)
- New award: Hack-a-Shaq (most free-throws missed)

### Changed
- The Final Boss award now tracks most points scored in 4th quarter (instead of most shots made)
- Weekly Whiffer award now excludes free-throw misses (only counts field goal misses)
- Defensive Tackle award now uses fouls-per-game average with minimum 10 total fouls (instead of most total fouls)

v0.6.0
------

### Added
- Playoff bracket visualization with tournament tree
- Playoff configuration for teams and rounds
- Team playoff seeding functionality
- Mark games as playoff games
- Dedicated /playoffs page with bracket display
- API endpoints for playoff operations
- PlayoffConfig model for tournament settings
- playoff_seed field to Team model
- is_playoff_game field to Game/ScheduledGame models

### Changed
- Enhanced game forms with playoff checkbox
- Updated navigation with playoffs link
- Improved modal handling in playoff templates

### Fixed
- Fixed hardcoded year display in playoffs template to use API season data
- Removed unimplemented double elimination bracket type option
- Added race condition protection for playoff config updates
- Added validation for team IDs and seeds in save_team_seeds endpoint


v0.5.5
------

### Bug Fixes
- Fixed incorrect opponent display in player profile game stats


v0.5.4
------

### Bug Fixes
- Fixed Dub Club award only being given to one player per week instead of all qualifying players
- Fixed dashboard awards caching issue showing old results after recalculation
- Eliminated code duplication in player detail template

### Database Changes
- Added `game_id` field to PlayerAward model for proper per-game award tracking


v0.5.3
------

### UI Enhancements
- Enhanced Player Profile Recent Games section with comprehensive player statistics



v0.5.2
------

### Features
- Added four new per-game awards: Dub Club, The Marksman, Perfect Performance, Breakout Performance
- Added "The Rick Barry Award" for highest season free-throw percentage

### Performance Improvements
- Optimized award calculations to fix performance hangs
- Fixed all weekly awards to be based on best single-game performance instead of weekly totals
- Centralized award configuration in backend

### CLI Enhancements
- Updated `calculate-season-awards` and `calculate-all-awards` commands

### Bug Fixes

v0.5.1
------

### Features
- Added interactive week selector dropdown for viewing historical weekly awards
- Added API endpoint `/api/weekly-awards/{week_date}` for fetching week-specific awards

### Bug Fixes
- Enhanced logging and debugging for production weekly awards display

### Improvements
- Changed "Weekly FT King/Queen" to "Freethrow Merchant"
- Improved error handling in weekly awards retrieval
- Better separation of template logic and API endpoints

v0.5.0
------

### Features
- Added comprehensive awards system for tracking weekly and season-long player awards
- Added Player of the Week (POTW) awards with PlayerAward table
- Added 6 new weekly award types (Quarterly Firepower, Weekly FT King/Queen, Hot Hand Weekly, etc.)
- Added 8 new season award types (Top Scorer, Sharpshooter, Efficiency Expert, etc.)

### CLI Enhancements
- Enhanced `calculate-potw` command with season and recalculate options
- Added new CLI commands: `calculate-season-awards`, `calculate-weekly-awards`, `calculate-all-awards`, `finalize-season`

### Database Schema
- Added `player_awards` table for detailed award tracking
- Refactored table for comprehensive awards support with nullable week_date for season awards

### API Improvements
- Enhanced `/v1/players/{id}/stats` endpoint with detailed award data
- Added `POST /v1/players/calculate-awards` endpoint for triggering award calculations

### Services & Architecture
- Added Awards Service and Season Awards Service
- Centralized award creation and management

### UI/UX Improvements
- Added Weekly Awards Section to dashboard
- Added Awards & Achievements section to player detail pages
- Added Admin Awards Management section to players list page

### Infrastructure
- Added award calculation step to deployment workflow

### Testing
- Added extensive test suites covering the new awards system



v0.4.33
-------

### Features
- **Scheduled Games**: Added the ability to edit scheduled games from the UI.

### Bug Fixes
- **Player Portraits**: Fixed an issue where player portraits were not showing in the game detail box scores.
- **Dashboard**: Fixed "Players of the Week" component by including player IDs.

### Internal
- Added integration tests for the scheduled game edit functionality.
- Cleaned up unused imports.


v0.4.32
-------

### Bug Fixes
- Fixed dashboard "Players of the Week" by adding 'id' field to player data
- Fixed game detail box scores by removing function override that prevented portraits from showing
- Fixed player portraits display on Dashboard, Game Leaders, Players list, and Box Scores

v0.4.31
-------

### Bug Fixes
- Fixed player portrait images not displaying in several locations
- Added missing thumbnail_image field to players list API endpoint
- Fixed players list page to use shared player-portraits.js module

v0.4.30
-------

### Features
- Enhanced user experience by making player names clickable throughout the application

### Testing
- Added integration test ensuring Players of the Week names link correctly

v0.4.28
-------

### Bug Fixes
- Changed metric for determining top players on matchup screen from points-per-game to total points
- Fixed team logos not consistently displaying due to logic error in image URL generation

v0.4.27
-------

### Bug Fixes
- Fixed 0-0 scores in production matchup history
- Fixed scorebook submission to save calculated scores to Game model fields
- Enhanced head-to-head history with "Box Score" links to game detail pages

v0.4.26
-------

### Features
- Added comprehensive season selection and management capabilities
- Added season dropdown to scorebook entry form for manual season assignment
- Added `/v1/seasons/list` API endpoint for season selection dropdowns

### Bug Fixes
- Fixed critical production issues with missing season statistics
- Resolved 0-0 team records showing on matchup pages
- Fixed missing player statistics in matchup previews

### Infrastructure
- Added automated production migration workflow

v0.4.25
-------

### Features
- Added player portrait/headshot display across multiple UI pages

### Bug Fixes
- Fixed multiple issues with player portrait rendering
- Resolved malformed HTML and rogue quote sequences on player detail page after upload
- Fixed camera button positioning to stay in bottom-right corner of portrait
- Added `thumbnail_image` field to box score API responses for proper portrait display
- Updated PlayerResponse schema to include thumbnail_image for team roster display

v0.4.24
-------

### Features
- Added team logos to the matchup header display
- Improved player statistics display in matchup preview

### Bug Fixes
- Fixed missing authentication context causing header to show logged out state
- Fixed season string mismatch by using season code instead of name for TeamSeasonStats queries
- Resolved issue where team records and statistics showed as 0-0 despite having games in database
- Fixed empty player lists by ensuring proper season filtering in PlayerSeasonStats queries

v0.4.23
-------

### Features
- Added comprehensive pre-game matchup analysis for scheduled games
- Added `/scheduled-games/{id}/matchup` endpoint displaying detailed preview for upcoming games

### API Enhancements
- Added `status` field to GameSummary schema to distinguish between completed and scheduled games
- Updated games list endpoint to properly set status values
- Added new dedicated matchup router with comprehensive error handling

### Services & Architecture
- Added MatchupService for matchup data aggregation
- Added smart season handling and consistent record formatting
- Leveraged existing models without schema changes

### UI/UX Improvements
- Updated games list component to show appropriate action buttons based on game status
- Added comprehensive matchup.html template
- Added proper rounding and percentage display for statistical comparisons

### Testing
- Added full unit and integration test suites for matchup functionality

v0.4.22
-------

### Features
- Enhanced player statistics table sorting behavior
- Added smart default sort order for percentage columns
- Added minimum points filter for percentage columns

### Code Quality
- Replaced hard-coded column index ranges with semantic `data-is-percentage` attributes
- Added integration tests for player statistics sorting functionality

v0.4.21
-------

### Features
- Added comprehensive player statistics dashboard with advanced metrics
- Added teams page URL parameters for tab navigation with browser history support

### API Enhancements
- Added `GET /v1/players/stats` endpoint with team filtering

### Services & Architecture
- Added PlayerStatsService for player statistics calculations

### Testing
- Added comprehensive unit test suite for player statistics
- Added integration tests for teams page tab functionality

v0.4.20
-------

### Features
- Added team rankings dashboard with offensive and defensive team metrics

### Backend Enhancements
- Added TeamStatsService for calculating team-level statistics
- Added `get_player_game_stats_for_game_and_team()` function
- Added `/v1/teams/rankings` API endpoint

### Frontend Improvements
- Enhanced teams page with tabbed interface and sortable rankings table

### Testing
- Added comprehensive test suite for TeamStatsService

v0.4.18
-------

### Features
- Added enhanced fuzzy name matching for player name variations
- Added OT1 and OT2 columns to scorebook entry form
- Enhanced CSV import to handle overtime data

### Bug Fixes
- Fixed game queries to use `is_deleted` instead of deprecated `deleted_at` column
- Resolved jersey number conflicts in integration tests

### Code Quality Improvements
- Extracted name matching logic to dedicated utility module
- Updated project version to 0.4.18

v0.4.17
-------

### Features
- Added comprehensive overtime support for up to 2 overtime periods (OT1, OT2)

### Database Improvements
- Added overtime support migration extending quarter constraints from 4 to 6 quarters

### Service Layer Enhancements
- Enhanced Game State Service with intelligent overtime logic
- Updated Report Generator to handle dynamic quarter counts

### UI/UX Improvements
- Added dynamic quarter display that adapts to show overtime columns

### Testing
- Added 17 new tests covering overtime functionality

### Development Infrastructure
- Added test data loading targets to Makefile
- Lint cleanup and code formatting improvements

v0.4.16
-------

### Code Architecture Improvements
- Consolidated report generation business logic into dedicated service layer

v0.4.15
-------

### Test Infrastructure Improvements
- Major test fixture consolidation eliminating duplication (~30% performance improvement)
- Achieved 100% pass rate across all test types
- Reduced season stats processing overhead by 95%
- Fixed `make test-ui` to properly activate Python virtual environment

v0.4.14
-------

### Features
- Added comprehensive player portrait upload and display system

### Code Quality Improvements
- Refactored template helpers to eliminate code duplication
- Enhanced API error handling with structured error information

### Refactoring / Enhancement
- Refactored Image Processing Service to support both team logos and player portraits

### API Enhancements
- Added `POST /v1/players/{player_id}/portrait` and `DELETE /v1/players/{player_id}/portrait` endpoints

### Testing
- Added comprehensive tests for player portrait functionality

v0.4.13
-------

### Features
- Added Cloud Storage support for persistent file uploads in production

### Infrastructure
- Added Google Cloud Storage bucket resource in Terraform configuration
- Terraform now manages all Cloud service account IAM permissions automatically

### Bug Fixes
- Fixed team logo uploads being deleted on each deployment
- Fixed Pydantic validation errors in Settings class
- Fixed dashboard/homepage loading error
- Fixed team logo 404 errors

### Testing
- Added comprehensive UI tests for dashboard data display functionality

### Refactoring / Optimization
- Moved uploads directory outside application code directory
- Updated upload URLs for consistency
- Optimized Dockerfile dependency caching

v0.4.12
-------

### Bug Fixes
- Fixed tests overwriting real uploaded team logos
- Made upload directory configurable via UPLOAD_DIR environment variable
- Added test fixtures for image creation


v0.4.11
-------

### Added
- UI validation tests with authentication support
- Enhanced team logo processing and display functionality

### Refactoring / Optimization
- Refactored duplicated listing logic in CLI commands
- Consolidated banner CSS styles into main.css
- Improved test client setup for integration tests

### Bug Fixes
- Preserve jersey number string format in CSV parser
- Fixed authentication cookie security settings for local development
- Fixed admin session authentication in UI validation tests
- Fixed Box Score table display on game detail page
- Fixed UI validation tests in CI

v0.4.10
-------

### Added
- Team logo upload functionality with automatic image resizing
- Unit tests for team logo functionality

### Refactoring / Optimization
- Eliminated inline CSS styles across 18+ templates
- Organized CSS into dedicated component files

### Bug Fixes
- Fixed 500 errors on /v1/games and /v1/teams endpoints due to missing logo_filename column
- Fixed team logo upload issues
- Fixed team logo image format preservation
- Fixed team logo resizing to preserve aspect ratios

v0.4.9
------

### Added
- Template component system with reusable partials
- Form field macros for consistent input styling
- JavaScript modules for API interactions and CRUD operations

### Refactoring / Optimization
- Consolidated 4 responsive CSS files into single mobile-first main.css file
- Created component-based CSS architecture
- Standardized mobile table behavior across all pages
- Extracted template partials to eliminate duplication
- Removed redundant CI workflow steps

### Bug Fixes
- Fixed CI unit tests failing due to missing DATABASE_URL environment variable
- Fixed JavaScript scoping issue in CRUD module
- Fixed dashboard "Players of the Week" styling inconsistency
- Fixed team roster table column hiding behavior
- Fixed player detail page recent games styling and data issues
- Created unified games list component
- Added safety checks for query results in player stats API

### Architecture Improvements
- Established template partial system with organized directory structure
- Created JavaScript module structure for better code organization
- Unified responsive table strategies
- Standardized CSS naming conventions

v0.4.8
------
### Features
- Added game editing functionality
- Added shot notation conversion service
- Added GET /v1/games/{game_id}/scorebook-format API endpoint

### UI Improvements
- Added 2 additional players to "Game Leaders" section
- Implemented responsive design for game leaders

### API Enhancements
- Added `top_players` field to TeamStats schema
- Enhanced scorebook endpoint with update mode detection

### Security
- Added proper authentication and authorization for game editing

### Bug Fixes
- Fixed UnboundLocalError in scorebook game creation

### Testing
- Added comprehensive unit test coverage for ShotNotationService

v0.4.7
------

### UI improvements
- Improved mobile device view of team detail and player list pages
- Refactored CSS mobile table view styles
- Fixed players list display on mobile
- Fixed CSS specificity issues preventing column hiding on mobile

v0.4.5
------

### Features
- Added comprehensive game schedule feature with CRUD operations
- Implemented ScheduledGame model with status tracking

### Bug Fixes
- Fixed team standings showing 0-0 in production game detail pages
- Fixed JavaScript errors on game creation page
- Fixed scheduled games table and API issues
- Fixed failing unit tests

### UI Improvements
- Replaced browser alert dialogs with HTML banners
- Added auto-dismissing success banners
- Updated game list UI to handle scheduled games

### Tests
- Added comprehensive unit and integration tests for scheduling functionality

v0.4.4
------

### Authentication Improvements
- Fixed login authentication not persisting
- Updated authentication dependencies to support both Bearer tokens and cookies
- Fixed logout to properly clear authentication cookies
- Added comprehensive integration tests for cookie-based authentication

v0.4.3
------

### Features
- Added mobile-friendly hamburger menu for navigation
- Enhanced smartphone portrait mode with comprehensive mobile menu implementation
- Added responsive table design for mobile devices
- Implemented compact game card layout for mobile devices

### Fixes
- Fixed user authentication checking in templates
- Fixed hamburger button styling and alignment
- Fixed menu toggle functionality
- Fixed games tables display on mobile
- Fixed Players of the Week layout on mobile

v0.4.2
------

### Code Quality Improvements
- Fixed all ruff lint validation errors and warnings
- Added proper exception chaining
- Fixed boolean comparison patterns

### Bug Fixes
- Fixed player stats API endpoint to return season_stats when no active season exists
- Fixed missing `get_db_session` import causing test failures
- Fixed integration test authentication setup

### Authentication Fixes
- Reverted admin page authentication approach to client-side checking
- Updated tests to reflect correct authentication behavior

### Test Improvements
- Fixed integration test authentication mocking
- Updated OAuth integration tests

v0.4.1
------

### Fixes
- Fixed logout functionality
- Fixed player season stats endpoint to use active season
- Fixed inconsistency between player and team season stats
- Fixed SeasonStatsService to use actual Season table date ranges
- Fixed linting issues

v0.4.0
------
### Features
- Added team statistics and team season statistics

### API Improvements
- Replaced generic dict response models with explicit Pydantic schemas
- Added TeamBasicResponse, RosterPlayer, TeamWithRosterResponse, and DeletedTeamResponse schemas

### Security Fixes
- Fixed missing authentication on admin pages

### Test Infrastructure Improvements
- Fixed circular import issues and resolved 18 failing unit tests
- Improved test pass rate from 96% to 100%


v0.3.0
------

### Features
- Introduced user authentication and authorization with JWT tokens
- Added Google OAuth 2.0 integration for user login
- Implemented role-based access control (Admin, User)
- Added team-based data access restrictions
- Created user management and account pages

### Changes
- Enhanced security with mandatory JWT secret key validation
- Added OAuth provider fields to user model
- Implemented comprehensive authentication middleware
- Github action now just uploads and reloads the app/image

### Fixes
- Fixed test command to fail fast instead of continuing on errors

### Documentation / Tests
- Added comprehensive authentication test suite
- Created security integration tests
- Added FastAPI startup validation tests

v0.2.0
------
