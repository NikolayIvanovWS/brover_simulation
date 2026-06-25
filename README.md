# brover_gazebo

ROS 2 Jazzy пакет с упрощенной моделью ровера BRover-E5 для Gazebo Sim.

Модель предназначена для быстрого запуска симуляции, проверки управления через ROS 2 и получения базовых данных с виртуальных сенсоров. Внешний вид упрощен: корпус сделан прямоугольником, а колеса, подвеска, дифференциал и передняя камера основаны на облегченных mesh-файлах.

## Возможности

- запуск BRover-E5 в Gazebo Sim;
- управление через `/cmd_vel`;
- публикация одометрии в `/odom`;
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
  ros-jazzy-ros-gz \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-xacro
```

## Сборка

```bash
git clone https://github.com/NikolayIvanovWS/brover-gazebo.git
cd brover-gazebo

source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

Если проект находится в VMware Shared Folder (`/mnt/hgfs/...`), не используйте `--symlink-install`: такие папки часто не поддерживают символические ссылки.

## Запуск симуляции

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch brover_e5_description gazebo.launch.py
```

## Управление ровером

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

Лидар:

```bash
ros2 topic echo /scan
```

Камера:

```bash
ros2 topic hz /front_camera/image
ros2 topic echo /front_camera/camera_info --once
```

## Состав пакета

Основной ROS 2 пакет находится в `src/brover_e5_description`.

- `urdf/brover_e5.urdf.xacro` - описание модели;
- `launch/gazebo.launch.py` - запуск Gazebo Sim, спавн модели и bridge;
- `config/bridge.yaml` - мост Gazebo <-> ROS 2;
- `worlds/brover_e5_empty.sdf` - простой мир Gazebo;
- `meshes/` - облегченные mesh-файлы колес, подвески, дифференциала и камеры.

## Примечания

Модель специально облегчена для комфортной работы в виртуальной машине. Физика использует простые collision-формы, а визуальные mesh-файлы оптимизированы по количеству треугольников. Исходные CAD-файлы не требуются для запуска пакета.
