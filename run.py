import sys
from app import app, backend
from argparse import ArgumentParser
import os
import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

def on_created(event):
    print(f"{event.src_path} has been created!")
    backend.check_for_changes()

def on_deleted(event):
    print(f"deleted {event.src_path}!")
    backend.check_for_changes()

def on_modified(event):
    print(f"{event.src_path} has been modified")
    backend.check_for_changes()

def on_moved(event):
    print(f"moved {event.src_path} to {event.dest_path}")
    backend.check_for_changes()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--data', default="data/OOgle")
    args = parser.parse_args()
    backend.initialize(args.data)
    app.json_encoder = backend.MyEncoder
    my_event_handler = PatternMatchingEventHandler(["*"], None, False, True)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_event_handler.on_modified = on_modified
    my_event_handler.on_moved = on_moved
    go_recursively = True
    my_observer = Observer()
    my_observer.schedule(my_event_handler, os.path.join("data", "OOgle", "sources"), recursive=True)
    my_observer.start()
    try:
        app.run(host='0.0.0.0')
    finally:
        my_observer.stop()
        my_observer.join()