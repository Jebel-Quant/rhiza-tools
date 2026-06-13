#!/bin/bash -eu
# Build script for ClusterFuzzLite / OSS-Fuzz.
#
# Installs the project so its modules are importable, then compiles every
# Atheris fuzz target shipped under fuzzers/ into a standalone executable.

# Install the package (and its dependencies) into the build image so the
# fuzz targets can import rhiza_tools during PyInstaller analysis and at run
# time.
pip3 install .

# Compile each fuzz target. compile_python_fuzzer names the resulting binary
# after the source file (e.g. version_matrix_fuzzer.py -> version_matrix_fuzzer).
for fuzzer in "$SRC"/rhiza-tools/fuzzers/*_fuzzer.py; do
  compile_python_fuzzer "$fuzzer"
done
