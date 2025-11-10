FROM nikolaik/python-nodejs:python3.12-nodejs22

SHELL ["/bin/bash", "-c"]

# Shared environment variables
ENV POETRY_VIRTUALENVS_PATH=/Forge/poetry \
    POETRY_HTTP_TIMEOUT=120 \
    POETRY_HTTP_RETRIES=5 \
    MAMBA_ROOT_PREFIX=/Forge/micromamba \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    EDITOR=code \
    VISUAL=code \
    GIT_EDITOR="code --wait" \
    OPENVSCODE_SERVER_ROOT=/Forge/.openvscode-server \
    PYTHONPATH=/Forge/code











# ================================================================
# START: Build Runtime Image from Scratch
# ================================================================
# This is used in cases where the base image is something more generic like nikolaik/python-nodejs
# rather than the current Forge release



# Set PATH early to ensure system commands are available
ENV PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Install base system dependencies




RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget curl ca-certificates  apt-utils git jq tmux build-essential ripgrep ffmpeg \
        coreutils util-linux procps findutils grep sed \
        libgl1 \
        libasound2-plugins libatomic1 \
        # Install Docker dependencies
        apt-transport-https ca-certificates curl gnupg lsb-release




# Install uv (required by MCP)
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/Forge/bin" sh
# Add /Forge/bin to PATH
ENV PATH="/Forge/bin:${PATH}"

# Remove UID 1000 and GID 1000 users/groups that might conflict with Forge user
RUN (if getent passwd 1000; then getent passwd 1000 | cut -d: -f1 | xargs -r userdel; fi) && \
    (if getent group 1000; then getent group 1000 | cut -d: -f1 | xargs -r groupdel; fi)

# Create Forge group and user
RUN groupadd -g 1000 Forge && \
    useradd -u 1000 -g 1000 -m -s /bin/bash Forge && \
    usermod -aG Forge Forge && \
    # Set empty password for Forge user to allow passwordless su
    passwd -d Forge && \
    # Set empty password for root user as well to ensure su works in both directions
    passwd -d root && \
    # Ensure root can su to Forge without password by configuring PAM
    sed -i '/pam_rootok.so/d' /etc/pam.d/su && \
    sed -i '1i auth sufficient pam_rootok.so' /etc/pam.d/su

# Create necessary directories
RUN mkdir -p /Forge && \
    mkdir -p /Forge/logs && \
    mkdir -p /Forge/poetry && \
    chown -R Forge:Forge /Forge


# ================================================================
# Define Docker installation macro


# Install Docker only if not a swebench or mswebench image


# Install Docker following official documentation
# https://docs.docker.com/engine/install/ubuntu/
# https://docs.docker.com/engine/install/debian/
RUN \
    # Determine OS type and install accordingly
    if [[ "nikolaik/python-nodejs:python3.12-nodejs22" == *"ubuntu"* ]]; then \
        # Handle Ubuntu (following https://docs.docker.com/engine/install/ubuntu/)
        # Add Docker's official GPG key
        apt-get update && \
        apt-get install -y ca-certificates curl && \
        install -m 0755 -d /etc/apt/keyrings && \
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && \
        chmod a+r /etc/apt/keyrings/docker.asc && \
        # Add the repository to Apt sources
        # For Ubuntu 24.04 (noble), use jammy repository as noble isn't supported yet
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null; \
    else \
        # Handle Debian (following https://docs.docker.com/engine/install/debian/)
        # Add Docker's official GPG key
        apt-get update && \
        apt-get install -y ca-certificates curl && \
        install -m 0755 -d /etc/apt/keyrings && \
        curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
        chmod a+r /etc/apt/keyrings/docker.asc && \
        # Add the repository to Apt sources (default to bookworm for stability)
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null; \
    fi && \
    # Install Docker Engine, containerd, and Docker Compose
    apt-get update && \
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure Docker daemon with MTU 1450 to prevent packet fragmentation issues
RUN mkdir -p /etc/docker && \
    echo '{"mtu": 1450}' > /etc/docker/daemon.json


# ================================================================



# Install micromamba
RUN mkdir -p /Forge/micromamba/bin && \
    /bin/bash -c "PREFIX_LOCATION=/Forge/micromamba BIN_FOLDER=/Forge/micromamba/bin INIT_YES=no CONDA_FORGE_YES=yes $(curl -L https://micro.mamba.pm/install.sh)" && \
    /Forge/micromamba/bin/micromamba config remove channels defaults && \
    /Forge/micromamba/bin/micromamba config list && \
    chown -R Forge:Forge /Forge/micromamba && \
    # Create read-only shared access to micromamba for all users
    # This allows both root and Forge users to access the same packages
    # while maintaining security by keeping Forge as the owner
    chmod -R 755 /Forge/micromamba && \
    # Create a separate writable location for root's micromamba cache/config
    mkdir -p /root/.local/share/micromamba && \
    # Set up environment variables for system-wide access
    echo 'export PATH="/Forge/micromamba/bin:$PATH"' >> /etc/environment

