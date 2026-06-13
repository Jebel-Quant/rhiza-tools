# ClusterFuzzLite build image for the rhiza-tools Atheris fuzz targets.
# OSS-Fuzz publishes this base image only as :latest, so an explicit version
# tag isn't available — silence hadolint's untagged-image / latest warnings.
# hadolint ignore=DL3006,DL3007
FROM gcr.io/oss-fuzz-base/base-builder-python

# Copy the whole repository into the OSS-Fuzz source tree.
COPY . $SRC/rhiza-tools

# Build commands run from the project root.
WORKDIR $SRC/rhiza-tools

# The build script is invoked by the OSS-Fuzz `compile` entrypoint.
COPY .clusterfuzzlite/build.sh $SRC/
