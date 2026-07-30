from metavision_sdk_stream import Camera, CameraStreamSlicer

def main():
    # Load first available camera or from a RAW file if preferred
    # camera = Camera.from_file("path/to/file.raw")
    try:
        camera = Camera.from_first_available()
    except Exception as e:
        print(f"Error: {e}. Ensure a camera is connected.")
        return

    # Use a slicer to retrieve events from the camera stream
    slicer = CameraStreamSlicer(camera.move())
    
    print("Streaming events... Press Ctrl+C to stop.")
    for _ in slicer:
        # Each iteration represents a 'slice' of events being available
        print("Events are available!")

if __name__ == "__main__":
    main()
