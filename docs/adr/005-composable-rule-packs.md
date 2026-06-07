# ADR 005: Composable Rule Packs

## Status
Accepted

## Context
Governance rules vary wildly between projects. A monolithic configuration file (like `eslint.config.js`) becomes unwieldy when defining complex architectural boundaries, domain semantics, and structural conventions. Furthermore, enforcing organizational standards across hundreds of repositories requires a central distribution mechanism, rather than copy-pasting YAML files.

## Decision
We designed a modular **Rule Pack Architecture**:

1. **Modular YAML**: Rules are defined in focused YAML files (e.g., `clean-architecture.yaml`, `domain-semantics.yaml`) located in `.aegis/rules/`.
2. **Extends Keyword**: Rule packs can inherit from remote packs using the `extends: [url]` directive.
3. **Registry System**: The `RulePackManager` can fetch, cache, and install community or organizational rule packs dynamically.
4. **Local Overrides**: Projects can extend a remote, strict organizational rule pack and apply local suppressions or additions without modifying the remote source of truth.

## Consequences
- **Pros**: Highly composable. Organizations can enforce "Base Security Rules" remotely while allowing teams to define their own "Domain Naming Rules" locally. Easy sharing of architectural patterns across the open-source ecosystem.
- **Cons**: Remote rule resolution introduces network dependencies during kernel boot, necessitating robust caching strategies.
