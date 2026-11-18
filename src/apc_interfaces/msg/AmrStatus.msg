uint8 STATE_IDLE = 0
uint8 STATE_LOADING = 1
uint8 STATE_MOVING = 2
uint8 STATE_UNLOADING = 3
uint8 STATE_ERROR = 4

std_msgs/Header header
string robot_id
uint8 state
uint32 current_apple_id
string target_zone
uint32 queue_length
