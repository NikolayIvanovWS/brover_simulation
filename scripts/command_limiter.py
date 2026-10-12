#!/usr/bin/env python3
"""Limit planar commands before Gazebo; stop stale streams using steady time."""
import math
import time
import rclpy
from geometry_msgs.msg import Twist
from rosgraph_msgs.msg import Clock as ClockMessage
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import ParameterDescriptor

DEFAULTS = dict(wheel_radius=0.0625, track_width=0.42, max_linear_velocity=0.375,
                max_wheel_velocity=6.0, min_wheel_velocity=1.0, wheel_deadband=0.2,
                publish_period=0.05, cmd_vel_timeout=0.25)


def validate(p):
    if not all(math.isfinite(v) for v in p.values()):
        raise ValueError('Control parameters must be finite')
    for name in ('wheel_radius','track_width','max_linear_velocity',
                 'max_wheel_velocity','publish_period','cmd_vel_timeout'):
        if p[name] <= 0:
            raise ValueError(name+' must be positive')
    if not 0 <= p['wheel_deadband'] <= p['min_wheel_velocity'] <= p['max_wheel_velocity']:
        raise ValueError('Require 0 <= deadband <= min_wheel_velocity <= max_wheel_velocity')
    if p['publish_period'] >= p['cmd_vel_timeout']:
        raise ValueError('publish_period must be shorter than cmd_vel_timeout')


def limit_command(v, w, p):
    if not math.isfinite(v) or not math.isfinite(w):
        return 0.0, 0.0
    radius, half_track = p['wheel_radius'], p['track_width']/2
    maximum = p['max_wheel_velocity']
    vmax = min(p['max_linear_velocity'], maximum*radius)
    wmax = maximum*radius/half_track
    v, w = max(-vmax,min(vmax,v)), max(-wmax,min(wmax,w))
    left, right = (v-w*half_track)/radius, (v+w*half_track)/radius
    requested = max(abs(left),abs(right))
    if requested > maximum:
        left, right = left*maximum/requested, right*maximum/requested
    def limit_side(value):
        magnitude = abs(value)
        if magnitude == 0.0 or magnitude < p['wheel_deadband']:
            return 0.0
        return math.copysign(min(maximum,max(p['min_wheel_velocity'],magnitude)),value)
    left, right = limit_side(left), limit_side(right)
    # Convert logical side speeds back to Twist; no hardware motor sign convention.
    return radius*(left+right)/2, radius*(right-left)/(2*half_track)


class CommandLimiter(Node):
    def __init__(self):
        super().__init__('command_limiter')
        self.params = {}
        for name,value in DEFAULTS.items():
            self.params[name] = float(self.declare_parameter(
                name,value,ParameterDescriptor(read_only=True)).value)
        validate(self.params)
        self.publisher = self.create_publisher(Twist, '/_brover_simulation/cmd_vel', 1)
        self.subscription = self.create_subscription(Twist, '/cmd_vel', self.on_command, 1)
        self.create_subscription(ClockMessage, '/clock', self.on_clock, qos_profile_sensor_data)
        self.command, self.command_time = (0.0,0.0), None
        self.sim_time, self.clock_time = None, None
        self.timer = self.create_timer(self.params['publish_period'], self.on_timer,
                                      clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_clock(self, msg):
        stamp = msg.clock.sec*1000000000+msg.clock.nanosec
        if self.sim_time is not None and stamp < self.sim_time:
            self.command_time = None
        if stamp != self.sim_time:
            self.clock_time = time.monotonic()
        self.sim_time = stamp

    def clock_running(self, now):
        return self.clock_time is not None and now-self.clock_time <= self.params['cmd_vel_timeout']

    def on_command(self, msg):
        now = time.monotonic()
        if not self.clock_running(now):
            self.command_time = None
            return
        self.command = limit_command(msg.linear.x,msg.angular.z,self.params)
        self.command_time = now

    def on_timer(self):
        now = time.monotonic()
        if not self.clock_running(now):
            self.command_time = None
        active = self.command_time is not None and now-self.command_time <= self.params['cmd_vel_timeout']
        v, w = self.command if active else (0.0,0.0)
        self.publish(v,w)

    def publish(self, v=0.0,w=0.0):
        msg = Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = CommandLimiter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.publish()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=='__main__':
    main()