#!/bin/bash -eu
# ClusterFuzzLite build script — installs rhiza_tools and compiles each Atheris
# fuzz target under fuzzers/ via OSS-Fuzz's compile_python_fuzzer helper.

cd "$SRC"

# Pin pip so the build environment is reproducible and only changes through a
# reviewed bump (the same rationale as the SHA-pinned base image).
pip3 install --upgrade "pip==24.3.1"

# Install the package and its runtime dependencies into the build environment so
# PyInstaller can discover and bundle rhiza_tools into each frozen fuzz target.
# compile_python_fuzzer names the resulting binary after the source file
# (e.g. version_matrix_fuzzer.py -> version_matrix_fuzzer).
pip3 install .

for fuzzer in fuzzers/*_fuzzer.py; do
  compile_python_fuzzer "$fuzzer"
done
