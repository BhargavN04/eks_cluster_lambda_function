
---

## 🔧 Components Overview

### 1. `app.py` – Lambda Function Logic

This is the core script executed by the AWS Lambda function.

**Key Features:**
- Retrieves all namespaces from the connected EKS cluster.
- Iterates through each pod in each namespace and fetches memory usage via `kubectl top pod`.
- Collects all data into a JSON structure and uploads it to an S3 bucket with KMS encryption.

**Important Functions:**
- `run_cmd(cmd)`: Executes shell commands with debug output and handles errors.
- `upload_json_to_s3(...)`: Uploads JSON-formatted metrics to the specified S3 bucket.
- `lambda_handler(event, context)`: The Lambda entrypoint function.

**Environment Variables:**
- `AWS_REGION`: AWS region (e.g., `us-west-1`)
- `CLUSTER_NAME`: EKS cluster name
- `S3_BUCKET_NAME`: S3 bucket to store metrics

---

### 2. `Dockerfile` – AWS Lambda Docker Image

Defines the container environment for the Lambda function.

**What It Does:**
- Uses AWS Lambda’s Python 3.9 base image.
- Installs:
  - `awscli` to manage EKS authentication
  - `kubectl` to query pod metrics
- Copies `app.py` into the container.
- Sets the Lambda entrypoint to `app.lambda_handler`.

**Note:**
Ensure the Lambda has IAM permissions for:
- `eks:DescribeCluster`
- `eks:List*`
- `cloudwatch:Get*`
- `s3:PutObject` (for the target S3 bucket)

---

### 3. `docker-image.yml` – GitHub Actions Workflow

GitHub Actions workflow to automate CI/CD of the Lambda Docker image.

**Triggers:**
- On push or pull request to the `main` branch.

**Workflow Steps:**
1. **Checkout** the source code.
2. **Configure AWS Credentials** using GitHub secrets.
3. **Authenticate to Amazon ECR**.
4. **Build Docker Image** and tag with:
   - SHA tag (`${{ github.sha }}`)
   - `latest`
5. **Push Docker Image** to Amazon ECR.

**Required Secrets in GitHub:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

**Environment Variables Used:**
- `AWS_REGION`: Region for ECR (e.g., `us-west-1`)
- `AWS_ACCOUNT_ID`: AWS Account ID
- `ECR_REPOSITORY`: ECR repo path (e.g., `test/monitering`)

---

## 🚀 Deployment & Usage

### Step 1: Build and Push Image (CI/CD)
Commit changes to the `main` branch — GitHub Actions will:
- Build the Docker image.
- Push to ECR.

### Step 2: Deploy Lambda Function
- Use the pushed image from ECR in a new or existing AWS Lambda function.
- Ensure environment variables (`AWS_REGION`, `CLUSTER_NAME`, `S3_BUCKET_NAME`) are set.
- Attach a suitable IAM role with necessary permissions.

### Step 3: Trigger Execution
You can test your Lambda function via the AWS Console or programmatically. It will:
- Connect to EKS
- Collect memory usage metrics for all pods
- Store the results in the specified S3 bucket

---

## 🛡️ Security & Compliance

- S3 uploads are encrypted using AWS KMS (`ServerSideEncryption="aws:kms"`).
- No secrets are hard-coded; AWS credentials are injected via GitHub Secrets.

---

## 📌 Requirements

- EKS cluster running and accessible by the Lambda function.
- S3 bucket already created and accessible by the Lambda role.
- Lambda execution role with:
  - `eks:DescribeCluster`, `eks:List*`
  - `s3:PutObject`
  - `cloudwatch:Get*`
- GitHub repository connected with required AWS credentials and secrets.

---

##
