# Stage 1: Build C++ Trading Engine
# ==========================================
ARG REGISTRY=""
FROM ${REGISTRY}mc-cpp-base:latest AS builder

WORKDIR /build

# Copy source code
COPY trading_engine/CMakeLists.txt trading_engine/CMakeLists.txt
COPY trading_engine/src trading_engine/src
COPY trading_engine/include trading_engine/include
COPY core_lib core_lib

# Build using pre-installed dependencies in the base image
WORKDIR /build/trading_engine
RUN cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DVCPKG_MANIFEST_MODE=OFF
RUN cmake --build build --config Release --parallel $(nproc)

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/trading_engine/build/TradingEngineCpp /app/TradingEngineCpp
RUN chmod +x /app/TradingEngineCpp

CMD ["/app/TradingEngineCpp"]

