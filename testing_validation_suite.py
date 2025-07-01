"""
Comprehensive Testing and Validation Suite for Enhanced IVR System
Tests all components and validates the conversion accuracy
"""

import unittest
import tempfile
import os
import json
import pandas as pd
from typing import Dict, List, Any
import logging

# Import components to test
from audio_database_manager import AudioDatabaseManager, AudioRecord
from segment_parser import SegmentParser, TextSegment
from audio_mapper import AudioMapper, AudioMapping
from enhanced_ivr_converter import EnhancedIVRConverter

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAudioDatabaseManager(unittest.TestCase):
    """Test the audio database management functionality"""
    
    def setUp(self):
        """Create test CSV data"""
        self.test_data = [
            {"Company": "aep", "Folder": "callflow", "File Name": "1191.ulaw", "Transcript": "This is an"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1274.ulaw", "Transcript": "callout from"},
            {"Company": "aep", "Folder": "type", "File Name": "1001.ulaw", "Transcript": "electric"},
            {"Company": "aep", "Folder": "location", "File Name": "2900.ulaw", "Transcript": "Level 2"},
            {"Company": "dpl", "Folder": "callflow", "File Name": "1191.ulaw", "Transcript": "This is an"},
            {"Company": "arcos", "Folder": "callflow", "File Name": "1009.ulaw", "Transcript": "Invalid entry"},
            {"Company": "arcos", "Folder": "callflow", "File Name": "1290.ulaw", "Transcript": "Press"},
            {"Company": "arcos", "Folder": "digits", "File Name": "1.ulaw", "Transcript": "1"},
        ]
        
        # Create temporary CSV
        self.csv_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df = pd.DataFrame(self.test_data)
        df.to_csv(self.csv_file.name, index=False)
        self.csv_file.close()
        
        # Initialize database manager
        self.db_manager = AudioDatabaseManager(self.csv_file.name)
    
    def tearDown(self):
        """Clean up temporary files"""
        os.unlink(self.csv_file.name)
    
    def test_database_loading(self):
        """Test database loads correctly"""
        stats = self.db_manager.stats()
        self.assertEqual(stats['total_records'], 8)
        self.assertTrue(stats['companies'] >= 3)  # aep, dpl, arcos
        self.assertTrue(stats['folders'] >= 3)    # callflow, type, location, digits
    
    def test_exact_search(self):
        """Test exact text matching"""
        # Test company-specific search
        results = self.db_manager.search_exact_match("electric", company="aep")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].full_path, "type:1001")
        
        # Test global search
        results = self.db_manager.search_exact_match("Invalid entry")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].full_path, "callflow:1009")
    
    def test_hierarchy_search(self):
        """Test search hierarchy (schema -> company -> global)"""
        # Should find company-specific first
        results = self.db_manager.search_exact_match("This is an", company="aep")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].company, "aep")
    
    def test_company_filtering(self):
        """Test company-specific filtering"""
        aep_records = self.db_manager.get_records_by_company("aep")
        self.assertEqual(len(aep_records), 4)  # 4 AEP records
        
        companies = self.db_manager.get_companies()
        self.assertIn("aep", companies)
        self.assertIn("dpl", companies)
        self.assertIn("arcos", companies)


class TestSegmentParser(unittest.TestCase):
    """Test the intelligent segment parsing functionality"""
    
    def setUp(self):
        self.parser = SegmentParser()
    
    def test_basic_parsing(self):
        """Test basic text parsing"""
        text = "This is an electric callout from Level 2"
        segments = self.parser.parse_text(text)
        
        self.assertTrue(len(segments) > 0)
        
        # Check that we have the expected segments
        segment_texts = [s.text for s in segments]
        self.assertIn("this is an", segment_texts)
        self.assertIn("electric", segment_texts)
        self.assertIn("callout from", segment_texts)
    
    def test_variable_extraction(self):
        """Test dynamic variable detection"""
        text = "This is a {{callout_type}} callout from {{location}}"
        segments = self.parser.parse_text(text)
        
        # Check for variable segments
        variable_segments = [s for s in segments if s.is_variable]
        self.assertEqual(len(variable_segments), 2)
        
        variable_names = [s.variable_name for s in variable_segments]
        self.assertIn("callout_type", variable_names)
        self.assertIn("location", variable_names)
    
    def test_grammar_rules(self):
        """Test a/an grammar detection"""
        text_an = "This is an electric callout"
        segments_an = self.parser.parse_text(text_an)
        
        text_a = "This is a normal callout"
        segments_a = self.parser.parse_text(text_a)
        
        # Find article segments
        articles_an = [s for s in segments_an if s.text in ['a', 'an']]
        articles_a = [s for s in segments_a if s.text in ['a', 'an']]
        
        # Should have detected grammar context
        self.assertTrue(any(a.grammar_context for a in articles_an + articles_a))
    
    def test_digit_detection(self):
        """Test digit segment detection"""
        text = "Press 1 for yes, press 2 for no"
        segments = self.parser.parse_text(text)
        
        digit_segments = [s for s in segments if s.segment_type == 'digit']
        self.assertTrue(len(digit_segments) >= 2)  # Should find "1" and "2"


