# Agent Instructions for griptape-nodes-library-openassetio

## Project Overview

A Griptape Nodes library providing OpenAssetIO integration — allowing asset management systems to
drive workflow inputs (resolve) and capture workflow outputs (publish) via entity references and
the trait system.

______________________________________________________________________

## Development Commands

> **Prefer `make` targets over raw tool invocations.** The exception is targeting a specific file
> or directory (e.g. `uv run pytest tests/unit/test_session.py`), which is fine. Agent-critical
> loop:

- After every substantial change: `make check` — fix every issue before continuing.
- After every code change: `make test/coverage` — do **not** run `pytest` or `slipcover` directly.
  See `CONTRIBUTING.md` for install, pre-commit hooks, release, and per-tool targets.

______________________________________________________________________

## Iteration Loop

Follow this loop when developing Python code:

1. **Write a failing test (RED)** — write one or more tests that describe the desired behaviour.
   Run them and **confirm they fail** for the expected reason before writing any production code.
   Tests live under `tests/unit/` or `tests/integration/`, mirroring the source tree. Mark async
   test functions with `@pytest.mark.asyncio`.
2. **Make the change (GREEN)** — write the minimum production code to make the failing tests pass.
3. **Run static checks** — `make check`. Fix every issue before continuing.
4. **Run tests with coverage** — `make test/coverage`. If you add code you must add tests that
   cover it. Never lower the coverage threshold configured in the Makefile.
5. **Fix issues** — resolve every failure from steps 2 and 3 before continuing.
6. **Repeat** — continue to the next change.

______________________________________________________________________

## Node / Logic Split

Every node must be split into two files:

- **`<name>.py`** — contains all business logic (functions, classes, dataclasses — whatever form
  fits). It **may** import the Griptape Nodes *framework* (e.g. `griptape_nodes.files`,
  `griptape_nodes.common`) but must **not** import any node module (`*_node.py`), including its own
  wrapper. This keeps the logic reusable by other nodes without pulling in a specific node class,
  and independently testable.
- **`<name>_node.py`** — contains the node class (a thin shell). It wires parameters, delegates to
  the logic module in `process()`, and translates results into output parameter values. For
  example, `session.py` holds `create_session()` and the `ManagerSession` dataclass, while
  `session_node.py` holds the `OpenAssetIOSession` node that calls `create_session()` and populates
  outputs. Similarly, `resolve_entity.py` holds the `resolve_entity()` function, while
  `resolve_entity_node.py` holds the `ResolveEntity` node. This separation:
- Makes business logic easy to unit-test without instantiating a node or mocking the node base
  classes.
- Allows `monkeypatch.setattr(node_module, "function_name", mock)` in node tests, keeping them
  focused on parameter wiring and status reporting.
- Enables reuse of the logic by other nodes and integrations without importing the wrapper node.

______________________________________________________________________

## Parameter Passthrough vs Mutation

When a node receives a value on an input and also exposes it as an output, use one of two patterns
depending on whether the value is modified:

- **Passthrough** — the value flows through unchanged. Use a **single parameter** with both `INPUT`
  and `OUTPUT` modes. The output value is the same object the node received.
  ```python
  # entity_reference passes through unchanged — same parameter, INPUT + OUTPUT.
  self.add_parameter(
      Parameter(
          name="entity_reference",
          type="str",
          output_type="str",
          allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT},
      )
  )
  ```
- **Mutation** — the node transforms, derives, or replaces the value. Use **separate input and
  output parameters** with distinct names so the change is visible in the graph.
  ```python
  # traits_data is mutated (merged/enriched) — separate input and output parameters.
  self.add_parameter(
      Parameter(
          name="traits_data_in",
          input_types=["TraitsData"],
          allowed_modes={ParameterMode.INPUT},
      )
  )
  self.add_parameter(
      Parameter(
          name="traits_data_out",
          output_type="TraitsData",
          allowed_modes={ParameterMode.OUTPUT},
      )
  )
  ```

The distinction matters because a user reading the graph can assume that a single INPUT+OUTPUT
parameter carries the **same** value through. If the node silently replaces the value, downstream
nodes receive something different from what the upstream node sent, with no visual indication in
the graph.

