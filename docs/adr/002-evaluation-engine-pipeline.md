# ADR 002: Multi-modal Evaluation Engine Pipeline

## Status
Accepted

## Context
When an AI agent modifies code, Aegis must verify whether the changes adhere to the defined architectural rules. Relying purely on an LLM to evaluate its own code against complex architectural rules ("Semantic Prompting") is inherently flaky, non-deterministic, and prone to hallucinations. However, using purely static analysis (AST/Graph) is too rigid and cannot enforce domain-specific language rules or naming conventions effectively.

## Decision
We adopted a **Multi-modal Evaluation Pipeline** that cascades through specialized engines rather than relying on a single evaluation method.

1. **TreeSitter AST Engine**: Provides fast, deterministic structural evaluation of source code. It catches structural violations (e.g., "classes in this package must implement this interface") with 100% accuracy.
2. **Import Graph Engine**: Provides $O(1)$ JIT-cached dependency analysis. It ensures module isolation and boundary enforcement (e.g., "Presentation cannot import from Infrastructure") instantly, without the overhead of parsing entire files semantically.
3. **Regex Engine**: Provides fast, pattern-based checks for low-level formatting or banned token usage.
4. **Hardened Semantic Engine**: Used strictly as a fallback or for rules that require human-like judgment (e.g., domain terminology compliance). This engine forces the LLM to use a rigorous "rubric" approach rather than open-ended judgment, reducing hallucination.

## Consequences
- **Pros**: High performance, deterministic architectural enforcement, reduced LLM API token costs, and high confidence in architectural compliance.
- **Cons**: Increased complexity in rule definition, as rules must specify which engine to target. Evaluators must maintain TreeSitter grammar dependencies.
