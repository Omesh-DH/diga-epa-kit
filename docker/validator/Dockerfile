# Reproducible gate: same validator, JDK and Python as CI.
#   docker build -t diga-epa-kit-validator docker/validator
#   docker run --rm -v "$PWD":/work diga-epa-kit-validator
FROM eclipse-temurin:17-jre-jammy

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
ENTRYPOINT ["sh", "-c", "python3 -m venv /tmp/venv && /tmp/venv/bin/pip install -q -e . && /tmp/venv/bin/python scripts/fetch_spec.py && /tmp/venv/bin/python scripts/validate.py"]
