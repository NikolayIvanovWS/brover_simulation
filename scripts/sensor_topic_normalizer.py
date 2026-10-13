#!/usr/bin/env python3
"""Publish stable public sensor topics and encode camera frames once."""
import copy
import math
import cv2
from cv_bridge import CvBridge, CvBridgeError
import rclpy
from sensor_msgs.msg import CameraInfo, CompressedImage, Image, Imu, LaserScan
from rclpy.node import Node
from rcl_interfaces.msg import ParameterDescriptor


class SensorTopicNormalizer(Node):
    def __init__(self, **kwargs):
        super().__init__("sensor_topic_normalizer", **kwargs)
        readonly = ParameterDescriptor(read_only=True)
        self.horizontal_fov = float(self.declare_parameter(
            "camera_horizontal_fov", 1.047, readonly).value)
        self.jpeg_quality = int(self.declare_parameter("jpeg_quality", 85, readonly).value)
        if not math.isfinite(self.horizontal_fov) or not 0 < self.horizontal_fov < math.pi:
            raise ValueError("camera_horizontal_fov must be between 0 and pi")
        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100")
        self.cv_bridge = CvBridge()
        self.scan_publisher = self.create_publisher(LaserScan, "/scan", 10)
        self.imu_publisher = self.create_publisher(Imu, "/bhi360/imu", 10)
        self.image_publisher = self.create_publisher(Image, "/camera1/image_raw", 10)
        self.camera_info_publisher = self.create_publisher(CameraInfo, "/camera1/camera_info", 10)
        self.compressed_publisher = self.create_publisher(CompressedImage, "/image_raw/compressed", 10)
        self.create_subscription(LaserScan, "/_brover_simulation/scan", self.scan_callback, 10)
        self.create_subscription(Imu, "/_brover_simulation/imu", self.imu_callback, 10)
        # Keep only the latest incoming image if JPEG encoding cannot keep up.
        self.create_subscription(Image, "/_brover_simulation/camera1/image_raw", self.image_callback, 1)

    def imu_callback(self, msg):
        msg.header.frame_id = "imu_link"
        self.imu_publisher.publish(msg)

    def scan_callback(self, msg):
        msg.header.frame_id = "lidar_link"
        self.scan_publisher.publish(msg)

    def image_callback(self, raw):
        msg = copy.deepcopy(raw)
        msg.header.frame_id = "front_camera_optical_frame"
        info = self.make_camera_info(msg)
        self.image_publisher.publish(msg)
        self.camera_info_publisher.publish(info)
        try:
            compressed = self.make_compressed(msg)
        except (CvBridgeError, cv2.error, ValueError) as error:
            self.get_logger().warning("Camera JPEG encoding failed: "+str(error),
                                      throttle_duration_sec=5.0)
            return
        self.compressed_publisher.publish(compressed)

    def make_compressed(self, image_msg):
        frame = self.cv_bridge.imgmsg_to_cv2(image_msg, desired_encoding="bgr8")
        success, data = cv2.imencode(".jpg", frame,
                                    [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not success:
            raise ValueError("JPEG encoder returned no image")
        msg = CompressedImage()
        msg.header = copy.deepcopy(image_msg.header)
        msg.format = image_msg.encoding+"; jpeg compressed bgr8"
        msg.data = data.tobytes()
        return msg

    def make_camera_info(self, image_msg):
        width, height = image_msg.width, image_msg.height
        focal = width/(2.0*math.tan(self.horizontal_fov/2.0))
        cx, cy = (width-1.0)/2.0, (height-1.0)/2.0
        msg = CameraInfo()
        msg.header = copy.deepcopy(image_msg.header)
        msg.width, msg.height = width, height
        msg.distortion_model = "plumb_bob"
        msg.d = [0.0]*5
        msg.k = [focal,0.0,cx,0.0,focal,cy,0.0,0.0,1.0]
        msg.r = [1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0]
        msg.p = [focal,0.0,cx,0.0,0.0,focal,cy,0.0,0.0,0.0,1.0,0.0]
        return msg


def main(args=None):
    rclpy.init(args=args)
    node = SensorTopicNormalizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
