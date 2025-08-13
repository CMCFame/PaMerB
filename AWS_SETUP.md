# AWS DynamoDB Setup for PaMerB

## Overview

PaMerB now integrates with AWS DynamoDB to access the voice file database created by Andres. The application automatically falls back to a built-in ARCOS database if DynamoDB is unavailable.

## Database Information

- **Table Name**: `callflow-generator-ia-db`
- **Region**: `us-east-2` (Ohio)
- **Records**: 35,200+ voice files
- **Structure**: Contains company, voice_file_type, voice_file_id, and transcript fields

## AWS Credentials Configuration

### Option 1: Environment Variables (Recommended for Production)

```bash
# Set these environment variables
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-2
```

On Windows:
```cmd
set AWS_ACCESS_KEY_ID=your_access_key_here
set AWS_SECRET_ACCESS_KEY=your_secret_key_here
set AWS_DEFAULT_REGION=us-east-2
```

### Option 2: AWS Credentials File

Create `~/.aws/credentials` (Linux/Mac) or `C:\Users\{username}\.aws\credentials` (Windows):

```ini
[default]
aws_access_key_id = your_access_key_here
aws_secret_access_key = your_secret_key_here
region = us-east-2
```

### Option 3: IAM Role (For EC2/ECS Deployment)

If running on AWS infrastructure, assign an IAM role with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:us-east-2:*:table/callflow-generator-ia-db"
    }
  ]
}
```

## Testing the Connection

Run the test script to verify your connection:

```bash
python test_dynamodb_simple.py
```

Expected output when working:
```
SUCCESS: Database connection successful!
   Table: callflow-generator-ia-db
   Region: us-east-2
   Records: 35200
   Size: X.X MB
```

## Fallback Behavior

If DynamoDB is unavailable, the application will:
1. Log a warning about the connection failure
2. Automatically use the built-in ARCOS voice database
3. Continue generating IVR code with fallback voice files
4. Display fallback status in the UI

## Troubleshooting

### Common Issues

1. **"AWS credentials not found"**
   - Solution: Configure credentials using one of the methods above

2. **"ResourceNotFoundException"**
   - Check that the table name `callflow-generator-ia-db` exists in `us-east-2`
   - Verify your AWS account has access to the table

3. **"Access Denied"**
   - Ensure your AWS credentials have the required DynamoDB permissions
   - Check IAM policies for the user/role

4. **Connection timeout**
   - Verify network connectivity to AWS
   - Check if running behind a corporate firewall

### Logs

The application logs database connection status. Check console output for detailed error messages.

## Production Deployment

For production deployment:

1. Use IAM roles instead of access keys when possible
2. Set up proper VPC and security groups if running on EC2
3. Consider using AWS Systems Manager Parameter Store for credential management
4. Monitor DynamoDB usage and costs
5. Set up CloudWatch alarms for connection failures

## Development vs Production

- **Development**: The fallback system allows development without AWS credentials
- **Production**: Configure proper AWS credentials for real-time voice file access

## Voice Database Updates

The database is automatically updated via the Lambda function when Excel files are uploaded to the S3 bucket `callflow-generator-ia` in the `db-migration/` folder.