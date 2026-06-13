# ClusterFuzzLite build image for the rhiza-tools Atheris fuzz targets.
FROM gcr.io/oss-fuzz-base/base-builder-python

# Copy the whole repository into the OSS-Fuzz source tree.
COPY . $SRC/rhiza-tools

# Build commands run from the project root.
WORKDIR $SRC/rhiza-tools

# The build script is invoked by the OSS-Fuzz `compile` entrypoint.
COPY .clusterfuzzlite/build.sh $SRC/
