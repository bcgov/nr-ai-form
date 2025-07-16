FROM mcr.microsoft.com/devcontainers/typescript-node:1-20-bullseye

# Install additional packages
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        curl \
        wget \
        unzip \
        git \
        jq \
        vim \
        gpg \
        lsb-release \
    && apt-get autoremove -y && apt-get clean -y

# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Install Terraform
RUN wget -O- https://apt.releases.hashicorp.com/gpg | \
    gpg --dearmor | \
    tee /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
    https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
    tee /etc/apt/sources.list.d/hashicorp.list && \
    apt update && \
    apt-get install -y terraform

# Install Azure Functions Core Tools
RUN npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Install additional npm packages globally
RUN npm install -g typescript ts-node nodemon

# Set the default user
USER node

# Set up shell for the node user
RUN echo 'alias ll="ls -la"' >> /home/node/.bashrc \
    && echo 'alias tf="terraform"' >> /home/node/.bashrc \
    && echo 'alias tfi="terraform init"' >> /home/node/.bashrc \
    && echo 'alias tfp="terraform plan"' >> /home/node/.bashrc \
    && echo 'alias tfa="terraform apply"' >> /home/node/.bashrc

# Create workspace directory
RUN mkdir -p /workspaces
WORKDIR /workspaces
