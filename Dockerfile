# Use AWS Lambda base image for Python
FROM public.ecr.aws/lambda/python:3.9

# Install AWS CLI, kubectl, and necessary packages
RUN yum install -y \
        unzip \
        curl \
        tar \
        gzip \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm -rf awscliv2.zip aws kubectl

# Set environment variables for AWS CLI and EKS
ENV PATH="/usr/local/bin:/root/.local/bin:$PATH"

# Copy the function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (file.function)
CMD ["app.lambda_handler"]
