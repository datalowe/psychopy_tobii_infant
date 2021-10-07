import os
import types

import numpy as np

import pandas as pd

from psychopy import core, data, event, gui, prefs, sound, visual
import psychopy

from moviepy.config import get_setting

from psychopy_tobii_infant import TobiiInfantController


# ========================================
# SETTINGS
# ========================================
# use PsychToolBox(PTB) audio engine
prefs.hardware['audioLib'] = 'ptb'

# ========================================
# CONSTANTS
# ========================================
# this isn't really a constant, but is included
# here to keep consistent with original 'psychopy_tobii_infant' package
# scripts
DIR = os.path.dirname(os.path.abspath(__file__))
# size/resolution, in pixels, of monitor which __participant__ is to be looking at
PARTICIPANT_DISPSIZE = (1920, 1080)
# size/resolution, in pixels, of monitor which __experimenter__ is to be looking at
# when checking calibration results
EXPERIMENTER_DISPSIZE = (1920, 1080)

# define calibration points
CALINORMP = [(-0.4, 0.4), (-0.4, -0.4), (0.0, 0.0), (0.4, 0.4), (0.4, -0.4)]
CALIPOINTS = [(x * PARTICIPANT_DISPSIZE[0], y * PARTICIPANT_DISPSIZE[1]) for x, y in CALINORMP]

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

# relative paths to target ('grow') sounds, which are randomly sampled from
GROW_SOUND_PATHS = [
    'infant/target_sound1.wav',
    'infant/target_sound2.wav',
    'infant/target_sound3.wav',
    'infant/target_sound4.wav'
]

# relative path to attention grabber movie file
ATT_GRAB_MOVIE_PATH = "infant/waybuloo_intro.mp4"

# grow sound audio volume (scale goes from 0 to 1)
GROW_SOUND_VOLUME = 1

# attention grabber video's audio volume (scale goes from 0 to 1)
ATT_GRAB_VOLUME = 0.5

# maximum x/y coordinates of display that gaze target may be
# positioned at during validation, after calibration is finished
# (these maximum values are also 'flipped' by multiplying by -1 in
# order to get minimum x/y coordinates)
GAZE_TARGET_X_MAX = 600
GAZE_TARGET_Y_MAX = 400

# speed of post-calibration validation target, in pixels/frame
# (eg 5 pixels/frame means roughly 5*60=300 pixels/second)
VALIDATION_MOVEMENT_SPEED = 5

# ========================================
# DEFINE FUNCTIONS
# ========================================
# (calibration) create a 'parent' function which will be given to the
# psychopy_tobii_infant package 'core', and which makes use of custom
# calibration procedures defined below
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

# (calibration) create a customized calibration procedure with sound, etc.
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
    target_min_width = self.targets.get_stim_original_size(0)[0] * self.calibration_target_min
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
            self.targets.get_stim(current_point_index).setPos(
                self.original_calibration_points[current_point_index])
            t = (clock.getTime() - target_start_time) * self.shrink_speed
            newsize = [(np.sin(t)**2 + self.calibration_target_min) * e
                       for e in self.targets.get_stim_original_size(current_point_index)]
            self.targets.get_stim(current_point_index).setSize(newsize)
            self.targets.get_stim(current_point_index).draw()
            
            # handle playing sounds if target started growing
            if previous_frame_width is not None:
                target_is_growing = previous_frame_width < newsize[0]
                if target_is_growing and allow_grow_sound:
                    grow_sound = np.random.choice(grow_sounds)
                    grow_sound.play()
                    allow_grow_sound = False
                elif not target_is_growing and not allow_grow_sound:
                    grow_sound.stop()
                    allow_grow_sound = True
            previous_frame_width = newsize[0]
        
        # get current target width 
        target_curr_width = self.targets.get_stim(current_point_index).size[0]
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

