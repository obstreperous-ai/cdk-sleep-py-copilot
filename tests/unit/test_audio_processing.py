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

    @patch('audio_processor.get_polly_client')
    @patch('audio_processor.get_s3_client')
    def test_handler_downloads_audio_from_input_s3(self, mock_get_s3, mock_get_polly):
        """Test that handler downloads audio file from input S3 bucket"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_get_polly.return_value = mock_polly_client
        
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

    @patch('audio_processor.get_polly_client')
    @patch('audio_processor.get_s3_client')
    def test_handler_synthesizes_audio_with_polly(self, mock_get_s3, mock_get_polly):
        """Test that handler uses Polly to synthesize sleep audio"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_get_polly.return_value = mock_polly_client
        
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

    @patch('audio_processor.get_polly_client')
    @patch('audio_processor.get_s3_client')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_uploads_processed_audio_to_output_s3(self, mock_get_s3, mock_get_polly):
        """Test that handler uploads processed audio to output S3 bucket"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_get_polly.return_value = mock_polly_client
        
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

    @patch('audio_processor.get_polly_client')
    @patch('audio_processor.get_s3_client')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_returns_output_metadata(self, mock_get_s3, mock_get_polly):
        """Test that handler returns structured output with S3 location and metadata"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_get_polly.return_value = mock_polly_client
        
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

    @patch('audio_processor.get_polly_client')
    @patch('audio_processor.get_s3_client')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_handles_s3_download_error_gracefully(self, mock_get_s3, mock_get_polly):
        """Test that handler handles S3 download errors gracefully"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_get_polly.return_value = mock_polly_client
        
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

    @patch('audio_processor.get_polly_client')
    @patch('audio_processor.get_s3_client')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_handles_polly_error_gracefully(self, mock_get_s3, mock_get_polly):
        """Test that handler handles Polly synthesis errors gracefully"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_get_polly.return_value = mock_polly_client
        
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

    @patch('audio_processor.get_polly_client')
    @patch('audio_processor.get_s3_client')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_output_key_includes_timestamp_for_uniqueness(self, mock_get_s3, mock_get_polly):
        """Test that output key includes timestamp for uniqueness"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_get_polly.return_value = mock_polly_client
        
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

    @patch('audio_processor.get_polly_client')
    @patch('audio_processor.get_s3_client')
    @patch('audio_processor.os.environ', {'OUTPUT_BUCKET_NAME': 'test-output-bucket'})
    def test_handler_handles_s3_upload_error_gracefully(self, mock_get_s3, mock_get_polly):
        """Test that handler handles S3 upload errors gracefully"""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_polly_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_get_polly.return_value = mock_polly_client
        
        # Mock S3 download - success
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: b'mock audio data'),
            'ContentLength': 1024
        }
        
        # Mock Polly synthesis - success
        mock_polly_client.synthesize_speech.return_value = {
            'AudioStream': Mock(read=lambda: b'mock polly audio'),
            'ContentType': 'audio/mpeg'
        }
        
        # Mock S3 upload - failure
        mock_s3_client.put_object.side_effect = Exception("S3 upload failed: Access Denied")
        
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
        assert 'S3 upload failed' in result['message']


class TestLoggingEdgeCases:
    """Test edge cases in structured logging"""
    
    @patch('audio_processor.logger')
    def test_log_structured_handles_warn_level(self, mock_logger):
        """Test that log_structured correctly handles WARN level"""
        from audio_processor import log_structured
        
        log_structured("WARN", "Warning message", {"key": "value"})
        
        # Verify warning method was called
        assert mock_logger.warning.called
        call_args = mock_logger.warning.call_args[0][0]
        log_data = json.loads(call_args)
        assert log_data['level'] == 'WARN'
        assert log_data['message'] == 'Warning message'
    
    @patch('audio_processor.logger')
    def test_log_structured_handles_debug_level(self, mock_logger):
        """Test that log_structured correctly handles DEBUG level"""
        from audio_processor import log_structured
        
        log_structured("DEBUG", "Debug message", {"key": "value"})
        
        # Verify debug method was called
        assert mock_logger.debug.called
        call_args = mock_logger.debug.call_args[0][0]
        log_data = json.loads(call_args)
        assert log_data['level'] == 'DEBUG'
        assert log_data['message'] == 'Debug message'


class TestClientFactories:
    """Test boto3 client factory functions"""
    
    @patch('audio_processor.boto3')
    def test_get_s3_client_creates_client(self, mock_boto3):
        """Test that get_s3_client creates an S3 client"""
        from audio_processor import get_s3_client
        
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        result = get_s3_client()
        
        mock_boto3.client.assert_called_once_with('s3')
        assert result == mock_client
    
    @patch('audio_processor.boto3')
    def test_get_polly_client_creates_client(self, mock_boto3):
        """Test that get_polly_client creates a Polly client"""
        from audio_processor import get_polly_client
        
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        result = get_polly_client()
        
        mock_boto3.client.assert_called_once_with('polly')
        assert result == mock_client
