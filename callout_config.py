"""
Callout type configuration system for PaMerB IVR converter.
Allows users to define schema and callout type ID for proper file naming.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class CalloutDirection(Enum):
    """Direction of the callout"""
    INBOUND = "ib"
    OUTBOUND = "ob"

@dataclass
class CalloutType:
    """Configuration for a specific callout type"""
    id: str
    name: str
    description: str
    direction: CalloutDirection
    schema_prefix: str
    default_features: List[str]

class CalloutTypeRegistry:
    """Registry of available callout types"""
    
    # Predefined callout types based on common IVR patterns
    CALLOUT_TYPES = {
        # Inbound callout types
        "1001": CalloutType(
            id="1001",
            name="Employee PIN Verification",
            description="Basic employee verification with PIN entry",
            direction=CalloutDirection.INBOUND,
            schema_prefix="EMPLOYEE_VERIFY",
            default_features=["pin_entry", "employee_verification"]
        ),
        "1025": CalloutType(
            id="1025",
            name="Emergency Callout Response",
            description="Emergency callout with accept/decline options",
            direction=CalloutDirection.INBOUND,
            schema_prefix="EMERGENCY",
            default_features=["accept_decline", "emergency_response"]
        ),
        "1072": CalloutType(
            id="1072",
            name="General IVR Menu",
            description="General purpose IVR menu system",
            direction=CalloutDirection.INBOUND,
            schema_prefix="GENERAL",
            default_features=["menu_navigation", "dtmf_input"]
        ),
        "1006": CalloutType(
            id="1006",
            name="Notification Only",
            description="Information delivery without response required",
            direction=CalloutDirection.INBOUND,
            schema_prefix="NOTIFY",
            default_features=["notification", "confirmation"]
        ),
        "1009": CalloutType(
            id="1009",
            name="Error Handling",
            description="Error handling and retry logic",
            direction=CalloutDirection.INBOUND,
            schema_prefix="ERROR",
            default_features=["error_handling", "retry_logic"]
        ),
        
        # Outbound callout types
        "2001": CalloutType(
            id="2001",
            name="Automated Callout",
            description="Automated outbound callout system",
            direction=CalloutDirection.OUTBOUND,
            schema_prefix="AUTO_CALLOUT",
            default_features=["answering_machine", "callback_number"]
        ),
        "2025": CalloutType(
            id="2025",
            name="Fill Shift Callout",
            description="Fill shift and overtime callouts",
            direction=CalloutDirection.OUTBOUND,
            schema_prefix="FILL_SHIFT",
            default_features=["pre_arranged", "qualified_no"]
        ),
        "2050": CalloutType(
            id="2050",
            name="Test Callout",
            description="Test callout for system verification",
            direction=CalloutDirection.OUTBOUND,
            schema_prefix="TEST",
            default_features=["test_mode", "no_work_required"]
        ),
        "2100": CalloutType(
            id="2100",
            name="REU Notification",
            description="REU-specific notification callout",
            direction=CalloutDirection.OUTBOUND,
            schema_prefix="REU_NOTIFY",
            default_features=["reu_specific", "notification"]
        ),
        "1050": CalloutType(
            id="1050",
            name="Scheduled Overtime",
            description="Scheduled overtime callout for utility workers",
            direction=CalloutDirection.OUTBOUND,
            schema_prefix="SCHEDULED_OT",
            default_features=["scheduled_work", "overtime", "answering_machine", "pin_check"]
        )
    }
    
    @classmethod
    def get_callout_type(cls, callout_id: str) -> Optional[CalloutType]:
        """Get callout type by ID"""
        return cls.CALLOUT_TYPES.get(callout_id)
    
    @classmethod
    def get_all_callout_types(cls) -> Dict[str, CalloutType]:
        """Get all available callout types"""
        return cls.CALLOUT_TYPES.copy()
    
    @classmethod
    def get_inbound_types(cls) -> Dict[str, CalloutType]:
        """Get only inbound callout types"""
        return {
            k: v for k, v in cls.CALLOUT_TYPES.items() 
            if v.direction == CalloutDirection.INBOUND
        }
    
    @classmethod
    def get_outbound_types(cls) -> Dict[str, CalloutType]:
        """Get only outbound callout types"""
        return {
            k: v for k, v in cls.CALLOUT_TYPES.items() 
            if v.direction == CalloutDirection.OUTBOUND
        }
    
    @classmethod
    def add_custom_callout_type(cls, callout_type: CalloutType):
        """Add a custom callout type"""
        cls.CALLOUT_TYPES[callout_type.id] = callout_type
    
    @classmethod
    def suggest_callout_type(cls, mermaid_content: str) -> Optional[str]:
        """
        Suggest appropriate callout type based on Mermaid content analysis
        """
        content_lower = mermaid_content.lower()
        
        # Analyze content for keywords
        if "test" in content_lower and "callout" in content_lower:
            return "2050"  # Test Callout
        elif "reu" in content_lower and ("notification" in content_lower or "message" in content_lower):
            return "2100"  # REU Notification
        elif "fill shift" in content_lower or "pre-arranged" in content_lower:
            return "2025"  # Fill Shift Callout
        elif "pin" in content_lower and "enter" in content_lower:
            return "1001"  # Employee PIN Verification
        elif ("accept" in content_lower and "decline" in content_lower) or "emergency" in content_lower:
            return "1025"  # Emergency Callout Response
        elif "welcome" in content_lower and ("press" in content_lower or "menu" in content_lower):
            return "1072"  # General IVR Menu
        elif "notification" in content_lower or "message" in content_lower:
            return "1006"  # Notification Only
        
        # Default to general menu if no specific pattern detected
        return "1072"

@dataclass
class CalloutConfiguration:
    """Complete configuration for a callout generation"""
    schema: str
    callout_type_id: str
    direction: CalloutDirection
    custom_schema: Optional[str] = None
    features: Optional[List[str]] = None
    description: Optional[str] = None
    
    def get_filename(self) -> str:
        """Generate appropriate filename based on configuration"""
        schema = self.custom_schema or self.schema
        # Only add "_ib" suffix for inbound flows, outbound flows use base name
        direction_suffix = "_ib" if self.direction == CalloutDirection.INBOUND else ""
        return f"{schema}_{self.callout_type_id}{direction_suffix}.js"
    
    def get_display_name(self) -> str:
        """Get human-readable display name"""
        callout_type = CalloutTypeRegistry.get_callout_type(self.callout_type_id)
        if callout_type:
            return f"{callout_type.name} ({self.callout_type_id})"
        return f"Callout {self.callout_type_id}"

class CalloutConfigurationManager:
    """Manages callout configuration for the application"""
    
    def __init__(self):
        self.current_config: Optional[CalloutConfiguration] = None
    
    def set_configuration(self, config: CalloutConfiguration):
        """Set the current configuration"""
        self.current_config = config
    
    def get_configuration(self) -> Optional[CalloutConfiguration]:
        """Get the current configuration"""
        return self.current_config
    
    def create_configuration_from_analysis(self, mermaid_content: str, 
                                         user_schema: Optional[str] = None,
                                         user_callout_id: Optional[str] = None) -> CalloutConfiguration:
        """
        Create configuration based on content analysis and user input
        """
        # Suggest callout type if not provided by user
        suggested_id = user_callout_id or CalloutTypeRegistry.suggest_callout_type(mermaid_content)
        callout_type = CalloutTypeRegistry.get_callout_type(suggested_id)
        
        if not callout_type:
            # Create a default configuration
            callout_type = CalloutType(
                id=suggested_id or "1072",
                name="Custom Callout",
                description="User-defined callout type",
                direction=CalloutDirection.INBOUND,
                schema_prefix="CUSTOM",
                default_features=[]
            )
        
        # Determine schema
        schema = user_schema or callout_type.schema_prefix
        
        config = CalloutConfiguration(
            schema=schema,
            callout_type_id=callout_type.id,
            direction=callout_type.direction,
            custom_schema=user_schema if user_schema != callout_type.schema_prefix else None,
            features=callout_type.default_features,
            description=callout_type.description
        )
        
        self.set_configuration(config)
        return config
    
    def get_filename_for_download(self) -> str:
        """Get the appropriate filename for download"""
        if self.current_config:
            return self.current_config.get_filename()
        return "ivr_code.js"
    
    def reset_configuration(self):
        """Reset the current configuration"""
        self.current_config = None

# Global instance
callout_manager = CalloutConfigurationManager()