isaac_ros_scene_recorder
Source code available on GitHub.

This node records data published to given topics and saves them as rosbag. It only works with Isaac ROS Mission Client. Please read the tutorial of isaac_ros_vda5050_client_bringup first.

Usage
To run Mission Client with the recorder, set the ros_recorder launch file parameter to true.

ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client.launch.py ros_recorder:=true robot_type:=MANIPULATOR
Note

The recorder supports any robot type. We use MANIPULATOR here to run the recorder with minimal setup. For mobile robot types like CARRIER, Nav2 and global localization are required.

To start the recorder, post a mission from mission dispatch. Here is an example mission:

{
  "robot": "carter01",
  "mission_tree": [
    {
      "name": "string",
      "parent": "root",
      "action": {
        "action_type": "start_recording",
        "action_parameters": {"path": "/tmp/data", "topics": "/rgb_left", "time":3}
      }
    }
  ],
  "timeout": 300,
  "deadline": "2022-10-07T00:21:31.112Z",
  "needs_canceled": false,
  "name": "mission01"
}
The action_type should be start_recording and the parameters path, topics, time are required. The recorder saves data published by topics in folder path for time seconds.

To stop the recorder, post a mission with action of type stop_recording from Mission Dispatch. Here is an example:

{
  "robot": "carter01",
  "mission_tree": [
    {
      "name": "string",
      "parent": "root",
      "action": {
        "action_type": "stop_recording"
      }
    }
  ],
  "timeout": 300,
  "deadline": "2022-10-07T00:21:31.112Z",
  "needs_canceled": false,
  "name": "mission02"
}