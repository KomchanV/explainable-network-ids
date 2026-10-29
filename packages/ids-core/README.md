# ids-core boundary

The engine remains in root `src/` to preserve trusted format-1 Joblib artifacts,
particularly `src.preprocess.NumericFeatures`. Root `project.json` registers it
as the `ids-core` Nx library and owns root Python tests/scripts and Streamlit.
This directory documents the intended future Python packaging boundary; it is
not an installable package or a second copy of the engine.

See [architecture](../../docs/architecture.md) and [development](../../docs/development.md).
