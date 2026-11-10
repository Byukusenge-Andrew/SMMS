# AI Context & Change Tracking Instructions

> [!IMPORTANT]
> **Token Preservation Rule**: Do NOT re-read or scan entire codebase source files indiscriminately.
> Instead, read `.aicontext/SUMMARY.md` for complete codebase architecture, symbol maps, and connection graphs.

## Instructions for AI Assistant

1. **Context & Architecture Discovery**:
   - Read `.aicontext/SUMMARY.md` to understand all available modules, classes, functions, and import relationships in ~2,000 tokens.
   - Inspect `.aicontext/recent_changes.md` to see recent modifications and impact radius.

2. **Self-Updating Context (0 LLM Tokens Burned)**:
   - Whenever you create, modify, or delete files in this project, execute `aicontext sync` (or invoke the `sync_context` MCP tool).
   - *Note: `aicontext sync` executes 100% locally on CPU via fast AST/hash parsing. It uses 0 LLM API tokens.*

3. **Impact Radius Verification**:
   - Before suggesting edits to shared modules, check `.aicontext/recent_changes.md` or use `get_impact_radius` to verify which downstream dependent files are affected.
