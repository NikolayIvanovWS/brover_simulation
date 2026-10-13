from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_name = "brover_simulation"
    mode = LaunchConfiguration("mode")
    use_sim_time = ParameterValue(LaunchConfiguration("use_sim_time"), value_type=bool)
    share = FindPackageShare(package_name)
    xacro_file = PathJoinSubstitution([share, "urdf", "brover_e5.urdf.xacro"])
    mesh_dir = PathJoinSubstitution([share, "meshes"])
    model_only = IfCondition(PythonExpression(["'", mode, "' == 'model'"]))
    robot_description = {
        "robot_description": ParameterValue(Command([
            FindExecutable(name="xacro"), " ", xacro_file, " mesh_dir:=file://", mesh_dir
        ]), value_type=str),
        "use_sim_time": use_sim_time,
    }
    config = PathJoinSubstitution([
        share, "rviz",
        PythonExpression(["'brover_e5_sim.rviz' if '",mode,"' == 'simulation' else 'brover_e5.rviz'"])
    ])
    return LaunchDescription([
        DeclareLaunchArgument("mode", default_value="model", choices=["model","simulation"],
                              description="Standalone model or connection to running Gazebo"),
        DeclareLaunchArgument("use_sim_time",
            default_value=PythonExpression(["'",mode,"' == 'simulation'"]),
            description="Use /clock (enabled by default for simulation mode)"),
        Node(package="joint_state_publisher", executable="joint_state_publisher",
             name="joint_state_publisher", parameters=[robot_description], condition=model_only),
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             name="robot_state_publisher", parameters=[robot_description], condition=model_only),
        Node(package="rviz2", executable="rviz2", name="rviz2", output="screen",
             arguments=["-d",config], parameters=[{"use_sim_time":use_sim_time}]),
    ])
