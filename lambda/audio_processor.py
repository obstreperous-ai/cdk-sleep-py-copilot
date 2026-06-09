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
- Structured JSON logging with request context

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
from datetime import datetime, timezone

# Configure structured JSON logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Supported audio file extensions
SUPPORTED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}


def log_structured(level: str, message: str, context: Dict[str, Any] = None):
    """
    Log a structured JSON message with context.
    
    Args:
        level: Log level (INFO, ERROR, WARN, DEBUG)
        message: Log message
        context: Additional context fields
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
    }
    
    if context:
        log_entry.update(context)
    
    # Log as JSON string
    log_message = json.dumps(log_entry)
    
    if level == "ERROR":
        logger.error(log_message)
    elif level == "WARN":
        logger.warning(log_message)
    elif level == "DEBUG":
        logger.debug(log_message)
    else:
        logger.info(log_message)


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
    # Extract request context
    request_id = context.request_id
    function_name = context.function_name
    
    # Log the incoming event with structured logging
    log_structured(
        "INFO",
        "Received audio processing request",
        {
            "request_id": request_id,
            "function_name": function_name,
            "event": event
        }
    )
    
    # Extract table name from environment (for future DynamoDB operations)
    metadata_table_name = os.environ.get('METADATA_TABLE_NAME', 'unknown')
    
    log_structured(
        "INFO",
        "Environment configuration loaded",
        {
            "request_id": request_id,
            "metadata_table": metadata_table_name
        }
    )
    
    try:
        # Validate input and extract S3 details
        bucket_name, object_key = validate_input(event)
        
        log_structured(
            "INFO",
            "Input validation passed",
            {
                "request_id": request_id,
                "bucket": bucket_name,
                "key": object_key,
                "status": "validation_success"
            }
        )
        
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
            'processorFunction': function_name,
            'requestId': request_id
        }
        
        log_structured(
            "INFO",
            "Processing completed successfully",
            {
                "request_id": request_id,
                "audio_id": object_key,
                "status": "success",
                "result": result
            }
        )
        
        return result
        
    except ValidationError as e:
        # Handle validation errors specifically
        error_message = f"Validation error: {str(e)}"
        
        log_structured(
            "ERROR",
            error_message,
            {
                "request_id": request_id,
                "error_type": "ValidationError",
                "status": "validation_failed"
            }
        )
        
        return {
            'status': 'error',
            'message': error_message,
            'errorType': 'ValidationError'
        }
        
    except Exception as e:
        # Log the error with structured logging
        error_message = f"Error processing audio: {str(e)}"
        
        log_structured(
            "ERROR",
            error_message,
            {
                "request_id": request_id,
                "error_type": type(e).__name__,
                "status": "error",
                "error_details": str(e)
            }
        )
        
        # Return error details for Step Functions error handling
        return {
            'status': 'error',
            'message': error_message,
            'errorType': type(e).__name__
        }
