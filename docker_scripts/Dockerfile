FROM nvidia/cuda:11.8.0-devel-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    zip \
    unzip \
    sox \
    libsox-dev \
    libsox-fmt-all \
    build-essential \
    ca-certificates \
    sudo \
    git \
    libsndfile1-dev \
    libyaml-cpp-dev \
    bzip2 \
    libx11-6 \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app
ENV PYTHONPATH=/app

ARG GID
ARG UID
ARG NAME

USER root
RUN groupadd -g ${GID} ${NAME}
RUN adduser --disabled-password --force-badname --uid ${UID} --gid ${GID} --gecos '' --shell /bin/bash ${NAME} \
    && chown -R ${NAME}:${NAME} /app
RUN echo "${NAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

USER ${NAME}
ENV HOME=/home/${NAME}
RUN mkdir -p $HOME/.cache $HOME/.config

COPY --chown=${NAME} requirements.txt /app/requirements.txt

ENV CONDA_AUTO_UPDATE_CONDA=false \
    PATH=$HOME/miniconda/bin:$PATH

# Lock the torch stack so nothing can change it during later steps.
# torch 2.6 (required by transformers per CVE-2025-32434) + cu118 (works on driver 535 / CUDA 12.2)
RUN printf 'torch==2.6.0+cu118\ntorchaudio==2.6.0+cu118\n' > /app/constraints.txt

RUN curl -sLo ~/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-py311_24.9.2-0-Linux-x86_64.sh \
 && chmod +x ~/miniconda.sh \
 && ~/miniconda.sh -b -p ~/miniconda \
 && rm ~/miniconda.sh \
 && pip install --no-cache-dir --upgrade pip \
 # 1) torch stack (cu118) FIRST
 && pip install --no-cache-dir \
      torch==2.6.0+cu118 torchaudio==2.6.0+cu118 \
      --index-url https://download.pytorch.org/whl/cu118 \
 # 2) lm-polygraph ALONE (heaviest constrainer), torch bound by constraints
 && pip install --no-cache-dir lm-polygraph \
      -c /app/constraints.txt \
      --extra-index-url https://download.pytorch.org/whl/cu118 \
 # 3) Everything else, under the SAME constraints
 && pip install --no-cache-dir -r requirements.txt \
      -c /app/constraints.txt \
      --extra-index-url https://download.pytorch.org/whl/cu118 \
 # 4) Re-pin torch stack LAST to guarantee the right build wins
 && pip install --no-cache-dir --force-reinstall --no-deps \
      torch==2.6.0+cu118 torchaudio==2.6.0+cu118 \
      --index-url https://download.pytorch.org/whl/cu118 \
 && rm /app/requirements.txt /app/constraints.txt \
 && conda clean -ya

RUN pip install --no-cache-dir --upgrade pip cmake ninja
ENV CUDA_HOME=/usr/local/cuda
ENV CUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

RUN python -c "import torch, torchaudio; \
print('torch', torch.__version__, '| torchaudio', torchaudio.__version__); \
assert torch.__version__.split('+')[0] == torchaudio.__version__.split('+')[0], 'version mismatch'; \
assert 'cu118' in torch.__version__ and 'cu118' in torchaudio.__version__, 'not cu118 build'; \
assert tuple(map(int, torch.__version__.split('+')[0].split('.')[:2])) >= (2, 6), 'torch < 2.6'; \
import torchaudio._extension; print('torchaudio C++ ext loaded OK')"