# (calibration) create an automated version of the above
# custom calibration procedure
def automated_calibration(
    self,
    _focus_time=0.5,
    collect_key='space',
    exit_key='return',
    cycles_before_calibrate=2):
    """
    This is an automated version of the above 'manual'
    calibration function. It is to be run the first time through -
    any following recalibrations are handled manually, ie
    by the experimenter.

    'cycles_before_calibrate' specifies the number of grow/shrink cycles
    each target should finish before it stops and calibration data are
    recorded. This defaults to 2 cycles.
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
    target_min_width = self.targets.get_stim_original_size(0)[0] * self.calibration_target_min
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
    # define 'cycle counter' that counts the number of grow/shrink cycles
    # the target has finished
    cycle_counter = 0

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
            self.targets.get_stim(current_point_index).setPos(
                self.original_calibration_points[current_point_index])
            t = (clock.getTime() - target_start_time) * self.shrink_speed
            newsize = [(np.sin(t)**2 + self.calibration_target_min) * e
                       for e in self.targets.get_stim_original_size(current_point_index)]
            self.targets.get_stim(current_point_index).setSize(newsize)
            self.targets.get_stim(current_point_index).draw()
            
            # handle playing sound if target started growing
            if previous_frame_width is not None:
                target_is_growing = previous_frame_width < newsize[0]
                if target_is_growing and allow_grow_sound:
                    grow_sound = np.random.choice(grow_sounds)
                    grow_sound.play()
                    allow_grow_sound = False
                elif not target_is_growing and not allow_grow_sound:
                    # stop the 'growing sound' from playing, and switch 
                    # boolean indicating that it's OK to start playing 
                    # it again once the target starts growing again
                    grow_sound.stop()
                    allow_grow_sound = True
                    # increase cycle counter (note that this is done halfway 
                    # through a cycle, to ensure that calibration trigger 
                    # is switched on in time)
                    cycle_counter += 1
            # enable calibration trigger if on the last target grow/shrink
            # cycle, meaning calibration data will be collected once target has
            # shrunk enough
            if cycle_counter >= cycles_before_calibrate:
                collect_when_shrunk = True
            # store target's current frame width for comparison during next
            # loop iteration / frame handling
            previous_frame_width = newsize[0]
        
        # get current target width 
        target_curr_width = self.targets.get_stim(current_point_index).size[0]
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
                cycle_counter = 0
        self.win.flip()
        # if calibration for current point is done, and there
        # are no points left to calibrate for, end calibration
        if not target_activated and not pos_nums:
            in_calibration = False

# (validation) function for positioning target at starting position before
# initiating smooth movement
def place_target_at_start(movement_dir, target):
    """
    movement_dir: Direction of movement. Must be
    one of 'LtR', 'TtB', 'RtL' or 'BtT'.
    target: PsychoPy visual object, ie target object that is
    to be moved.
    """
    if movement_dir == 'LtR':
        x_pos = -GAZE_TARGET_X_MAX
        y_pos = 0
    elif movement_dir == 'RtL':
        x_pos = GAZE_TARGET_X_MAX
        y_pos = 0
    elif movement_dir == 'TtB':
        x_pos = 0
        y_pos = GAZE_TARGET_Y_MAX
    elif movement_dir == 'BtT':
        x_pos = 0
        y_pos = -GAZE_TARGET_Y_MAX
    target.pos = (x_pos, y_pos)
    return None

# (validation) function for smoothly moving target.
# returns True if target has finished
# moving, otherwise False
def smoothly_move_target(movement_dir, target, step_size):
    """
    movement_dir: Direction of movement. Must be
    one of 'LtR', 'TtB', 'RtL' or 'BtT'.
    target: PsychoPy visual object, ie target object that is
    to be moved.
    step_size: float value which indicates how large each 'step'
    taken at each frame should be, in target object's units. Eg
    if target uses unit 'pix' and passed step_size is 3.0,
    target will move 3 pixels each frame.
    """
    x_pos, y_pos = target.pos
    finished_moving = False
    if movement_dir == 'LtR':
        x_pos += step_size
        y_pos = 0
        if x_pos > GAZE_TARGET_X_MAX:
            finished_moving = True
    elif movement_dir == 'RtL':
        x_pos -= step_size
        y_pos = 0
        if x_pos < -GAZE_TARGET_X_MAX:
            finished_moving = True
    elif movement_dir == 'TtB':
        x_pos = 0
        y_pos -= step_size
        if y_pos < -GAZE_TARGET_Y_MAX:
            finished_moving = True
    elif movement_dir == 'BtT':
        x_pos = 0
        y_pos += step_size
        if y_pos > GAZE_TARGET_Y_MAX:
            finished_moving = True
    target.pos = (x_pos, y_pos)
    return finished_moving

# ========================================
# COLLECT PARTICIPANT/SESSION DATA
# ========================================
expInfo = {'participant_code': ''}
dlg = gui.DlgFromDict(dictionary=expInfo, sortKeys=False, title='ease_et_calibration')
# did experimenter press 'cancel' in dialog?
if dlg.OK is False:
    core.quit()
expInfo['date'] = data.getDateStr()
expInfo['expName'] = 'ease_et_calibration'
expInfo['psychopyVersion'] = psychopy.__version__

# make sure this script's parent directory
# is the working directory at runtime
os.chdir(DIR)

# make sure that the participant_data directory
# exists
data_dir_path = os.path.join(DIR, 'participant_data')
if not os.path.isdir(data_dir_path):
    os.mkdir(data_dir_path)

# form paths to calibration-related data files
vdata_file_name = '{}_{}_{}_validation_data.csv'.format(
    expInfo['participant_code'],
    expInfo['expName'],
    expInfo['date']
)
vdata_file_path = os.path.join(data_dir_path, vdata_file_name)


# ========================================
# WINDOW & STIMULUS SETUP
# ========================================
# create a Window to control the monitor which the participant is to be
# looking at
win = visual.Window(size=PARTICIPANT_DISPSIZE,
                    units='pix',
                    fullscr=True,
                    allowGUI=False,
                    color=[1, 1, 1],
                    screen=1)

# create a Window to control the monitor on which calibration results
# are to be shown (ie experimenter's display)
calibration_res_win = visual.Window(size=EXPERIMENTER_DISPSIZE,
                    units='pix',
                    fullscr=True,
                    allowGUI=False,
                    color=[1, 1, 1],
                    screen=0)


# prepare the audio stimuli used in calibration
grow_sounds = []
for sound_path in GROW_SOUND_PATHS:
    grow_sound = sound.Sound(
        sound_path, 
        secs=-1, 
        stereo=True, 
        hamming=True, 
        name='grow_sound',
        volume=GROW_SOUND_VOLUME
    )
    grow_sounds.append(grow_sound)
# initialize global 'grow_sound' variable which initially points
# at first of loaded grow sounds, but will be randomly updated
grow_sound = grow_sounds[0]

# setup the attention grabber to be shown while adjusting the
# participant's position
grabber = visual.MovieStim3(
    win, 
    ATT_GRAB_MOVIE_PATH, 
    noAudio=False,
    volume=ATT_GRAB_VOLUME,
    size=(1280 * 2/3, 720 * 2/3)
)
# set up message to experimenter about how to end positioning phase 
end_positioning_txt = visual.TextStim(
    win=calibration_res_win,
    text="Once participant is correctly positioned, hit SPACE",
    pos=(0, 0),
    color="black",
    units="pix",
    alignText="center",
    autoLog=False,
)

# ========================================
# REMIND EXPERIMENTER ABOUT VOLUME
# ========================================
# the experimenter needs to make sure that
# computer audio is set to a certain volume.
# here, a message is displayed on the experimenter's
# screen until they either hit 'space' to proceed,
# or 'Esc' to abort (so that they can update
# audio settings and come back)

# form message to be shown to experimenter
experimenter_msg = visual.TextStim(
    win=calibration_res_win,
    text=(
        "Have you checked the computer's sound/volume settings?\n\n"
        "If you have NOT checked the sound, hit ESCAPE to abort calibration.\n"
        "If you HAVE checked the sound, hit SPACE to continue calibration.\n"
    ),
    pos=(0, 0),
    color=[-1, -1, -1],
    units='pix',
    height=40
)

wait_confirmation = True
while wait_confirmation:
    experimenter_msg.draw()
    calibration_res_win.flip()
    keys = event.getKeys()
    if 'space' in keys:
        wait_confirmation = False
        calibration_res_win.flip()
    elif 'escape' in keys:
        calibration_res_win.flip()
        # close experiment windows
        win.close()
        calibration_res_win.close()
        # close PsychoPy
        core.quit()

# ========================================
# CONTROLLER SETUP
# ========================================
# initialize TobiiInfantController to communicate with the eyetracker
controller = TobiiInfantController(
    win=win, 
    calibration_res_win=calibration_res_win
)
# use the customized calibration
controller.update_calibration = types.MethodType(
    main_calibration,
    controller
)

# ========================================
# POSITION PARTICIPANT
# ========================================
# show attention grabber
grabber.setAutoDraw(True)
grabber.play()
end_positioning_txt.setAutoDraw(True)
# show the relative position of the subject to the eyetracker
# Press space to exit
controller.show_status()

# stop the attention grabber
grabber.setAutoDraw(False)
end_positioning_txt.setAutoDraw(False)
# pause movie, so that it can then be switched back to during calibration
grabber.pause()


# ========================================
# RUN CALIBRATION
# ========================================
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


# ========================================
# RUN VALIDATION
# ========================================
# a marker that is to show to the experimenter where the participant
# is looking
gaze_marker = visual.Rect(
    calibration_res_win, 
    width=20, 
    height=20, 
    autoLog=False
)
# a target which the participant is to (if possible) track with their gaze
gaze_target = visual.ImageStim(
    win,
    image=CALISTIMS[0],
    autoLog=False
)

# start recording 
controller.start_recording('ease_calibration_validation.tsv')

# Find ratios between experimenter/participant display width/height
disp_ratios = (
    EXPERIMENTER_DISPSIZE[0] / PARTICIPANT_DISPSIZE[0],
    EXPERIMENTER_DISPSIZE[1] / PARTICIPANT_DISPSIZE[1]
)
# Initialize list which will hold (euclidean) distances between
# participant gaze and target position at each recording timepoint
gaze_to_target_dists = []
# Initialize list which will hold values which indicate if
# participant gaze could be captured (1) or not (0) at each
# recording timepoint
gaze_on_screen_inds = []

# initialize list which specifies gaze target movement directions
# (eg 'LtR' for 'Left to Right', 'TtB' for 'Top to Bottom')
original_target_dir_ls = [
    'LtR',
    'TtB',
    'RtL',
    'BtT'
]
# boolean for indicating if target is moving(True) or not (False)
target_is_moving = False
# boolean for indicating if validation is finished
validation_is_finished = False

# boolean which is to be set to False once
# experimenter is satisfied with validation
repeat_validation = True

while repeat_validation:
    # make a copy of list of gaze target movement directions,
    # to enable popping off directions one by one (without
    # modifying original list)
    target_dir_ls = original_target_dir_ls[:]
    # clear validation data, in case this is not the first
    # validation run
    gaze_to_target_dists.clear()
    gaze_on_screen_inds.clear()
    # keep going until target has finished all movements
    while not validation_is_finished:
        if not target_is_moving:
            target_dir = target_dir_ls.pop()
            place_target_at_start(target_dir, gaze_target)
            target_is_moving = True
            # play a random attention grabbing sound in conjunction
            # with movement initialization
            grow_sound.stop()
            grow_sound = np.random.choice(grow_sounds)
            grow_sound.play()

        # move target a certain number of pixels before next frame, and
        # and check if movement is finished
        finished_moving = smoothly_move_target(
            movement_dir=target_dir, 
            target=gaze_target, 
            step_size=VALIDATION_MOVEMENT_SPEED
        )
        if finished_moving:
            target_is_moving = False

        # Get the latest gaze position data.
        currentGazePosition = controller.get_current_gaze_position()

        # position and draw gaze target
        gaze_target.draw()

        # The value is numpy.nan if Tobii failed to detect gaze position.
        if np.nan not in currentGazePosition:
            gaze_x, gaze_y = currentGazePosition
            # Scale the gaze position data according to the ratios between
            # experimenter/participant display width/height
            rescaled_gaze_x, rescaled_gaze_y = (
                gaze_x * disp_ratios[0],
                gaze_y * disp_ratios[1]
            )
            # show experimenter where gaze is directed
            gaze_marker.setPos((rescaled_gaze_x, rescaled_gaze_y))
            gaze_marker.setLineColor('black')
            # indicate that gaze was recorded
            gaze_on_screen_inds.append(1)
            
            # calculate and store euclidean distance from
            # gaze to target (using Pythagora's here)
            delta_x = gaze_x - gaze_target.pos[0]
            delta_y = gaze_y - gaze_target.pos[1]
            euc_dist = np.sqrt(delta_x**2 + delta_y**2)
            gaze_to_target_dists.append(euc_dist)
        else:
            gaze_marker.setLineColor('red')
            # indicate that gaze was __not__ recorded
            gaze_on_screen_inds.append(0)

        gaze_marker.draw()
        calibration_res_win.flip()
        win.flip()

        # if there are no movement directions left, and
        # there is no ongoing movement, stop the validation
        if not target_dir_ls and not target_is_moving:
            validation_is_finished = True
            # clear participant screen
            win.flip()


    wait_for_press = True
    # show mean/standard deviation of registered euclidean distances,
    # and proportion of timepoints where participant gaze
    # was recorded
    if gaze_to_target_dists:
        mean_target_dist = np.mean(gaze_to_target_dists)
        std_target_dist = np.std(gaze_to_target_dists)
    else:
        # if for some reason no distances were calculated/recorded,
        # mark the value as missing
        mean_target_dist = np.nan
    if gaze_on_screen_inds:
        prop_on_screen = sum(gaze_on_screen_inds) / len(gaze_on_screen_inds)
    else:
        prop_on_screen = np.nan

    # put together message to experimenter about validation results
    if mean_target_dist is np.nan:
        mean_dist_msg = (
            "Could not record any distances. "
            "Please repeat calibration/validation."
        )
        std_dist_msg = ""
    else:
        mean_dist_msg = round(mean_target_dist, 5)
        std_dist_msg = round(std_target_dist, 5)

    if prop_on_screen is np.nan:
        prop_screen_msg = (
            "Could not record whether participant "
            "was looking at screen or not."
            "Please repeat calibration/validation."
        )
    else:
        prop_screen_msg = round(prop_on_screen*100, 5)
    res_message = (
        "Validation results:\n\n"
        "Mean distance (in pixels) between gaze and target:\n"
        f"{mean_dist_msg}\n\n"
        "Standard deviation of distance (in pixels) between gaze and target:\n"
        f"{std_dist_msg}\n\n"
        "Proportion of time participant looked at screen during validation\n"
        f"{prop_screen_msg}%\n\n"
        "Press SPACE to end validation, or R to repeat it."
    )
    res_txt = visual.TextStim(
        win=calibration_res_win,
        text=res_message,
        pos=(0, 0),
        color="black",
        units="pix",
        alignText="center",
        autoLog=False,
    )
    res_txt.draw()
    calibration_res_win.flip()
    while wait_for_press:
        keys = event.getKeys()
        if 'space' in keys:
            wait_for_press = False
            repeat_validation = False
        elif 'r' in keys or 'R' in keys:
            wait_for_press = False
            validation_is_finished = False

# save validation data
val_df = pd.DataFrame({
    'mean_distance_gaze_to_target': [mean_target_dist],
    'std_distance_gaze_to_target': [std_target_dist],
    'proportion_of_time_gaze_on_screen': [prop_on_screen]
})
val_df.to_csv(vdata_file_path, index=False)

# stop recording
controller.stop_recording()
# close the file
controller.close()

# close experiment windows
win.close()
calibration_res_win.close()

# close PsychoPy
core.quit()
