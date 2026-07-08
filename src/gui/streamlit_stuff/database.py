from src.gui.services.db_service import get_segment_ids

def get_placemarks(db_path: str) -> list[str]:
    """Get list of placemarks from database."""
    try:
        placemarks = get_segment_ids(db_path)
        return placemarks
    except Exception as e:
        print(f"Error loading database: {e}")
        return []