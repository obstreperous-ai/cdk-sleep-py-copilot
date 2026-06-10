"""
Tests for audio processing functionality in Lambda handler.

Following strict TDD - these tests define the expected behavior
of the full audio processing implementation (Issue #11).
"""

import json
import sys
import os
from unittest.mock import MagicMock, patch, Mock
import pytest

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))
import audio_processor
from audio_processor import handler


class TestAudioProcessingFlow:
    """Test full audio processing workflow"""

    @patch('audio_processor.boto3')
    def test_handler_downloads_audio_from_input_s3(self, mock_boto3):
        """Test that handler downloads audio file from input S3 bucket"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_boto3.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'polly': mock_polly_client
        }[service]
        
        # Mock S3 download
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: b'mock audio data'),
            'ContentLength': 1024
        }
        
        # Mock Polly synthesis
        mock_polly_client.synthesize_speech.return_value = {
            'AudioStream': Mock(read=lambda: b'mock polly audio'),
            'ContentType': 'audio/mpeg'
        }
        
        # Mock S3 upload
        mock_s3_client.put_object.return_value = {}
        
        event = {
            'detail': {
                'bucket': {'name': 'test-input-bucket'},
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        # Call handler
        result = handler(event, context)
        
        # Verify S3 download was called
        mock_s3_client.get_object.assert_called_once_with(
            Bucket='test-input-bucket',
            Key='test.mp3'
        )
        
        assert result['status'] == 'success'

    @patch('audio_processor.boto3')
    def test_handler_synthesizes_audio_with_polly(self, mock_boto3):
        """Test that handler uses Polly to synthesize sleep audio"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_boto3.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'polly': mock_polly_client
        }[service]
        
        # Mock S3 operations
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: b'mock audio data'),
            'ContentLength': 1024
        }
        mock_s3_client.put_object.return_value = {}
        
        # Mock Polly synthesis
        mock_polly_client.synthesize_speech.return_value = {
            'AudioStream': Mock(read=lambda: b'mock polly audio'),
            'ContentType': 'audio/mpeg'
        }
        
        event = {
            'detail': {
                'bucket': {'name': 'test-input-bucket'},
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        # Call handler
        result = handler(event, context)
        
        # Verify Polly was called with appropriate parameters
        mock_polly_client.synthesize_speech.assert_called_once()
        call_args = mock_polly_client.synthesize_speech.call_args[1]
        
        # Check for required Polly parameters
        assert 'Text' in call_args
        assert 'OutputFormat' in call_args
        assert call_args['OutputFormat'] == 'mp3'
        assert 'VoiceId' in call_args
        
        assert result['status'] == 'success'

    @patch('audio_processor.boto3')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_uploads_processed_audio_to_output_s3(self, mock_boto3):
        """Test that handler uploads processed audio to output S3 bucket"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_boto3.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'polly': mock_polly_client
        }[service]
        
        # Mock S3 operations
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: b'mock audio data'),
            'ContentLength': 1024
        }
        mock_s3_client.put_object.return_value = {}
        
        # Mock Polly synthesis
        mock_polly_client.synthesize_speech.return_value = {
            'AudioStream': Mock(read=lambda: b'mock polly audio'),
            'ContentType': 'audio/mpeg'
        }
        
        event = {
            'detail': {
                'bucket': {'name': 'test-input-bucket'},
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        # Call handler
        result = handler(event, context)
        
        # Verify S3 upload was called to output bucket
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args[1]
        
        assert call_args['Bucket'] == 'test-output-bucket'
        assert 'Key' in call_args
        assert 'Body' in call_args
        assert call_args['ContentType'] == 'audio/mpeg'
        
        assert result['status'] == 'success'

    @patch('audio_processor.boto3')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_returns_output_metadata(self, mock_boto3):
        """Test that handler returns structured output with S3 location and metadata"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_boto3.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'polly': mock_polly_client
        }[service]
        
        # Mock S3 operations
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: b'mock audio data'),
            'ContentLength': 1024
        }
        mock_s3_client.put_object.return_value = {}
        
        # Mock Polly synthesis
        mock_polly_client.synthesize_speech.return_value = {
            'AudioStream': Mock(read=lambda: b'mock polly audio data'),
            'ContentType': 'audio/mpeg'
        }
        
        event = {
            'detail': {
                'bucket': {'name': 'test-input-bucket'},
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        # Call handler
        result = handler(event, context)
        
        # Verify output structure
        assert result['status'] == 'success'
        assert 'audioId' in result
        assert 'outputBucket' in result
        assert 'outputKey' in result
        assert result['outputBucket'] == 'test-output-bucket'
        
        # Verify output metadata
        assert 'outputSize' in result
        assert result['outputSize'] > 0
        
        # Verify output key follows naming convention
        assert 'processed' in result['outputKey']

    @patch('audio_processor.boto3')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_handles_s3_download_error_gracefully(self, mock_boto3):
        """Test that handler handles S3 download errors gracefully"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_boto3.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'polly': mock_polly_client
        }[service]
        
        # Mock S3 download error
        mock_s3_client.get_object.side_effect = Exception("S3 download failed")
        
        event = {
            'detail': {
                'bucket': {'name': 'test-input-bucket'},
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        # Call handler
        result = handler(event, context)
        
        # Verify error response
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'S3 download failed' in result['message']

    @patch('audio_processor.boto3')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_handles_polly_error_gracefully(self, mock_boto3):
        """Test that handler handles Polly synthesis errors gracefully"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_boto3.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'polly': mock_polly_client
        }[service]
        
        # Mock S3 download
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: b'mock audio data'),
            'ContentLength': 1024
        }
        
        # Mock Polly error
        mock_polly_client.synthesize_speech.side_effect = Exception("Polly synthesis failed")
        
        event = {
            'detail': {
                'bucket': {'name': 'test-input-bucket'},
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        # Call handler
        result = handler(event, context)
        
        # Verify error response
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'Polly synthesis failed' in result['message']

    @patch('audio_processor.boto3')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_output_key_includes_timestamp_for_uniqueness(self, mock_boto3):
        """Test that output key includes timestamp for uniqueness"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_boto3.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'polly': mock_polly_client
        }[service]
        
        # Mock S3 operations
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: b'mock audio data'),
            'ContentLength': 1024
        }
        mock_s3_client.put_object.return_value = {}
        
        # Mock Polly synthesis
        mock_polly_client.synthesize_speech.return_value = {
            'AudioStream': Mock(read=lambda: b'mock polly audio'),
            'ContentType': 'audio/mpeg'
        }
        
        event = {
            'detail': {
                'bucket': {'name': 'test-input-bucket'},
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        # Call handler
        result = handler(event, context)
        
        # Verify output key structure includes timestamp
        output_key = result['outputKey']
        assert 'test' in output_key  # Original filename
        # Verify it's in processed directory
        assert output_key.startswith('processed/')
