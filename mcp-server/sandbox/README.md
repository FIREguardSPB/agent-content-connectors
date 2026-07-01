# sandbox/

Self-generated tools land here (one folder per tool: `tool.py` + `manifest.json`).

**Nothing in this directory is loaded by the production MCP server.**
`registry.load_builtin_tools()` only imports `broker_connectors.tools.*`; sandbox
is invisible to it. A generated tool becomes usable only after a human reviews
the diff and calls `selfextend.promote(name, approved=True)`, which copies it
into `src/broker_connectors/tools/`. This review-before-activation step is the
single security gate (§7.2): it's what stops the agent from wiring up a new
capability that some comment/article told it to add.