______________________________________________________________________

## Code Style

### Copyright Header

Every file that supports comments **must** begin with this header:

```python
# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
```

For YAML, TOML, and other non-Python formats that support `#` comments, use the same header.
Markdown files are exempt.

### Code Organisation — Dependent Before Dependency

Within every module and class, place **callers above the callees they depend on**. A reader should
encounter *what* something does before *how* it does it. **Module-level ordering:**

01. Public entry-point functions (e.g. `get_default_catalogue()`, `build_catalogue()`)
02. Public classes (in test modules, test classes are the public entry points)
03. Private helpers — functions **and classes** prefixed with `_`, ordered so that each helper
    appears before the helpers it calls
04. In test modules: module-level fixtures, at the bottom of the file. Order fixtures so that each
    fixture appears before the fixtures it depends on. This ordering is safe because
    `from __future__ import annotations` is required in every module (making type annotations
    strings) and method/function bodies are only executed at runtime — after the entire module has
    been loaded. A test class can therefore reference `_make_catalogue()` or `_HelperNode` in its
    method bodies without a `NameError`. **Class member ordering:**
05. Class attributes
06. `__init__`
07. Other dunder methods
08. Properties
09. Public instance methods — ordered so that higher-level methods appear before the lower-level
    methods they call
10. Private instance methods — same caller-before-callee ordering
11. Class methods
12. Static methods

### Imports

- All imports must be at the top of the file — no lazy imports inside functions unless the only way
  to break a circular dependency.
- If a lazy import is unavoidable, add a comment naming the circular dependency.
- Use `isort`-compatible ordering (enforced by ruff rule `I`).

### Logic Flow

- Prefer simple, explicit `if`/`else` statements over ternary operators or nested conditionals.
- **Evaluate all failure cases first.** Every validation check, error condition, and guard clause
  goes at the top of the function with an immediate `return`/`raise`. The success path is always
  last.
- Break complex nested expressions into clearly named intermediate variables.

### Return Values

- Avoid returning bare tuples. Use `dataclasses`, named `TypedDict`s, or `NamedTuple`s when
  multiple values must be returned together.

### Exception Handling

- Only wrap code that is *known* to raise the caught exception — keep `try` blocks as small as
  possible.
- Catch the most specific exception type available. Never use bare `except:` or `except Exception:`
  unless explicitly justified with a comment.
- Include context in error messages:
  `"Attempted to <action>. Failed with <data> because <reason>."`.

### Docstrings

- All public classes, methods, and functions must have docstrings.
- Use **Sphinx-style** docstrings (`:param name:`, `:returns:`, `:raises:`), enforced by
  `pydoclint` (style = sphinx in `pyproject.toml`).
- Format docstrings to the line length enforced by `docstrfmt` (88 chars).
- Document all parameters; omit `*args`/`**kwargs` unless meaningful.

### Comments

- Add inline code comments frequently. If in doubt, add a comment. Explain *why* something is done,
  not just *what*.

### Naming

- Use precise, domain-specific names for node parameters — not generic names like `value`, `input`,
  or `data`. For example, use `entity_reference` (not `value`), `trait_ids` (not `items`).

### Mocking

- Prefer `Mock` over `MagicMock`. `MagicMock` pre-implements every dunder method (`__len__`,
  `__iter__`, `__bool__`, etc.), so code that accidentally relies on a magic method will silently
  pass. `Mock` is stricter — it only supports what you explicitly configure. Only reach for
  `MagicMock` when the code under test genuinely calls a dunder method on the mock.
- Use `monkeypatch.setattr` (pytest) to replace objects under test — do not use `@patch` decorators
  from `unittest.mock`.
- Always use `create_autospec(target)` for functions/methods, or `Mock(spec=ClassName)` for class
  instances. **Never pass a boolean to `spec`** — `Mock(spec=True)` sets the spec to the Python
  `bool` object, not to the target, so it silently accepts any call. Bare `Mock()` / `MagicMock()`
  have the same problem.
