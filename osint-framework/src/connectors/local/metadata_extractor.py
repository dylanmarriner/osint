"""
Metadata Extractor — No API Keys Required

Extracts metadata from images (EXIF), PDFs, and other files.
All processing is done locally with no external calls.
"""

import logging
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    filename: str
    filepath: str
    file_size: int = 0
    file_type: str = ""
    created: Optional[str] = None
    modified: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    gps: Optional[Dict[str, float]] = None
    errors: List = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}


class MetadataExtractor:
    """Extract metadata from files locally."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.MetadataExtractor")

    def extract(self, filepath: str) -> FileMetadata:
        """Extract metadata from a file."""
        path = Path(filepath)
        meta = FileMetadata(
            filename=path.name,
            filepath=str(path),
            file_size=path.stat().st_size if path.exists() else 0,
        )

        if not path.exists():
            meta.errors.append("File not found")
            return meta

        suffix = path.suffix.lower()
        meta.file_type = suffix

        # File system metadata
        stat = path.stat()
        meta.modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
        meta.created = datetime.fromtimestamp(stat.st_ctime).isoformat()

        if suffix in ('.jpg', '.jpeg', '.png', '.tiff', '.heic'):
            self._extract_image_exif(path, meta)
        elif suffix == '.pdf':
            self._extract_pdf_metadata(path, meta)

        return meta

    def _extract_image_exif(self, path: Path, meta: FileMetadata):
        """Extract EXIF data from images."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS

            img = Image.open(str(path))
            exif_data = img._getexif()

            if not exif_data:
                return

            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                if isinstance(value, bytes):
                    continue
                try:
                    meta.metadata[tag_name] = str(value)
                except Exception:
                    pass

            # GPS extraction
            gps_info = exif_data.get(34853)  # GPSInfo tag
            if gps_info:
                gps = {}
                for gps_tag_id, gps_value in gps_info.items():
                    gps_tag_name = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
                    gps[gps_tag_name] = gps_value

                lat = self._convert_gps(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
                lon = self._convert_gps(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
                if lat is not None and lon is not None:
                    meta.gps = {"latitude": lat, "longitude": lon}

        except ImportError:
            meta.errors.append("Pillow not installed for EXIF extraction")
        except Exception as e:
            meta.errors.append(f"EXIF extraction failed: {str(e)}")

    def _convert_gps(self, coords, ref) -> Optional[float]:
        """Convert GPS coordinates to decimal degrees."""
        if not coords or not ref:
            return None
        try:
            degrees = float(coords[0])
            minutes = float(coords[1])
            seconds = float(coords[2])
            decimal = degrees + minutes / 60 + seconds / 3600
            if ref in ('S', 'W'):
                decimal = -decimal
            return round(decimal, 6)
        except (TypeError, IndexError, ValueError):
            return None

    def _extract_pdf_metadata(self, path: Path, meta: FileMetadata):
        """Extract metadata from PDF files."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(path))
            pdf_meta = doc.metadata
            if pdf_meta:
                for key, value in pdf_meta.items():
                    if value:
                        meta.metadata[key] = value
            meta.metadata["page_count"] = doc.page_count
            doc.close()

        except ImportError:
            # Fallback: try to read PDF header manually
            try:
                with open(str(path), "rb") as f:
                    header = f.read(1024).decode("latin-1", errors="replace")
                    if "/Author" in header:
                        meta.metadata["note"] = "PDF metadata present but PyMuPDF not installed for full extraction"
            except Exception:
                pass
        except Exception as e:
            meta.errors.append(f"PDF metadata extraction failed: {str(e)}")
