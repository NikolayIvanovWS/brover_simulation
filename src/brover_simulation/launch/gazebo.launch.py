from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
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
            ]
        ),
        "use_sim_time": True,
    }

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
        ),
        launch_arguments={"gz_args": ["-r ", world_file]}.items(),
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

    odom_pose2d_publisher = Node(
        package=package_name,
        executable="odom_pose2d_publisher.py",
        name="odom_pose2d_publisher",
        output="screen",
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
                ],
                description=(
                    "World to load: empty, test_yard, rough_terrain, "
                    "indoor_corridor, sensor_test_world, obstacle_course, "
                    "or calibration_world."
                ),
            ),
            gazebo,
            robot_state_publisher,
            spawn_robot,
            bridge,
            odom_pose2d_publisher,
            sensor_topic_normalizer,
        ]
    )
