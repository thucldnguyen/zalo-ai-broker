"""
Vietnamese NLP utilities for real estate conversations

Extracts structured information from Vietnamese text:
- Budget ranges (tỷ, triệu)
- Locations (districts, areas, projects)
- Interest level signals
- Intent classification
"""

import re
from typing import Tuple, List, Optional
from core.models import Intent, InterestLevel


class VietnameseExtractor:
    """Extract structured data from Vietnamese real estate conversations"""
    
    # Budget patterns with multipliers
    BUDGET_PATTERNS = [
        (r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*tỷ', 1_000_000_000),      # "2-3 tỷ"
        (r'tầm\s*(\d+\.?\d*)\s*tỷ', 1_000_000_000),                   # "tầm 2 tỷ"
        (r'khoảng\s*(\d+\.?\d*)\s*tỷ', 1_000_000_000),                # "khoảng 2.5 tỷ"
        (r'(\d+\.?\d*)\s*tỷ', 1_000_000_000),                         # "3 tỷ"
        (r'(\d+)\s*-\s*(\d+)\s*triệu', 1_000_000),                    # "500-700 triệu"
        (r'(\d+)\s*triệu', 1_000_000),                                # "800 triệu"
    ]
    
    # Location keywords
    DISTRICTS = [
        r'quận\s*\d+', r'q\s*\d+', r'q\.\s*\d+',
        'thủ đức', 'bình thạnh', 'phú nhuận', 'tân bình',
        'gò vấp', 'tân phú', 'bình tân', 'hóc môn'
    ]
    
    AREAS = [
        'thảo điền', 'an phú', 'bình an', 'cát lái',
        'thạnh mỹ lợi', 'sala', 'đại quang minh'
    ]
    
    PROJECTS = [
        'vinhomes', 'masteri', 'estella', 'the vista',
        'gateway', 'feliz en vista', 'gem riverside',
        'sunwah pearl', 'the sun avenue'
    ]
    
    # Interest level signals
    HOT_SIGNALS = [
        'cần gấp', 'trong tuần', 'càng sớm càng tốt',
        'urgent', 'hôm nay', 'ngay', 'trong tháng này'
    ]
    
    WARM_SIGNALS = [
        'đang tìm', 'quan tâm', 'muốn xem', 'cho em thông tin',
        'có thể xem', 'được không', 'xem khi nào'
    ]
    
    # Intent keywords
    INTENT_KEYWORDS = {
        Intent.BUY: ['mua', 'sở hữu', 'về ở', 'chuyển về'],
        Intent.INVEST: ['đầu tư', 'cho thuê', 'sinh lời', 'lãi'],
        Intent.RENT: ['thuê', 'cần thuê', 'tìm thuê'],
    }
    
    def extract_budget(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract budget range from Vietnamese text
        
        Returns:
            (min_budget, max_budget) in VND
            Creates ±15% range for single values
        """
        text = text.lower()
        
        for pattern, multiplier in self.BUDGET_PATTERNS:
            match = re.search(pattern, text)
            if match:
                if '-' in pattern and match.lastindex == 2:
                    # Range specified: "2-3 tỷ"
                    min_val = int(float(match.group(1)) * multiplier)
                    max_val = int(float(match.group(2)) * multiplier)
                    return (min_val, max_val)
                else:
                    # Single value: create range ±15%
                    value = int(float(match.group(1)) * multiplier)
                    return (int(value * 0.85), int(value * 1.15))
        
        return (None, None)
    
    def extract_locations(self, text: str) -> List[str]:
        """Extract mentioned locations (districts, areas, projects)"""
        text = text.lower()
        locations = []
        
        # Check districts
        for pattern in self.DISTRICTS:
            matches = re.findall(pattern, text)
            locations.extend(matches)
        
        # Check specific areas
        for area in self.AREAS:
            if area in text:
                locations.append(area)
        
        # Check project names
        for project in self.PROJECTS:
            if project in text:
                locations.append(project)
        
        # Deduplicate while preserving order
        seen = set()
        unique_locations = []
        for loc in locations:
            if loc not in seen:
                seen.add(loc)
                unique_locations.append(loc)
        
        return unique_locations
    
    def classify_interest(
        self, 
        text: str, 
        response_time_seconds: Optional[int] = None
    ) -> InterestLevel:
        """
        Classify interest level based on text signals and response behavior
        
        Args:
            text: Message text
            response_time_seconds: Time taken to respond (optional)
        
        Returns:
            InterestLevel (HOT, WARM, or COLD)
        """
        text = text.lower()
        
        # Check for hot signals
        if any(signal in text for signal in self.HOT_SIGNALS):
            return InterestLevel.HOT
        
        # Quick response indicates high interest
        if response_time_seconds and response_time_seconds < 300:  # < 5 minutes
            return InterestLevel.HOT
        
        # Check for warm signals
        if any(signal in text for signal in self.WARM_SIGNALS):
            return InterestLevel.WARM
        
        # Questions indicate engagement
        if '?' in text or text.endswith('không'):
            return InterestLevel.WARM
        
        return InterestLevel.COLD
    
    def detect_intent(self, text: str) -> Intent:
        """
        Detect customer intent from text
        
        Returns:
            Intent enum (BUY, INVEST, RENT, or BROWSE as default)
        """
        text = text.lower()
        
        # Count keyword matches for each intent
        scores = {intent: 0 for intent in Intent}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[intent] += 1
        
        # Return intent with highest score, or BROWSE if no matches
        max_score = max(scores.values())
        if max_score > 0:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return Intent.BROWSE
    
    def extract_property_type(self, text: str) -> List[str]:
        """Extract property type mentions"""
        text = text.lower()
        property_types = []
        
        type_keywords = {
            'apartment': ['căn hộ', 'chung cư', 'apartment', 'condo'],
            'villa': ['biệt thự', 'nhà phố', 'villa', 'townhouse'],
            'land': ['đất', 'đất nền', 'land', 'nền'],
            'office': ['văn phòng', 'officetel', 'office']
        }
        
        for prop_type, keywords in type_keywords.items():
            if any(kw in text for kw in keywords):
                property_types.append(prop_type)
        
        return property_types
    
    def extract_bedroom_count(self, text: str) -> Optional[int]:
        """Extract number of bedrooms mentioned"""
        # Patterns: "2PN", "2 PN", "2 phòng ngủ"
        patterns = [
            r'(\d+)\s*pn',
            r'(\d+)\s*phòng\s*ngủ',
            r'(\d+)\s*bedroom'
        ]
        
        text = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        
        return None
    
    def extract_key_phrases(self, text: str) -> List[str]:
        """Extract important phrases that indicate preferences or concerns"""
        text = text.lower()
        key_phrases = []
        
        # Feature preferences
        feature_keywords = [
            'view sông', 'view đẹp', 'thoáng mát', 'yên tĩnh',
            'gần trường', 'gần chợ', 'gần metro', 'tiện ích',
            'hồ bơi', 'gym', 'công viên', 'sân vườn'
        ]
        
        for phrase in feature_keywords:
            if phrase in text:
                key_phrases.append(phrase)
        
        return key_phrases
