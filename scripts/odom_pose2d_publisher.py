#!/usr/bin/env python3
"""Publish one consistent planar odometry origin for Odometry, Pose2D and TF."""
import copy
import math
import rclpy
from geometry_msgs.msg import Pose2D, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_srvs.srv import Empty
from tf2_ros import TransformBroadcaster


def quaternion_to_yaw(x, y, z, w):
    return math.atan2(2.0 * (w*z + x*y), 1.0 - 2.0 * (y*y + z*z))


def rotate_covariance(covariance, yaw):
    """Rotate parent-frame position/orientation covariance, including cross terms."""
    c, s = math.cos(yaw), math.sin(yaw)
    rotation = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    matrix = [[0.0]*6 for _ in range(6)]
    for offset in (0, 3):
        for i in range(3):
            for j in range(3):
                matrix[offset+i][offset+j] = rotation[i][j]
    return [sum(matrix[i][a]*covariance[a*6+b]*matrix[j][b]
                for a in range(6) for b in range(6))
            for i in range(6) for j in range(6)]


def relative_odometry(raw, origin):
    """Rebase x/y and heading; keep z and child-frame velocities."""
    result = copy.deepcopy(raw)
    ox, oy, heading = origin
    p = result.pose.pose.position
    dx, dy = p.x-ox, p.y-oy
    c, s = math.cos(heading), math.sin(heading)
    p.x, p.y = c*dx+s*dy, -s*dx+c*dy
    q = result.pose.pose.orientation
    # Left multiply by inverse origin yaw, preserving roll/pitch.
    sh, ch = math.sin(-heading/2), math.cos(-heading/2)
    x, y, z, w = q.x, q.y, q.z, q.w
    q.x, q.y = ch*x-sh*y, ch*y+sh*x
    q.z, q.w = ch*z+sh*w, ch*w-sh*z
    result.pose.covariance = rotate_covariance(raw.pose.covariance, -heading)
    result.header.frame_id = 'odom'
    result.child_frame_id = 'base_footprint'
    return result


class OdomPose2DPublisher(Node):
    def __init__(self):
        super().__init__('odom_pose2d_publisher')
        self.publisher = self.create_publisher(Pose2D, '/odom_pose2d', 10)
        self.odom_publisher = self.create_publisher(Odometry, '/odom', 10)
        self.broadcaster = TransformBroadcaster(self)
        self.origin = (0.0, 0.0, 0.0)
        self.latest = None
        self.last_stamp = None
        self.reset_service = None
        self.subscription = self.create_subscription(
            Odometry, '/_brover_simulation/odom', self.odom_callback, 10)

    def publish_state(self, raw):
        odom = relative_odometry(raw, self.origin)
        p, q = odom.pose.pose.position, odom.pose.pose.orientation
        pose = Pose2D()
        pose.x, pose.y = p.x, p.y
        pose.theta = quaternion_to_yaw(q.x, q.y, q.z, q.w)
        transform = TransformStamped()
        transform.header = copy.deepcopy(odom.header)
        transform.child_frame_id = odom.child_frame_id
        transform.transform.translation.x = p.x
        transform.transform.translation.y = p.y
        transform.transform.translation.z = p.z
        transform.transform.rotation = copy.deepcopy(q)
        self.odom_publisher.publish(odom)
        self.publisher.publish(pose)
        self.broadcaster.sendTransform(transform)

    def odom_callback(self, msg):
        stamp = msg.header.stamp.sec*1_000_000_000 + msg.header.stamp.nanosec
        if self.last_stamp is not None and stamp < self.last_stamp:
            self.origin = (0.0, 0.0, 0.0)
            self.get_logger().warning('Odometry time moved backwards; reset origin discarded')
        self.last_stamp = stamp
        self.latest = copy.deepcopy(msg)
        self.publish_state(msg)
        # No misleading successful reset before the first odometry sample.
        if self.reset_service is None:
            self.reset_service = self.create_service(Empty, '/odom/reset', self.reset_callback)

    def reset_callback(self, request, response):
        p, q = self.latest.pose.pose.position, self.latest.pose.pose.orientation
        self.origin = (p.x, p.y, quaternion_to_yaw(q.x, q.y, q.z, q.w))
        self.publish_state(self.latest)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = OdomPose2DPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()