import os
import sys
import time
import json

# Background worker for processing tasks
# This runs as a separate process to handle long-running tasks like PDF processing

TASK_QUEUE_FILE = '/tmp/task_queue.json'

def process_task(task):
    """Process a single task"""
    task_type = task.get('type')
    task_id = task.get('id')
    
    print(f"Processing task {task_id}: {task_type}")
    
    if task_type == 'pdf_processing':
        # Import here to avoid circular imports
        from logic_engine import LogicEngine
        from app import DB_PATH
        
        file_path = task.get('file_path')
        profile = task.get('profile')
        
        engine = LogicEngine(DB_PATH)
        
        try:
            engine.load_file(file_path, profile_name=profile)
            # ... additional processing
            print(f"Task {task_id} completed successfully")
            return {"status": "success", "task_id": task_id}
        except Exception as e:
            print(f"Task {task_id} failed: {e}")
            return {"status": "failed", "task_id": task_id, "error": str(e)}
        finally:
            engine.close()
    
    return {"status": "unknown_task_type"}

def worker_loop():
    """Main worker loop - polls for tasks"""
    print("Background worker started...")
    
    while True:
        try:
            # Check for tasks
            if os.path.exists(TASK_QUEUE_FILE):
                with open(TASK_QUEUE_FILE, 'r') as f:
                    tasks = json.load(f)
                
                # Process first task
                if tasks:
                    task = tasks.pop(0)
                    with open(TASK_QUEUE_FILE, 'w') as f:
                        json.dump(tasks, f)
                    
                    result = process_task(task)
                    print(f"Result: {result}")
            
            time.sleep(5)  # Poll every 5 seconds
            
        except KeyboardInterrupt:
            print("Worker stopped")
            break
        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    worker_loop()
