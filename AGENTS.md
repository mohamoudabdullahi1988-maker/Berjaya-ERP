# AGENTS.md — sidra-erp

Instructions for Codex and any other coding agent. Latest user allocation (7 Nov 2026): Claude implements the backend/test server; Codex implements the lightweight Android/macOS staff apps, shared web dashboards and their relevant tests. Codex also provides the explicitly requested plot/construction-site location API as an isolated adapter for Claude's backend integration. This task allocation supersedes older role allocations, including decision G7, for this work. Keep backend business logic on the server and preserve the remaining repository rules.

Follow `CLAUDE.md` exactly: it is the single source of rules, commands and the current task. Read `docs/DECISIONS-AND-GATES_v0.1.md` before any work; its decisions win over older documents.

Before starting, check open pull requests and branches from Claude Code, and continue the unfinished one instead of starting over. Merge into `develop` only when CI is green (decision G6).
