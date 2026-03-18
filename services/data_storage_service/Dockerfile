FROM python:3.13-slim

ARG GITLAB_CREDENTIALS=""

ARG NEXUS_PYPI_INDEX_URL

ENV HOME="/dude"
ENV PYTHONPATH=$HOME

RUN groupadd -g 999 dudes && \
    useradd -u 999 -m -g dudes -s /bin/bash dude && \
    mkdir -p ${HOME} && chown dude:dudes $HOME

RUN mkdir -p /var/lib/app/storage && chown -R dude:dudes /var/lib/app

WORKDIR ${HOME}

RUN apt-get update && apt-get install -y curl build-essential netcat-openbsd \
    gcc \
    libpq-dev \
    postgresql-client \
    cargo \
    rustc \
    gosu \
    git \
    zlib1g-dev \
    libjpeg-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN if [ -n "$GITLAB_CREDENTIALS" ]; then \
        git config --global credential.helper store && \
        echo "https://${GITLAB_CREDENTIALS}@gitlab.gigalegal.space" > ~/.git-credentials; \
    fi

RUN python -m pip install -i "${NEXUS_PYPI_INDEX_URL:-https://pypi.org/simple}" --disable-pip-version-check --no-cache-dir uv

COPY --chown=dude:dudes ./requirements.txt ${HOME}/

RUN uv pip install --system --index-url "${NEXUS_PYPI_INDEX_URL:-https://pypi.org/simple}" -r requirements.txt

RUN rm -f ~/.git-credentials && \
    git config --global --unset credential.helper || true

COPY --chown=dude:dudes ./service ${HOME}/service
COPY --chown=dude:dudes ./alembic ${HOME}/alembic
COPY --chown=dude:dudes ./entrypoints.sh ${HOME}
COPY --chown=dude:dudes ./docker-entrypoint.sh ${HOME}

RUN chmod +x ${HOME}/entrypoints.sh ${HOME}/docker-entrypoint.sh

ENTRYPOINT ["/dude/docker-entrypoint.sh"]

CMD ["server"]
