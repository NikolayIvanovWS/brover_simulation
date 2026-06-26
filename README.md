# brover_simulation

ROS 2 Jazzy пакет с упрощенной моделью ровера BRover-E5 для Gazebo Sim и RViz.

Модель предназначена для быстрого запуска симуляции, проверки управления через ROS 2 и получения базовых данных с виртуальных сенсоров. Внешний вид упрощен: корпус сделан прямоугольником, а колеса, подвеска, дифференциал и передняя камера основаны на облегченных mesh-файлах.

## Возможности

- запуск BRover-E5 в Gazebo Sim;
- просмотр модели в RViz без запуска Gazebo;
- управление через `/cmd_vel`;
- управление ровером с клавиатуры;
- публикация одометрии в `/odom`;
- публикация двумерной позы ровера в `/odom_pose2d`;
- TF и симуляционное время `/clock`;
- виртуальный лидар с топиком `/scan`;
- виртуальная передняя камера с топиками `/front_camera/image` и `/front_camera/camera_info`;
- шестиколесная skid-steer схема на базе Gazebo Sim `DiffDrive`.

## Требования

- Ubuntu 24.04;
- ROS 2 Jazzy Jalisco;
- Gazebo Sim из пакетов `ros-jazzy-ros-gz`;
- `colcon`.

Установка зависимостей:

```bash
sudo apt update
sudo apt install \
  python3-colcon-common-extensions \
  ros-jazzy-joint-state-publisher \
  ros-jazzy-rclpy \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-ros-gz \
  ros-jazzy-rviz2 \
  ros-jazzy-xacro
```

## Сборка

```bash
git clone https://github.com/NikolayIvanovWS/brover_simulation.git
cd brover_simulation

source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

Если проект находится в VMware Shared Folder (`/mnt/hgfs/...`), не используйте `--symlink-install`: такие папки часто не поддерживают символические ссылки.

## Просмотр модели в RViz

RViz можно запустить без Gazebo. Этот режим удобен, чтобы быстро проверить внешний вид URDF-модели, TF-дерево и расположение визуальных элементов.

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch brover_simulation rviz.launch.py
```

Launch-файл запускает:

- `joint_state_publisher`;
- `robot_state_publisher`;
- `rviz2` с готовой конфигурацией `brover_e5.rviz`.

В этом режиме топики Gazebo-сенсоров (`/scan`, `/front_camera/image`, `/odom`) не публикуются, потому что сама симуляция не запущена. Для проверки сенсоров используйте запуск Gazebo.

Если RViz используется одновременно с запущенной симуляцией Gazebo для просмотра `/scan`, `/odom` или камеры, запускайте его с симуляционным временем:

```bash
ros2 launch brover_simulation rviz.launch.py use_sim_time:=true
```

## Запуск симуляции

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch brover_simulation gazebo.launch.py
```

По умолчанию запускается пустой мир `empty`. Можно выбрать другой мир через аргумент `world`:

```bash
ros2 launch brover_simulation gazebo.launch.py world:=test_yard
ros2 launch brover_simulation gazebo.launch.py world:=rough_terrain
ros2 launch brover_simulation gazebo.launch.py world:=indoor_corridor
ros2 launch brover_simulation gazebo.launch.py world:=sensor_test_world
ros2 launch brover_simulation gazebo.launch.py world:=obstacle_course
ros2 launch brover_simulation gazebo.launch.py world:=calibration_world
ros2 launch brover_simulation gazebo.launch.py world:=left_wall
```

Доступные миры:

- `empty` - базовая плоскость для быстрой проверки модели и топиков;
- `test_yard` - тестовый полигон со стенами и препятствиями для проверки лидара и камеры;
- `rough_terrain` - простой неровный участок с рампами, ступенью и камнями для проверки движения;
- `indoor_corridor` - коридорная среда со стенами и поворотами для проверки лидара в ограниченном пространстве;
- `sensor_test_world` - стенд с панелями и объектами на известных расстояниях для проверки `/scan` и камеры;
- `obstacle_course` - полоса препятствий со стойками, воротами, ступенью и рампой для ручного управления;
- `calibration_world` - калибровочный мир с метровой линейкой по оси X и угловыми лучами 45, 90, 135, 180, -45, -90 и -135 градусов. Зеленая ось показывает движение вперед, оранжевая - назад, синие лучи - положительные углы, красные - отрицательные;
- `left_wall` - мир с длинной стеной слева от ровера: длина 6 м, высота 1 м, центр стены на расстоянии 1.5 м по оси `+Y`.

## Управление ровером

### Управление с клавиатуры

В отдельном терминале:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 run brover_simulation keyboard_teleop.py
```

Клавиши управления работают в режиме удержания: ровер движется только пока соответствующая клавиша нажата. Если клавиша не нажата, публикуется нулевая скорость.

Клавиши управления:

- удерживать `w` - движение вперед;
- удерживать `s` - движение назад;
- удерживать `a` - поворот влево;
- удерживать `d` - поворот вправо;
- `x` или `Space` - остановка;
- `q` / `z` - увеличить / уменьшить линейную скорость;
- `e` / `c` - увеличить / уменьшить угловую скорость.

Терминал с `keyboard_teleop.py` должен быть активным, чтобы нажатия клавиш попадали в node.

### Публикация команды вручную

В отдельном терминале:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.25}, angular: {z: 0.0}}" -r 10
```

Остановить ровер:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}" --once
```

## Проверка топиков

Список топиков:

```bash
ros2 topic list
```

Одометрия:

```bash
ros2 topic echo /odom
```

Двумерная поза ровера:

```bash
ros2 topic echo /odom_pose2d
```

Топик `/odom_pose2d` имеет тип `geometry_msgs/msg/Pose2D`: `x` и `y` задают положение ровера на плоскости, `theta` задает угол поворота вокруг вертикальной оси в градусах.

Лидар:

```bash
ros2 topic echo /scan
```

В сообщениях `/scan` frame должен быть `lidar_link`. Если RViz не показывает LaserScan, проверьте TF:

```bash
ros2 run tf2_ros tf2_echo base_footprint lidar_link
```

В текущей настройке лидара `ranges[0]` направлен вперед по ходу ровера.

Камера:

```bash
ros2 topic hz /front_camera/image
ros2 topic echo /front_camera/camera_info --once
```

Топики `/scan`, `/front_camera/image` и `/front_camera/camera_info` публикуются вспомогательным node `sensor_topic_normalizer.py`. Он получает внутренние данные сенсоров из Gazebo, задает корректные `frame_id` и оставляет пользовательские имена топиков стабильными.

## Состав пакета

Основной ROS 2 пакет находится в `src/brover_simulation`.

- `urdf/brover_e5.urdf.xacro` - описание модели;
- `launch/gazebo.launch.py` - запуск Gazebo Sim, спавн модели и bridge;
- `launch/rviz.launch.py` - просмотр модели в RViz;
- `rviz/brover_e5.rviz` - конфигурация RViz;
- `config/bridge.yaml` - мост Gazebo <-> ROS 2;
- `scripts/` - вспомогательные ROS 2 node-скрипты для `/odom_pose2d`, сенсорных топиков и управления с клавиатуры;
- `worlds/` - миры Gazebo для разных сценариев;
- `meshes/` - облегченные mesh-файлы колес, подвески, дифференциала и камеры.

## Примечания

Модель специально облегчена для комфортной работы в виртуальной машине. Физика использует простые collision-формы, а визуальные mesh-файлы оптимизированы по количеству треугольников. Исходные CAD-файлы не требуются для запуска пакета.
