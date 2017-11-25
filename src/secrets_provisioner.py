import sys, os
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor')
sys.path.append(vendor_dir)

import logging, datetime, json
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
handler = Handler()

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

# Create requests
@handler.create
def handle_create(event, context):
  log.info("Received create event: %s" % format_json(event))
  secret = validate(event['ResourceProperties'])
  return event

# Update requests
@handler.update
def handle_update(event, context):
  log.info("Received update event: %s" % format_json(event))
  return event

# Delete requests
@handler.delete
def handle_delete(event, context):
  log.info("Received delete event: %s" % format_json(event))
  return event

