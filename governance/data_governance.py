"""
Data Governance Implementation
Handles data classification, PII detection, and data quality SLAs
"""

import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json


class DataClassification(Enum):
    """Data sensitivity levels"""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class PIIType(Enum):
    """Types of Personally Identifiable Information"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    ACCOUNT_NUMBER = "account_number"


@dataclass
class DataClassificationPolicy:
    """Policy for data classification"""
    name: str
    sensitivity: DataClassification
    retention_days: int
    encryption_required: bool
    audit_logging_required: bool
    pii_types: List[PIIType]


class DataGovernanceRegistry:
    """Registry for data governance policies"""

    def __init__(self):
        self.classifications: Dict[str, DataClassificationPolicy] = {}
        self._load_default_policies()

    def _load_default_policies(self):
        """Load default governance policies"""
        # Customer data - RESTRICTED
        self.register_policy(DataClassificationPolicy(
            name="customer_data",
            sensitivity=DataClassification.RESTRICTED,
            retention_days=2555,  # 7 years
            encryption_required=True,
            audit_logging_required=True,
            pii_types=[
                PIIType.EMAIL,
                PIIType.PHONE,
                PIIType.ADDRESS,
                PIIType.DATE_OF_BIRTH
            ]
        ))

        # Financial data - RESTRICTED
        self.register_policy(DataClassificationPolicy(
            name="financial_data",
            sensitivity=DataClassification.RESTRICTED,
            retention_days=2555,  # 7 years
            encryption_required=True,
            audit_logging_required=True,
            pii_types=[
                PIIType.ACCOUNT_NUMBER,
                PIIType.CREDIT_CARD
            ]
        ))

        # Internal analytics - CONFIDENTIAL
        self.register_policy(DataClassificationPolicy(
            name="internal_analytics",
            sensitivity=DataClassification.CONFIDENTIAL,
            retention_days=365,
            encryption_required=True,
            audit_logging_required=True,
            pii_types=[]
        ))

        # Public data - PUBLIC
        self.register_policy(DataClassificationPolicy(
            name="public_data",
            sensitivity=DataClassification.PUBLIC,
            retention_days=0,  # No retention limit
            encryption_required=False,
            audit_logging_required=False,
            pii_types=[]
        ))

    def register_policy(self, policy: DataClassificationPolicy):
        """Register a new governance policy"""
        self.classifications[policy.name] = policy

    def get_policy(self, name: str) -> Optional[DataClassificationPolicy]:
        """Get governance policy by name"""
        return self.classifications.get(name)

    def list_policies(self) -> List[DataClassificationPolicy]:
        """List all registered policies"""
        return list(self.classifications.values())


class PIIDetector:
    """Detects Personally Identifiable Information in data"""

    def __init__(self):
        self.patterns = self._build_patterns()

    @staticmethod
    def _build_patterns() -> Dict[PIIType, re.Pattern]:
        """Build regex patterns for PII detection"""
        return {
            PIIType.EMAIL: re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            PIIType.PHONE: re.compile(
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
            ),
            PIIType.SSN: re.compile(
                r'\b(?!000|666|9\d{2})\d{3}-\d{2}-\d{4}\b'
            ),
            PIIType.CREDIT_CARD: re.compile(
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b'
            ),
            PIIType.ACCOUNT_NUMBER: re.compile(
                r'\b(?:account[_-]?(?:number|num|id)?[\s:]*)?[0-9]{8,17}\b',
                re.IGNORECASE
            ),
        }

    def detect_pii(self, text: str) -> Dict[PIIType, List[str]]:
        """Detect PII in text"""
        detections = {}
        
        for pii_type, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                # Handle tuple results from groups
                if isinstance(matches[0], tuple):
                    detections[pii_type] = [''.join(m) for m in matches]
                else:
                    detections[pii_type] = matches

        return detections

    def detect_pii_in_column_name(self, column_name: str) -> Optional[PIIType]:
        """Detect if column name suggests PII"""
        lower_col = column_name.lower()
        
        # Email patterns
        if any(x in lower_col for x in ['email', 'e_mail', 'mail']):
            return PIIType.EMAIL
        
        # Phone patterns
        if any(x in lower_col for x in ['phone', 'tel', 'mobile']):
            return PIIType.PHONE
        
        # SSN patterns
        if any(x in lower_col for x in ['ssn', 'social_security', 'social_sec']):
            return PIIType.SSN
        
        # Credit card patterns
        if any(x in lower_col for x in ['card', 'credit', 'payment']):
            return PIIType.CREDIT_CARD
        
        # Address patterns
        if any(x in lower_col for x in ['address', 'street', 'city', 'zip']):
            return PIIType.ADDRESS
        
        # DOB patterns
        if any(x in lower_col for x in ['dob', 'birth', 'birthday', 'age']):
            return PIIType.DATE_OF_BIRTH
        
        return None


class DataQualitySLA:
    """Data Quality Service Level Agreement"""

    def __init__(self, metric_name: str, threshold: float, period_hours: int):
        self.metric_name = metric_name
        self.threshold = threshold
        self.period_hours = period_hours
        self.breaches: List[Dict] = []

    def check_sla(self, actual_value: float) -> bool:
        """Check if metric meets SLA"""
        return actual_value >= self.threshold

    def record_breach(self, actual_value: float, timestamp: str):
        """Record SLA breach"""
        self.breaches.append({
            "timestamp": timestamp,
            "expected": self.threshold,
            "actual": actual_value,
            "gap": self.threshold - actual_value
        })

    def get_breach_summary(self) -> Dict:
        """Get SLA breach summary"""
        return {
            "metric": self.metric_name,
            "threshold": self.threshold,
            "total_breaches": len(self.breaches),
            "latest_breaches": self.breaches[-5:] if self.breaches else []
        }


class DataQualityFramework:
    """Framework for data quality SLAs and monitoring"""

    def __init__(self):
        self.slas: Dict[str, DataQualitySLA] = {}
        self._load_default_slas()

    def _load_default_slas(self):
        """Load default data quality SLAs"""
        # Customer data completeness SLA
        self.register_sla(
            "customer_data_completeness",
            DataQualitySLA("customer_completeness", 99.5, 24)
        )

        # Order data freshness SLA
        self.register_sla(
            "order_data_freshness",
            DataQualitySLA("order_freshness", 98.0, 4)
        )

        # Test passage SLA
        self.register_sla(
            "dbt_test_passage",
            DataQualitySLA("test_pass_rate", 95.0, 24)
        )

    def register_sla(self, name: str, sla: DataQualitySLA):
        """Register a data quality SLA"""
        self.slas[name] = sla

    def evaluate_sla(self, sla_name: str, actual_value: float) -> bool:
        """Evaluate if actual value meets SLA"""
        if sla_name not in self.slas:
            return True
        
        sla = self.slas[sla_name]
        return sla.check_sla(actual_value)

    def get_sla_report(self) -> Dict:
        """Get SLA performance report"""
        return {
            "total_slas": len(self.slas),
            "slas": {
                name: sla.get_breach_summary()
                for name, sla in self.slas.items()
            }
        }


# Global governance registry instance
_governance_registry: Optional[DataGovernanceRegistry] = None
_pii_detector: Optional[PIIDetector] = None
_quality_framework: Optional[DataQualityFramework] = None


def get_governance_registry() -> DataGovernanceRegistry:
    """Get or create global governance registry"""
    global _governance_registry
    if _governance_registry is None:
        _governance_registry = DataGovernanceRegistry()
    return _governance_registry


def get_pii_detector() -> PIIDetector:
    """Get or create global PII detector"""
    global _pii_detector
    if _pii_detector is None:
        _pii_detector = PIIDetector()
    return _pii_detector


def get_quality_framework() -> DataQualityFramework:
    """Get or create global data quality framework"""
    global _quality_framework
    if _quality_framework is None:
        _quality_framework = DataQualityFramework()
    return _quality_framework
