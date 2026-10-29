# MinIO server + mc, built from upstream source at pinned release tags
# (aggsys AGG-393). Replaces the frozen bitnamilegacy/minio image.
#
# MinIO withdrew its community binaries and images (dl.min.io answers
# 410 Gone, 2026-10-12) and archived github.com/minio/minio (2026-04); the
# source at the release tags is still published, so this builds it. Each
# clone is checked against the commit the tag pointed at when pinned, so a
# moved tag fails the build instead of changing the binary.
#
# mc rides along for admin work inside the pod (kubectl exec): users and
# policies (e.g. the erp-server user, AGG-466), versioning, lifecycle.
#
# Build and push from the repo root, then pin apps/minio/values.yaml
# image.digest to the digest `docker push` prints:
#   docker build -t 192.168.2.17:5000/minio:RELEASE.2025-10-15T17-29-55Z apps/minio/image
#   docker push 192.168.2.17:5000/minio:RELEASE.2025-10-15T17-29-55Z
#
# To switch to a maintained fork (e.g. github.com/pgsty/minio), change
# MINIO_REPO / MINIO_TAG / MINIO_COMMIT together.

ARG GO_IMAGE=golang:1.26-bookworm@sha256:23ce71337b726608afb1bc00986e630a05034a87a87ea1fc2cd1ae5cf33387eb
ARG RUNTIME_IMAGE=gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab

FROM ${GO_IMAGE} AS build
ARG MINIO_REPO=https://github.com/minio/minio.git
ARG MINIO_TAG=RELEASE.2025-10-15T17-29-55Z
ARG MINIO_COMMIT=9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a
ARG MC_REPO=https://github.com/minio/mc.git
ARG MC_TAG=RELEASE.2025-08-13T08-35-41Z
ARG MC_COMMIT=7394ce0dd2a80935aded936b09fa12cbb3cb8096
ENV CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOTOOLCHAIN=local GOFLAGS=-buildvcs=false MINIO_RELEASE=RELEASE MC_RELEASE=RELEASE
WORKDIR /src
RUN set -eux; \
    git clone -q --depth 1 --branch "$MINIO_TAG" "$MINIO_REPO" minio; \
    test "$(git -C minio rev-parse HEAD)" = "$MINIO_COMMIT"; \
    git clone -q --depth 1 --branch "$MC_TAG" "$MC_REPO" mc; \
    test "$(git -C mc rev-parse HEAD)" = "$MC_COMMIT"
# Same flags as upstream `make build`; gen-ldflags stamps the release tag and
# commit into `minio --version` (MINIO_RELEASE/MC_RELEASE=RELEASE, as upstream release
# builds set it, so the version reads RELEASE.… rather than DEVELOPMENT.…).
RUN --mount=type=cache,target=/root/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build \
    set -eux; \
    cd /src/minio; \
    go build -tags kqueue -trimpath -ldflags "$(go run buildscripts/gen-ldflags.go)" -o /out/minio .; \
    cd /src/mc; \
    go build -tags kqueue -trimpath -ldflags "$(go run buildscripts/gen-ldflags.go)" -o /out/mc .; \
    /out/minio --version; /out/mc --version; \
    install -d -o 1001 -g 1001 /out/data /out/tmp

FROM ${RUNTIME_IMAGE}
ARG MINIO_TAG=RELEASE.2025-10-15T17-29-55Z
LABEL org.opencontainers.image.title="minio" \
      org.opencontainers.image.version="${MINIO_TAG}" \
      org.opencontainers.image.source="https://github.com/thatsimonsguy/homelab-k8s/tree/main/apps/minio/image" \
      org.opencontainers.image.licenses="AGPL-3.0-only"
COPY --from=build /out/minio /out/mc /usr/bin/
# /data is the default data dir; /tmp is writable for mc's config under a
# read-only root filesystem (the chart mounts an emptyDir there).
COPY --from=build --chown=1001:1001 /out/data /data
COPY --from=build --chown=1001:1001 /out/tmp /tmp
# uid/gid 1001: the bitnami image's user, which owns the existing data.
USER 1001:1001
ENV HOME=/tmp MC_CONFIG_DIR=/tmp/.mc
WORKDIR /tmp
EXPOSE 9000 9001
ENTRYPOINT ["/usr/bin/minio"]
CMD ["server", "/data", "--address", ":9000", "--console-address", ":9001"]
