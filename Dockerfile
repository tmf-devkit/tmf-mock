# ---- Build stage ----
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir hatchling
COPY pyproject.toml README.md ./
COPY tmf_mock/ ./tmf_mock/
RUN pip wheel --no-deps --wheel-dir /wheels .

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title="tmf-mock" \
      org.opencontainers.image.description="Smart TMForum Open API mock server" \
      org.opencontainers.image.source="https://github.com/manojchavan23/tmf-mock" \
      org.opencontainers.image.licenses="Apache-2.0"
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
RUN adduser --disabled-password --gecos "" appuser
USER appuser
ENV TMF_MOCK_APIS="638,639,641" \
    TMF_MOCK_SEED="1" \
    TMF_MOCK_HOST="0.0.0.0" \
    TMF_MOCK_PORT="8000" \
    TMF_MOCK_BASE_URL="http://localhost:8000"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["sh", "-c", "tmf-mock start --host $TMF_MOCK_HOST --port $TMF_MOCK_PORT --apis $TMF_MOCK_APIS"]
