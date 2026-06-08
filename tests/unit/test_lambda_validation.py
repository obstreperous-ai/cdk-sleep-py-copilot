"""
Unit tests for Lambda function input validation logic.

These tests verify that the Lambda handler correctly validates input
and returns appropriate error responses for invalid inputs.
"""

import json
import pytest
from unittest.mock import MagicMock

# Import the Lambda handler
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda'))

from audio_processor import handler


class TestLambdaValidation:
    """Tests for Lambda input validation"""

    def test_handler_validates_missing_detail_field(self):
        """Test that handler rejects events without 'detail' field"""
        event = {}
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        result = handler(event, context)
        
        assert result['status'] == 'error'
        assert 'validation' in result['message'].lower() or 'detail' in result['message'].lower()

    def test_handler_validates_missing_bucket_name(self):
        """Test that handler rejects events without bucket name"""
        event = {
            'detail': {
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        result = handler(event, context)
        
        assert result['status'] == 'error'
        assert 'bucket' in result['message'].lower()

    def test_handler_validates_missing_object_key(self):
        """Test that handler rejects events without object key"""
        event = {
            'detail': {
                'bucket': {'name': 'test-bucket'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        result = handler(event, context)
        
        assert result['status'] == 'error'
        assert 'key' in result['message'].lower()

    def test_handler_validates_unsupported_file_extension(self):
        """Test that handler rejects unsupported file extensions"""
        unsupported_extensions = ['.txt', '.exe', '.zip', '.pdf', '.jpg']
        
        for ext in unsupported_extensions:
            event = {
                'detail': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': f'test{ext}'}
                }
            }
            context = MagicMock()
            context.function_name = "test-function"
            context.request_id = "test-request-id"
            
            result = handler(event, context)
            
            assert result['status'] == 'error', f"Expected error for extension {ext}"
            assert 'format' in result['message'].lower() or 'extension' in result['message'].lower()

    def test_handler_accepts_supported_audio_extensions(self):
        """Test that handler accepts supported audio file extensions"""
        supported_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
        
        for ext in supported_extensions:
            event = {
                'detail': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': f'test{ext}'}
                }
            }
            context = MagicMock()
            context.function_name = "test-function"
            context.request_id = "test-request-id"
            
            result = handler(event, context)
            
            assert result['status'] == 'success', f"Expected success for extension {ext}"

    def test_handler_validates_empty_bucket_name(self):
        """Test that handler rejects empty bucket names"""
        event = {
            'detail': {
                'bucket': {'name': ''},
                'object': {'key': 'test.mp3'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        result = handler(event, context)
        
        assert result['status'] == 'error'
        assert 'bucket' in result['message'].lower()

    def test_handler_validates_empty_object_key(self):
        """Test that handler rejects empty object keys"""
        event = {
            'detail': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': ''}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        result = handler(event, context)
        
        assert result['status'] == 'error'
        assert 'key' in result['message'].lower()

    def test_handler_returns_validation_error_type(self):
        """Test that handler returns appropriate error type for validation failures"""
        event = {
            'detail': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'test.txt'}
            }
        }
        context = MagicMock()
        context.function_name = "test-function"
        context.request_id = "test-request-id"
        
        result = handler(event, context)
        
        assert result['status'] == 'error'
        assert 'errorType' in result
        assert result['errorType'] == 'ValidationError'
