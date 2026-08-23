# Production image for the Habbi-Tracker API.
#
# Two stages so the compiler toolchain never reaches the runtime image, and a
# non-root user because nothing in here needs to be root. No secrets are baked
# in: every setting arrives as an environment variable at run time.

# --- build ---------------------------------------------------------------
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Only what the package metadata needs to resolve, then the package itself.
COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --upgrade pip setuptools wheel \
    && pip install .

# --- runtime -------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

RUN useradd --create-home --uid 10001 habbi

WORKDIR /srv

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh && chown -R habbi:habbi /srv

USER habbi

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