- Note that `create_autospec` cannot verify call signatures for pybind11/C++ extension classes
  (their `__init__` is not introspectable by `inspect.signature`). For those classes, write
  explicit call assertions (see below) to verify the correct arguments were passed.
- Prefer `assert_called_once_with(...)` or `assert_called_with(...)` over inspecting `call_args`
  directly — they are more readable and produce clearer failure messages. When you need to verify
  multiple calls in order, use a `MagicMock` manager:
  ```python
  calls = MagicMock()
  calls.attach_mock(mock_a, "a")
  calls.attach_mock(mock_b, "b")
  assert calls.method_calls == [call.a(...), call.b(...)]
  ```

### Type Annotations

- All function signatures (arguments and return types) must be fully annotated.
- Use `from __future__ import annotations` at the top of every module to enable PEP 563 postponed
  evaluation.
- Avoid `Any` except where genuinely unavoidable (the ruff rule `ANN401` is intentionally relaxed
  for `**kwargs` in base-class overrides only).

### Markdown

- All Markdown is formatted by `mdformat` (wrap = 99, numbered lists). `make check` enforces this.

______________________________________________________________________

## Testing

### Status Assertions

- Every `process()` test — both success and failure paths — must assert on `_execution_succeeded`
  **and** the full `result_details` string.
- Assert on the exact `result_details` string using `==`, not substring matching with `in`. This
  catches unintended changes to user-facing messages.

### Unit Test Data

- Unit tests must not use manager-specific entity reference prefixes (e.g. `bal:///`). Those
  prefixes are real manager formats and make unit tests look like integration tests. Use a generic
  placeholder like `asset://my/thing` instead.
- Reserve real manager prefixes (e.g. `bal:///`) for integration tests that run against that
  manager.

______________________________________________________________________

## Commit Messages

Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/)
specification, enforced by `gitlint`. Allowed types:

- `feat` — new feature
- `fix` — bug fix
- `refactor` — code restructure without behaviour change
- `deps` — dependency updates
- `chore` — maintenance (build, tooling, config)
- `docs` — documentation only
- `ci` — CI/CD pipeline changes Format: `<type>: <short description>` (imperative mood, no trailing
  period).

Commit message bodies must describe what the **code actually does** — read the implementation
before writing the message. Never paraphrase reference documentation or design plans; those
describe what *could* be done, not what *was* done. Before writing any commit message, run
`git diff` (or `git diff <target-sha>` for squash/fixup commits) and base the message on the actual
diff, not on conversational memory of what changed during the session. The diff is the ground
truth.

### Commit Discipline

Each commit must be **self-contained** — the codebase must be in a valid, non-broken state after
every single commit. Nothing should be left "pending further changes". Keep commits as small as
reasonably possible while satisfying this requirement. If an issue is discovered with a previous
commit during the same development session, use autosquash-style fixup commits:

```bash
git commit --fixup=<sha>   # or --squash=<sha> if the message needs rewriting
```

These will be squashed into their targets during interactive rebase before merge. Never force-push
to shared branches without coordination. **Fixup/squash commit formatting rules:**

- **Do not write a title.** `--fixup` and `--squash` set the title automatically (e.g.
  `fixup! <original title>`). Do not duplicate it.
- **Always add a body.** Although the body will not survive the squash, reviewers need to
  understand *why* the fixup was needed. Describe what was wrong and what the fix changes.
- **Always target the root commit.** Never target another fixup or squash commit. Walk back through
  `git log` to find the original commit that introduced the code being fixed, and use that SHA. Do
  **not** add `Co-Authored-By` trailers to commit messages.

______________________________________________________________________

## Griptape Nodes Patterns Used Here

This section covers only the Griptape Nodes features this library actually uses. For the full API
surface (other traits, artifacts, secrets, async processing, control flow, manifest schema, etc.)
see the upstream `griptape-nodes` documentation.

### Base Classes

- **`DataNode`** — nodes that produce or transform data and have no control flow. Used by `Traits`,
  `IsEntityReference`, `CreateChildContext`.
- **`SuccessFailureNode`** — extends `ControlNode` with built-in success/failure status reporting.
  Used for every operation that can fail via the OpenAssetIO API (`OpenAssetIOSession`,
  `ResolveEntity`, `PreflightEntity`, `RegisterEntity`, `RelatedEntities`, `FileUrlConverter`).
  Call `_create_status_parameters()` as the **last** step in `__init__`.

