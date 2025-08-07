# Build stage: Python 3.12.8-bookworm
FROM docker.io/library/python:3.13.6-bookworm@sha256:21f8dc4bf471755d7b48c294540f5e5db79508f9453a3638075cf9ae76f525a1 as build-python

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.5.14@sha256:f0786ad49e2e684c18d38697facb229f538a6f5e374c56f54125aabe7d14b3f7 /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy the application into the container.
COPY pyproject.toml README.md uv.lock /app/
COPY src /app/src

RUN --mount=type=cache,target=/root/.cache \
    cd /app && \
    uv sync \
        --frozen \
        --no-group dev \
        --group prod

# runtime stage: Python 3.12.8-slim-bookworm
FROM docker.io/library/python:3.13.6-slim-bookworm@sha256:6f79e7a10bb7d0b0a50534a70ebc78823f941fba26143ecd7e6c5dca9d7d7e8a

ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --no-create-home --ingroup appuser appuser

WORKDIR /app
COPY --from=build-python /app /app

ENV PATH="/app/.venv/bin:$PATH"
# Set the user to 'appuser'
USER appuser

ENTRYPOINT ["private-assistant-time-skill"]
