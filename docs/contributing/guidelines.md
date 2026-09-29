# Contributing Guidelines

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/pokex.git`
3. Create branch: `git checkout -b feat/your-feature-name`
4. Set up local environment (see [Local Setup](../development/local-setup.md))
5. Make changes following [Coding Standards](../development/coding-standards.md)
6. Run tests (see [Testing Strategy](../development/testing.md))
7. Submit PR to `main` branch

---

## Development Workflow

### Branch Naming

| Type | Format | Example |
|------|--------|---------|
| Feature | `feat/<short-description>` | `feat/card-scan-page` |
| Bug Fix | `fix/<short-description>` | `fix/recognition-timeout` |
| Refactor | `refactor/<short-description>` | `refactor/cache-invalidation` |
| Docs | `docs/<short-description>` | `docs/api-reference-update` |
| Chore | `chore/<short-description>` | `chore/update-dependencies` |

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

Types:
- `feat` — New feature
- `fix` — Bug fix
- `refactor` — Code change, no behavior change
- `perf` — Performance improvement
- `docs` — Documentation only
- `test` — Adding/updating tests
- `chore` — Maintenance (deps, config, CI)
- `build` — Build system changes
- `ci` — CI/CD changes

Examples:
```
feat(web): add camera scan page with torch toggle

fix(data-ingestion): handle duplicate card upsert on conflict

refactor(ui): extract Button variant logic to useButtonVariant hook

perf(recognition): batch ONNX inference for multiple crops

chore(deps): update pydantic to 2.9.2
```

### PR Requirements

- [ ] Single logical change — One feature/fix per PR
- [ ] All CI passes — Lint, typecheck, tests, build
- [ ] Tests added/updated — Cover new behavior
- [ ] Docs updated — If public API changed
- [ ] No merge commits — Rebase onto `main`
- [ ] Descriptive title & description — Link issue if applicable

---

## Code Review Process

### Reviewer Checklist

- [ ] Code follows [Coding Standards](../development/coding-standards.md)
- [ ] Tests cover new/changed behavior
- [ ] No obvious bugs or edge cases missed
- [ ] Performance implications considered
- [ ] Security implications considered (input validation, secrets)
- [ ] Documentation updated if needed
- [ ] No unnecessary dependencies added

### Review Comments Style

- **Blocking** — Must fix before merge (security, correctness, breaking changes)
- **Suggesting** — Improvement, not required (style, alternative approach)
- **Question** — Clarification needed
- **Praise** — Good pattern, nice solution

### Response Time

- First review: Within 24 hours (business days)
- Follow-up: Within 4 hours
- PR author: Respond within 24 hours

---

## Testing Requirements

### Minimum Coverage

| Change Type | Required Tests |
|-------------|----------------|
| New API endpoint | Unit + integration |
| New React component | Unit (RTL) + snapshot |
| New Rust command | Unit (cargo test) |
| Bug fix | Regression test |
| Refactor | Existing tests pass |

### Running Tests Locally

```bash
# Quick check (run before commit)
pnpm lint && pnpm typecheck && pnpm test

# Full test suite
cd D:\github\pokex
test-env\Scripts\python.exe -m pytest test/python/ test/e2e/ -v
cd apps/web && pnpm playwright test
cd apps/desktop-mobile/src-tauri && cargo test --lib
```

---

## Dependency Management

### Adding Dependencies

**JavaScript (pnpm):**
```bash
# Runtime
pnpm add <package> --filter web

# Dev
pnpm add -D <package> --filter web

# UI package (shared)
pnpm add <package> --filter @pokex/ui
```

**Python (uv):**
```bash
cd services/data-ingestion
uv add <package>           # Runtime
uv add --dev <package>     # Dev
```

**Rust (Cargo):**
```bash
cd apps/desktop-mobile/src-tauri
cargo add <crate>
```

### Dependency Guidelines

1. Prefer stdlib — No dependency for what stdlib provides
2. Audit before add — Check maintenance, license, bundle size
3. Pin versions — Exact versions in lockfiles
4. Group updates — Update related deps together
5. Document rationale — Comment in PR for non-obvious adds

---

## Security

### Reporting Vulnerabilities

Do not open public issues for security vulnerabilities.

Email: security@pokex.dev (or use GitHub Security Advisories)

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

### Security Checklist for PRs

- [ ] No secrets in code (API keys, passwords, tokens)
- [ ] Input validation at all boundaries
- [ ] Parameterized queries (no string interpolation in SQL)
- [ ] No `eval`/`exec`/`dangerouslySetInnerHTML` without sanitization
- [ ] Dependencies scanned for vulnerabilities (`pnpm audit`, `uv pip audit`, `cargo audit`)

---

## Release Process

### Versioning

Semantic Versioning (MAJOR.MINOR.PATCH):
- MAJOR — Breaking changes
- MINOR — New features, backward compatible
- PATCH — Bug fixes, backward compatible

### Release Steps (Maintainers)

1. Update version in root `package.json` and service `pyproject.toml` files
2. Generate changelog from conventional commits
3. Create release branch: `release/v1.2.0`
4. Run full CI on release branch
5. Tag release: `git tag -a v1.2.0 -m "Release v1.2.0"`
6. Push tag: `git push origin v1.2.0`
7. GitHub Actions builds and pushes Docker images
8. Create GitHub Release with changelog
9. Deploy to staging → production

### Automated Releases (Future)

```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ['v*']
jobs:
  release:
    # Build, sign, publish to registries
    # Create GitHub Release
    # Notify Discord/Slack
```

---

## Code of Conduct

### Our Standards

- Be respectful — Disagree constructively
- Be inclusive — Welcome newcomers, diverse perspectives
- Be collaborative — Share knowledge, help others
- Be professional — No harassment, discrimination, or toxicity

### Enforcement

Violations may result in:
- Warning (first offense)
- Temporary ban from PR reviews/discussions
- Permanent ban from organization

Report to: conduct@pokex.dev

---

## Project Structure Conventions

### Adding a New Service

1. Create `services/<name>/` with:
   - `pyproject.toml` (uv config)
   - `Dockerfile` (multi-stage)
   - `<name>_app/` (source code)
   - `.env.example`
2. Add to `docker-compose.yml`
3. Add to `docker-bake.hcl`
4. Add CI matrix entry in `.github/workflows/ci.yml`
5. Add tests in `test/python/`
6. Document in [API Reference](../api/reference.md) and [Services](../architecture/services.md)

### Adding a New Shared Component

1. Create in `packages/ui/src/components/<ComponentName>/`
2. Export from `packages/ui/src/index.ts`
3. Add tests in `packages/ui/src/components/<ComponentName>/*.test.tsx`
4. Update `packages/ui/package.json` peer deps if needed
5. Use in both `apps/web` and `apps/desktop-mobile`

---

## Getting Help

- Documentation: Check `docs/` first
- Issues: Search existing issues before creating new
- Discussions: Use GitHub Discussions for questions
- Discord: #pokex-dev (invite in repo description)

---

## License

By contributing, you agree that your contributions will be licensed under the project's license (MIT).