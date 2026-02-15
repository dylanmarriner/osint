"""
Advanced Entity Matching Engine for OSINT Framework

Implements sophisticated matching algorithms for entity deduplication and linking:
- Fuzzy string matching (Levenshtein, Jaro-Winkler, Soundex)
- Email domain aliasing and variations
- Phone number normalization and portability
- Username pattern matching and variations
- Biographical data alignment
- Cross-platform identity linking
"""

import asyncio
import difflib
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import unicodedata

import structlog

logger = structlog.get_logger(__name__)


class MatchingAlgorithm(Enum):
    """Available matching algorithms."""
    EXACT = "exact"
    LEVENSHTEIN = "levenshtein"
    JARO_WINKLER = "jaro_winkler"
    SOUNDEX = "soundex"
    METAPHONE = "metaphone"
    SEMANTIC = "semantic"


@dataclass
class MatchScore:
    """Result of a matching operation."""
    algorithm: MatchingAlgorithm
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 100.0
    details: Dict[str, any] = field(default_factory=dict)
    reasoning: str = ""

    def __hash__(self):
        return hash((self.algorithm.value, round(self.score, 4)))

    def __eq__(self, other):
        return (self.algorithm == other.algorithm and 
                abs(self.score - other.score) < 0.01)


class AdvancedMatcher:
    """Advanced entity matching using multiple algorithms."""

    def __init__(self):
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    # ==================== String Matching ====================

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def levenshtein_ratio(self, s1: str, s2: str) -> float:
        """Levenshtein ratio (0-1) where 1 is identical."""
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        return 1.0 - (self.levenshtein_distance(s1, s2) / max_len)

    def jaro_winkler_similarity(self, s1: str, s2: str, scaling: float = 0.1) -> float:
        """
        Jaro-Winkler similarity (0-1).
        Better for typos and transpositions.
        """
        s1 = str(s1).lower()
        s2 = str(s2).lower()

        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # Calculate Jaro similarity
        match_distance = max(len1, len2) // 2 - 1
        if match_distance < 0:
            match_distance = 0

        s1_matches = [False] * len1
        s2_matches = [False] * len2

        matches = 0
        transpositions = 0

        # Find matches
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)

            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        # Find transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

        jaro = (matches / len1 + matches / len2 + 
                (matches - transpositions / 2) / matches) / 3.0

        # Apply Winkler modification
        prefix = 0
        for i in range(min(len(s1), len(s2))):
            if s1[i] == s2[i]:
                prefix += 1
            else:
                break

        prefix = min(4, prefix)  # Max prefix length
        return jaro + prefix * scaling * (1 - jaro)

    def soundex(self, name: str) -> str:
        """
        Generate Soundex code for phonetic matching.
        Good for name variations.
        """
        name = name.upper()
        
        # Remove non-alphabetic characters and normalize
        name = re.sub(r'[^A-Z]', '', name)
        
        if not name:
            return "0000"

        # Keep first letter
        first_letter = name[0]
        
        # Soundex mapping
        mapping = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6',
            'A': '0', 'E': '0', 'I': '0', 'O': '0', 'U': '0', 'Y': '0'
        }

        # Convert to codes
        codes = [mapping.get(c, '0') for c in name[1:]]
        
        # Remove consecutive duplicates and zeros
        result = first_letter
        last_code = mapping.get(first_letter, '0')
        
        for code in codes:
            if code != '0' and code != last_code:
                result += code
                if len(result) == 4:
                    break
            if code != '0':
                last_code = code

        # Pad with zeros
        return (result + '000')[:4]

    def metaphone(self, name: str) -> str:
        """
        Simplified Metaphone for phonetic matching.
        """
        name = name.upper()
        name = re.sub(r'[^A-Z]', '', name)
        
        if not name:
            return ""

        # Remove duplicates
        result = name[0]
        for i in range(1, len(name)):
            if name[i] != name[i-1]:
                result += name[i]

        # Metaphone rules
        result = result.replace('PH', 'F')
        result = result.replace('GH', '')
        result = result.replace('DG', 'G')
        result = re.sub(r'[AEIOU]', '', result[1:])
        
        return (result + '0000')[:4]

    # ==================== Email Matching ====================

    def normalize_email(self, email: str) -> str:
        """Normalize email for comparison."""
        email = email.lower().strip()
        
        # Handle Gmail aliases (everything after + is ignored)
        if '@gmail.com' in email:
            local_part = email.split('@')[0].split('+')[0]
            return f"{local_part}@gmail.com"
        
        # Handle corporate domain aliases
        domain_aliases = {
            'gmail.com': ['googlemail.com'],
            'outlook.com': ['hotmail.com', 'live.com', 'msn.com'],
        }
        
        for canonical, aliases in domain_aliases.items():
            for alias in aliases:
                if email.endswith(f'@{alias}'):
                    local_part = email.split('@')[0]
                    return f"{local_part}@{canonical}"
        
        return email

    def email_similarity(self, email1: str, email2: str) -> MatchScore:
        """Compare email addresses with alias handling."""
        norm1 = self.normalize_email(email1)
        norm2 = self.normalize_email(email2)
        
        if norm1 == norm2:
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=1.0,
                confidence=100.0,
                reasoning="Emails match after normalization"
            )
        
        local1, domain1 = norm1.split('@')
        local2, domain2 = norm2.split('@')
        
        # Check if domains are same
        if domain1 == domain2:
            local_score = self.jaro_winkler_similarity(local1, local2)
            confidence = local_score * 100
            
            if local_score > 0.85:
                return MatchScore(
                    algorithm=MatchingAlgorithm.JARO_WINKLER,
                    score=local_score,
                    confidence=confidence,
                    details={'local_part_match': local_score},
                    reasoning="Same domain with similar local parts"
                )
        
        return MatchScore(
            algorithm=MatchingAlgorithm.LEVENSHTEIN,
            score=0.0,
            confidence=0.0,
            reasoning="Different email addresses"
        )

    # ==================== Phone Number Matching ====================

    def normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format."""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Handle country codes
        if len(digits) == 10:  # Assume US
            digits = '1' + digits
        elif len(digits) == 11 and digits[0] == '1':  # US with leading 1
            pass
        elif not digits.startswith('1') and len(digits) == 11:
            digits = '1' + digits[1:]  # Remove first digit and add 1
        
        return digits if digits else None

    def phone_similarity(self, phone1: str, phone2: str) -> MatchScore:
        """Compare phone numbers."""
        norm1 = self.normalize_phone(phone1)
        norm2 = self.normalize_phone(phone2)
        
        if not norm1 or not norm2:
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=0.0,
                confidence=0.0,
                reasoning="Invalid phone numbers"
            )
        
        if norm1 == norm2:
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=1.0,
                confidence=100.0,
                reasoning="Phone numbers match exactly"
            )
        
        # Partial match (last 7 digits - local number)
        if norm1[-7:] == norm2[-7:]:
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=0.9,
                confidence=90.0,
                details={'match_type': 'local_number'},
                reasoning="Local phone numbers match"
            )
        
        return MatchScore(
            algorithm=MatchingAlgorithm.LEVENSHTEIN,
            score=0.0,
            confidence=0.0,
            reasoning="Phone numbers differ"
        )

    # ==================== Username Matching ====================

    def generate_username_variations(self, username: str) -> Set[str]:
        """Generate common username variations."""
        variations = {username}
        
        # Remove underscores/hyphens/dots
        for sep in ['_', '-', '.']:
            variations.add(username.replace(sep, ''))
        
        # Add with common separators
        parts = re.split(r'[_\-.]', username)
        if len(parts) > 1:
            variations.add(''.join(parts))
            variations.add('_'.join(parts))
            variations.add('-'.join(parts))
        
        # First/last name variations
        if len(parts) == 2:
            variations.add(parts[0][0] + parts[1])  # jsmith
            variations.add(parts[1] + parts[0][0])  # smithj
        
        return variations

    def username_similarity(self, user1: str, user2: str) -> MatchScore:
        """Compare usernames with variation handling."""
        user1_lower = user1.lower()
        user2_lower = user2.lower()
        
        if user1_lower == user2_lower:
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=1.0,
                confidence=100.0,
                reasoning="Usernames match exactly"
            )
        
        # Check variations
        vars1 = self.generate_username_variations(user1_lower)
        vars2 = self.generate_username_variations(user2_lower)
        
        if vars1 & vars2:  # Intersection
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=0.95,
                confidence=95.0,
                reasoning="Usernames match via variation"
            )
        
        # Phonetic matching
        score = self.jaro_winkler_similarity(user1_lower, user2_lower)
        confidence = score * 100
        
        if score > 0.80:
            return MatchScore(
                algorithm=MatchingAlgorithm.JARO_WINKLER,
                score=score,
                confidence=confidence,
                reasoning="Usernames are phonetically similar"
            )
        
        return MatchScore(
            algorithm=MatchingAlgorithm.LEVENSHTEIN,
            score=score,
            confidence=confidence,
            reasoning="Usernames differ"
        )

    # ==================== Name Matching ====================

    def tokenize_name(self, name: str) -> List[str]:
        """Break name into components."""
        # Remove accents
        name = ''.join(
            c for c in unicodedata.normalize('NFD', name)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Split on common separators
        tokens = re.split(r'[\s\-\.]+', name.lower().strip())
        return [t for t in tokens if t]

    def name_similarity(self, name1: str, name2: str) -> MatchScore:
        """Compare names intelligently."""
        tokens1 = self.tokenize_name(name1)
        tokens2 = self.tokenize_name(name2)
        
        if not tokens1 or not tokens2:
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=0.0,
                confidence=0.0,
                reasoning="Invalid names"
            )
        
        # Exact match
        if name1.lower() == name2.lower():
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=1.0,
                confidence=100.0,
                reasoning="Names match exactly"
            )
        
        # Token-based matching (first/last name swap, etc.)
        common_tokens = set(tokens1) & set(tokens2)
        
        if len(common_tokens) >= min(len(tokens1), len(tokens2)):
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=0.95,
                confidence=95.0,
                details={'common_tokens': list(common_tokens)},
                reasoning="Names share all tokens (possible name order variation)"
            )
        
        if common_tokens and len(common_tokens) >= 2:
            overlap = len(common_tokens) / min(len(tokens1), len(tokens2))
            return MatchScore(
                algorithm=MatchingAlgorithm.EXACT,
                score=overlap,
                confidence=overlap * 100,
                details={'common_tokens': list(common_tokens)},
                reasoning="Names share multiple tokens"
            )
        
        # Phonetic matching on first name/last name
        if len(tokens1) > 0 and len(tokens2) > 0:
            first_score = self.soundex(tokens1[0]) == self.soundex(tokens2[0])
            last_score = False
            
            if len(tokens1) > 1 and len(tokens2) > 1:
                last_score = self.soundex(tokens1[-1]) == self.soundex(tokens2[-1])
            
            if first_score and last_score:
                return MatchScore(
                    algorithm=MatchingAlgorithm.SOUNDEX,
                    score=0.85,
                    confidence=85.0,
                    reasoning="Names are phonetically similar"
                )
        
        # Jaro-Winkler on full string
        score = self.jaro_winkler_similarity(name1, name2)
        if score > 0.80:
            return MatchScore(
                algorithm=MatchingAlgorithm.JARO_WINKLER,
                score=score,
                confidence=score * 100,
                reasoning="Names are similar"
            )
        
        return MatchScore(
            algorithm=MatchingAlgorithm.LEVENSHTEIN,
            score=score,
            confidence=score * 100,
            reasoning="Names differ"
        )

    # ==================== Biographical Matching ====================

    def biographical_consistency(self, bio1: Dict, bio2: Dict) -> float:
        """
        Check biographical data consistency.
        Returns confidence 0-1.
        """
        score = 0.0
        checks = 0
        
        # Age/birth year consistency
        if 'birth_year' in bio1 and 'birth_year' in bio2:
            checks += 1
            if abs(bio1['birth_year'] - bio2['birth_year']) <= 1:
                score += 1.0
            elif abs(bio1['birth_year'] - bio2['birth_year']) <= 2:
                score += 0.7
        
        # Location consistency
        if 'location' in bio1 and 'location' in bio2:
            checks += 1
            loc_score = self.jaro_winkler_similarity(
                bio1['location'].lower(),
                bio2['location'].lower()
            )
            score += loc_score
        
        # Education consistency
        if 'school' in bio1 and 'school' in bio2:
            checks += 1
            school_score = self.jaro_winkler_similarity(
                bio1['school'].lower(),
                bio2['school'].lower()
            )
            score += school_score
        
        # Employer consistency
        if 'employer' in bio1 and 'employer' in bio2:
            checks += 1
            employer_score = self.jaro_winkler_similarity(
                bio1['employer'].lower(),
                bio2['employer'].lower()
            )
            score += employer_score
        
        if checks == 0:
            return 0.5  # Neutral score if no data
        
        return score / checks

    # ==================== Multi-Signal Matching ====================

    async def match_entities(
        self,
        entity1: Dict,
        entity2: Dict,
        weights: Optional[Dict[str, float]] = None
    ) -> Tuple[float, Dict[str, any]]:
        """
        Multi-signal entity matching using weighted scores.
        
        Returns:
            (overall_confidence, detailed_results)
        """
        if weights is None:
            weights = {
                'name': 0.30,
                'email': 0.25,
                'phone': 0.20,
                'username': 0.15,
                'biographical': 0.10
            }
        
        results = {
            'name_match': MatchScore(MatchingAlgorithm.EXACT, 0, 0),
            'email_match': MatchScore(MatchingAlgorithm.EXACT, 0, 0),
            'phone_match': MatchScore(MatchingAlgorithm.EXACT, 0, 0),
            'username_match': MatchScore(MatchingAlgorithm.EXACT, 0, 0),
            'biographical_match': MatchScore(MatchingAlgorithm.EXACT, 0, 0),
        }
        
        # Name matching
        if 'name' in entity1 and 'name' in entity2:
            results['name_match'] = self.name_similarity(entity1['name'], entity2['name'])
        
        # Email matching
        if 'email' in entity1 and 'email' in entity2:
            results['email_match'] = self.email_similarity(entity1['email'], entity2['email'])
        
        # Phone matching
        if 'phone' in entity1 and 'phone' in entity2:
            results['phone_match'] = self.phone_similarity(entity1['phone'], entity2['phone'])
        
        # Username matching
        if 'username' in entity1 and 'username' in entity2:
            results['username_match'] = self.username_similarity(
                entity1['username'],
                entity2['username']
            )
        
        # Biographical matching
        if 'biographical' in entity1 and 'biographical' in entity2:
            bio_score = self.biographical_consistency(
                entity1['biographical'],
                entity2['biographical']
            )
            results['biographical_match'] = MatchScore(
                algorithm=MatchingAlgorithm.SEMANTIC,
                score=bio_score,
                confidence=bio_score * 100,
                reasoning="Biographical data consistency check"
            )
        
        # Calculate weighted overall score
        total_weight = 0
        weighted_score = 0
        
        for field, weight in weights.items():
            match_field = f"{field}_match"
            if match_field in results:
                match = results[match_field]
                weighted_score += match.score * weight
                total_weight += weight
        
        if total_weight > 0:
            overall_confidence = (weighted_score / total_weight) * 100
        else:
            overall_confidence = 0.0
        
        return overall_confidence, results

    async def link_cross_platform_identities(
        self,
        entities: List[Dict]
    ) -> Dict[str, List[str]]:
        """
        Link entities across platforms using multiple signals.
        
        Returns:
            Map of canonical IDs to lists of linked entity IDs
        """
        clusters = {}
        assignments = {}
        
        for i, entity in enumerate(entities):
            if i in assignments:
                continue
            
            # Start new cluster
            cluster_id = f"cluster_{entity.get('id', i)}"
            clusters[cluster_id] = [entity['id']]
            assignments[i] = cluster_id
            
            # Compare with all other unassigned entities
            for j in range(i + 1, len(entities)):
                if j in assignments:
                    continue
                
                confidence, _ = await self.match_entities(entity, entities[j])
                
                # Link if confidence is high enough
                if confidence >= 75.0:
                    clusters[cluster_id].append(entities[j]['id'])
                    assignments[j] = cluster_id
        
        return clusters
