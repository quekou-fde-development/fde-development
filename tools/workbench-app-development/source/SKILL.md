---
name: workbench-app-development
description: Use when creating, extending, publishing, or redeploying Syngy Workbench apps, especially with octopus-cli, Taskboard, Arcubase, or Workbench authentication.
---

# Workbench App Development

## Core contract

Use only the official Workbench React scaffold and `octopus-cli` for creation/deployment. Every app keeps `@syngy/workbench-auth`; optional features are business clients, never authentication switches.

Inspect repository instructions and target first. Never scaffold a non-empty app. For existing apps, inspect `package.json` and the facade, infer features, preserve custom/uncommitted work, and add only a required official client using its package manager and current official contract.

| Requirement | Feature |
| --- | --- |
| Authenticated Workbench UI only | empty |
| Host users, teams, members, organization, digital employees, conversations, files, knowledge, skills, integrations, or runtime resources | `octopus` |
| Tasks or projects | `taskboard` |
| Persisted, shared, queryable records | `arcubase` |

Local TypeScript objects and static fixtures do not imply Arcubase.
When `octopus` is selected, read the [Octopus client contract](references/octopus-client.md) before installing or calling Host APIs. Displaying only the authenticated viewer does not require it.

## Human authorization

For apps with differentiated human access, define one canonical source for business role memberships, permissions, and scopes, operated through one administrative workflow. Host login supplies trusted identity; platform administration and team eligibility retain their own scope and must not silently grant application privileges.

- Verify the platform's supported authorization capabilities before choosing the canonical backend. A management screen may live in Octopus while authorization is stored elsewhere; one screen alone does not establish one authority. Do not invent permissions inside editable profile text or assume platform admin/member is the application's role model.
- Reference shared native roles where supported. Any per-table grants, role caches, or identity mappings must be automatically maintained projections of the canonical source with a defined activation/revocation contract, versioned changes, failure handling, and verified recovery. Never require operators to maintain duplicate human business-role lists across Octopus, Arcubase, tables, scripts, and frontend code. For migrations, snapshot and compare effective grants, preserve unrelated human and digital-employee scopes, and verify recovery without silently restoring revoked access.
- Remove hardcoded human IDs used for privilege selection. The frontend consumes the current session's effective authorization; the backend enforces it for reads, writes, and applicable alternate entrypoints. Display filtering or hiding a control cannot establish data isolation.
- Keep object ownership, project membership, and assigned reviewers in their authoritative business records. Combine these relationships with canonical role permissions at enforcement time. Verify the mapping between the host principal, data-store user, and business-person record; never assume their IDs are interchangeable. Protect authorization data and identity bindings from ordinary business editing; editable labels cannot independently grant privileges.
- Before claiming completion, verify onboarding/role change/revocation through the single workflow, including existing sessions and direct allowed API paths, without frontend redeployment or manual per-table membership edits. Check the actual human principal; administrative CLI success is not a human-session test. Document any revocation propagation interval and verify it.
- When required native capabilities are unavailable, present the specific platform gap and a concrete proposed remedy. Do not deliver independent permission stores or manual synchronization as a completed centralized design. Unrelated UI-only changes do not require a new authorization system.

## Arcubase decision

When Arcubase is required, stop before writes: the developer explicitly chooses an existing or new App.

- Existing: list Apps; require an explicit ID when candidates are ambiguous; inspect schema and stable keys; generate typed project code.
- New: present tables, fields, relations, and access model. Create through `octopus-cli arcubase-admin` only after that choice, then generate typed code.

Never guess an ID, match by name alone, or silently create storage.
Before writing datetime row values or defining `serialnumber` fields, read [Arcubase runtime gotchas](references/arcubase-runtime-gotchas.md).
Even when `octopus.api` exposes Arcubase proxy methods, persisted business data uses the `arcubase` feature and its generated typed ingress clients.

## Workflow

Read [command contracts](references/command-contracts.md) before scaffolding, Arcubase work, or deployment.

1. Scaffold a safe empty target or inspect the existing app.
2. Before team-scoped discovery (including Arcubase App list) and every external write, run `octopus-cli auth whoami --json`; verify profile, host, account, and team. On mismatch, stop with a copyable correction.
3. Use the generated authenticated facade; do not add a token store or standalone login. Generate typed clients for selected backend features and implement only working visible controls.
4. Follow the [local validation contract](references/local-validation.md) before any production build or remote project creation: start the declared dev server, connect through the supported local Workbench login, and prove the selected real backend supplies the rendered business state.
5. Report the local URL, verified context, selected feature/App IDs, evidence, and unresolved issues. Stop until the developer explicitly approves publishing. An earlier request to deploy does not waive this checkpoint; skip it only when the developer explicitly waives interactive local acceptance.
6. After approval, run only declared relevant tests and the production build; require `dist/index.html`.
7. Create at most one first remote Workbench project, and only after the accepted build. If its response is uncertain, use `coding projects list/show` to resolve it before any retry. Never introduce or write a hidden local project-ID mapping file. Later deployments use an explicit project ID or an unambiguous exact list result.
8. Publish the built directory and boundedly watch its task: `queued`/`processing` continue; `failed` stops immediately with `errorMessage` and action; `active` plus `workbenchUrl` succeeds. Successful handoff reports exactly `projectId`, `taskId`, `status=active`, `workbenchUrl`, verified `profile`, `host`, `team`; never substitute Arcubase `appId` or deployment/version/environment fields.

Direct HTTP, `kubectl`, GitHub Actions, copied scaffold, alternate publish, and remote archive/delete are outside this skill.

Every stop or failure must state the proven reason and a directly copyable next action. For an unsupported CLI flag, run that exact command’s current `--help`; never try legacy or guessed aliases.

## Skill improvement

Change this skill only when explicitly requested. Read [acceptance scenarios](references/acceptance-scenarios.md), reproduce the concrete gap before editing, make the smallest correction, validate it, and rerun the failing and affected scenarios. Do not add speculative compatibility or a changelog.
