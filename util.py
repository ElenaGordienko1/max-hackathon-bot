from datetime import datetime
import json
import os

def clean_expired_events(events_file_path):
    if not os.path.exists(events_file_path):
        return 0

    try:
        with open(events_file_path, "r", encoding="utf-8") as f:
            events = json.load(f)
        
        if not isinstance(events, list):
            return 0

        current_time = datetime.now()
        updated_events = []
        deleted_count = 0

        for event in events:
            time_str = event.get("time", "")
            
            try:
                event_date = datetime.strptime(time_str, "%d.%m.%Y %H:%M")
                if event_date >= current_time:
                    updated_events.append(event)
                else:
                    deleted_count += 1
            except (ValueError, TypeError):
                updated_events.append(event)
        if deleted_count > 0:
            with open(events_file_path, "w", encoding="utf-8") as f:
                json.dump(updated_events, f, ensure_ascii=False, indent=4)
        
        return deleted_count

    except Exception as e:
        print(f"                                : {e}")
        return 0
