"""
Memory/Storage layer for lead profiles

MVP implementation using JSON files
Future: Migrate to PostgreSQL with JSONB
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from core.models import LeadProfile, Message, FollowUpTask


class LeadStore:
    """
    JSON-based storage for lead profiles
    
    Storage structure:
        data/leads/
            {lead_id}.json - Individual lead profiles
            index.json - Quick lookup index
    """
    
    def __init__(self, data_dir: str = "data/leads"):
        """Initialize lead store with data directory"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.data_dir / "index.json"
        self._ensure_index()
    
    def _ensure_index(self):
        """Create index file if it doesn't exist"""
        if not self.index_file.exists():
            self.index_file.write_text(json.dumps({
                "total_leads": 0,
                "hot_leads": 0,
                "warm_leads": 0,
                "cold_leads": 0,
                "last_updated": datetime.now().isoformat()
            }, indent=2))
    
    def _update_index(self):
        """Rebuild index from all lead files"""
        all_files = list(self.data_dir.glob("*.json"))
        all_files = [f for f in all_files if f.name != "index.json"]
        
        hot_count = 0
        warm_count = 0
        cold_count = 0
        
        for lead_file in all_files:
            try:
                data = json.loads(lead_file.read_text())
                level = data.get('interest_level', 'cold')
                if level == 'hot':
                    hot_count += 1
                elif level == 'warm':
                    warm_count += 1
                else:
                    cold_count += 1
            except:
                continue
        
        index_data = {
            "total_leads": len(all_files),
            "hot_leads": hot_count,
            "warm_leads": warm_count,
            "cold_leads": cold_count,
            "last_updated": datetime.now().isoformat()
        }
        
        self.index_file.write_text(json.dumps(index_data, indent=2))
    
    def save(self, lead: LeadProfile) -> bool:
        """
        Save lead profile to disk
        
        Args:
            lead: LeadProfile to save
        
        Returns:
            True if successful, False otherwise
        """
        try:
            lead_file = self.data_dir / f"{lead.lead_id}.json"
            lead_data = lead.to_dict()
            lead_file.write_text(json.dumps(lead_data, indent=2, ensure_ascii=False))
            self._update_index()
            return True
        except Exception as e:
            print(f"Error saving lead {lead.lead_id}: {e}")
            return False
    
    def get(self, lead_id: str) -> Optional[LeadProfile]:
        """
        Retrieve lead profile by ID
        
        Args:
            lead_id: Lead identifier
        
        Returns:
            LeadProfile if found, None otherwise
        """
        try:
            lead_file = self.data_dir / f"{lead_id}.json"
            if not lead_file.exists():
                return None
            
            data = json.loads(lead_file.read_text())
            return LeadProfile.from_dict(data)
        except Exception as e:
            print(f"Error loading lead {lead_id}: {e}")
            return None
    
    def get_all(self) -> List[LeadProfile]:
        """Get all lead profiles"""
        leads = []
        for lead_file in self.data_dir.glob("*.json"):
            if lead_file.name == "index.json":
                continue
            
            try:
                data = json.loads(lead_file.read_text())
                leads.append(LeadProfile.from_dict(data))
            except Exception as e:
                print(f"Error loading {lead_file}: {e}")
                continue
        
        return leads
    
    def get_by_interest_level(self, level: str) -> List[LeadProfile]:
        """Get all leads with specific interest level"""
        all_leads = self.get_all()
        return [lead for lead in all_leads if lead.interest_level.value == level]
    
    def get_hot_leads(self) -> List[LeadProfile]:
        """Get all hot leads"""
        return self.get_by_interest_level("hot")
    
    def delete(self, lead_id: str) -> bool:
        """
        Delete lead profile
        
        Args:
            lead_id: Lead identifier
        
        Returns:
            True if deleted, False if not found
        """
        try:
            lead_file = self.data_dir / f"{lead_id}.json"
            if lead_file.exists():
                lead_file.unlink()
                self._update_index()
                return True
            return False
        except Exception as e:
            print(f"Error deleting lead {lead_id}: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get storage statistics"""
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return {}


class ConversationHistory:
    """
    Store conversation history per lead
    
    Storage: data/conversations/{lead_id}.jsonl
    """
    
    def __init__(self, data_dir: str = "data/conversations"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def add_message(self, lead_id: str, message: Message):
        """Append message to lead's conversation history"""
        conv_file = self.data_dir / f"{lead_id}.jsonl"
        
        with conv_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(message.to_dict(), ensure_ascii=False) + '\n')
    
    def get_history(self, lead_id: str, limit: Optional[int] = None) -> List[Message]:
        """
        Get conversation history for a lead
        
        Args:
            lead_id: Lead identifier
            limit: Maximum number of messages to return (most recent)
        
        Returns:
            List of Message objects, most recent first
        """
        conv_file = self.data_dir / f"{lead_id}.jsonl"
        
        if not conv_file.exists():
            return []
        
        messages = []
        with conv_file.open('r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    messages.append(Message(**data))
                except:
                    continue
        
        # Return most recent first
        messages.reverse()
        
        if limit:
            return messages[:limit]
        
        return messages
