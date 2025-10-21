#!/usr/bin/env python3
"""
Test script for MemoryManager
Verifies buffer calculation and system memory detection
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory_manager import MemoryManager

def main():
    print("=" * 70)
    print("Memory Manager Test")
    print("=" * 70)
    print()

    # Create MemoryManager instance
    print("Creating MemoryManager...")
    manager = MemoryManager(
        max_ram_usage_percent=70,
        frame_width=1920,
        frame_height=1080
    )
    print()

    # Get system memory info
    print("-" * 70)
    print("System Memory Information:")
    print("-" * 70)
    mem_info = manager.get_system_memory_info()
    print(f"Total RAM:     {mem_info['total_mb']:>10.1f} MB")
    print(f"Available RAM: {mem_info['available_mb']:>10.1f} MB")
    print(f"Used RAM:      {mem_info['used_mb']:>10.1f} MB")
    print(f"Usage:         {mem_info['percent']:>10.1f}%")
    print()

    # Calculate optimal buffers
    print("-" * 70)
    print("Optimal Buffer Sizes:")
    print("-" * 70)
    buffers = manager.calculate_optimal_buffers()

    # Calculate actual memory usage
    frame_size_mb = manager.frame_size_bytes / (1024**2)
    frame_buffer_mb = (buffers['frame_buffer_size'] * manager.frame_size_bytes) / (1024**2)
    recording_buffer_mb = (buffers['recording_queue_size'] * manager.frame_size_bytes) / (1024**2)
    udp_buffer_mb = buffers['udp_buffer_size'] / (1024**2)

    print(f"Frame size:            {frame_size_mb:>10.2f} MB per frame")
    print(f"Frame buffer:          {buffers['frame_buffer_size']:>10,} frames ({frame_buffer_mb:>10.1f} MB)")
    print(f"Recording queue:       {buffers['recording_queue_size']:>10,} frames ({recording_buffer_mb:>10.1f} MB)")
    print(f"UDP buffer:            {buffers['udp_buffer_size']:>10,} bytes ({udp_buffer_mb:>10.1f} MB)")
    print(f"Total allocation:      {buffers['total_memory_mb']:>10.1f} MB")
    print(f"% of available RAM:    {(buffers['total_memory_mb'] / mem_info['available_mb']) * 100:>10.1f}%")
    print()

    # Check memory health
    print("-" * 70)
    print("Memory Health Check:")
    print("-" * 70)
    is_healthy, message = manager.check_memory_health()
    status = "[OK] HEALTHY" if is_healthy else "[!!] UNHEALTHY"
    print(f"Status: {status}")
    print(f"Message: {message}")
    print()

    # Calculate buffer duration at 30 FPS
    print("-" * 70)
    print("Buffer Duration at 30 FPS:")
    print("-" * 70)
    fps = 30
    frame_buffer_duration = buffers['frame_buffer_size'] / fps
    recording_buffer_duration = buffers['recording_queue_size'] / fps
    print(f"Frame buffer:    {frame_buffer_duration:>10.1f} seconds")
    print(f"Recording queue: {recording_buffer_duration:>10.1f} seconds")
    print()

    # Test different resolutions
    print("-" * 70)
    print("Comparison Across Resolutions:")
    print("-" * 70)
    resolutions = [
        (640, 480, "SD"),
        (1280, 720, "HD"),
        (1920, 1080, "Full HD"),
        (3840, 2160, "4K UHD")
    ]

    print(f"{'Resolution':<15} {'Frame Size':<15} {'Frame Buffer':<20} {'Duration@30fps':<15}")
    print("-" * 70)

    for width, height, label in resolutions:
        test_manager = MemoryManager(
            max_ram_usage_percent=70,
            frame_width=width,
            frame_height=height
        )
        test_buffers = test_manager.calculate_optimal_buffers()
        test_frame_size = test_manager.frame_size_bytes / (1024**2)
        test_duration = test_buffers['frame_buffer_size'] / 30

        print(f"{width}x{height} ({label}:<6) {test_frame_size:>6.2f} MB      "
              f"{test_buffers['frame_buffer_size']:>8,} frames      "
              f"{test_duration:>6.1f} sec")

    print()
    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"ERROR: Missing dependency - {e}")
        print("\nPlease install psutil:")
        print("  pip install psutil")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