# Create the Forge virtual environment and install poetry and python
RUN /Forge/micromamba/bin/micromamba create -n forge -y && \
    /Forge/micromamba/bin/micromamba install -n forge -c conda-forge poetry python=3.12 -y

# Create a clean Forge directory including only the pyproject.toml, poetry.lock and Forge/__init__.py
RUN \
    if [ -d /Forge/code ]; then rm -rf /Forge/code; fi && \
    mkdir -p /Forge/code/forge && \
    touch /Forge/code/forge/__init__.py && \
    chown -R Forge:Forge /Forge/code && \
    # Set global git configuration to ensure proper author/committer information
    git config --global user.name "Forge" && \
    git config --global user.email "Forge@all-hands.dev"

COPY --chown=Forge:Forge ./pyproject.toml ./poetry.lock /Forge/code/
COPY --chown=Forge:Forge ./README.md /Forge/code/README.md
COPY --chown=Forge:Forge ./build_vscode.py /Forge/code/build_vscode.py
COPY --chown=Forge:Forge ./forge /Forge/code/forge
COPY --chown=Forge:Forge ./microagents /Forge/code/microagents
RUN chmod a+rwx /Forge/code/forge/__init__.py && \
    chown -R Forge:Forge /Forge/code


# Install user-level dependencies as Forge user
WORKDIR /Forge/code

USER Forge
ENV SKIP_VSCODE_BUILD=1
RUN \
    /Forge/micromamba/bin/micromamba config set changeps1 False && \
    /Forge/micromamba/bin/micromamba run -n forge poetry config virtualenvs.path /Forge/poetry && \
    /Forge/micromamba/bin/micromamba run -n forge poetry env use python3.12 && \
    # Install project dependencies (including forge package)
    /Forge/micromamba/bin/micromamba run -n forge poetry install --no-interaction --no-ansi && \
    # Clean up user caches
    /Forge/micromamba/bin/micromamba run -n forge poetry cache clear --all . -n && \
    /Forge/micromamba/bin/micromamba clean --all



# Install system-level dependencies that require root
USER root
RUN \
    # Install system dependencies for Playwright (requires root)
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxrandr2 libgbm1 libxss1 \
        libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 libenchant-2-2 libsecret-1-0 \
        libhyphen0 libmanette-0.2-0 libflite1 libgles2 libegl1 libnotify4 \
        libxslt1.1 libevent-2.1-7t64 libopus0 libwoff1 libharfbuzz-icu0 libwebpdemux2 \
        libvpx9 libwebp7 libcups2 xvfb fonts-unifont fonts-liberation fonts-noto-color-emoji && \
    # Install libasound2 - try new package name first (Ubuntu 24.04+/Debian Trixie+), fallback to old name
    (apt-get install -y --no-install-recommends libasound2t64 || apt-get install -y --no-install-recommends libasound2) && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # Install Playwright browsers in shared location accessible to all users
    export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers && \
    mkdir -p /opt/playwright-browsers && \
    /Forge/micromamba/bin/micromamba run -n forge poetry run playwright install chromium && \
    # Set proper permissions for shared access
    chmod -R 755 /opt/playwright-browsers && \
    # Create cache directories and symlinks for both users
    mkdir -p /home/Forge/.cache && \
    mkdir -p /root/.cache && \
    ln -sf /opt/playwright-browsers /home/Forge/.cache/ms-playwright && \
    ln -sf /opt/playwright-browsers /root/.cache/ms-playwright && \
    chown -h Forge:Forge /home/Forge/.cache/ms-playwright && \
    # Set environment variable for all users
    echo 'export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers' >> /etc/environment && \
    # Set environment variables (requires root)
    /Forge/micromamba/bin/micromamba run -n forge poetry run python -c "import sys; print('OH_INTERPRETER_PATH=' + sys.executable)" >> /etc/environment && \
    # Set permissions for shared read-only access
    chmod -R 755 /Forge/poetry && \
    chmod -R 755 /Forge/micromamba && \
    chown -R Forge:Forge /Forge/poetry && \
    mkdir -p /Forge/workspace && chmod -R g+rws,o+rw /Forge/workspace && \
    chown -R Forge:Forge /Forge/workspace && \
    mkdir -p /workspace && chmod -R 777 /workspace && \
    chown -R Forge:Forge /workspace && \
    chown -R Forge:Forge /Forge/micromamba && \
    # Ensure PATH includes system binaries early in startup
    echo 'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"' >> /etc/environment && \
    echo 'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"' >> /etc/bash.bashrc && \
    # Set up conda environment activation for all users
    echo 'eval "$(/Forge/micromamba/bin/micromamba shell hook --shell bash)"' >> /etc/bash.bashrc && \
    echo 'micromamba activate forge 2>/dev/null || true' >> /etc/bash.bashrc && \
    # Set up environment for root user
    echo 'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/Forge/micromamba/bin:$PATH"' >> /root/.bashrc && \
    echo 'export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers' >> /root/.bashrc && \
    echo 'eval "$(/Forge/micromamba/bin/micromamba shell hook --shell bash)"' >> /root/.bashrc && \
    echo 'micromamba activate forge 2>/dev/null || true' >> /root/.bashrc && \
    # Clean up system packages (requires root)
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*



