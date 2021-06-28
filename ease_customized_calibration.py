import os
import types

import numpy as np
from psychopy import core, event, sound, visual, prefs

from moviepy.config import get_setting

from psychopy_tobii_infant import TobiiInfantController

###############################################################################
# Settings
prefs.hardware['audioLib'] = 'ptb'

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
# keyboard key that is to be used, during calibration, for temporarily switching 
# back to the attention grabber movie, if the child seems to lose all interest
# in the screen. pick **a letter** here, since the code below ensures that
# both upper-and lowercase versions of the letter (eg 'a' or 'A') are checked
# for, to avoid issues with caps lock
ATTENTION_GRAB_KEY = 'a'
# relative path to grow sound file
GROW_SOUND_PATH = 'infant/target_sound.wav'

###############################################################################
# Demo
# create a Window to control the monitor
win = visual.Window(size=(1920, 1080),
                    units='pix',
                    fullscr=True,
                    allowGUI=False,
                    color=[1, 1, 1],
                    screen=1)

# prepare the audio stimuli used in calibration
grow_sound = sound.Sound(GROW_SOUND_PATH, secs=-1, stereo=True, hamming=True, name='grow_sound')

# setup the attention grabber during adjusting the participant's position
grabber = visual.MovieStim3(
    win, 
    "infant/teletubbies_intro.mp4", 
    noAudio=False,
    size=(1280 * 2/3, 720 * 2/3)
)

def main_calibration(
    self,
    _focus_time=0.5,
    collect_key='space',
    exit_key='return'
    ):
    # set boolean property that indicates if the experimenter wants to
    # temporarily show the attention grabber movie at the moment
    self.show_att_grabber = False
    # run automated procedure if it hasn't already been run
    if not hasattr(self, 'automated_calib_done'):
        automated_calibration(
            self,
            _focus_time,
            collect_key,
            exit_key
        )
        # add attribute to 'self', ie the TobiiInfantController
        # instance, to indicate that automated calibration
        # has been run
        # (any additional calibrations are to be done 'manually')
        self.automated_calib_done = True
    else:
        manual_calibration(
            self,
            _focus_time,
            collect_key,
            exit_key
        )

# create a customized calibration procedure with sound
# code snippets copied from _update_calibration_infant()
def manual_calibration(
    self,
    _focus_time=0.5,
    collect_key='space',
    exit_key='return'
    ):
    """
    A customized manual (see automated version below)
    calibration procedure which uses grow sounds.
    Partly uses code copied from the psychopy_tobii_infant 
    package's demos.
    """
    # boolean indicating if calibration data are to be collected
    # when target is shrunk to close to minimum size
    collect_when_shrunk = False
    # booleans indicating if grow sounds are allowed to be
    # played (these are for avoiding sounds being repeatedly started
    # in very quick succession)
    allow_grow_sound = True
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
            elif key.lower() == ATTENTION_GRAB_KEY:
                # toggle attention grabber movie on/off
                self.show_att_grabber = not self.show_att_grabber
                # pause (if it was previously playing) or start (
                # if it wasn't previously playing) attention grabber
                # movie
                grabber.play() if self.show_att_grabber else grabber.pause()
        
        # if the experimenter wants to temporarily play part of the
        # attention grabber movie, keep playing it and don't do anything
        # else this frame
        if self.show_att_grabber:
            grabber.draw()
            win.flip()
            continue

        # draw calibration target
        if current_point_index in self.retry_points:
            self.targets[current_point_index].setPos(
                self.original_calibration_points[current_point_index])
            t = (clock.getTime() - target_start_time) * self.shrink_speed
            newsize = [(np.sin(t)**2 + self.calibration_target_min) * e
                       for e in self.target_original_size]
            self.targets[current_point_index].setSize(newsize)
            self.targets[current_point_index].draw()
            
            # handle playing sounds if target started growing
            if previous_frame_width is not None:
                target_is_growing = previous_frame_width < newsize[0]
                if target_is_growing and allow_grow_sound:
                    grow_sound.play()
                    allow_grow_sound = False
                elif not target_is_growing and not allow_grow_sound:
                    grow_sound.stop()
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

