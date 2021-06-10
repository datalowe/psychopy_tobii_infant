import os
import types

import numpy as np
from psychopy import core, event, sound, visual

from psychopy_tobii_infant import TobiiInfantController

###############################################################################
# Constants
DIR = os.path.dirname(__file__)
# users should know the display well.
DISPSIZE = (1920, 1080)
# define calibration points
CALINORMP = [(-0.4, 0.4), (-0.4, -0.4), (0.0, 0.0), (0.4, 0.4), (0.4, -0.4)]
CALIPOINTS = [(x * DISPSIZE[0], y * DISPSIZE[1]) for x, y in CALINORMP]
# stimuli to use in calibration
# The number of stimuli must be the same or larger than the calibration points.
CALISTIMS = [
    'infant/{}'.format(x) for x in os.listdir(os.path.join(DIR, 'infant'))
    if x.endswith('.png') and not x.startswith('.')
]
GROW_SOUND_PATH = 'infant/grow.wav'
SHRINK_SOUND_PATH = 'infant/shrink.wav'

###############################################################################
# Demo
# create a Window to control the monitor
win = visual.Window(size=(1920, 1080),
                    units='pix',
                    fullscr=True,
                    allowGUI=False,
                    screen=0)

# prepare the audio stimuli used in calibration
grow_sound = sound.Sound(GROW_SOUND_PATH)
shrink_sound = sound.Sound(SHRINK_SOUND_PATH)

# setup the attention grabber during adjusting the participant's position
grabber = visual.MovieStim3(win, "infant/seal-clip.mp4")


# create a customized calibration procedure with sound
# code snippets copied from _update_calibration_infant()
def customized_update_calibration(self,
                                  _focus_time=0.5,
                                  collect_key='space',
                                  exit_key='return'):
    # boolean indicating if calibration data are to be collected
    # when target is shrunk to close to minimum size
    collect_when_shrunk = False
    # booleans indicating if shrink/grow sounds are allowed to be
    # played (these are for avoiding sounds being repeatedly started
    # in very quick succession)
    allow_grow_sound = True
    allow_shrink_sound = True
    # boolean indicating if the target is currently growing
    target_is_growing = False
    # variable for holding previous frame's target width
    previous_frame_width = None
    # minimum possible target width
    target_min_width = self.target_original_size[0] * self.calibration_target_min
    # start calibration
    event.clearEvents()
    current_point_index = -1
    in_calibration = True
    clock = core.Clock()
    # time at which the currently active target started being shown
    # (the default value assigned here will be overwritten, see below)
    target_start_time = clock.getTime()
    while in_calibration:
        # get keys
        keys = event.getKeys()
        for key in keys:
            if key in self.numkey_dict:
                current_point_index = self.numkey_dict[key]
                target_start_time = clock.getTime()
            elif key == collect_key and current_point_index in self.retry_points:
                # trigger calibration data collection once target has
                # shrunk enough
                collect_when_shrunk = True
            elif key == exit_key:
                # exit calibration when return is presssed
                in_calibration = False
                break

        # draw calibration target
        if current_point_index in self.retry_points:
            self.targets[current_point_index].setPos(
                self.original_calibration_points[current_point_index])
            t = (clock.getTime() - target_start_time) * self.shrink_speed
            newsize = [(np.cos(t)**2 + self.calibration_target_min) * e
                       for e in self.target_original_size]
            self.targets[current_point_index].setSize(newsize)
            self.targets[current_point_index].draw()
            
            # handle playing sounds if target started growing/shrinking
            if previous_frame_width is not None:
                target_is_growing = previous_frame_width < newsize[0]
                if target_is_growing and allow_grow_sound:
                    grow_sound.play()
                    shrink_sound.stop()
                    allow_grow_sound = False
                    allow_shrink_sound = True
                elif not target_is_growing and allow_shrink_sound:
                    shrink_sound.play()
                    grow_sound.stop()
                    allow_shrink_sound = False
                    allow_grow_sound = True
            previous_frame_width = newsize[0]
        
        # get current target width 
        target_curr_width = self.targets[current_point_index].size[0]
        if collect_when_shrunk:
            # check if the current target width is less than twice
            # as large as the minimum possible width
            if target_curr_width < (2 * target_min_width):
                # allow the participant to focus
                core.wait(_focus_time)
                # collect calibration data
                self._collect_calibration_data(
                    self.original_calibration_points[current_point_index]
                )
                # reset calibration point index and calibration-related
                # boolean
                current_point_index = -1
                collect_when_shrunk = False
        self.win.flip()
        
        


# initialize TobiiInfantController to communicate with the eyetracker
controller = TobiiInfantController(win)
# use the customized calibration
controller.update_calibration = types.MethodType(customized_update_calibration,
                                                 controller)

# setup the attention grabber during adjusting the participant's position
grabber.setAutoDraw(True)
grabber.play()
# show the relative position of the subject to the eyetracker
# Press space to exit
controller.show_status()

# stop the attention grabber
grabber.setAutoDraw(False)
grabber.stop()

# How to use:
# - Use 1~9 (depending on the number of calibration points) to present
#   calibration stimulus and 0 to hide the target.
# - Press space to start collect calibration samples.
# - Press return (Enter) to finish the calibration and show the result.
# - Choose the points to recalibrate with 1~9.
# - Press decision_key (default is space) to accept the calibration or
# recalibrate.
success = controller.run_calibration(CALIPOINTS, CALISTIMS)
if not success:
    core.quit()

marker = visual.Rect(win, width=20, height=20, autoLog=False)

# Start recording.
# filename of the data file could be define in this method or when creating an
# TobiiInfantController instance
controller.start_recording('demo5-test.tsv')
waitkey = True
timer = core.Clock()

# Press space to leave
while waitkey:
    # Get the latest gaze position data.
    currentGazePosition = controller.get_current_gaze_position()

    # The value is numpy.nan if Tobii failed to detect gaze position.
    if np.nan not in currentGazePosition:
        marker.setPos(currentGazePosition)
        marker.setLineColor('white')
    else:
        marker.setLineColor('red')
    keys = event.getKeys()
    if 'space' in keys:
        waitkey = False
    elif len(keys) >= 1:
        # Record the pressed key to the data file.
        controller.record_event(keys[0])
        print('pressed {k} at {t} ms'.format(k=keys[0],
                                             t=timer.getTime() * 1000))

    marker.draw()
    win.flip()

# stop recording
controller.stop_recording()
# close the file
controller.close()

win.close()
core.quit()
