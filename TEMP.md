## Product Requirements Document (PRD): Aegis Dual Distribution Architecture

**Document Status:** Final

**Target:** Enterprise Agentic Governance Engine

---

### Executive Summary

To establish Aegis as a foundational standard for autonomous agent governance, the system must deploy seamlessly across diverse enterprise environments. This PRD outlines the **Dual Distribution Strategy**, providing both a localized, embedded Python library and a highly scalable, network-accessible containerized microservice. This dual architecture ensures that Aegis satisfies the requirements of isolated local execution and distributed cooperative agent swarms, maintaining strict adherence to Object-Oriented Design (OOD) and SOLID principles for long-term extensibility.

---

### I. Distribution Vector I: Native Python Library (`aegis-engine`)

This distribution vector serves environments requiring microsecond latency, zero network overhead, and direct graph integration.

* **Target Audience:** Python application developers, platform engineers, and localized orchestration frameworks (e.g., DeepAgents, LangGraph).
* **Deployment Mechanism:** Standardized Python wheel (`.whl`) and source archive (`tar.gz`) published to the Python Package Index (PyPI).
* **Execution Profile:** Aegis runs natively in-process. It executes synchronously within the host application's memory space, preserving the empirically validated sub-10ms AST evaluation latency and negligible 50 KB memory footprint.
* **Implementation Requirements:**
* Zero dependency on external agent orchestration frameworks within the `core` engine.
* Exportable `AegisEnforcementNode` for direct injection into existing state graphs.
* Self-documenting APIs with strict type hinting for seamless IDE integration.



---

### II. Distribution Vector II: FastMCP Containerized Microservice

This distribution vector serves networked environments, providing a centralized, language-agnostic governance server.

* **Target Audience:** Distributed engineering teams, polyglot microservice environments, and remote cooperative agent swarms.
* **Deployment Mechanism:** A secure, minimal Docker image built on `python:3.12-slim`, distributed via a container registry (e.g., GitHub Container Registry (GHCR) or Docker Hub).
* **Execution Profile:** Standalone service exposing the Model Context Protocol (MCP).
* **Implementation Requirements:**
* Implement FastMCP using the `StreamableHTTP` transport layer to ensure broad compatibility and reliable network traversal.
* Enforce isolated execution: the container must securely hold rule registries, baseline configurations, and required credentials server-side.
* Remote agents must receive only deterministic evaluation results and remediation prompts, ensuring the host shell environment is never exposed to the LLM.



---

### III. CI/CD Pipeline Automation Blueprint

To guarantee production-grade reliability and zero-drift between the library and the microservice, all releases must be automated through a unified continuous integration and deployment pipeline.

| Pipeline Stage | Target Environment | Automated Execution Requirements |
| --- | --- | --- |
| **1. Validation & Audit** | Pre-Flight | Execute the complete test suite ($N=50$ Monte Carlo simulation, Red-Team evasion suite, unit tests) and `ruff` linting. Fails pipeline on any regression. |
| **2. Artifact Compilation** | PyPI | Compile the pure Python `.whl` and `tar.gz` distributions. Authenticate via secure OIDC tokens to stage the release. |
| **3. Containerization** | GHCR / Docker Hub | Build the `python:3.12-slim` image, install locked dependencies, and configure the FastMCP entry point. Tag with the precise semantic version. |
| **4. Parallel Release** | Global Availability | Push the wheel to PyPI and the Docker image to the registry simultaneously upon a tagged `main` branch push. |

---

### IV. Success Criteria

* **Parity:** Both distribution vectors pass the 546-test empirical audit natively.
* **Scalability:** The containerized microservice processes concurrent rule evaluations without race conditions.
* **Ergonomics:** Developers can install Aegis natively via `uv add aegis-engine` or attach it remotely via a single Docker run command.