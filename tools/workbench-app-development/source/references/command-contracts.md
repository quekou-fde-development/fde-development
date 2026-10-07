# Workbench Command Contracts

## Scaffold

Auth-only uses this exact command:

```bash
npm create @syngy/workbench-app-react@latest <target> -- --features=
```

Optional clients are a comma-separated subset of `octopus,taskboard,arcubase`:

```bash
npm create @syngy/workbench-app-react@latest <target> -- --features=octopus,arcubase
```

Never omit `--features`: the scaffold otherwise defaults to `octopus`. Auth is always supplied as `@syngy/workbench-auth`.

`--features=octopus` installs the current scaffold-compatible `@syngy/octopus-client` and exposes it through the generated facade. Read [Octopus client](octopus-client.md) for its selection, usage, and data-boundary contract. For an existing app, inspect its dependency versions and facade first; add this official client with the existing package manager only when the requirement needs Host APIs beyond the authenticated viewer.

## CLI context

Before team-scoped discovery (including Arcubase App list) and every external write, run:

```bash
octopus-cli auth whoami --json
```

Require matching profile, host, account, and team. For missing login, host, or account context, recover it with:

```bash
octopus-cli auth login --profile <profile> --web-url <tenant-web-origin>
```

For a wrong existing profile or team selection, use:

```bash
octopus-cli auth profiles list
octopus-cli auth profiles use <profile>
octopus-cli configure team use <teamId>
```

Rerun `octopus-cli auth whoami --json`; do not discover or write until all four values match the requested target.

## Arcubase

For datetime row writes or `serialnumber` fields, read [Arcubase runtime gotchas](arcubase-runtime-gotchas.md) before creating data or saving the schema.

Discover and inspect an existing App with:

```bash
octopus-cli arcubase-admin app list --json
octopus-cli arcubase-admin app get --app-id <appId> --json
```

For a new App, first read the current contracts:

```bash
octopus-cli arcubase-admin app create --help
octopus-cli arcubase-admin table create --help
octopus-cli arcubase-admin table update-schema --help
octopus-cli arcubase-admin access-rule create --help
```

Use the documented `--body-json` payloads exactly. Give fields and ingress stable TypeScript-compatible keys, then generate typed source:

```bash
octopus-cli arcubase-admin dev sdk-gen --app-id <appId> --out src/arcubase
```

Fix an invalid schema or missing keys; never replace generated types with untyped calls.

For an existing app, inspect `package.json` and `src/lib/syngy.ts`, do not scaffold again, use the current official scaffold/package contract and existing package manager, and preserve custom code and Auth. Do not assert a target path, package version, facade import or method, CLI identity, project ID, or URL unless the developer supplied it or current files, CLI output, or `--help` evidence shows it. If the selected app directory or deployment context is unknown, stop and ask the developer.

## Local development

Read [local validation](local-validation.md) before starting a dev server or preparing a deployment. Inspect the selected app's package manager and declared scripts instead of assuming npm script names. For the current official scaffold, local development uses the selected Workbench team:

```bash
WORKBENCH_REQUIRED_TEAM_ID=<teamId> npm run dev
```

This local server and JCode flow are the pre-publish validation path. They do not require a remote Workbench coding project. Do not create one merely to preview or debug the app.

## Verify and deploy

Deployment requires completed local validation and the developer's explicit publishing approval, unless the developer explicitly waived interactive local acceptance. Before naming verification commands, inspect `package.json` and package-manager metadata. Run only declared, relevant test/type-check/build scripts; never assume `npm test` or `npm run typecheck`. Then require:

```bash
test -f dist/index.html
```

Use this one remote workflow:

```bash
octopus-cli coding projects list --json
octopus-cli coding projects show <projectId> --json
octopus-cli coding projects create --type workbench --title <title> --description <description> --json
octopus-cli coding projects publish <projectId> --path dist --json
octopus-cli coding projects watch <taskId> --json
```

Create at most one first project. Create output must contain `id`; if uncertain, resolve with `coding projects list/show` before retry, never a hidden local project-ID mapping. Publish output must contain non-empty `deployment.taskId`; `deployment.id` may only be checked for consistency, never substituted. Missing `taskId` is a contract failure: do not start `watch`; run `octopus-cli coding projects publish --help`, recheck context, then rerun:

```bash
octopus-cli coding projects publish <projectId> --path dist --json
```

`watch` is one GET: poll every five seconds for at most ten minutes (or a supplied shorter deadline), reporting progress at least once a minute. `queued`/`processing` continue; `failed` stops immediately with `errorMessage` and a directly copyable action; `active` plus `workbenchUrl` succeeds. Successful handoff reports exactly `projectId`, `taskId`, `status=active`, `workbenchUrl`, verified `profile`, `host`, `team`; never substitute Arcubase `appId` or deployment/version/environment fields. For unsupported flags, run that exact command’s current `--help`, never a legacy or guessed alias.

Direct HTTP, `kubectl`, GitHub Actions, copied scaffold, alternate publish, and remote archive/delete are outside this skill.

Inside the aiworker repository, `npm --prefix packages/octopus-cli run octopus-cli -- <arguments>` is a context-specific launcher for this same workflow, not a second path.
