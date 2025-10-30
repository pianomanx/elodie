# Test for pyexiftool non-ASCII filename handling
import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import helper
from elodie.external.pyexiftool import ExifTool, fsencode

def test_fsencode_with_non_ascii_characters():
    """Test that fsencode properly handles non-ASCII characters in filenames.
    
    This test reproduces issue #379 where Elodie crashes when encountering
    files with non-ASCII characters in their paths on systems with limited
    filesystem encodings (like Windows with cp1252).
    """
    test_filename = "/tmp/test_фото_сад/тест_файл.jpg"
    
    # Test 1: Should work fine with UTF-8 encoding (current behavior on macOS/Linux)
    encoded = fsencode(test_filename)
    assert isinstance(encoded, bytes)
    assert len(encoded) > 0
    
    # Test 2: Simulate problematic encoding scenario (Windows with cp1252)
    # This simulates the conditions that cause issue #379
    with patch('sys.getfilesystemencoding', return_value='cp1252'):
        with patch('codecs.lookup_error') as mock_lookup:
            # Simulate that surrogateescape is not available (old Python versions)
            mock_lookup.side_effect = LookupError("surrogateescape not available")
            
            # Re-import to pick up the mocked encoding
            import importlib
            from elodie.external import pyexiftool
            importlib.reload(pyexiftool)
            
            # This should raise UnicodeEncodeError with the original code
            # but should work with the fix
            try:
                encoded = pyexiftool.fsencode(test_filename)
                # If we get here, the fix is working
                assert isinstance(encoded, bytes)
                assert len(encoded) > 0
                print("✓ Fix is working - non-ASCII encoding successful")
            except UnicodeEncodeError as e:
                # This is the expected failure with the original code
                pytest.fail(f"fsencode failed with non-ASCII characters: {e}")

def test_exiftool_with_non_ascii_file():
    """Test that ExifTool can process files with non-ASCII characters in paths.
    
    This is an integration test that reproduces the specific JSON parsing error
    from issue #379.
    """
    # Create a temporary file with non-ASCII characters in the path
    test_dir = "/tmp/test_фото_сад"
    test_file = os.path.join(test_dir, "тест_файл.jpg")
    
    # Get a real test image using helper function
    source_file = helper.get_file('with-album.jpg')
    
    assert source_file, "Test image file not found - helper.get_file('with-album.jpg') returned None"
    
    try:
        os.makedirs(test_dir, exist_ok=True)
        shutil.copy2(source_file, test_file)
        
        # This should not raise JSONDecodeError with the fix
        with ExifTool() as et:
            result = et.execute_json(test_file)
            assert isinstance(result, list)
            assert len(result) > 0
            assert "SourceFile" in result[0]
            
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists(test_dir):
            os.rmdir(test_dir)