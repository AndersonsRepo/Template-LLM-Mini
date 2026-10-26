# Approved optional data analyzer

The owner approved a conditional analyzer for task-relevant raw, processed, and
generated data, both before building and after processing when relevant. Activate
under approved configuration; do not spend model calls on absent/unrelated data.
Missing expected data, structural mismatch, or semantic irrelevance must prompt
the user and pause dependent work without blocking unrelated tasks.

Scope includes deterministic Python inspection, task tracking, data-versioned
analysis evidence and handoffs, initial interview/configuration, role instructions,
README/primer updates, and meaningful behavioral tests. Builder writes processors;
coordinator runs them; analyzer interprets. Do not alter raw originals, fabricate
inputs, substitute unapproved data, or send whole datasets into model context.
