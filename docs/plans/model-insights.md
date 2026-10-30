# Model Insights implementation plan

Use the existing once-loaded artifact; add a typed read-only `/model/evaluation` projection. Validate the saved matrix against each score using scikit-learn zero-division conventions, and report inconsistency with a structured error without changing artifact loading or inference. Whitelist metadata and preserve absent values as null. Keep saved evaluation independent of analysis sessions.

Build a dark, responsive `/model-insights` route using generated types, native metric cards and a semantic confusion-matrix table. Include provenance, pipeline methodology and explicit scientific limitations. Guard asynchronous responses on unmount and refresh.

1. Add synthetic API tests for saved parity, invalid snapshots, unavailable model and read-only retrieval; run before implementation.
2. Implement typed projection and endpoint; regenerate OpenAPI/client.
3. Add metric formatting tests and route, navigation and browser tests.
4. Run baseline/regression checks, contract synchronization, build, browser suite and trusted compatibility.
5. Document actual behavior, verification evidence and release readiness; commit and open PR without merging.

The user's detailed specification supplies the approved scope and authorizes inline implementation. No additional design approval is needed.
