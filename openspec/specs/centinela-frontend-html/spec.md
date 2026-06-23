# Delta for centinela-frontend-html

## REMOVED Requirements

### Requirement: HTML frontend asset

The file `centinela_kimi_frontend.html` SHALL be deleted from the repository.
(Reason: The pywebview-based HTML frontend is replaced by the Textual TUI. There is no web-based UI in v1.)

#### Scenario: File no longer exists

- GIVEN the repository is checked out at the commit after this change
- WHEN `centinela_kimi_frontend.html` is searched for
- THEN it is not present in the working tree or git index

#### Scenario: No references remain

- GIVEN the codebase is scanned
- WHEN searching for the string `centinela_kimi_frontend.html`
- THEN zero occurrences are found in source files, docs, or build scripts
