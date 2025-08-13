"""
DynamoDB connection module for PaMerB IVR converter.
Handles connection to the callflow-generator-ia-db table.
"""

import boto3
import os
import logging
import streamlit as st
from typing import List, Dict, Optional
from botocore.exceptions import ClientError, NoCredentialsError

# Set up logging
logger = logging.getLogger(__name__)

class VoiceFileDatabase:
    """
    Handles connection and queries to the DynamoDB voice file database.
    """
    
    def __init__(self, table_name: str = 'callflow-generator-ia-db', region_name: str = 'us-east-2'):
        """
        Initialize the database connection.
        
        Args:
            table_name: Name of the DynamoDB table
            region_name: AWS region where the table is located
        """
        self.table_name = table_name
        self.region_name = region_name
        self.dynamodb = None
        self.table = None
        self.connection_status = "disconnected"
        self.error_message = None
        
        self._connect()
    
    def _connect(self):
        """
        Establish connection to DynamoDB.
        """
        try:
            # Get AWS credentials from Streamlit secrets
            aws_access_key_id = None
            aws_secret_access_key = None
            
            # Try to get credentials from Streamlit secrets first
            try:
                aws_config = st.secrets.get("AWS", {})
                aws_access_key_id = aws_config.get("AWS_ACCESS_KEY_ID")
                aws_secret_access_key = aws_config.get("AWS_SECRET_ACCESS_KEY")
                region_override = aws_config.get("AWS_DEFAULT_REGION")
                if region_override:
                    self.region_name = region_override
                    
                logger.info("Using AWS credentials from Streamlit secrets")
            except Exception as e:
                logger.info(f"Could not load Streamlit secrets: {e}, falling back to environment variables")
            
            # Fallback to environment variables if secrets not available
            if not aws_access_key_id:
                aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
                aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
                logger.info("Using AWS credentials from environment variables")
            
            # Initialize DynamoDB resource with explicit credentials if available
            if aws_access_key_id and aws_secret_access_key:
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    region_name=self.region_name,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key
                )
            else:
                # Fall back to default boto3 credential chain
                self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
                
            self.table = self.dynamodb.Table(self.table_name)
            
            # Test the connection by checking if table exists
            self.table.load()
            self.connection_status = "connected"
            logger.info(f"Successfully connected to DynamoDB table: {self.table_name}")
            
        except NoCredentialsError:
            self.error_message = "AWS credentials not found. Please configure AWS credentials."
            self.connection_status = "error"
            logger.error(self.error_message)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                self.error_message = f"DynamoDB table '{self.table_name}' not found."
            else:
                self.error_message = f"AWS error: {e.response['Error']['Message']}"
            self.connection_status = "error"
            logger.error(self.error_message)
            
        except Exception as e:
            self.error_message = f"Unexpected error connecting to DynamoDB: {str(e)}"
            self.connection_status = "error"
            logger.error(self.error_message)
    
    def get_connection_status(self) -> Dict[str, str]:
        """
        Get the current connection status.
        
        Returns:
            Dict with status and error message if any
        """
        return {
            "status": self.connection_status,
            "error": self.error_message,
            "table_name": self.table_name,
            "region": self.region_name
        }
    
    def get_all_voice_files(self) -> List[Dict[str, str]]:
        """
        Retrieve all voice files from the database.
        
        Returns:
            List of voice file records
        """
        if self.connection_status != "connected":
            logger.warning("Database not connected. Cannot retrieve voice files.")
            return []
        
        try:
            voice_files = []
            
            # Scan the entire table (use pagination for large tables)
            response = self.table.scan()
            voice_files.extend(response['Items'])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                voice_files.extend(response['Items'])
            
            logger.info(f"Retrieved {len(voice_files)} voice files from database")
            return voice_files
            
        except ClientError as e:
            logger.error(f"Error retrieving voice files: {e.response['Error']['Message']}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving voice files: {str(e)}")
            return []
    
    def get_voice_files_by_company(self, company: str) -> List[Dict[str, str]]:
        """
        Retrieve voice files for a specific company.
        
        Args:
            company: Company name to filter by
            
        Returns:
            List of voice file records for the company
        """
        if self.connection_status != "connected":
            logger.warning("Database not connected. Cannot retrieve voice files.")
            return []
        
        try:
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('company').eq(company)
            )
            
            voice_files = response['Items']
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr('company').eq(company),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                voice_files.extend(response['Items'])
            
            logger.info(f"Retrieved {len(voice_files)} voice files for company: {company}")
            return voice_files
            
        except ClientError as e:
            logger.error(f"Error retrieving voice files for company {company}: {e.response['Error']['Message']}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving voice files for company {company}: {str(e)}")
            return []
    
    def search_voice_files_by_transcript(self, search_text: str) -> List[Dict[str, str]]:
        """
        Search voice files by transcript content.
        
        Args:
            search_text: Text to search for in transcripts
            
        Returns:
            List of matching voice file records
        """
        if self.connection_status != "connected":
            logger.warning("Database not connected. Cannot search voice files.")
            return []
        
        try:
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('transcript').contains(search_text)
            )
            
            voice_files = response['Items']
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr('transcript').contains(search_text),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                voice_files.extend(response['Items'])
            
            logger.info(f"Found {len(voice_files)} voice files matching transcript: {search_text}")
            return voice_files
            
        except ClientError as e:
            logger.error(f"Error searching voice files: {e.response['Error']['Message']}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching voice files: {str(e)}")
            return []
    
    def get_table_stats(self) -> Dict[str, any]:
        """
        Get statistics about the voice file table.
        
        Returns:
            Dict with table statistics
        """
        if self.connection_status != "connected":
            return {"error": "Database not connected"}
        
        try:
            # Get table metadata
            table_info = self.table.meta.client.describe_table(TableName=self.table_name)
            item_count = table_info['Table']['ItemCount']
            table_size = table_info['Table']['TableSizeBytes']
            
            return {
                "item_count": item_count,
                "table_size_bytes": table_size,
                "table_size_mb": round(table_size / (1024 * 1024), 2),
                "status": "active"
            }
            
        except ClientError as e:
            logger.error(f"Error getting table stats: {e.response['Error']['Message']}")
            return {"error": f"AWS error: {e.response['Error']['Message']}"}
        except Exception as e:
            logger.error(f"Unexpected error getting table stats: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}


# Global database instance
_db_instance = None

def get_database() -> VoiceFileDatabase:
    """
    Get the global database instance (singleton pattern).
    
    Returns:
        VoiceFileDatabase instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = VoiceFileDatabase()
    return _db_instance

def test_connection() -> Dict[str, any]:
    """
    Test the database connection and return status.
    
    Returns:
        Dict with connection test results
    """
    db = get_database()
    status = db.get_connection_status()
    
    if status["status"] == "connected":
        stats = db.get_table_stats()
        status.update(stats)
    
    return status