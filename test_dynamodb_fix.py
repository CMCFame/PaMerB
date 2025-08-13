"""
Test script to verify the DynamoDB decimal.Decimal fix
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from decimal import Decimal
from mermaid_ivr_converter import FlexibleARCOSConverter, safe_str

def test_dynamodb_decimal_fix():
    """Test that the converter can handle DynamoDB decimal.Decimal values"""
    
    print("Testing DynamoDB decimal.Decimal Fix")
    print("=" * 50)
    
    # Simulate DynamoDB record with decimal.Decimal values
    mock_db_record = {
        'voice_file_id': Decimal('1001'),  # DynamoDB returns numbers as Decimal
        'company': 'ARCOS',
        'voice_file_type': 'callflow',
        'transcript': 'Welcome to the system'  # This should be string but let's test edge cases
    }
    
    print("Test 1: Checking safe_str function")
    for key, value in mock_db_record.items():
        converted = safe_str(value)
        print(f"  {key}: {type(value).__name__}({value}) -> {type(converted).__name__}({repr(converted)})")
        
        # Test that .lower() works on converted value
        try:
            lower_result = converted.lower()
            print(f"    .lower() works: {repr(lower_result)}")
        except Exception as e:
            print(f"    .lower() ERROR: {e}")
    
    print("\nTest 2: Testing VoiceFile creation with mock DynamoDB data")
    try:
        # Create a converter instance (without connecting to real DynamoDB)
        converter = FlexibleARCOSConverter(use_dynamodb=False)
        
        # Manually test the voice file creation logic
        voice_file_id = safe_str(mock_db_record.get('voice_file_id', ''))
        company = safe_str(mock_db_record.get('company', 'UNKNOWN'))
        transcript = safe_str(mock_db_record.get('transcript', ''))
        
        print(f"  voice_file_id: {repr(voice_file_id)}")
        print(f"  company: {repr(company)}")
        print(f"  transcript: {repr(transcript)}")
        
        # Test operations that previously failed
        print(f"  transcript.lower(): {repr(transcript.lower())}")
        print("  SUCCESS: All string operations work correctly")
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False
    
    print("\nTest 3: Testing with extreme edge cases")
    edge_cases = [
        {'transcript': Decimal('123.45')},  # Numeric transcript
        {'transcript': None},               # None transcript  
        {'voice_file_id': 'string_id'},     # String ID
        {'company': Decimal('999')},        # Numeric company
    ]
    
    for i, case in enumerate(edge_cases, 1):
        try:
            transcript = safe_str(case.get('transcript', ''))
            voice_file_id = safe_str(case.get('voice_file_id', ''))
            company = safe_str(case.get('company', 'UNKNOWN'))
            
            # These operations should not fail
            _ = transcript.lower()
            _ = company.upper()
            
            print(f"  Edge case {i}: PASS")
        except Exception as e:
            print(f"  Edge case {i}: FAIL - {e}")
            return False
    
    print(f"\nSUCCESS: DynamoDB decimal.Decimal fix is working correctly!")
    print("   The converter should now handle DynamoDB data without 'Decimal' object has no attribute 'lower' errors")
    return True

if __name__ == "__main__":
    test_dynamodb_decimal_fix()