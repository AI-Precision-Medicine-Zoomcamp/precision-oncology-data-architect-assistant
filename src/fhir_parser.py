"""
FHIR Bundle Parser for Oncology Data.

Parses FHIR JSON bundles into structured text chunks suitable for
embedding and ingestion. Includes specialised extraction for NSCLC
and EGFR variants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from loguru import logger

from src.models import OncologyDocument


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Resource types we know how to render to text
PARSABLE_RESOURCE_TYPES = frozenset({
    "Patient",
    "Condition",
    "Observation",
    "MedicationRequest",
    "DiagnosticReport",
    "Specimen",
    "Encounter",
    "Practitioner",
    "Organization",
    "Procedure",
    "MedicationAdministration",
    "Immunization",
})

# Oncology-relevant LOINC / SNOMED codes we specifically handle
EGFR_RELATED_CODES = {
    "69548-6",   # Genetic variant assessment
    "48018-6",   # Gene studied
    "48019-4",   # Gene variant type
    "48002-0",   # Genomic DNA change (c.HGVS)
    "48004-6",   # Genomic protein change (p.HGVS)
}

NSCLC_SNOMED_CODES = {
    "254637007",  # Non-small cell lung cancer
    "115215501",  # Adenocarcinoma of lung
    "431759002",  # Squamous cell carcinoma of lung
    "447812008",  # Large cell carcinoma of lung
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_text(value: Any, default: str = "") -> str:
    """Safely extract text from a FHIR ``code`` / ``CodeableConcept`` field."""
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Prefer "text", then first coding.display, then first coding.code
        if value.get("text"):
            return value["text"]
        codings = value.get("coding", [])
        if codings:
            return codings[0].get("display") or codings[0].get("code", default)
    return default


def _codings_to_str(coding_list: Any) -> str:
    """Render a list of codings to a compact string."""
    if not coding_list:
        return ""
    if isinstance(coding_list, dict):
        coding_list = [coding_list]
    parts = []
    for c in coding_list:
        sys = c.get("system", "").split("/")[-1] if c.get("system") else ""
        code = c.get("code", "")
        display = c.get("display", "")
        if display:
            parts.append(f"{display} ({sys}:{code})" if sys else display)
        else:
            parts.append(f"{sys}:{code}" if sys else code)
    return "; ".join(parts)


def _extract_narrative(resource: Dict[str, Any]) -> str:
    """Return the ``resource.text.div`` (narrative) as plain text."""
    text = resource.get("text", {})
    div: Optional[str] = text.get("div")
    if div:
        # Strip HTML tags lightly
        import re
        clean = re.sub(r"<[^>]+>", "", div)
        return clean.strip()
    return ""


# ---------------------------------------------------------------------------
# FhirResourceParser
# ---------------------------------------------------------------------------

class FhirResourceParser:
    """Parse a single FHIR resource dict into human-readable text."""

    def parse(self, resource: Dict[str, Any]) -> str:
        """
        Convert *resource* to a structured text representation.

        Delegates to ``_parse_<resourceType>`` if available, otherwise falls
        back to a generic key-value renderer.
        """
        resource_type = resource.get("resourceType", "Unknown")
        parser = getattr(self, f"_parse_{resource_type}", None)
        if parser is None:
            parser = self._parse_generic
        try:
            return parser(resource)
        except Exception as exc:
            logger.warning(
                "Failed to parse {} resource {}: {}",
                resource_type,
                resource.get("id", "<no-id>"),
                exc,
            )
            return self._parse_generic(resource)

    # -- Resource-type-specific parsers ------------------------------------

    def _parse_Patient(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== PATIENT ===")
        for name in r.get("name", []):
            given = " ".join(name.get("given", []))
            family = name.get("family", "")
            lines.append(f"Name: {given} {family}".strip())
        lines.append(f"Gender: {r.get('gender', 'unknown')}")
        lines.append(f"DOB: {r.get('birthDate', 'unknown')}")
        lines.append(f"Deceased: {r.get('deceasedBoolean', r.get('deceasedDateTime', 'no'))}")
        return "\n".join(lines)

    def _parse_Condition(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== CONDITION ===")
        code = _safe_text(r.get("code"))
        lines.append(f"Diagnosis: {code}")
        if r.get("clinicalStatus"):
            lines.append(f"Clinical Status: {_safe_text(r['clinicalStatus'])}")
        if r.get("verificationStatus"):
            lines.append(f"Verification: {_safe_text(r['verificationStatus'])}")
        if r.get("onsetDateTime"):
            lines.append(f"Onset: {r['onsetDateTime']}")
        body_sites = r.get("bodySite", [])
        for site in body_sites:
            lines.append(f"Body Site: {_safe_text(site)}")
        # Check for NSCLC relevance
        codings = r.get("code", {}).get("coding", [])
        for c in codings:
            if c.get("code") in NSCLC_SNOMED_CODES:
                lines.append(f"[Oncology] NSCLC-associated condition: {c.get('display', c['code'])}")
                break
        return "\n".join(lines)

    def _parse_Observation(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== OBSERVATION ===")
        obs_code = _safe_text(r.get("code"))
        lines.append(f"Test: {obs_code}")
        lines.append(f"Status: {r.get('status', 'unknown')}")
        # Value
        value = r.get("valueCodeableConcept") or r.get("valueQuantity") or r.get("valueString")
        if isinstance(value, dict):
            lines.append(f"Value: {_safe_text(value)}")
            # Check for numeric value
            if "value" in value and "unit" in value:
                lines.append(f"Value: {value['value']} {value['unit']}")
        elif value is not None:
            lines.append(f"Value: {value}")
        # Interpretation
        for interp in r.get("interpretation", []):
            lines.append(f"Interpretation: {_safe_text(interp)}")
        # Components (e.g. genetic variant details)
        for comp in r.get("component", []):
            comp_code = _safe_text(comp.get("code"))
            comp_val = _safe_text(comp.get("valueCodeableConcept")) or \
                       comp.get("valueString", "")
            if comp_val:
                lines.append(f"  {comp_code}: {comp_val}")
        # EGFR-specific highlighting
        codings = r.get("code", {}).get("coding", [])
        for c in codings:
            if c.get("code") in EGFR_RELATED_CODES:
                lines.append(f"[Molecular] EGFR-related observation: {c.get('display', c['code'])}")
        value_text = _safe_text(r.get("valueCodeableConcept"))
        if "egfr" in value_text.lower() or "exon 19" in value_text.lower():
            lines.append("[Molecular] EGFR variant detected in this observation")
        return "\n".join(lines)

    def _parse_MedicationRequest(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== MEDICATION REQUEST ===")
        med = _safe_text(r.get("medicationCodeableConcept"))
        lines.append(f"Medication: {med}")
        lines.append(f"Status: {r.get('status', 'unknown')}")
        lines.append(f"Intent: {r.get('intent', 'unknown')}")
        if r.get("authoredOn"):
            lines.append(f"Authored: {r['authoredOn']}")
        for reason in r.get("reasonCode", []):
            lines.append(f"Reason: {_safe_text(reason)}")
        return "\n".join(lines)

    def _parse_DiagnosticReport(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== DIAGNOSTIC REPORT ===")
        code = _safe_text(r.get("code"))
        lines.append(f"Report: {code}")
        lines.append(f"Status: {r.get('status', 'unknown')}")
        if r.get("effectiveDateTime"):
            lines.append(f"Effective Date: {r['effectiveDateTime']}")
        if r.get("issued"):
            lines.append(f"Issued: {r['issued']}")
        for conc in r.get("conclusionCode", []):
            lines.append(f"Conclusion: {_safe_text(conc)}")
        if r.get("conclusion"):
            lines.append(f"Conclusion Text: {r['conclusion']}")
        # References to results
        for result_ref in r.get("result", []):
            lines.append(f"Result reference: {result_ref.get('reference', '')}")
        for form in r.get("presentedForm", []):
            if form.get("title"):
                lines.append(f"Attachment: {form['title']} ({form.get('contentType', 'unknown')})")
        return "\n".join(lines)

    def _parse_Specimen(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== SPECIMEN ===")
        spec_type = _safe_text(r.get("type"))
        lines.append(f"Type: {spec_type}")
        collection = r.get("collection", {})
        if collection.get("collectedDateTime"):
            lines.append(f"Collected: {collection['collectedDateTime']}")
        method = collection.get("method")
        if method:
            lines.append(f"Method: {_safe_text(method)}")
        body_site = collection.get("bodySite")
        if body_site:
            lines.append(f"Body Site: {_safe_text(body_site)}")
        return "\n".join(lines)

    def _parse_Encounter(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== ENCOUNTER ===")
        lines.append(f"Status: {r.get('status', 'unknown')}")
        cls = r.get("class", {})
        lines.append(f"Class: {cls.get('display', cls.get('code', 'unknown'))}")
        for t in r.get("type", []):
            lines.append(f"Type: {_safe_text(t)}")
        period = r.get("period", {})
        if period.get("start"):
            lines.append(f"Period: {period['start']} → {period.get('end', 'ongoing')}")
        return "\n".join(lines)

    def _parse_Practitioner(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== PRACTITIONER ===")
        for name in r.get("name", []):
            given = " ".join(name.get("given", []))
            family = name.get("family", "")
            lines.append(f"Name: {given} {family}".strip())
        for qual in r.get("qualification", []):
            lines.append(f"Qualification: {_safe_text(qual.get('code'))}")
        return "\n".join(lines)

    def _parse_Organization(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== ORGANIZATION ===")
        lines.append(f"Name: {r.get('name', 'unknown')}")
        for identifier in r.get("identifier", []):
            system = identifier.get("system", "")
            value = identifier.get("value", "")
            if system and value:
                lines.append(f"ID: {system} = {value}")
        return "\n".join(lines)

    def _parse_Procedure(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== PROCEDURE ===")
        code = _safe_text(r.get("code"))
        lines.append(f"Procedure: {code}")
        lines.append(f"Status: {r.get('status', 'unknown')}")
        if r.get("performedDateTime"):
            lines.append(f"Performed: {r['performedDateTime']}")
        return "\n".join(lines)

    def _parse_MedicationAdministration(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== MEDICATION ADMINISTRATION ===")
        med = _safe_text(r.get("medicationCodeableConcept"))
        lines.append(f"Medication: {med}")
        lines.append(f"Status: {r.get('status', 'unknown')}")
        if r.get("effectiveDateTime"):
            lines.append(f"Administered: {r['effectiveDateTime']}")
        return "\n".join(lines)

    def _parse_Immunization(self, r: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("=== IMMUNIZATION ===")
        vaccine = _safe_text(r.get("vaccineCode"))
        lines.append(f"Vaccine: {vaccine}")
        lines.append(f"Status: {r.get('status', 'unknown')}")
        if r.get("occurrenceDateTime"):
            lines.append(f"Date: {r['occurrenceDateTime']}")
        return "\n".join(lines)

    def _parse_generic(self, r: Dict[str, Any]) -> str:
        """Fallback: render all top-level key-value pairs."""
        lines: List[str] = []
        rtype = r.get("resourceType", "Resource")
        rid = r.get("id", "")
        lines.append(f"=== {rtype} ({rid}) ===")
        # Skip meta, text, and large nested structures
        skip_keys = {"meta", "text", "identifier"}
        for key, value in r.items():
            if key in skip_keys:
                continue
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"{key}: {value}")
            elif isinstance(value, list) and len(value) < 10:
                for item in value:
                    if isinstance(item, dict) and "coding" in item:
                        lines.append(f"{key}: {_codings_to_str(item.get('coding', []))}")
                    elif isinstance(item, dict) and "reference" in item:
                        lines.append(f"{key}: {item['reference']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# FhirBundleParser
# ---------------------------------------------------------------------------

class FhirBundleParser:
    """Parse a FHIR ``Bundle`` (collection) into a list of ``OncologyDocument``."""

    def __init__(self, resource_parser: Optional[FhirResourceParser] = None) -> None:
        self._resource_parser = resource_parser or FhirResourceParser()

    def parse_bundle(
        self,
        bundle: Union[str, Path, Dict[str, Any]],
        source: Optional[str] = None,
    ) -> List[OncologyDocument]:
        """
        Parse a FHIR bundle into a list of ``OncologyDocument``.

        Parameters
        ----------
        bundle:
            A FHIR JSON string, ``Path`` to a JSON file, or a parsed dict.
        source:
            Optional source identifier (defaults to bundle id or file path).

        Returns
        -------
        List[OncologyDocument]
            One document per resource in the bundle, plus an overall summary.
        """
        raw = self._load_bundle(bundle)
        if source is None:
            source = raw.get("id", "unknown-bundle")

        entries: List[Dict[str, Any]] = raw.get("entry", [])
        if not entries:
            logger.warning("Bundle {} has no entries", source)
            return []

        documents: List[OncologyDocument] = []

        for entry in entries:
            resource = entry.get("resource")
            if not resource:
                continue

            resource_type = resource.get("resourceType", "Unknown")
            if resource_type not in PARSABLE_RESOURCE_TYPES:
                continue

            # Build metadata
            resource_id = resource.get("id", "")
            metadata: Dict[str, Any] = {
                "source": source,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "full_url": entry.get("fullUrl", ""),
            }

            # Extract narrative if available
            narrative = _extract_narrative(resource)
            parsed_text = self._resource_parser.parse(resource)

            # Combine: narrative first, then structured parse
            content_parts = []
            if narrative:
                content_parts.append(f"[Narrative]\n{narrative}")
            content_parts.append(parsed_text)
            content = "\n\n".join(content_parts)

            # Add NSCLC / EGFR tags in metadata
            self._enrich_oncology_metadata(resource, metadata)

            # Add patient reference if present
            subject = resource.get("subject")
            if subject:
                metadata["subject_ref"] = subject.get("reference", "")

            doc = OncologyDocument(
                source=f"{source}/{resource_type}/{resource_id}",
                content=content,
                metadata=metadata,
            )
            documents.append(doc)

        # Optionally add a bundle-level summary document
        summary = self._build_summary(raw, source, documents)
        if summary:
            documents.append(summary)

        logger.info(
            "Parsed bundle '{}': {} resources → {} documents",
            source,
            len(entries),
            len(documents),
        )
        return documents

    def parse_all_in_directory(
        self,
        directory: Path,
        glob_pattern: str = "*.json",
    ) -> Generator[Tuple[Path, List[OncologyDocument]], None, None]:
        """
        Yield ``(file_path, documents)`` for every FHIR bundle JSON file in
        *directory* matching *glob_pattern*.
        """
        dir_path = Path(directory)
        if not dir_path.is_dir():
            logger.warning("Directory does not exist: {}", dir_path)
            return

        for fpath in sorted(dir_path.glob(glob_pattern)):
            try:
                docs = self.parse_bundle(fpath, source=fpath.name)
                yield fpath, docs
            except Exception as exc:
                logger.error("Failed to parse {}: {}", fpath, exc)

    # -- Internal helpers --------------------------------------------------

    @staticmethod
    def _load_bundle(bundle: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(bundle, dict):
            return bundle
        if isinstance(bundle, Path):
            with bundle.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        # string: assume JSON
        return json.loads(bundle)

    @staticmethod
    def _enrich_oncology_metadata(
        resource: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:
        """Add oncology-specific tags to *metadata*."""
        resource_type = resource.get("resourceType")
        code_field = resource.get("code", {})
        codings = code_field.get("coding", []) if isinstance(code_field, dict) else []

        # Check for NSCLC
        for c in codings:
            if c.get("code") in NSCLC_SNOMED_CODES:
                metadata["tumor_type"] = "NSCLC"
                metadata["oncology_relevant"] = True
                break

        # Check for EGFR / molecular markers
        if resource_type == "Observation":
            for c in codings:
                if c.get("code") in EGFR_RELATED_CODES:
                    metadata["molecular_marker"] = True
                    metadata["oncology_relevant"] = True
                    break
            value_text = _safe_text(resource.get("valueCodeableConcept"))
            if value_text:
                low = value_text.lower()
                if "egfr" in low or "exon 19" in low:
                    metadata["molecular_marker"] = True
                    metadata["oncology_relevant"] = True
                    metadata["gene"] = "EGFR"

    @staticmethod
    def _build_summary(
        bundle: Dict[str, Any],
        source: str,
        documents: List[OncologyDocument],
    ) -> Optional[OncologyDocument]:
        """Create a bundle-level summary document."""
        resource_types = {}
        for doc in documents:
            rt = doc.metadata.get("resource_type", "Unknown")
            resource_types[rt] = resource_types.get(rt, 0) + 1

        lines = [
            "=== FHIR BUNDLE SUMMARY ===",
            f"Bundle ID: {bundle.get('id', 'unknown')}",
            f"Type: {bundle.get('type', 'unknown')}",
            f"Timestamp: {bundle.get('timestamp', 'unknown')}",
            f"Total entries: {len(bundle.get('entry', []))}",
            f"Parsed resources: {len(documents)}",
            "Resource type breakdown:",
        ]
        for rt, count in sorted(resource_types.items()):
            lines.append(f"  - {rt}: {count}")

        # Check for oncology relevance across the bundle
        oncology_count = sum(
            1 for d in documents if d.metadata.get("oncology_relevant")
        )
        if oncology_count > 0:
            lines.append(f"Oncology-relevant resources: {oncology_count}")
            lines.append("[Oncology] Bundle contains cancer-related data")

        return OncologyDocument(
            source=f"{source}/_bundle_summary",
            content="\n".join(lines),
            metadata={
                "source": source,
                "resource_type": "BundleSummary",
                "bundle_id": bundle.get("id"),
                "resource_counts": resource_types,
                "oncology_relevant": oncology_count > 0,
            },
        )


# Convenience function
def parse_fhir_bundle(
    bundle: Union[str, Path, Dict[str, Any]],
    source: Optional[str] = None,
) -> List[OncologyDocument]:
    """Shortcut to parse a FHIR bundle in one call."""
    parser = FhirBundleParser()
    return parser.parse_bundle(bundle, source=source)