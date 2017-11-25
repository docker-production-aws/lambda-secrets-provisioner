# Docker in Production using AWS CloudFormation Secrets Provisioner Custom Resource

This repository defines a CloudFormation custom resource Lamdba function called `secretsProvisioner`, which is included with the Pluralsight course [Docker in Production using Amazon Web Services](https://app.pluralsight.com/library/courses/docker-production-using-amazon-web-services/table-of-contents).

This function is a CloudFormation custom resource that securely provisions secrets into the EC2 systems manager parameter store.

## Branches

This repository contains two branches:

- [`master`](https://github.com/docker-production-aws/lambda-secrets-provisioner/tree/master) - represents the initial starting state of the repository as viewed in the course.  Specifically this is an empty repository that you are instructed to create in the module **Managing Secrets in AWS**.

- [`final`](https://github.com/docker-production-aws/lambda-secrets-provisioner/tree/final) - represents the final state of the repository after completing all configuration tasks as described in the course material.

> The `final` branch is provided as a convenience in the case you get stuck, or want to avoid manually typing out large configuration files.  In most cases however, you should attempt to configure this repository by following the course material.

To clone this repository and checkout a branch you can simply use the following commands:

```
$ git clone https://github.com/docker-production-aws/lambda-secrets-provisioner.git
...
...
$ git checkout final
Switched to branch 'final'
$ git checkout master
Switched to branch 'master'
```

## Errata

No known issues.

## Further Reading

- [Systems Manager Parameter Store Docs](http://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-paramstore.html)

## Build Instructions

To complete the build process you need the following tools installed:

- Python 2.7
- PIP package manager
- [AWS CLI](https://aws.amazon.com/cli/)

Any dependencies need to defined in `src/requirements.txt`.  Note that you do not need to include `boto3`, as this is provided by AWS for Python Lambda functions.

To build the function and its dependencies:

`make build`

This will create the necessary dependencies in the `src` folder and create a ZIP package in the `build` folder.  This file is suitable for upload to the AWS Lambda service to create a Lambda function.

```
$ make build
=> Building secretsProvisioner.zip...
Collecting cfn_lambda_handler (from -r requirements.txt (line 1))
Installing collected packages: cfn-lambda-handler
...
...
Successfully installed cfn-lambda-handler-1.0.0
updating: vendor/cfn_lambda_handler_1.0.0.dist-info/ (stored 0%)
updating: vendor/cfn_lambda_handler.py (deflated 67%)
updating: vendor/cfn_lambda_handler.pyc (deflated 62%)
updating: requirements.txt (stored 0%)
updating: setup.cfg (stored 0%)
updating: secretsProvisioner.py (deflated 63%)
=> Built build/secretsProvisioner.zip
```

### Function Naming

The default name for this function is `secretsProvisioner` and the corresponding ZIP package that is generated is called `secretsProvisioner.zip`.

If you want to change the function name, you can either update the `FUNCTION_NAME` setting in the `Makefile` or alternatively configure an environment variable of the same name to override the default function name.

## Publishing the Function

When you publish the function, you are simply copying the built ZIP package to an S3 bucket.  Before you can do this, you must ensure you have created the S3 bucket and your environment is configured correctly with appropriate AWS credentials and/or profiles.

To specify the S3 bucket that the function should be published to, you can either configure the `S3_BUCKET` setting in the `Makefile` or alternatively configure an environment variable of the same name to override the default S3 bucket name.

> [Versioning](http://docs.aws.amazon.com/AmazonS3/latest/dev/Versioning.html) should be enabled on the S3 bucket

To deploy the built ZIP package:

`make publish`

This will upload the built ZIP package to the configured S3 bucket.

> When a new or updated package is published, the S3 object version will be displayed.

### Publish Example

```
$ make publish
...
...
=> Built build/secretsProvisioner.zip
=> Publishing secretsProvisioner.zip to s3://123456789012-cfn-lambda...
=> Published to S3 URL: https://s3.amazonaws.com/123456789012-cfn-lambda/secretsProvisioner.zip
=> S3 Object Version: gyujkgVKoH.NVeeuLYTi_7n_NUburwa4
```

## CloudFormation Usage

This function is designed to be called from a CloudFormation template as a custom resource.

In general you should create a Lambda function per CloudFormation stack and then create custom resources that call the Lambda function.

### Defining the Lambda Function

The following CloudFormation template snippet demonstrates creating the Lambda function, along with supporting CloudWatch Logs and IAM role resources:

```
...
Resources:
  SecretsProvisionerLogGroup:
    Type: "AWS::Logs::LogGroup"
    DeletionPolicy: "Delete"
    Properties:
      LogGroupName:
        Fn::Sub: /aws/lambda/${AWS::StackName}-secretsProvisioner
      RetentionInDays: 30
  SecretsProvisioner:
    Type: "AWS::Lambda::Function"
    DependsOn:
      - "SecretsProvisionerLogGroup"
    Properties:
      Description: 
        Fn::Sub: "${AWS::StackName} Secrets Provisioner"
      Handler: "secrets_provisioner.handler"
      MemorySize: 128
      Runtime: "python2.7"
      Timeout: 300
      Role: 
        Fn::Sub: ${SecretsProvisionerRole.Arn}
      FunctionName: 
        Fn::Sub: "${AWS::StackName}-secretsProvisioner"
      Code:
        S3Bucket: 
          Fn::Sub: "${AWS::AccountId}-cfn-lambda"
        S3Key: "secretsProvisioner.zip"
        S3ObjectVersion: "gyujkgVKoH.NVeeuLYTi_7n_NUburwa4"
  SecretsProvisionerRole:
    Type: "AWS::IAM::Role"
    Properties:
      Path: "/"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
        - Effect: "Allow"
          Principal: {"Service": "lambda.amazonaws.com"}
          Action: [ "sts:AssumeRole" ]
      Policies:
      - PolicyName: "SecretsProvisionerPermissions"
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
          - Sid: Encrypt
            Effect: Allow
            Action:
            - kms:Decrypt
            - kms:Encrypt
            Resource:
              Fn::Sub: arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:key/1234abcd-12ab-34cd-56ef-1234567890ab
          - Sid: ProvisionSecrets
            Effect: Allow
            Action:
            - ssm:GetParameters
            - ssm:PutParameter
            - ssm:DeleteParameter
            - ssm:AddTagsToResource
            - ssm:ListTagsForResource
            Resource:
              Fn::Sub: arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/${AWS::StackName}/*
          - Sid: ManageLambdaLogs
            Effect: Allow
            Action:
            - logs:CreateLogStream
            - logs:DescribeLogStreams
            - logs:PutLogEvents
            Resource:
              Fn::Sub: ${SecretsProvisionerLogGroup.Arn}
...
...
```

### Creating Custom Resources that use the Lambda Function

The following custom resource calls the `SecretsProvisioner` Lambda function when the resource is created, updated or deleted:

```
  DatabaseSecret:
    Type: "Custom::Secret"
    Properties:
      ServiceToken:
        Fn::Sub: "${SecretsProvisioner.Arn}"
      Name:
        Fn::Sub: /${AWS::StackName}/database/password
      Key: JDBC_PASSWORD
      Value:
        Ref: DatabasePassword
      KmsKeyId:
        Fn::ImportValue: CfnMasterKey
```

The following table describes the various properties you can configure when creating a custom resource that uses this Lambda function:

| Property     | Description                                                                                                                                                                                        | Required |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| ServiceToken | The ARN of the Lambda function                                                                                                                                                                     | Yes      |
| Name         | The name of the parameter to create                                                                                                                                                                | Yes      |
| Key          | A key to store along with the plaintext version of the secret.  This is typically in the form of an environment variable, which will be stored in the format <ENVIRONMENT_VARIABLE>=<secret-value> | Yes      |
| Value        | The value of the secret.  If provided, the value must be encrypted using KMS.  If not provided, the provisioner with create a random password                                                      | No       |
| KmsKeyId     | The ID of the KMS key to use to encrypt the parameter when it is provisioned into the parameter store                                                                                              | No       |