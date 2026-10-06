# Octopus Client Contract

Use the `octopus` feature when application behavior needs the typed Host user API beyond the authenticated viewer already supplied by Workbench Auth.

## Select the feature

Representative `octopus.api` areas include:

- current user, teams, team membership, profiles, invitations, and role-sensitive management;
- organization-directory search and filters for departments, roles, employee types, and digital employees;
- digital employees, reporting relationships, skillsets, knowledge bases, workspaces, Stations, and channel bindings;
- conversations, messages, timelines, turns, streaming, resume/steer, temporary files, and shares;
- Group Sessions, Stations, Web Sessions, embed tokens, team files, artifacts, skills, integrations, calendars, automation, browsers, devices, images, and endpoint types.

Use `taskboard` instead for task/project workflows. Use no optional feature when the app only renders the authenticated viewer and has no Octopus business operation.

## Install and access

For a new app, include the feature explicitly, alone or with other required features:

```bash
npm create @syngy/workbench-app-react@latest <target> -- --features=octopus
```

The official scaffold installs `@syngy/octopus-client`, adds `createOctopusClient()` to `src/lib/syngy.ts`, and preserves `@syngy/workbench-auth`. The generated access path is `createSyngyClients().octopus.api`; use it instead of adding a second token store, raw Host client, or standalone login.

For an existing app, inspect `package.json`, its lockfile, and `src/lib/syngy.ts`. If the client is absent, add `@syngy/octopus-client` with the existing package manager at the version supported by current scaffold evidence, then add the same facade entry without replacing custom code.

## Choose methods from current types

Treat the current installed type declarations for `@syngy/octopus-client` as the source of truth. Search them or use TypeScript completion for the exact method, parameters, request body, and response type; the generated surface is broad and can change. Do not infer semantics from similar generated names such as `Detail` and `Detail2`.

Examples that establish the boundary, not an exhaustive API catalog:

- `v1MeList`, `v1TeamsList`, `v1TeamsDetail`, and `v1TeamsMeProfileDetail` for viewer/team context;
- `v1TeamsMembersDetail`, `v1TeamsMembersDetail2`, and `v1TeamsMembersProfileDetail` for team membership;
- `v1TeamsOrganizationMembersSearchCreate` for organization-directory search.

Only call operations required by the product. Package availability does not grant permission: omit unauthorized management controls, handle permission failures, and do not exercise privileged or mutating methods merely because they appear in the client.

## Preserve the data boundary

Persisted, shared, queryable business records must use the `arcubase` feature and generated typed ingress clients, never its generic Arcubase proxy methods exposed under `octopus.api`. Selecting Octopus for users, teams, or directories does not replace Arcubase for application storage.
