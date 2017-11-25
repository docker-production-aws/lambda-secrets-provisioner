import sys, os
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor')
sys.path.append(vendor_dir)

import logging, datetime, json, uuid, random, string, base64
import boto3
from cfn_lambda_handler import Handler
from voluptuous import Required, All, Schema, Invalid, MultipleInvalid

# Configure logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(os.environ.get('LOG_LEVEL','INFO'))
def format_json(data):
  return json.dumps(data, default=lambda d: d.isoformat() if isinstance(d, datetime.datetime) else str(d))

# Lambda handler 
handler = Handler(secure_attributes=['Value'])

# Boto3 clients
kms = boto3.client('kms')
ssm = boto3.client('ssm')

# Validate input
def get_validator():
  return Schema({
    Required('Name'): All(basestring),
    Required('Key'): All(basestring),
    Required('Value', default=None): All(basestring),
    Required('KmsKeyId'): All(basestring)
  }, extra=True)

def validate(data):
  request_validator = get_validator()
  return request_validator(data)

# Random password generator
LENGTH = 13
CHARS = string.ascii_letters + string.digits + '!#$%^*()'
def generate_password(length, chars):
  rnd = random.SystemRandom()
  return ''.join(rnd.choice(chars) for i in range(length))

# Create/update requests
@handler.create
@handler.update
def handle_create(event, context):
  log.info("Received event: %s" % format_json(event))
  secret = validate(event['ResourceProperties'])
  # Create UUID for secret
  secret['Id'] = str(uuid.uuid4())
  if secret['Value'] is None:
    # Generate random password
    secret['Value'] = generate_password(LENGTH, CHARS)
  else:
    # Decrypt supplied secret value
    secret['Value'] = kms.decrypt(CiphertextBlob=base64.b64decode(secret['Value'])).get('Plaintext')
  # Provision secret in the form KEY=VALUE - e.g. DB_PASSWORD=abc123
  ssm.put_parameter(
    Name=secret['Name'],
    Type='SecureString',
    KeyId=secret['KmsKeyId'],
    Value='%s=%s' % (secret['Key'],secret['Value']),
    Overwrite=True
  )
  # Tag the parameter with the UUID
  ssm.add_tags_to_resource(
    ResourceType='Parameter',
    ResourceId=secret['Name'],
    Tags=[{'Key': 'Id', 'Value': secret['Id']}]
  )
  event['PhysicalResourceId'] = secret['Id']
  event['Data'] = {'Value': secret['Value']}
  return event

# Delete requests
@handler.delete
def handle_delete(event, context):
  log.info("Received delete event: %s" % format_json(event))
  secret = validate(event['ResourceProperties'])
  # Delete parameter if it exists and is tagged with an Id that matches the physical resource Id
  if (not [invalid for invalid in ssm.get_parameters(Names=[secret['Name']])['InvalidParameters']] and
      next((
        tag for tag in ssm.list_tags_for_resource(ResourceType='Parameter',ResourceId=secret['Name'])['TagList']
        if tag.get('Key') == 'Id' and tag.get('Value') == event['PhysicalResourceId']
    ), None)):
    ssm.delete_parameter(Name=secret['Name'])
  return event