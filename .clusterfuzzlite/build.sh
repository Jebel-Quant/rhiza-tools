#!/bin/bash -eu
# ClusterFuzzLite build script — installs rhiza_tools and compiles each Python
# harness in tests/fuzz/ via OSS-Fuzz's compile_python_fuzzer helper.

cd "$SRC"

# Pin pip so the build environment is reproducible and only changes through a
# reviewed bump (the same rationale as the SHA-pinned base image).
pip3 install --upgrade "pip==24.3.1"

# Install the package and its runtime dependencies so PyInstaller can discover
# and bundle rhiza_tools into each frozen fuzzer binary. The fuzz target only
# touches the pure-Python suppression comment parser, so no compiled-extension
# dependencies need a --collect-all here.
pip3 install .

for fuzzer in tests/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$fuzzer"
done
