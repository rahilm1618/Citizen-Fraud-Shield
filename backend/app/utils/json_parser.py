import json
import re

def extract_json_from_text(text: str) -> dict | list:
    """
    Attempts to extract JSON from a string that might contain markdown formatting
    (e.g. ```json ... ```) or other preamble.
    """
    text = text.strip()
    
    # Fast path if it's already clean JSON
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
    # Try to find JSON inside markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass
            
    # Fallback: try to find the first { or [ and last } or ]
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    
    # If both {} and [] exist, figure out which one encloses the other at the root
    if first_brace != -1 and last_brace != -1:
        if first_bracket == -1 or (first_brace < first_bracket and last_brace > last_bracket):
            try:
                return json.loads(text[first_brace:last_brace+1])
            except json.JSONDecodeError:
                pass
                
    if first_bracket != -1 and last_bracket != -1:
        try:
            return json.loads(text[first_bracket:last_bracket+1])
        except json.JSONDecodeError:
            pass
            
    # Ultimate fallback, just raise the standard error
    return json.loads(text)
