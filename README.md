# Eqaab-Drone
An autonomous security and tracking drone system utilizing YOLOv8 for real-time threat detection and automated aerial surveillance.


# Project Overview: Eqaab (عقـــاب)
Eqaab is an intelligent, autonomous drone platform designed for high-stakes security environments. By merging Computer Vision with autonomous flight controllers, the system can identify, lock onto, and track specific targets without manual pilot intervention.

Technical Stack

Core Logic: Python / C++ (ArduPilot/PX4)
AI/Vision: YOLOv8 (Custom trained for security personnel/vehicle detection)
Communication: MAVLink protocol for GCS (Ground Control Station) integration.
Hardware Interface: Raspberry Pi / Jetson Nano (On-board processing).

Key Features:
- Autonomous Mission Planning: Pre-defined patrol routes with dynamic obstacle avoidance.
- Real-Time Object Tracking: Low-latency inference using specialized CV models.
- Secure Telemetry: End-to-end encrypted data transmission from drone to base.
