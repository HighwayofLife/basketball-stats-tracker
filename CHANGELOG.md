v0.4.0
------
### Features
* Add team statistics and team season statistics

### API Improvements
* Replace generic dict[str, Any] response models with explicit Pydantic schemas in teams router for better type safety and API documentation
* Add TeamBasicResponse, RosterPlayer, TeamWithRosterResponse, and DeletedTeamResponse schemas

### Security Fixes
* Fix missing authentication on admin pages - added require_admin dependency to /admin/users and /admin/seasons endpoints


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
