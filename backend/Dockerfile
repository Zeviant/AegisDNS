FROM python:3.12-slim

# build-essential + cmake are needed to build llama-cpp-python if no prebuilt
# wheel matches the target platform; git is required by its CMake build-info
# step (fails outright without it, even though it only affects a version string);
# curl is used by the compose healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Without this, llama-cpp-python's CMake build defaults to -march=native, baking
# in whichever CPU happens to build the image — since docker-compose builds this
# image locally on every machine that runs it, that would silently defeat the
# "same on every device" goal (a build on a newer CPU could produce a binary that
# crashes with "Illegal instruction" on an older one). Portable baseline instead.
ENV CMAKE_ARGS="-DGGML_NATIVE=OFF"

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# The scanner/ package (WHOIS/DNS/TLS/HTTP heuristics) is reused as-is, unmodified.
COPY scanner/ ./scanner/
COPY backend/ ./backend/

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/data/db/UserInformation.db \
    VT_CACHE_DIR=/data/vt_cache \
    MODEL_DIR=/data/models \
    BACKEND_PORT=5005

RUN mkdir -p /data/db /data/vt_cache /data/models

EXPOSE 5005

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5005/health || exit 1

# -m so /app (the working dir, containing the `backend` package) is on sys.path.
CMD ["python", "-m", "backend.app"]
