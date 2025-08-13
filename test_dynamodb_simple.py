"""
Simple test script for DynamoDB integration in PaMerB IVR converter
"""

from db_connection import test_connection, get_database
from mermaid_ivr_converter import convert_mermaid_to_ivr

def test_database_connection():
    """Test the DynamoDB connection"""
    print("Testing DynamoDB connection...")
    
    connection_status = test_connection()
    print(f"Connection Status: {connection_status}")
    
    if connection_status["status"] == "connected":
        print("SUCCESS: Database connection successful!")
        print(f"   Table: {connection_status.get('table_name')}")
        print(f"   Region: {connection_status.get('region')}")
        print(f"   Records: {connection_status.get('item_count', 'N/A')}")
        print(f"   Size: {connection_status.get('table_size_mb', 'N/A')} MB")
        return True
    else:
        print("FAILED: Database connection failed!")
        print(f"   Error: {connection_status.get('error')}")
        return False

def test_voice_file_loading():
    """Test voice file loading from DynamoDB"""
    print("\nTesting voice file loading...")
    
    try:
        db = get_database()
        voice_files = db.get_all_voice_files()
        
        if voice_files:
            print(f"SUCCESS: Loaded {len(voice_files)} voice files")
            
            # Show sample records
            print("\nSample voice file records:")
            for i, record in enumerate(voice_files[:3]):
                print(f"   {i+1}. ID: {record.get('id')}")
                print(f"      Company: {record.get('company')}")
                print(f"      Voice File Type: {record.get('voice_file_type')}")
                print(f"      Voice File ID: {record.get('voice_file_id')}")
                print(f"      Transcript: {record.get('transcript', '')[:50]}...")
                print()
            
            return True
        else:
            print("FAILED: No voice files found in database")
            return False
            
    except Exception as e:
        print(f"FAILED: Error loading voice files: {e}")
        return False

def test_converter_integration():
    """Test the IVR converter with DynamoDB integration"""
    print("Testing IVR converter with DynamoDB...")
    
    # Simple test mermaid diagram
    test_mermaid = '''flowchart TD
    A["Welcome to the automated callout system"] --> B{"Press 1 if you are the employee"}
    B -->|"1"| C["Please enter your four digit PIN"]
    C --> D["You have accepted"]
    B -->|"2"| E["Good bye"]
    '''
    
    try:
        # Test with DynamoDB enabled
        print("   Testing with DynamoDB enabled...")
        ivr_flow, js_output = convert_mermaid_to_ivr(test_mermaid, use_dynamodb=True)
        
        if ivr_flow and js_output:
            print(f"SUCCESS: Conversion successful with DynamoDB!")
            print(f"   Generated {len(ivr_flow)} IVR nodes")
            print(f"   JavaScript output: {len(js_output)} characters")
            
            # Check for voice file references
            voice_refs = []
            for node in ivr_flow:
                if isinstance(node, dict) and 'playPrompt' in node:
                    voice_refs.extend(node['playPrompt'])
            
            print(f"   Voice file references found: {len(voice_refs)}")
            if voice_refs:
                print(f"   Sample references: {voice_refs[:3]}")
            
            return True
        else:
            print("FAILED: Conversion failed - no output generated")
            return False
            
    except Exception as e:
        print(f"FAILED: Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_mode():
    """Test fallback mode when DynamoDB is unavailable"""
    print("\nTesting fallback mode...")
    
    test_mermaid = '''flowchart TD
    A["Welcome"] --> B{"Press 1"}
    B -->|"1"| C["Accept"]
    '''
    
    try:
        # Test with DynamoDB disabled (fallback mode)
        print("   Testing with DynamoDB disabled (fallback mode)...")
        ivr_flow, js_output = convert_mermaid_to_ivr(test_mermaid, use_dynamodb=False)
        
        if ivr_flow and js_output:
            print(f"SUCCESS: Fallback mode working!")
            print(f"   Generated {len(ivr_flow)} IVR nodes using ARCOS fallback")
            return True
        else:
            print("FAILED: Fallback mode failed")
            return False
            
    except Exception as e:
        print(f"FAILED: Error in fallback mode: {e}")
        return False

def main():
    """Run all tests"""
    print("PaMerB DynamoDB Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Voice File Loading", test_voice_file_loading),
        ("Converter Integration", test_converter_integration),
        ("Fallback Mode", test_fallback_mode)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"CRASHED: Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! DynamoDB integration is working correctly.")
    else:
        print("Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    main()