"""
Sleep Audio Processor Lambda Function

This Lambda function validates audio file uploads and performs basic processing.

Validation checks:
- Verifies required fields from S3 event (bucket, key)
- Checks file extension for supported audio formats
- Returns clear error paths for validation failures

Currently supports:
- Audio file format validation (mp3, wav, m4a, ogg, flac)
- Required field validation
- Error handling with appropriate error types

Future enhancements might include:
- Audio file size validation
- Duration checks
- Metadata extraction and enrichment
- S3 object tagging or categorization
"""

import json
import logging
import os
from typing import Any, Dict

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Supported audio file extensions
SUPPORTED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_input(event: Dict[str, Any]) -> tuple[str, str]:
    """
    Validate the input event and extract S3 details.
    
    Args:
        event: The event data from Step Functions state machine
        
    Returns:
        Tuple of (bucket_name, object_key)
        
    Raises:
        ValidationError: If validation fails
    """
    # Check for required 'detail' field
    if 'detail' not in event:
        raise ValidationError("Missing required 'detail' field in event")
    
    detail = event['detail']
    
    # Validate bucket name
    bucket_dict = detail.get('bucket', {})
    bucket_name = bucket_dict.get('name', '').strip()
    
    if not bucket_name:
        raise ValidationError("Missing or empty bucket name in event")
    
    # Validate object key
    object_dict = detail.get('object', {})
    object_key = object_dict.get('key', '').strip()
    
    if not object_key:
        raise ValidationError("Missing or empty object key in event")
    
    # Validate file extension
    file_extension = os.path.splitext(object_key)[1].lower()
    
    if file_extension not in SUPPORTED_AUDIO_EXTENSIONS:
        supported_formats = ', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise ValidationError(
            f"Unsupported audio format '{file_extension}'. "
            f"Supported formats: {supported_formats}"
        )
    
    return bucket_name, object_key


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler function for audio processing.
    
    Args:
        event: The event data from Step Functions state machine
               Expected to contain S3 event details and metadata
        context: Lambda context object
        
    Returns:
        Dictionary with processing results and status
    """
    # Log the incoming event for debugging
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    # Extract table name from environment (for future DynamoDB operations)
    metadata_table_name = os.environ.get('METADATA_TABLE_NAME', 'unknown')
    logger.info(f"Metadata table: {metadata_table_name}")
    
    try:
        # Validate input and extract S3 details
        bucket_name, object_key = validate_input(event)
        
        logger.info(f"Processing audio file: s3://{bucket_name}/{object_key}")
        logger.info("Input validation passed successfully")
        
        # Placeholder for future processing logic
        # This is where we would:
        # - Validate the audio file (size, duration checks)
        # - Extract metadata (duration, codec, sample rate)
        # - Update DynamoDB with enriched metadata
        # - Perform any pre-processing checks
        
        # Return success with basic info
        result = {
            'status': 'success',
            'message': 'Audio processor invoked successfully',
            'audioId': object_key,
            'bucket': bucket_name,
            'processorFunction': context.function_name,
            'requestId': context.request_id
        }
        
        logger.info(f"Processing completed successfully: {json.dumps(result)}")
        return result
        
    except ValidationError as e:
        # Handle validation errors specifically
        error_message = f"Validation error: {str(e)}"
        logger.error(error_message)
        
        return {
            'status': 'error',
            'message': error_message,
            'errorType': 'ValidationError'
        }
        
    except Exception as e:
        # Log the error and return a failure response
        error_message = f"Error processing audio: {str(e)}"
        logger.error(error_message, exc_info=True)
        
        # Return error details for Step Functions error handling
        return {
            'status': 'error',
            'message': error_message,
            'errorType': type(e).__name__
        }
