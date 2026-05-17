# Aegis Target Specification

## L1: System Overview
Archetype: cli_tool
Concurrency Model: async

## L2: Container Topology
(To be refined by automated discovery)

## L3: Invariants & Policies
- **strict-ood**: Loose procedural functions are forbidden.
  ```query
  (module [(function_definition) (decorated_definition)] @violation)
  ```

- **hexagonal-isolation**: Domain logic must not depend on infrastructure.
  ```query:py
  (import_from_statement 
    module_name: (dotted_name (identifier) @mod) 
    (#match? @mod "infrastructure")
  ) @violation
  ```