# ================================================================
# END: Build Runtime Image from Scratch
# ================================================================


# Ensure Forge user/group and base dirs exist even when not building from scratch
USER root
RUN \
    # Ensure group exists (prefer GID 1000 if available)
    if ! getent group Forge >/dev/null 2>&1; then \
        if getent group 1000 >/dev/null 2>&1; then groupadd Forge; else groupadd -g 1000 Forge; fi; \
    fi && \
    # Ensure user exists (prefer UID 1000 if available)
    if ! id -u Forge >/dev/null 2>&1; then \
        if getent passwd 1000 >/dev/null 2>&1; then useradd -m -s /bin/bash -g Forge Forge; else useradd -u 1000 -g Forge -m -s /bin/bash Forge; fi; \
    fi && \
    # Ensure home and required directories exist before later steps
    mkdir -p /home/Forge && \
    mkdir -p /Forge && \
    mkdir -p $(dirname ${OPENVSCODE_SERVER_ROOT}) && \
    # Ensure ownership is correct for all Forge paths
    chown -R Forge:Forge /home/Forge || true && \
    chown -R Forge:Forge /Forge || true


# Reference:
# 1. https://github.com/gitpod-io/openvscode-server
# 2. https://github.com/gitpod-io/openvscode-releases

# Setup VSCode Server
ARG RELEASE_TAG="openvscode-server-v1.98.2"
ARG RELEASE_ORG="gitpod-io"
# ARG USERNAME=openvscode-server
# ARG USER_UID=1000
# ARG USER_GID=1000

RUN if [ -z "${RELEASE_TAG}" ]; then \
        echo "The RELEASE_TAG build arg must be set." >&2 && \
        exit 1; \
    fi && \
    arch=$(uname -m) && \
    if [ "${arch}" = "x86_64" ]; then \
        arch="x64"; \
    elif [ "${arch}" = "aarch64" ]; then \
        arch="arm64"; \
    elif [ "${arch}" = "armv7l" ]; then \
        arch="armhf"; \
    fi && \
    wget https://github.com/${RELEASE_ORG}/openvscode-server/releases/download/${RELEASE_TAG}/${RELEASE_TAG}-linux-${arch}.tar.gz && \
    tar -xzf ${RELEASE_TAG}-linux-${arch}.tar.gz && \
    if [ -d "${OPENVSCODE_SERVER_ROOT}" ]; then rm -rf "${OPENVSCODE_SERVER_ROOT}"; fi && \
    mv ${RELEASE_TAG}-linux-${arch} ${OPENVSCODE_SERVER_ROOT} && \
    cp ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/openvscode-server ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/code && \
    rm -f ${RELEASE_TAG}-linux-${arch}.tar.gz && \
    chown -R Forge:Forge ${OPENVSCODE_SERVER_ROOT}





# Set up environment for Forge user
USER root
RUN \
    # Set up environment for Forge user
    echo 'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/Forge/micromamba/bin:$PATH"' >> /home/Forge/.bashrc && \
    echo 'export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers' >> /home/Forge/.bashrc && \
    echo 'eval "$(/Forge/micromamba/bin/micromamba shell hook --shell bash)"' >> /home/Forge/.bashrc && \
    echo 'micromamba activate forge 2>/dev/null || true' >> /home/Forge/.bashrc && \
    chown Forge:Forge /home/Forge/.bashrc

# Switch to non-root user for security
USER Forge

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python --version || exit 1

