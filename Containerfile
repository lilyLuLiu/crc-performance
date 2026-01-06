FROM registry.access.redhat.com/ubi9/ubi-minimal

LABEL org.opencontainers.image.authors="CodeReady Containers <devtools-cdk@redhat.com>"

RUN microdnf install -y openssh-clients sshpass zip bash jq findutils python3 pip tar \
    && pip install --no-cache-dir requests opensearch-py pandas matplotlib jinja2\
    && microdnf clean all

COPY . /opt/


