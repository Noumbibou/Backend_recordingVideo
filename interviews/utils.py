# helper functions for remote url validation/download
import requests
import tempfile
import os

def get_remote_content_length(url, timeout=5):
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        cl = r.headers.get("Content-Length")
        return int(cl) if cl is not None else None
    except Exception:
        return None

def download_with_limit(url, max_bytes, dest_path, timeout=10):
    """
    Stream-download url to dest_path, abort if size exceeds max_bytes.
    Raises ValueError if too large or requests.exceptions on HTTP errors.
    """
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        total = 0
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    # cleanup and abort
                    f.close()
                    try:
                        os.remove(dest_path)
                    except Exception:
                        pass
                    raise ValueError(f"File too large: {total} bytes (limit {max_bytes})")
                f.write(chunk)
    return total