### SuccessFailureNode Template

```python
class MyNode(SuccessFailureNode):
    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(name=name, metadata=metadata)
        # ... add_parameter(...) calls ...
        # MUST be the last call in __init__:
        self._create_status_parameters(
            result_details_tooltip="Details about the operation result",
            result_details_placeholder="Operation details will appear here.",
        )
    def process(self) -> None:
        self._clear_execution_status()
        try:
            result = do_work(...)  # delegate to the logic module
        except SomeSpecificException as e:
            self._set_status_results(was_successful=False, result_details=f"FAILURE: {e}")
            self._handle_failure_exception(e)
            return
        self.parameter_output_values["output"] = result
        self._set_status_results(was_successful=True, result_details="SUCCESS: ...")
```

### Traits (Parameter Widgets)

Only two trait classes are used:

```python
from griptape_nodes.traits.options import Options            # single-select dropdown
from griptape_nodes.traits.multi_options import MultiOptions  # multi-select
Parameter(name="access", type="str", default_value="Read",
          traits={Options(choices=["Read", "Write"])})
```

### Lifecycle Hooks We Override

- `validate_before_node_run(self) -> list[Exception] | None` — pre-execution validation of required
  inputs and enum-valued parameters. Return a list of exceptions (not `None`) to block execution.
- `after_value_set(self, parameter: Parameter, value: Any) -> None` — used by `Traits` to reshape
  the node's parameters when the selected trait set changes. Always call `super().after_value_set`.
- `after_incoming_connection` / `after_incoming_connection_removed` — used by `ResolveEntity` to
  reshape outputs when an upstream `TraitsData` connection is made or removed. Always call the
  `super()` implementation.

### Library-Level State (`AdvancedNodeLibrary` hooks)

Shared state that must exist before any node is constructed lives in
`griptape_nodes_library_openassetio/library_hooks.py`. The engine instantiates `LibraryHooks`,
calls `before_library_nodes_loaded()`, and stores the instance on the `Library` object. Nodes
retrieve the shared trait catalogue via:

```python
LibraryRegistry.get_library(name).get_advanced_library().trait_catalogue
```

The library JSON points at this module via the top-level `"advanced_library_path"` key.

______________________________________________________________________

## Remote Documentation

### OpenAssetIO API Docs

- **URL:** `https://docs.openassetio.org/OpenAssetIO`
- **Structure:** Doxygen-generated. Key pages:
  - Introduction/overview: `/OpenAssetIO`
  - Class reference: `/annotated.html`
  - Manager class: `/classopenassetio_1_1v1_1_1host_api_1_1_manager.html`
  - HostInterface class: `/classopenassetio_1_1v1_1_1host_api_1_1_host_interface.html`
  - Glossary (entity, trait, resolve, publish): `/glossary.html`
- **Note:** Some subpages return 404 (e.g. `/examples.html`, `/notes_for_hosts.html`). The main
  `/OpenAssetIO` page and class reference pages are accessible.

### OpenAssetIO-MediaCreation Example Notebooks

- **URL:** `https://github.com/OpenAssetIO/OpenAssetIO-MediaCreation/tree/main/examples`

______________________________________________________________________

## Key Design Constraints

1. **Parameter names may not contain whitespace.** Dots, underscores, and alphanumeric characters
   are fine. Trait property output parameters should use a pattern like
   `openassetio-mediacreation:content.LocatableContent.location`.
2. **Dynamic parameters must be marked `is_user_defined=True`** to survive save/load in workflow
   JSON.
3. **TraitsData property values** are strictly `str | int | float | bool`. No complex types (lists,
   dicts, nested objects).
4. **The `context` object** ties related API calls together for stability. Reuse the same context
   across calls that are part of the same logical action.
5. **Trait ID format** — version 1: `{package}:{namespace}.{MemberName}` (e.g.
   `openassetio-mediacreation:content.LocatableContent`); version 2+:
   `{package}:{namespace}.{MemberName}.v{version}`.
