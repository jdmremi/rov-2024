from PyQt5.QtCore import pyqtSignal, QThread, QTimer, pyqtSlot
import pygame
import logging
import coloredlogs
import _thread as thread
import time

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GREEN_TEXT_CSS = "color: green"
RED_TEXT_CSS = "color: red"
RESTING_PULSEWIDTH = 1500.00
DEADZONE_MIN = 0.75
PWM_DEADZONE_MIN = 0.15
ARDUINO_SEND_TIMER_MIN = 0.1


class JoystickThread(QThread):

    # This signal is used to fire events related to joystick changes.
    joystick_change_signal = pyqtSignal(dict)

    # Takes in the GUI elements so that they can be updated in this thread.
    # Also takes in the video thread to take screenshots.
    # Also takes in the arduino thread to send data to the arduino.
    def __init__(self, forward_backward_thrust_label, left_right_thrust_label, vertical_thrust_label, pitch_thrust_label, status_bar, arduino_thread, video_thread):
        super().__init__()
        logger.info("Joystick thread initialized")
        self.__run_flag = True
        self.__joystick = None
        # References to various GUI elements.
        self.__forward_backward_thrust_label = forward_backward_thrust_label
        self.__left_right_thrust_label = left_right_thrust_label
        self.__vertical_thrust_label = vertical_thrust_label
        self.__pitch_thrust_label = pitch_thrust_label
        self.__connection_status_bar = status_bar
        # References to Arduino and video threads.
        self.__arduino_thread = arduino_thread
        self.__video_thread = video_thread

        # Holds interval in which data is sent to arduino
        self.__last_sent_time = time.time()

        # Initialize pygame so that its libraries can be used.
        pygame.init()

        # Initialize the timer to periodically check for joystick connection
        self._wait_for_joystick_timer = QTimer(self)
        self._wait_for_joystick_timer.timeout.connect(self._wait_for_joystick)

        # If no joysticks are connected
        if pygame.joystick.get_count() == 0:
            logger.warn("No joystick detected! Waiting for joysticks...")
            # Check for joysticks every second
            self._wait_for_joystick_timer.start(1000)  # Check every second
        else:
            # Otherwise, initialize the currently connected joystick.
            self._initialize_joystick()

        # Attach the event handler and start the thread.
        self.joystick_change_signal.connect(self.handle_joystick)
        self.start()

        # 10ms input delay for joystick inputs. Also helps with checking for joystick disconnects.
        self.__joystick_timer = QTimer(self)
        self.__joystick_timer.timeout.connect(self.check_joystick_input)
        self.__joystick_timer.start(10)

    def stop(self):
        self.__run_flag = False
        self.wait()

    # Joystick reconnect/disconnect handler
    def _wait_for_joystick(self):
        # pygame must be quit and then reinitialized so that joysticks can be detected.
        # If not, then pygame will say that 0 joysticks are available even if you reconnect a joystick after disconnecting it.
        pygame.quit()
        pygame.init()
        if pygame.joystick.get_count() > 0:
            self._initialize_joystick()
            self._wait_for_joystick_timer.stop()

    def _initialize_joystick(self):
        # Assume that our joystick is the first device.
        self.__joystick = pygame.joystick.Joystick(0)
        # Initialize the joystick through pygame.
        self.__joystick.init()
        logger.info(f"Joystick found! Name: {self.__joystick.get_name()}")
        # Update GUI elements
        self.__connection_status_bar.setText(
            f"Joystick ({self.__joystick.get_name()}) connected")
        # Green text!
        self.__connection_status_bar.setStyleSheet(GREEN_TEXT_CSS)

    @pyqtSlot(dict)
    def handle_joystick(self, commands):
        # Contains True/False depending on whether or not a joystick is connected.
        is_joystick_connected = commands.get("connected")
        # If False, then the joystick has been disconnected.
        if not is_joystick_connected:
            logger.warn("Joystick disconnected")
        else:
            pass  # If joystick is connected, we can do stuff here.

    def check_joystick_input(self):
        # If we have a valid joystick connection
        if self.__joystick is not None and pygame.joystick.get_count() > 0:
            # This is necessary: https://www.pygame.org/docs/ref/event.html
            # From documentation:
            # "For each frame of your game, you will need to make some sort of call to the event queue.
            # This ensures your program can internally interact with the rest of the operating system.
            # If you are not using other event functions in your game, you should call pygame.event.pump() to allow pygame to handle internal actions."
            pygame.event.pump()

            # Miscellaneous button press handlers
            for event in pygame.event.get():
                # Screenshots
                if event.type == pygame.JOYBUTTONDOWN and event.button == 4:
                    self.__video_thread.save_screenshot()
                # Todo: Implement claw functionality

            # Flip the signs of all values so that up on the left thumbstick corresponds to positive forward thrust, etc...
            left_thumbstick_left_right = self.__joystick.get_axis(0)
            left_thumbstick_up_down = -self.__joystick.get_axis(1)
            right_thumbstick_left_right = self.__joystick.get_axis(2)
            right_thumbstick_up_down = self.__joystick.get_axis(3)

            # Define a deadzone - This helps so that even the smallest of movements to the joystick don't cause sudden movement to the robot.
            if abs(left_thumbstick_left_right) < DEADZONE_MIN:
                left_thumbstick_left_right = 0
            if abs(left_thumbstick_up_down) < DEADZONE_MIN:
                left_thumbstick_up_down = 0
            if abs(right_thumbstick_left_right) < DEADZONE_MIN:
                right_thumbstick_left_right = 0
            if abs(right_thumbstick_up_down) < DEADZONE_MIN:
                right_thumbstick_up_down = 0

            axis_info = {
                "tLeft_LeftRight": left_thumbstick_left_right,
                "tLeft_UpDown": left_thumbstick_up_down,
                "tRight_LeftRight": right_thumbstick_left_right,
                "tRight_UpDown": right_thumbstick_up_down
            }

            # Calculate the pulsewidths that need to be sent to the Arduino.
            pulsewidths = self.__calculate_pulsewidth(axis_info)
            # logger.debug("Pulsewidths: %s", pulsewidths)

            # Debug
            # logger.debug("left_thumbstick_left_right = %s",
            #             left_thumbstick_left_right)
            # logger.debug("left_thumbstick_up_down = %s",
            #             left_thumbstick_up_down)
            # logger.debug("right_thumbstick_left_right = %s",
            #             right_thumbstick_left_right)
            # logger.debug("right_thumbstick_up_down = %s",
            #             right_thumbstick_up_down)

            # Updates the GUI thrust labels based on their pulsewidth
            self.__update_thrust_labels(pulsewidths)

            # Holds json to be sent to Arduino
            """
        return {
            "forward_backward_pulsewidth": round(forward_backward_pulsewidth),
            "left_pulsewidth": round(left_pulsewidth),
            "right_pulsewidth": round(right_pulsewidth),
            "ascend_descend_pulsewidth": round(ascend_descend_pulsewidth),
            "pitch_left_pulsewidth": round(pitch_left_pulsewidth),
            "pitch_right_pulsewidth": round(pitch_right_pulsewidth)
        }
            """
            joystick_info = {
                "connected": "True",
                "joystickName": self.__joystick.get_name(),
                "axisInfo": [
                    pulsewidths.get("forward_backward_pulsewidth"),
                    pulsewidths.get("left_pulsewidth"),
                    pulsewidths.get("right_pulsewidth"),
                    pulsewidths.get("ascend_descend_pulsewidth"),
                    pulsewidths.get("pitch_left_pulsewidth"),
                    pulsewidths.get("pitch_right_pulsewidth")
                ]
            }
            to_arduino = {
                "axisInfo": [
                    pulsewidths.get("forward_backward_pulsewidth"),
                    pulsewidths.get("left_pulsewidth"),
                    pulsewidths.get("right_pulsewidth"),
                    pulsewidths.get("ascend_descend_pulsewidth"),
                    pulsewidths.get("pitch_left_pulsewidth"),
                    pulsewidths.get("pitch_right_pulsewidth")
                ]
            }
            # Determine the rumble frequency for the joystick.
            # Finds the highest value out of all of the joystick thumbstick axes to determine rumble frequency.
            rumble_freq = max(abs(left_thumbstick_left_right), abs(left_thumbstick_up_down), abs(
                right_thumbstick_left_right), abs(right_thumbstick_up_down))
            # Rumble joystick
            self.__joystick.rumble(0, abs(rumble_freq), 1)

            # Send data to Arduino on separate thread so that we don't have blocking issues.
            # We can only send data every ARDUINO_SEND_TIMER_MIN seconds so that the Arduino can process the data correctly.
            current_time = time.time()
            if current_time - self.__last_sent_time > ARDUINO_SEND_TIMER_MIN:
                self.__arduino_thread.handle_data(to_arduino)
                self.__last_sent_time = current_time
            # self.__arduino_thread.handle_data(joystick_info)
            # logger.debug(joystick_info)

            # Emit joystick connection data to event handler
            self.joystick_change_signal.emit(joystick_info)
        else:
            # This else block handles joystick disconnections.
            # We must first emit a disconnected signal to the event handler.
            self.joystick_change_signal.emit({"connected": False})
            # Update GUI elements
            self.__connection_status_bar.setText(f"Joystick disconnected")
            # Red text!
            self.__connection_status_bar.setStyleSheet(RED_TEXT_CSS)
            # Joystick reconnect/disconnect handler
            self._wait_for_joystick()
    """
    axis_info:
            axis_info = {
                "tLeft_LeftRight": left_thumbstick_left_right,
                "tLeft_UpDown": left_thumbstick_up_down,
                "tRight_LeftRight": right_thumbstick_left_right,
                "tRight_UpDown": right_thumbstick_up_down
            }
    """
    # Calculate pulsewidths accordingly:
    # 1100: Full reverse thrust
    # 1500: No thrust
    # 1900: Full forward thrust

    def __calculate_pulsewidth(self, axis_info):
        left_thumbstick_left_right = axis_info.get("tLeft_LeftRight")
        left_thumbstick_up_down = axis_info.get("tLeft_UpDown")
        right_thumbstick_left_right = axis_info.get("tRight_LeftRight")
        right_thumbstick_up_down = axis_info.get("tRight_UpDown")

        # Default should be 1500 (no movement)
        forward_backward_pulsewidth = RESTING_PULSEWIDTH
        left_pulsewidth = RESTING_PULSEWIDTH
        right_pulsewidth = RESTING_PULSEWIDTH
        ascend_descend_pulsewidth = RESTING_PULSEWIDTH
        pitch_left_pulsewidth = RESTING_PULSEWIDTH
        pitch_right_pulsewidth = RESTING_PULSEWIDTH

        """
                Forward/Backward:

                Left thumb pushed up: Forward thrust on left and right motors.
                Left thumb pushed down: Backward thrust on left and right motors.
                Left thumb pushed up: -1.0
                Left thumb pushed down: 1.0
        """

        if left_thumbstick_up_down < 0:
            forward_backward_pulsewidth = self.__map_to_pwm(
                left_thumbstick_up_down)
        elif left_thumbstick_up_down > 0:
            forward_backward_pulsewidth = self.__map_to_pwm(
                left_thumbstick_up_down)

        """
                Left/Right:

                Left thumb pushed left: Forward thrust on right motor, reverse thrust on left motor.
                Left thumb pushed right: Forward thrust on left motor, reverse thrust on right motor.
                Left thumb pushed left: -1.0
                Left thumb pushed right: 1.0
        """
        if left_thumbstick_left_right < 0:
            left_pulsewidth = self.__map_to_pwm(left_thumbstick_left_right)
            right_pulsewidth = self.__map_to_pwm(
                -left_thumbstick_left_right)
        elif left_thumbstick_left_right > 0:
            left_pulsewidth = self.__map_to_pwm(left_thumbstick_left_right)
            right_pulsewidth = self.__map_to_pwm(
                -left_thumbstick_left_right)

        """
                Ascend/Descend:

                Right thumb pushed up: Forward thrust on vertical motors.
                Right thumb pushed down: Reverse thrust on vertical motors.
                Right thumb pushed up: -1.0
                Right thumb pushed down: 1.0
        """

        if right_thumbstick_up_down < 0:  # Thumbstick down (descend)
            ascend_descend_pulsewidth = self.__map_to_pwm(
                right_thumbstick_up_down)
        else:
            ascend_descend_pulsewidth = self.__map_to_pwm(
                right_thumbstick_up_down)

        """
                Pitch CW/Pitch CCW:

                Right thumb pushed left: Forward thrust on right motor, backward thrust on left motor.
                Right thumb pushed right: Forward thrust on left motor, backward thrust on right motor.
                Right thumb pushed left: -1.0
                Right thumb pushed right: 1.0
        """
        if right_thumbstick_left_right < 0:  # Pitch ccw
            pitch_left_pulsewidth = self.__map_to_pwm(
                right_thumbstick_left_right)
            pitch_right_pulsewidth = self.__map_to_pwm(
                -right_thumbstick_left_right)
        else:
            pitch_left_pulsewidth = self.__map_to_pwm(
                right_thumbstick_left_right)
            pitch_right_pulsewidth = self.__map_to_pwm(
                -right_thumbstick_left_right)

        # Round all values to integers
        forward_backward_pulsewidth = round(forward_backward_pulsewidth)
        left_pulsewidth = round(left_pulsewidth)
        right_pulsewidth = round(right_pulsewidth)
        ascend_descend_pulsewidth = round(ascend_descend_pulsewidth)
        pitch_left_pulsewidth = round(pitch_left_pulsewidth)
        pitch_right_pulsewidth = round(pitch_right_pulsewidth)

        # left up/down axis
        # left left/right axis
        # right up/down axis
        # right left/right axis
        return {
            "forward_backward_pulsewidth": round(forward_backward_pulsewidth),
            "left_pulsewidth": round(left_pulsewidth),
            "right_pulsewidth": round(right_pulsewidth),
            "ascend_descend_pulsewidth": round(ascend_descend_pulsewidth),
            "pitch_left_pulsewidth": round(pitch_left_pulsewidth),
            "pitch_right_pulsewidth": round(pitch_right_pulsewidth)
        }

    # Configured so that small joystick movements (stick drift, rumbles, etc) don't cause drifts away from 1500.

    def __map_to_pwm(self, val):
        if val >= -PWM_DEADZONE_MIN and val <= PWM_DEADZONE_MIN:
            return 1500
        else:
            return 400*(val + 1) + 1000

    def __update_thrust_labels(self, pulsewidths):
        # If forward thrust (pw > 1500): say direction is forward with thrust percentage
        forward_backward_thrust_label_text = None
        vertical_thrust_label_text = None
        left_right_thrust_label_text = None
        pitch_thrust_label_text = None

        fb_pw = pulsewidths.get("forward_backward_pulsewidth")
        v_pw = pulsewidths.get("ascend_descend_pulsewidth")
        l_pw = pulsewidths.get("left_pulsewidth")
        r_pw = pulsewidths.get("right_pulsewidth")
        pl_pw = pulsewidths.get("pitch_left_pulsewidth")
        pr_pw = pulsewidths.get("pitch_right_pulsewidth")

        # Reverse thrust (< 1500)
        if fb_pw < 1500:
            fb_pw_percent = (fb_pw/1100.0)*100.0
            forward_backward_thrust_label_text = "Backward" + \
                f" ({fb_pw_percent:.2f}% power)"
        # No thrust
        elif fb_pw == 1500:
            forward_backward_thrust_label_text = "0.00% power"
        # Forward thrust (> 1500)
        else:
            fb_pw_percent = (fb_pw/1900.0)*100.0
            forward_backward_thrust_label_text = "Forward" + \
                f" ({fb_pw_percent:.2f}% power)"

        # Downward thrust:
        if v_pw < 1500:
            v_pw_percent = (v_pw/1100.0)*100.0
            vertical_thrust_label_text = "Downward" + \
                f" ({v_pw_percent:.2f}% power)"
        elif v_pw == 1500:
            vertical_thrust_label_text = "0.00% power"
        # Upward thrust:
        else:
            v_pw_percent = (v_pw/1900.0)*100.0
            vertical_thrust_label_text = "Upward" + \
                f" ({v_pw_percent:.2f}% power)"

        # Turning left (l_pw < r_pw)
        if l_pw < r_pw:
            l_r_percent = (r_pw/1900.0)*100.0
            left_right_thrust_label_text = "Left" + \
                f" ({l_r_percent:.2f}% power)"
        # both are 1500
        elif l_pw == 1500 and r_pw == 1500 or l_pw == r_pw:
            left_right_thrust_label_text = "0.00% power"
        # Turning right (l_pw > r_pw)
        else:
            l_r_percent = (l_pw/1900.0)*100.0
            left_right_thrust_label_text = "Right" + \
                f" ({l_r_percent:.2f}% power)"

        # Pitch counter-clockwise (pl_pw < pr_pw)
        if pl_pw < pr_pw:
            p_percent = (pr_pw/1900.0)*100.0
            pitch_thrust_label_text = "CCW" + f" ({p_percent:.2f}% power)"
        # both are 1500 or equal
        elif pl_pw == 1500 and pr_pw == 1500 or pl_pw == pr_pw:
            pitch_thrust_label_text = "0.00% power"
        else:
            p_percent = (pl_pw/1900.0)*100.0
            pitch_thrust_label_text = "CW" + f" ({p_percent:.2f}% power)"

        self.__forward_backward_thrust_label.setText(
            forward_backward_thrust_label_text)
        self.__vertical_thrust_label.setText(
            vertical_thrust_label_text)
        self.__left_right_thrust_label.setText(
            left_right_thrust_label_text)
        self.__pitch_thrust_label.setText(pitch_thrust_label_text)