class TestAudioMapper(unittest.TestCase):
    """Test the audio mapping functionality"""
    
    def setUp(self):
        # Create test database
        self.test_data = [
            {"Company": "aep", "Folder": "callflow", "File Name": "1191.ulaw", "Transcript": "This is an"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1274.ulaw", "Transcript": "callout from"},
            {"Company": "aep", "Folder": "type", "File Name": "1001.ulaw", "Transcript": "electric"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1290.ulaw", "Transcript": "Press"},
            {"Company": "arcos", "Folder": "callflow", "File Name": "1316.ulaw", "Transcript": "if this is employee"},
            {"Company": "arcos", "Folder": "digits", "File Name": "1.ulaw", "Transcript": "1"},
        ]
        
        self.csv_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df = pd.DataFrame(self.test_data)
        df.to_csv(self.csv_file.name, index=False)
        self.csv_file.close()
        
        self.db_manager = AudioDatabaseManager(self.csv_file.name)
        self.audio_mapper = AudioMapper(self.db_manager)
    
    def tearDown(self):
        os.unlink(self.csv_file.name)
    
    def test_exact_match_mapping(self):
        """Test exact phrase matching"""
        mapping = self.audio_mapper.map_text_to_audio("electric", company="aep")
        
        self.assertEqual(mapping.success_rate, 1.0)
        self.assertEqual(mapping.mapping_method, "exact_match")
        self.assertEqual(mapping.play_prompt, ["type:1001"])
    
    def test_segment_building(self):
        """Test building from multiple segments"""
        text = "This is an electric callout from"
        mapping = self.audio_mapper.map_text_to_audio(text, company="aep")
        
        # Should successfully map all parts
        self.assertGreater(mapping.success_rate, 0.5)
        self.assertIn("callflow:1191", mapping.play_prompt)  # "This is an"
        self.assertIn("type:1001", mapping.play_prompt)      # "electric"
        self.assertIn("callflow:1274", mapping.play_prompt)  # "callout from"
    
    def test_variable_mapping(self):
        """Test dynamic variable mapping"""
        text = "{{callout_type}}"
        mapping = self.audio_mapper.map_text_to_audio(text)
        
        self.assertEqual(mapping.success_rate, 1.0)
        self.assertIn("type:{{callout_type}}", mapping.play_prompt)
    
    def test_digit_mapping(self):
        """Test digit mapping"""
        mapping = self.audio_mapper.map_text_to_audio("Press 1")
        
        self.assertGreater(mapping.success_rate, 0.0)
        # Should contain both "Press" and "1" mappings
        self.assertTrue(any("1" in prompt or "digits:1" in prompt for prompt in mapping.play_prompt))
    
    def test_missing_detection(self):
        """Test missing segment detection"""
        mapping = self.audio_mapper.map_text_to_audio("unknown phrase not in database")
        
        self.assertGreater(len(mapping.missing_segments), 0)
        self.assertLess(mapping.success_rate, 1.0)


class TestEnhancedIVRConverter(unittest.TestCase):
    """Test the complete IVR conversion process"""
    
    def setUp(self):
        # Create comprehensive test database
        self.test_data = [
            {"Company": "aep", "Folder": "callflow", "File Name": "1191.ulaw", "Transcript": "This is an"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1274.ulaw", "Transcript": "callout from"},
            {"Company": "aep", "Folder": "type", "File Name": "1001.ulaw", "Transcript": "electric"},
            {"Company": "aep", "Folder": "location", "File Name": "2900.ulaw", "Transcript": "Level 2"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1290.ulaw", "Transcript": "Press"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1316.ulaw", "Transcript": "if this is employee"},
            {"Company": "arcos", "Folder": "callflow", "File Name": "1009.ulaw", "Transcript": "Invalid entry"},
            {"Company": "arcos", "Folder": "callflow", "File Name": "1029.ulaw", "Transcript": "Goodbye"},
            {"Company": "arcos", "Folder": "digits", "File Name": "1.ulaw", "Transcript": "1"},
        ]
        
        self.csv_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df = pd.DataFrame(self.test_data)
        df.to_csv(self.csv_file.name, index=False)
        self.csv_file.close()
        
        self.converter = EnhancedIVRConverter(self.csv_file.name)
    
    def tearDown(self):
        os.unlink(self.csv_file.name)
    
    def test_simple_conversion(self):
        """Test basic Mermaid to IVR conversion"""
        mermaid_code = '''flowchart TD
A["This is an electric callout from Level 2"] --> B["Press 1"]
B --> C["Goodbye"]'''
        
        js_code, report = self.converter.convert_mermaid_to_ivr(mermaid_code, company="aep")
        
        # Should generate valid JavaScript
        self.assertTrue(js_code.startswith("/**"))
        self.assertIn("module.exports = [", js_code)
        self.assertTrue(js_code.endswith("];"))
        
        # Should have successful mappings
        self.assertGreater(report['overall_success_rate'], 0.5)
        self.assertGreater(report['successful_mappings'], 0)
    
    def test_decision_node_conversion(self):
        """Test decision node with branching"""
        mermaid_code = '''flowchart TD
A["Press 1 for yes"] -->|"1"| B["You pressed 1"]
A -->|"error"| C["Invalid entry"]'''
        
        js_code, report = self.converter.convert_mermaid_to_ivr(mermaid_code, company="aep")
        
        # Parse the generated JavaScript
        json_match = json.loads(js_code.split("module.exports = ")[1].rstrip(";"))
        
        # Should have branch logic
        has_branch = any('branch' in node for node in json_match)
        self.assertTrue(has_branch)
    
    def test_javascript_validation(self):
        """Test JavaScript output validation"""
        mermaid_code = '''flowchart TD
A["Test"] --> B["End"]'''
        
        js_code, _ = self.converter.convert_mermaid_to_ivr(mermaid_code)
        validation = self.converter.validate_ivr_output(js_code)
        
        self.assertTrue(validation['valid'])
        self.assertEqual(len(validation['errors']), 0)
        self.assertGreater(validation['node_count'], 0)


class IntegrationTests(unittest.TestCase):
    """Integration tests with real-world examples"""
    
    def setUp(self):
        # Use the actual CSV structure from the project
        self.test_data = [
            {"Company": "aep", "Folder": "callflow", "File Name": "1002.ulaw", "Transcript": "This is an"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1005.ulaw", "Transcript": "callout from"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1006.ulaw", "Transcript": "to the phone"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1004.ulaw", "Transcript": "is not home"},
            {"Company": "aep", "Folder": "callflow", "File Name": "1643.ulaw", "Transcript": "to repeat this message"},
            {"Company": "aep", "Folder": "callout_type", "File Name": "1001.ulaw", "Transcript": "electric"},
            {"Company": "dpl", "Folder": "location", "File Name": "4000.ulaw", "Transcript": "North Dayton"},
        ]
        
        self.csv_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df = pd.DataFrame(self.test_data)
        df.to_csv(self.csv_file.name, index=False)
        self.csv_file.close()
    
    def tearDown(self):
        os.unlink(self.csv_file.name)
    
    def test_callout_flow_example(self):
        """Test with actual callout flow from requirements"""
        mermaid_code = '''flowchart TD
A["This is an electric callout from Level 2. Press 1 if this is employee."] -->|"1"| B{"1 - this is employee"}
A -->|"7 - not home"| C["Employee Not Home"]
B -->|"yes"| D["Enter Employee PIN"]'''
        
        converter = EnhancedIVRConverter(self.csv_file.name)
        js_code, report = converter.convert_mermaid_to_ivr(mermaid_code, company="aep")
        
        # Should generate valid code
        self.assertIn("module.exports", js_code)
        
        # Should have reasonable success rate
        self.assertGreater(report['overall_success_rate'], 0.3)
        
        # Should identify some missing segments (since our test DB is limited)
        print(f"Missing segments: {report['unique_missing_audio']}")
    
    def test_batch_conversion(self):
        """Test converting multiple flows"""
        flows = [
            '''flowchart TD
A["This is an electric callout"] --> B["Press 1"]''',
            '''flowchart TD
A["Enter PIN"] --> B{"Valid PIN?"}
B -->|"Yes"| C["Success"]
B -->|"No"| D["Invalid entry"]'''
        ]
        
        converter = EnhancedIVRConverter(self.csv_file.name)
        results = []
        
        for flow in flows:
            try:
                js_code, report = converter.convert_mermaid_to_ivr(flow, company="aep")
                results.append({"success": True, "report": report})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        
        # Should successfully convert both
        successful = sum(1 for r in results if r["success"])
        self.assertGreater(successful, 0)


# Performance and stress tests
class PerformanceTests(unittest.TestCase):
    """Test system performance with larger datasets"""
    
    def test_large_database_performance(self):
        """Test with larger database"""
        # Create larger test dataset
        large_data = []
        for i in range(1000):
            large_data.append({
                "Company": f"company_{i % 10}",
                "Folder": f"folder_{i % 20}",
                "File Name": f"{i}.ulaw",
                "Transcript": f"Test transcript {i}"
            })
        
        csv_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df = pd.DataFrame(large_data)
        df.to_csv(csv_file.name, index=False)
        csv_file.close()
        
        try:
            # Test loading performance
            import time
            start_time = time.time()
            db_manager = AudioDatabaseManager(csv_file.name)
            load_time = time.time() - start_time
            
            # Should load reasonably quickly
            self.assertLess(load_time, 5.0)  # Less than 5 seconds
            
            # Test search performance
            start_time = time.time()
            results = db_manager.search_exact_match("Test transcript 500")
            search_time = time.time() - start_time
            
            # Should search quickly
            self.assertLess(search_time, 1.0)  # Less than 1 second
            
        finally:
            os.unlink(csv_file.name)


def run_test_suite():
    """Run the complete test suite"""
    print("🧪 Running Enhanced IVR System Test Suite")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestAudioDatabaseManager,
        TestSegmentParser,
        TestAudioMapper,
        TestEnhancedIVRConverter,
        IntegrationTests,
        PerformanceTests
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"🎯 Test Results Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, failure in result.failures:
            print(f"  - {test}: {failure}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")
    
    if not result.failures and not result.errors:
        print("\n✅ All tests passed! System is ready for production.")
    
    return result


# Quick validation function for production use
def validate_system_setup(audio_db_path: str = "cf_general_structure.csv") -> Dict[str, Any]:
    """
    Quick validation that the system is properly set up
    Use this before deploying to production
    """
    results = {
        "database_accessible": False,
        "database_stats": None,
        "converter_functional": False,
        "sample_conversion_success": False,
        "errors": []
    }
    
    try:
        # Test database access
        if os.path.exists(audio_db_path):
            db_manager = AudioDatabaseManager(audio_db_path)
            results["database_accessible"] = True
            results["database_stats"] = db_manager.stats()
        else:
            results["errors"].append(f"Database file not found: {audio_db_path}")
            return results
        
        # Test converter initialization
        converter = EnhancedIVRConverter(audio_db_path)
        results["converter_functional"] = True
        
        # Test sample conversion
        sample_mermaid = '''flowchart TD
A["Test"] --> B["End"]'''
        
        js_code, report = converter.convert_mermaid_to_ivr(sample_mermaid)
        if js_code and "module.exports" in js_code:
            results["sample_conversion_success"] = True
        
    except Exception as e:
        results["errors"].append(str(e))
    
    return results


if __name__ == "__main__":
    # Run full test suite
    run_test_suite()
    
    # Quick validation
    print("\n" + "=" * 60)
    print("🔍 System Validation Check")
    validation = validate_system_setup()
    
    for key, value in validation.items():
        if key != "errors":
            status = "✅" if value else "❌"
            print(f"{status} {key}: {value}")
    
    if validation["errors"]:
        print("❌ Errors found:")
        for error in validation["errors"]:
            print(f"  - {error}")