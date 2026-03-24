# Stage 1: Build C++ Market Data Streamer
# ==========================================
ARG REGISTRY=""
FROM ${REGISTRY}mc-cpp-base:latest AS builder

WORKDIR /build/market_data_streamer

# Build source code
COPY market_data_streamer/CMakeLists.txt .
COPY market_data_streamer/src/ ./src/
COPY market_data_streamer/include/ ./include/

RUN cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DVCPKG_MANIFEST_MODE=OFF
RUN cmake --build build --config Release --parallel $(nproc)

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    libssl-dev \
    ca-certificates \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/market_data_streamer/build/CppWsClient /app/CppWsClient
RUN chmod +x /app/CppWsClient

CMD ["/app/CppWsClient"]

