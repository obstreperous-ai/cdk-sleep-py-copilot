"""
Sleep Audio Processor Lambda Function

This Lambda function processes audio files through a full pipeline:
- Downloads input audio from S3
- Generates soothing sleep audio using Amazon Polly
- Uploads processed audio to output S3 bucket
- Returns metadata for DynamoDB updates

Processing workflow:
1. Validate S3 event and extract bucket/key
2. Download input audio file (validation only in current phase)
3. Synthesize sleep-inducing audio using Polly
4. Upload processed audio to output bucket
5. Return structured metadata with output location

Supports:
- Audio file format validation (mp3, wav, m4a, ogg, flac)
- Polly text-to-speech synthesis with neural voice
- S3 upload with proper content type
- Error handling with appropriate error types
- Structured JSON logging with request context
"""

import json
import logging
import os
import boto3
from typing import Any, Dict
from datetime import datetime, timezone

# Configure structured JSON logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Supported audio file extensions
SUPPORTED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}

# Soothing sleep prompt text for Polly synthesis
SLEEP_PROMPT_TEXT = """
Close your eyes and take a deep breath. 
Let your body relax as you drift into peaceful sleep. 
Feel the gentle waves of calm washing over you.
Your mind is quiet, your body is at rest.
Sleep comes naturally and easily now.
"""


def get_s3_client():
    """Get or create S3 client (lazy initialization for testing)"""
    return boto3.client('s3')


def get_polly_client():
    """Get or create Polly client (lazy initialization for testing)"""
    return boto3.client('polly')


def generate_output_key(input_key: str) -> str:
    """
    Generate output S3 key with timestamp for uniqueness.
    
    Args:
        input_key: Original input S3 key
        
    Returns:
        Output key in format: processed/{original_name}_{timestamp}.mp3
    """
    # Extract base filename without extension
    base_name = os.path.splitext(os.path.basename(input_key))[0]
    
    # Add timestamp for uniqueness
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    # Return structured output key
    return f"processed/{base_name}_{timestamp}.mp3"


def download_from_s3(bucket: str, key: str) -> bytes:
    """
    Download file from S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        File content as bytes
        
    Raises:
        Exception: If S3 download fails
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        raise Exception(f"S3 download failed: {str(e)}")


def synthesize_sleep_audio() -> bytes:
    """
    Synthesize sleep-inducing audio using Amazon Polly.
    
    Returns:
        Audio content as bytes (MP3 format)
        
    Raises:
        Exception: If Polly synthesis fails
    """
    try:
        polly_client = get_polly_client()
        response = polly_client.synthesize_speech(
            Text=SLEEP_PROMPT_TEXT,
            OutputFormat='mp3',
            VoiceId='Joanna',  # Soothing female voice
            Engine='neural'     # Neural engine for more natural speech
        )
        return response['AudioStream'].read()
    except Exception as e:
        raise Exception(f"Polly synthesis failed: {str(e)}")


def upload_to_s3(bucket: str, key: str, content: bytes) -> int:
    """
    Upload file to S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        content: File content as bytes
        
    Returns:
        Size of uploaded content in bytes
        
    Raises:
        Exception: If S3 upload fails
    """
    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType='audio/mpeg'
        )
        return len(content)
    except Exception as e:
        raise Exception(f"S3 upload failed: {str(e)}")


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
    
    # Extract environment variables
    metadata_table_name = os.environ.get('METADATA_TABLE_NAME', 'unknown')
    output_bucket_name = os.environ.get('OUTPUT_BUCKET_NAME', '')
    
    log_structured(
        "INFO",
        "Environment configuration loaded",
        {
            "request_id": request_id,
            "metadata_table": metadata_table_name,
            "output_bucket": output_bucket_name
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
        
        # Step 1: Download input audio from S3 (for validation)
        log_structured(
            "INFO",
            "Downloading input audio from S3",
            {
                "request_id": request_id,
                "bucket": bucket_name,
                "key": object_key
            }
        )
        input_audio = download_from_s3(bucket_name, object_key)
        
        log_structured(
            "INFO",
            "Input audio downloaded successfully",
            {
                "request_id": request_id,
                "size_bytes": len(input_audio)
            }
        )
        
        # Step 2: Synthesize sleep audio using Polly
        log_structured(
            "INFO",
            "Synthesizing sleep audio with Polly",
            {
                "request_id": request_id
            }
        )
        processed_audio = synthesize_sleep_audio()
        
        log_structured(
            "INFO",
            "Polly synthesis completed",
            {
                "request_id": request_id,
                "output_size_bytes": len(processed_audio)
            }
        )
        
        # Step 3: Generate output key and upload to output bucket
        output_key = generate_output_key(object_key)
        
        log_structured(
            "INFO",
            "Uploading processed audio to output bucket",
            {
                "request_id": request_id,
                "output_bucket": output_bucket_name,
                "output_key": output_key
            }
        )
        
        output_size = upload_to_s3(output_bucket_name, output_key, processed_audio)
        
        log_structured(
            "INFO",
            "Processed audio uploaded successfully",
            {
                "request_id": request_id,
                "output_size": output_size
            }
        )
        
        # Return success with output metadata
        result = {
            'status': 'success',
            'message': 'Audio processing completed successfully',
            'audioId': object_key,
            'bucket': bucket_name,
            'outputBucket': output_bucket_name,
            'outputKey': output_key,
            'outputSize': output_size,
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
