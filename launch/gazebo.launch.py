from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    ExecuteProcess,
    LogInfo,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_name = "brover_simulation"
    model_name = LaunchConfiguration("model_name")
    world_name = LaunchConfiguration("world")
    imu_rate = LaunchConfiguration("imu_rate")

    xacro_file = PathJoinSubstitution(
        [FindPackageShare(package_name), "urdf", "brover_e5.urdf.xacro"]
    )
    world_file = PathJoinSubstitution(
        [
            FindPackageShare(package_name),
            "worlds",
            PythonExpression(["'brover_e5_' + '", world_name, "' + '.sdf'"]),
        ]
    )
    bridge_config = PathJoinSubstitution(
        [FindPackageShare(package_name), "config", "bridge.yaml"]
    )
    mesh_dir = PathJoinSubstitution([FindPackageShare(package_name), "meshes"])

    robot_description = {
        "robot_description": Command(
            [
                FindExecutable(name="xacro"),
                " ",
                xacro_file,
                " mesh_dir:=file://",
                mesh_dir,
                " imu_rate:=",
                imu_rate,
            ]
        ),
        "use_sim_time": True,
    }

    gazebo = ExecuteProcess(
        cmd=[FindExecutable(name="gz"), "sim", "-r", world_file],
        output="screen",
    )

    shutdown_on_gazebo_exit = RegisterEventHandler(
        OnProcessExit(
            target_action=gazebo,
            on_exit=[
                LogInfo(msg="Gazebo closed, shutting down brover_simulation launch."),
                EmitEvent(event=Shutdown(reason="Gazebo closed")),
            ],
        )
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-topic",
            "robot_description",
            "-name",
            model_name,
            "-allow_renaming",
            "false",
            "-z",
            "0.02",
        ],
        output="screen",
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ros_gz_bridge",
        output="screen",
        parameters=[{"config_file": bridge_config}],
    )

    command_limiter = Node(
        package=package_name,
        executable="command_limiter.py",
        name="command_limiter",
        output="screen",
        parameters=[
            PathJoinSubstitution([FindPackageShare(package_name), "config", "control.yaml"]),
            {"use_sim_time": True},
        ],
    )
    shutdown_on_limiter_exit = RegisterEventHandler(
        OnProcessExit(
            target_action=command_limiter,
            on_exit=[EmitEvent(event=Shutdown(reason="Command limiter exited"))],
        )
    )
    odom_pose2d_publisher = Node(
        package=package_name,
        executable="odom_pose2d_publisher.py",
        name="odom_pose2d_publisher",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    sensor_topic_normalizer = Node(
        package=package_name,
        executable="sensor_topic_normalizer.py",
        name="sensor_topic_normalizer",
        output="screen",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "model_name",
                default_value="brover_e5",
                description="Name of the robot entity spawned in Gazebo.",
            ),
            DeclareLaunchArgument(
                "imu_rate",
                default_value="100.0",
                description="IMU update rate in simulation Hz (positive value)",
            ),
            DeclareLaunchArgument(
                "world",
                default_value="empty",
                choices=[
                    "empty",
                    "test_yard",
                    "rough_terrain",
                    "indoor_corridor",
                    "sensor_test_world",
                    "obstacle_course",
                    "calibration_world",
                    "left_wall",
                ],
                description=(
                    "World to load: empty, test_yard, rough_terrain, "
                    "indoor_corridor, sensor_test_world, obstacle_course, "
                    "calibration_world, or left_wall."
                ),
            ),
            shutdown_on_limiter_exit,
            command_limiter,
            gazebo,
            robot_state_publisher,
            spawn_robot,
            bridge,
            odom_pose2d_publisher,
            sensor_topic_normalizer,
            shutdown_on_gazebo_exit,
        ]
    )
