#!/usr/bin/env python3
"""Windowed keyboard control with release/focus-loss stop."""
import tkinter as tk
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

MOTION_KEYS = frozenset("wsad")


class KeyboardState:
    """No GUI/ROS dependencies in key combination and stop semantics."""
    def __init__(self):
        self.held = set()
        self.blocked = set()
        self.linear_speed = 0.25
        self.angular_speed = 0.8

    def press(self,key):
        if key in MOTION_KEYS and key not in self.blocked:
            self.held.add(key)

    def release(self,key):
        self.held.discard(key)
        self.blocked.discard(key)

    def stop(self):
        self.blocked.update(self.held)
        self.held.clear()

    def command(self):
        return (self.linear_speed*(int("w" in self.held)-int("s" in self.held)),
                self.angular_speed*(int("a" in self.held)-int("d" in self.held)))

    def adjust_speed(self,key):
        if key=="q":
            self.linear_speed = min(0.375,self.linear_speed+0.05)
        elif key=="z":
            self.linear_speed = max(0.07,self.linear_speed-0.05)
        elif key=="e":
            self.angular_speed = min(0.75/0.42,self.angular_speed+0.1)
        elif key=="c":
            self.angular_speed = max(0.3,self.angular_speed-0.1)


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__("keyboard_teleop")
        self.publisher = self.create_publisher(Twist,"/cmd_vel",1)
        self.state = KeyboardState()

    def publish_twist(self):
        msg = Twist()
        msg.linear.x,msg.angular.z = self.state.command()
        self.publisher.publish(msg)

    def stop(self):
        self.state.stop()
        if rclpy.ok():
            self.publish_twist()


class ControlWindow:
    def __init__(self,node):
        self.node = node
        self.root = tk.Tk()
        self.root.title("BRover — управление")
        self.root.geometry("440x290")
        self.closed = False
        self.keys_down = set()
        self.releases = {}
        self.speed = tk.StringVar()
        self.status = tk.StringVar(value="Удерживайте клавиши в этом окне")
        tk.Label(self.root,text="W / S — вперед / назад\nA / D — влево / вправо\n"
                 "Можно удерживать движение и поворот одновременно",justify="center").pack(pady=10)
        tk.Label(self.root,textvariable=self.speed).pack()
        tk.Label(self.root,text="Q / Z — линейная скорость\nE / C — угловая скорость").pack(pady=8)
        tk.Button(self.root,text="Стоп (X / Space)",command=self.stop).pack()
        tk.Label(self.root,textvariable=self.status,wraplength=420).pack(pady=12)
        tk.Label(self.root,text="Escape — закрыть. Потеря фокуса — остановка.").pack()
        self.root.bind("<KeyPress>",self.press)
        self.root.bind("<KeyRelease>",self.release)
        self.root.bind("<FocusOut>",lambda event:self.stop())
        self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.refresh()
        self.root.after(50,self.tick)

    def refresh(self):
        self.speed.set(f"Скорость: {self.node.state.linear_speed:.3f} м/с; "
                       f"{self.node.state.angular_speed:.3f} рад/с")

    def stop(self):
        self.node.stop()
        self.status.set("Остановлено. Отпустите клавиши перед новым движением.")

    def press(self,event):
        key = event.keysym.lower()
        pending = self.releases.pop(key,None)
        if pending is not None:
            self.root.after_cancel(pending)
        if key in self.keys_down:
            return
        self.keys_down.add(key)
        if key=="escape":
            self.close()
            return
        if key in ("x","space"):
            self.stop()
            return
        if key in MOTION_KEYS:
            self.node.state.press(key)
        else:
            self.node.state.adjust_speed(key)
        self.node.publish_twist()
        self.refresh()

    def release(self,event):
        key = event.keysym.lower()
        pending = self.releases.pop(key,None)
        if pending is not None:
            self.root.after_cancel(pending)
        # X11 auto-repeat may generate adjacent release/press pairs.
        # Defer release briefly and cancel it if the repeat press arrives.
        self.releases[key] = self.root.after(10,lambda:self.finish_release(key))

    def finish_release(self,key):
        self.releases.pop(key,None)
        self.keys_down.discard(key)
        self.node.state.release(key)
        if rclpy.ok():
            self.node.publish_twist()

    def tick(self):
        if self.closed:
            return
        if not rclpy.ok():
            self.close()
            return
        rclpy.spin_once(self.node,timeout_sec=0)
        self.node.publish_twist()
        self.root.after(50,self.tick)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.node.stop()
        self.root.destroy()


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardTeleop()
    window = None
    try:
        window = ControlWindow(node)
        window.root.mainloop()
    except tk.TclError as error:
        node.get_logger().error("Cannot open control window: "+str(error))
        raise SystemExit(1)
    except KeyboardInterrupt:
        pass
    finally:
        if window is not None and not window.closed:
            window.close()
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=="__main__":
    main()
