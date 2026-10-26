# Approved restructuring request

The owner asked for a review of template_llm_mini as a lightweight starting point
for new harnesses, then approved implementing every proposed fix: a state lock with
path-scoped claims and leases so Claude and Codex can work side by side; a
tool-agnostic Git pre-commit hook; Claude Code hooks and settings that move
mechanical rules out of prompts into a Python guard; per-role definition files with
frontmatter policy; deduplicated, shorter prompts; data analysis as an optional
add-on; and template history separated from new projects.

This is a consolidated scope record, not a verbatim transcript.
