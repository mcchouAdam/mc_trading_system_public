# ==============================================================================
# C++ BUILDER BASE IMAGE (mc-cpp-base)
# ------------------------------------------------------------------------------
# Usage: Pre-installs all C++ build tools and dependencies (vcpkg, boost, zmq, etc.)
# Purpose: Accelerates build times for downstream services (trading_engine, etc.)
# Notice: If new C++ libraries are needed, modify this file and rebuild mc-cpp-base.
# ==============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    cmake \
    ninja-build \
    build-essential \
    curl \
    zip \
    unzip \
    tar \
    pkg-config \
    libssl-dev \
    git \
    autoconf \
    autoconf-archive \
    automake \
    libtool \
    m4 \
    python3 \
    python3-dev \
    libffi-dev \
    ccache \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV VCPKG_ROOT=/opt/vcpkg
RUN git clone --depth 1 https://github.com/Microsoft/vcpkg.git $VCPKG_ROOT \
    && $VCPKG_ROOT/bootstrap-vcpkg.sh -disableMetrics

# Auto-detect architecture and set vcpkg triplet (Supports Intel x64 and Apple Silicon arm64)
RUN if [ "$(uname -m)" = "aarch64" ]; then \
    echo "arm64-linux" > /tmp/vcpkg_triplet; \
    else \
    echo "x64-linux" > /tmp/vcpkg_triplet; \
    fi

# Pre-compile common dependencies
RUN VCPKG_TRIPLET=$(cat /tmp/vcpkg_triplet) && \
    $VCPKG_ROOT/vcpkg install \
    cppzmq \
    nlohmann-json \
    redis-plus-plus \
    pybind11 \
    boost-beast \
    boost-asio \
    boost-system \
    boost-thread \
    openssl \
    --triplet $VCPKG_TRIPLET && \
    rm -rf $VCPKG_ROOT/buildtrees $VCPKG_ROOT/packages $VCPKG_ROOT/downloads

# Set environment variables required for child image builds
ENV CMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake
# If left empty, vcpkg toolchain will auto-detect based on host architecture
ENV VCPKG_TARGET_TRIPLET=

WORKDIR /build