def automated_calibration(
    self,
    _focus_time=0.5,
    collect_key='space',
    exit_key='return'):
    """
    This is an automated version of the above 'manual'
    calibration function. It is to be run the first time through -
    any following recalibrations are handled manually, ie
    by the experimenter.
    """
    # boolean indicating if calibration data are to be collected
    # when target is shrunk to close to minimum size
    collect_when_shrunk = False
    # boolean indicating if grow sounds are allowed to be
    # played (this is for avoiding sounds being repeatedly started
    # in very quick succession)
    allow_grow_sound = True
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
    # form a list of the target position numbers
    # (eg '1', '2', ... '5')
    pos_nums = [str(x) for x in range(1, len(CALINORMP) + 1)]
    target_activated = False
    while in_calibration:
        # if calibration hasn't already been set to trigger,
        # and there are still points left to calibrate with
        if not target_activated and pos_nums:
            # get the number of the position for which data will be fetched this time
            pos_num = pos_nums.pop()
            current_point_index = self.numkey_dict[pos_num]
            target_start_time = clock.getTime()
            target_activated = True
        
        # draw calibration target
        if current_point_index in self.retry_points:
            self.targets[current_point_index].setPos(
                self.original_calibration_points[current_point_index])
            t = (clock.getTime() - target_start_time) * self.shrink_speed
            newsize = [(np.sin(t)**2 + self.calibration_target_min) * e
                       for e in self.target_original_size]
            self.targets[current_point_index].setSize(newsize)
            self.targets[current_point_index].draw()
            
            # handle playing sounds if target started growing,
            # and enable calibration trigger if target has started
            # shrinking
            if previous_frame_width is not None:
                target_is_growing = previous_frame_width < newsize[0]
                if target_is_growing and allow_grow_sound:
                    grow_sound.play()
                    allow_grow_sound = False
                elif not target_is_growing and not allow_grow_sound:
                    grow_sound.stop()
                    allow_grow_sound = True
                    # trigger calibration data collection once target has
                    # shrunk enough
                    collect_when_shrunk = True
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
                target_activated = False
        self.win.flip()
        # if calibration for current point is done, and there
        # are no points left to calibrate for, end calibration
        if not target_activated and not pos_nums:
            in_calibration = False




# initialize TobiiInfantController to communicate with the eyetracker
controller = TobiiInfantController(win)
# use the customized calibration
controller.update_calibration = types.MethodType(
    main_calibration,
    controller
)

# setup the attention grabber during adjusting the participant's position
grabber.setAutoDraw(True)
grabber.play()
# show the relative position of the subject to the eyetracker
# Press space to exit
controller.show_status()

# stop the attention grabber
grabber.setAutoDraw(False)
# pause movie, so that it can then be switched back to during calibration
grabber.pause()

# How to use:
# The first 'calibration run' is automated, just let it run.
# Once the first calibration run has finished, you'll be presented
# a screen that estimates how close (shorter lines means closer) the participant's
# gaze was to each calibration point during calibration. Mark all points where
# the participant's gaze was 'too off' (ie lines are 'too long'), using the
# keyboard numbers 1-5. Each point that's set to be recalibrated will get a small
# blue circle drawn over it. If the calibration seems to have gone well enough
# (this is partly a subjective appraisal), press 'space' to end calibration.
# All recalibration is done manually by you as the experimenter:
# - Use keyboard numbers 1-9 (depending on how many calibration point 
#   coordinates you've specified, in CALINORMP) to activate
#   each calibration point's target stimulus and 0 to hide the target.
# - Press space to start calibration sample collection (the collection
#   is delayed, if necessary, until the target has shrunk down)
# - Press return (Enter) to finish the recalibration and see the 
#   updated results.
success = controller.run_calibration(CALIPOINTS, CALISTIMS, result_msg_color="black")
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
        marker.setLineColor('black')
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
