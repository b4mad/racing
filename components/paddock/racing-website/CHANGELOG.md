## v0.3.0 (2023-12-05)

### Feat

- copilot details view, minor tweeeeeks
- use sqlite3 for test or dev and pgsql for prod
- configure smtp settings based on the ENVIRONMENT setting
- templates for services
- add pre-commit
- last 5 sessions on the dashboard
- more work on profiles and templates
- use bootstrap5 for all templates, implement some test
- add allauth and use it
- add user and account applications

### Fix

- replace psycopg2_binary by psycopg
- include protocol in CSRF_TRUSTED_ORIGINS
- add CSRF_TRUSTED_ORIGINS setting
- add website.dev.b4mad.racing to ALLOWED_HOSTS
- clean the STATIC settings up
- increase code quality by using pre-commit, it leads to a lot of fixes

### Refactor

- rename Services to Copilots
- use a table for the copilots overview
- add django-bootstrap-icons as a dependency, minor profile details view editions
- add some more services and profile stuff
- remove a directory layer
- create the basic bootstrap5-based application, with a frontpage and user management system
