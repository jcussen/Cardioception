# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

import pickle
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from systole.detection import ppg_peaks

from cardioception.input import digit_key_list, parse_digit_key

SOUNDS_DIR = Path(__file__).resolve().parent / "Sounds"


def _save_oximeter_recording(oxi_task, fname: str) -> None:
    """Persist oximeter data for both Oximeter and Nonin3231USB APIs."""
    save_fn = getattr(oxi_task, "save", None)
    if callable(save_fn):
        save_fn(fname)
        return

    # Fallback for systole>=0.3 Nonin3231USB, which has no `.save()` method.
    columns = {}
    for attr in ("recording", "bpm", "SpO2", "times"):
        values = getattr(oxi_task, attr, None)
        if values is not None:
            columns[attr] = list(values)

    channels = getattr(oxi_task, "channels", None)
    if isinstance(channels, dict):
        for ch_name, values in channels.items():
            columns[ch_name] = list(values)

    if not columns:
        print(f"Warning: no oximeter samples available to save for {fname}")
        return

    max_len = max(len(values) for values in columns.values())
    padded = {}
    for name, values in columns.items():
        if len(values) < max_len:
            values = values + [np.nan] * (max_len - len(values))
        padded[name] = values

    output = pd.DataFrame(padded)
    if fname.endswith(".txt") or fname.endswith(".csv"):
        output.to_csv(fname, index=False)
    else:
        output.to_csv(f"{fname}.txt", index=False)


def _save_task_outputs(
    parameters: dict, n_trial: Optional[int] = None, partial: bool = False
) -> None:
    """Persist task outputs for completed or gracefully aborted runs."""

    if parameters["results_df"].empty:
        print("No completed trials to save.")
        return

    result_suffix = "_partial_final" if partial else "_final"
    signal_suffix = "_partial" if partial else ""
    posterior_suffix = "_posterior_partial" if partial else "_posterior"
    parameter_suffix = "_parameters_partial" if partial else "_parameters"
    recording_suffix = "partial" if partial else "end"
    n_completed = len(parameters["results_df"])
    recording_index = n_completed if partial else n_trial

    if partial:
        print(f"Saving partial results after {n_completed} completed trials...")
    else:
        print("Saving final results in .txt file...")

    parameters["results_df"].to_csv(
        parameters["resultPath"]
        + "/"
        + parameters["participant"]
        + parameters["session"]
        + result_suffix
        + ".txt",
        index=False,
    )

    print("Saving PPG signal data frame...")
    parameters["signal_df"].to_csv(
        parameters["resultPath"]
        + "/"
        + parameters["participant"]
        + "_signal"
        + signal_suffix
        + ".txt",
        index=False,
    )

    _save_oximeter_recording(
        parameters["oxiTask"],
        f"{parameters['resultPath']}/{parameters['participant']}_ppg_{recording_index}_{recording_suffix}.txt",
    )

    print("Saving posterior distributions...")
    for k in set(parameters["Modality"]):
        np.save(
            parameters["resultPath"]
            + "/"
            + parameters["participant"]
            + k
            + posterior_suffix
            + ".npy",
            np.array(parameters["staircaisePosteriors"][k]),
        )

    print("Saving Parameters in pickle...")
    save_parameter = parameters.copy()
    save_parameter["TaskCompleted"] = not partial
    save_parameter["nCompletedTrials"] = n_completed
    for k in [
        "win",
        "heartLogo",
        "listenLogo",
        "stairCase",
        "oxiTask",
        "myMouse",
        "handSchema",
        "pulseSchema",
    ]:
        save_parameter.pop(k, None)
    with open(
        save_parameter["resultPath"]
        + "/"
        + save_parameter["participant"]
        + parameter_suffix
        + ".pickle",
        "wb",
    ) as handle:
        pickle.dump(save_parameter, handle, protocol=pickle.HIGHEST_PROTOCOL)


def run(
    parameters: dict,
    confidenceRating: bool = True,
    runTutorial: bool = False,
):
    """Run the Heart Rate Discrimination task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    confidenceRating : bool
        Whether the trial show include a confidence rating scale.
    runTutorial : bool
        If `True`, will present a tutorial with one practice trial per modality.
    """
    from psychopy import core, visual

    # Initialization of the Pulse Oximeter
    parameters["oxiTask"].setup().read(duration=1)

    # Show tutorial and training trials
    if runTutorial is True:
        tutorial(parameters)

    nTrial = None
    try:
        trial_iterator = zip(
            range(parameters["nTrials"]),
            parameters["Modality"],
            parameters["staircaseType"],
        )
        for nTrial, modality, trialType in trial_iterator:

            # Initialize variable
            estimatedThreshold, estimatedSlope = None, None

            # Wait for key press if this is the first trial
            if nTrial == 0:

                # Ask the participant to press default button to start
                messageStart = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    text=parameters["texts"]["textTaskStart"],
                )
                press = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    pos=(0.0, -0.4),
                    text=parameters["texts"]["textNext"],
                )
                press.draw()
                messageStart.draw()  # Show instructions
                parameters["win"].flip()

                waitInput(parameters)

            # Next intensity value
            if trialType == "updown":
                print("... load UpDown staircase.")
                thisTrial = parameters["stairCase"][modality].next()
                stairCond = thisTrial[1]["label"]
                alpha = thisTrial[0]
            elif trialType == "psi":
                print("... load psi staircase.")
                alpha = parameters["stairCase"][modality].next()
                stairCond = "psi"
            elif trialType == "CatchTrial":
                print("... load catch trial.")
                # Select pseudo-random extrem value based on number
                # of previous catch trial.
                catchIdx = sum(
                    parameters["staircaseType"][:nTrial][
                        parameters["Modality"][:nTrial] == modality
                    ]
                    == "CatchTrial"
                )
                alpha = np.array([-30, 10, -20, 20, -10, 30])[catchIdx % 6]
                stairCond = "CatchTrial"

            # Before trial triggers
            parameters["oxiTask"].readInWaiting()
            parameters["oxiTask"].channels["Channel_0"][-1] = 1  # Trigger

            # Start trial
            (
                condition,
                listenBPM,
                responseBPM,
                decision,
                decisionRT,
                confidence,
                confidenceRT,
                alpha,
                isCorrect,
                respProvided,
                ratingProvided,
                startTrigger,
                soundTrigger,
                responseMadeTrigger,
                ratingStartTrigger,
                ratingEndTrigger,
                endTrigger,
            ) = trial(
                parameters,
                alpha,
                modality,
                confidenceRating=confidenceRating,
                nTrial=nTrial,
            )

            # Check if response is 'More' or 'Less'
            isMore = 1 if decision == "More" else 0
            # Update the UpDown staircase if initialization trial
            if trialType == "updown":
                print("... update UpDown staircase.")
                # Update the UpDown staircase
                parameters["stairCase"][modality].addResponse(isMore)
            elif trialType == "psi":
                print("... update psi staircase.")

                # Update the Psi staircase with forced intensity value
                # if impossible BPM was generated
                if listenBPM + alpha < 15:
                    parameters["stairCase"][modality].addResponse(isMore, intensity=15)
                elif listenBPM + alpha > 199:
                    parameters["stairCase"][modality].addResponse(isMore, intensity=199)
                else:
                    parameters["stairCase"][modality].addResponse(isMore)

                # Store posteriors in list for each trials
                parameters["staircaisePosteriors"][modality].append(
                    parameters["stairCase"][modality]._psi._probLambda[0, :, :, 0]
                )

                # Save estimated threshold and slope for each trials
                estimatedThreshold, estimatedSlope = parameters["stairCase"][
                    modality
                ].estimateLambda()

            print(
                f"... Initial BPM: {listenBPM} - Staircase value: {alpha} "
                f"- Response: {decision} ({isCorrect})"
            )

            # Store results
            parameters["results_df"] = pd.concat(
                [
                    parameters["results_df"],
                    pd.DataFrame(
                        {
                            "TrialType": [trialType],
                            "Condition": [condition],
                            "Modality": [modality],
                            "StairCond": [stairCond],
                            "Decision": [decision],
                            "DecisionRT": [decisionRT],
                            "Confidence": [confidence],
                            "ConfidenceRT": [confidenceRT],
                            "Alpha": [alpha],
                            "listenBPM": [listenBPM],
                            "responseBPM": [responseBPM],
                            "ResponseCorrect": [isCorrect],
                            "DecisionProvided": [respProvided],
                            "RatingProvided": [ratingProvided],
                            "nTrials": [nTrial],
                            "EstimatedThreshold": [estimatedThreshold],
                            "EstimatedSlope": [estimatedSlope],
                            "StartListening": [startTrigger],
                            "StartDecision": [soundTrigger],
                            "ResponseMade": [responseMadeTrigger],
                            "RatingStart": [ratingStartTrigger],
                            "RatingEnds": [ratingEndTrigger],
                            "endTrigger": [endTrigger],
                        }
                    ),
                ],
                ignore_index=True,
            )

            # Save the results at each iteration
            parameters["results_df"].to_csv(
                parameters["resultPath"]
                + "/"
                + parameters["participant"]
                + parameters["session"]
                + ".txt",
                index=False,
            )

            # Breaks
            n_completed = nTrial + 1
            if (n_completed % parameters["nBreaking"] == 0) & (
                n_completed != parameters["nTrials"]
            ):
                message = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    text=parameters["texts"]["textBreaks"],
                )
                percent_completed = round((n_completed / parameters["nTrials"]) * 100, 2)
                remain = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    pos=(0.0, 0.2),
                    text=f"{percent_completed}% completed",
                )
                remain.draw()
                message.draw()
                parameters["win"].flip()
                _save_oximeter_recording(
                    parameters["oxiTask"],
                    f"{parameters['resultPath']}/{parameters['participant']}_ppg_{n_completed}.txt",
                )

                # Wait for participant input before continue
                waitInput(parameters)

                # Fixation cross
                fixation = visual.GratingStim(
                    win=parameters["win"], mask="cross", size=0.1, pos=[0, 0], sf=0
                )
                fixation.draw()
                parameters["win"].flip()

                # Reset recording when ready
                parameters["oxiTask"].setup()
                parameters["oxiTask"].read(duration=1)
    except (KeyboardInterrupt, SystemExit):
        if not parameters["results_df"].empty:
            _save_task_outputs(parameters, n_trial=nTrial, partial=True)
        raise

    if nTrial is None:
        print("Task ended before any experimental trials were completed.")
        return

    _save_task_outputs(parameters, n_trial=nTrial, partial=False)

    # End of the task
    end = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.0),
        text=parameters["texts"]["done"],
    )
    end.draw()
    parameters["win"].flip()
    core.wait(3)


def trial(
    parameters: dict,
    alpha: float,
    modality: str,
    confidenceRating: bool = True,
    feedback: bool = False,
    nTrial: Optional[int] = None,
) -> Tuple[
    str,
    float,
    float,
    Optional[str],
    Optional[float],
    Optional[float],
    Optional[float],
    float,
    Optional[bool],
    bool,
    bool,
    float,
    float,
    float,
    Optional[float],
    Optional[float],
    float,
]:
    """Run one trial of the Heart Rate Discrimination task.

    Parameters
    ----------
    parameter : dict
        Task parameters.
    alpha : float
        The intensity of the stimulus, from the staircase procedure.
    modality : str
        The modality, can be `'Intero'` or `'Extro'` if an exteroceptive
        control condition has been added.
    confidenceRating : boolean
        If `False`, do not display confidence rating scale.
    feedback : boolean
        If `True`, will provide feedback.
    nTrial : int
        Trial number (optional).

    Returns
    -------
    condition : str
        The trial condition, can be `'Higher'` or `'Lower'` depending on the
        alpha value.
    listenBPM : float
        The frequency of the tones (exteroceptive condition) or of the heart
        rate (interoceptive condition), expressed in BPM.
    responseBPM : float
        The frequency of thefeebdack tones, expressed in BPM.
    decision : str
        The participant decision. Can be `'up'` (the participant indicates
        the beats are faster than the recorded heart rate) or `'down'` (the
        participant indicates the beats are slower than recorded heart rate).
    decisionRT : float
        The response time from sound start to choice (seconds).
    confidence : int
        If confidenceRating is *True*, the confidence of the participant. The
        range of the scale is defined in `parameters['confScale']`. Default is
        `[1, 7]`.
    confidenceRT : float
        The response time (RT) for the confidence rating scale.
    alpha : int
        The difference between the true heart rate and the delivered tone BPM.
        Alpha is defined by the stairCase.intensities values and is updated
        on each trial.
    isCorrect : int
        `0` for incorrect response, `1` for correct responses. Note that this
        value is not feeded to the staircase when using the (Yes/No) version
        of the task, but instead will check if the response is `'More'` or not.
    respProvided : bool
        Was the decision provided (`True`) or not (`False`).
    ratingProvided : bool
        Was the rating provided (`True`) or not (`False`). If no decision was
        provided, the ratig scale is not proposed and no ratings can be provided.
    startTrigger, soundTrigger, responseMadeTrigger, ratingStartTrigger,\
        ratingEndTrigger, endTrigger : float
        Time stamp of key timepoints inside the trial.
    """
    from psychopy import core, event, sound, visual

    # Print infos at each trial start
    print(f"Starting trial - Intensity: {alpha} - Modality: {modality}")

    parameters["win"].mouseVisible = parameters["device"] == "mouse"

    # Restart the trial until participant provide response on time
    confidence, confidenceRT, isCorrect, ratingProvided = None, None, None, False

    # Fixation cross
    fixation = visual.GratingStim(
        win=parameters["win"], mask="cross", size=0.1, pos=[0, 0], sf=0
    )
    fixation.draw()
    parameters["win"].flip()
    core.wait(np.random.uniform(parameters["isi"][0], parameters["isi"][1]))

    keys = event.getKeys()
    if "escape" in keys:
        print("User abort")
        parameters["win"].close()
        core.quit()

    if modality == "Intero":

        ###########
        # Recording
        ###########
        messageRecord = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text=parameters["texts"]["textHeartListening"],
        )
        messageRecord.draw()

        # Start recording trigger
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = 2  # Trigger

        parameters["heartLogo"].draw()
        parameters["win"].flip()

        startTrigger = time.time()

        # Recording
        while True:

            # Read the pulse oximeter using whichever systole API is active.
            read_result = parameters["oxiTask"].read(duration=5.0)
            if hasattr(read_result, "bpm"):
                # Nonin3231USB exposes BPM values directly.
                bpm = pd.Series(read_result.bpm)[-5:]
                signal = bpm
            else:
                # Oximeter/test mode exposes raw PPG, so derive BPM from peaks.
                signal = pd.Series(read_result.recording[-75 * 6 :])
                _, peaks = ppg_peaks(
                    signal, sfreq=75, new_sfreq=1000, clipping=True
                )
                bpm = pd.Series(60000 / np.diff(np.where(peaks[-5000:])[0]))

            print(f"... bpm: {[round(i) for i in bpm]}")

            # Prevent crash if NaN value
            if np.isnan(bpm).any() or (bpm is None) or (bpm.size == 0):
                message = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    text=parameters["texts"]["checkOximeter"],
                    color="red",
                )
                message.draw()
                parameters["win"].flip()
                core.wait(2)

            else:
                # Check for extreme heart rate values, if crosses theshold,
                # hold the task until resolved. Cutoff values determined in
                # parameters to correspond to biologically unlikely values.
                if not (
                    (np.any(bpm < parameters["HRcutOff"][0]))
                    or (np.any(bpm > parameters["HRcutOff"][1]))
                ):
                    listenBPM = round(bpm.mean() * 2) / 2  # Round nearest .5
                    break
                else:
                    message = visual.TextStim(
                        parameters["win"],
                        height=parameters["textSize"],
                        text=parameters["texts"]["stayStill"],
                        color="red",
                    )
                    message.draw()
                    parameters["win"].flip()
                    core.wait(2)

    elif modality == "Extero":

        ###########
        # Recording
        ###########
        messageRecord = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text=parameters["texts"]["textToneListening"],
        )
        messageRecord.draw()

        # Start recording trigger
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = 2  # Trigger

        parameters["listenLogo"].draw()
        parameters["win"].flip()

        startTrigger = time.time()

        # Random selection of HR frequency
        listenBPM = np.random.choice(np.arange(40, 100, 0.5))

        # Play the corresponding beat file
        listenFile = str(SOUNDS_DIR / f"{listenBPM}.wav")
        print(f"...loading file (Listen): {listenFile}")

        # Play selected BPM frequency
        listenSound = sound.Sound(listenFile)
        listenSound.play()
        core.wait(5)
        listenSound.stop()

    else:
        raise ValueError("Invalid modality")

    # Fixation cross
    fixation = visual.GratingStim(
        win=parameters["win"], mask="cross", size=0.1, pos=[0, 0], sf=0
    )
    fixation.draw()
    parameters["win"].flip()
    core.wait(0.5)

    #######
    # Sound
    #######

    # Generate actual stimulus frequency
    condition = "Less" if alpha < 0 else "More"

    # Check for extreme alpha values, e.g. if alpha changes massively from
    # trial to trial.
    if (listenBPM + alpha) < 15:
        responseBPM = 15.0
    elif (listenBPM + alpha) > 199:
        responseBPM = 199.0
    else:
        responseBPM = listenBPM + alpha
    responseFile = str(SOUNDS_DIR / f"{responseBPM}.wav")
    print(f"...loading file (Response): {responseFile}")

    # Play selected BPM frequency
    responseSound = sound.Sound(responseFile)
    if modality == "Intero":
        parameters["heartLogo"].autoDraw = True
    elif modality == "Extero":
        parameters["listenLogo"].autoDraw = True
    else:
        raise ValueError("Invalid modality provided")
    # Record participant response (+/-)
    message = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0, 0.4),
        text=parameters["texts"]["Decision"][modality],
    )
    message.autoDraw = True

    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["responseText"],
        pos=(0.0, -0.4),
    )
    press.autoDraw = True

    # Sound trigger
    parameters["oxiTask"].readInWaiting()
    parameters["oxiTask"].channels["Channel_0"][-1] = 3
    soundTrigger = time.time()
    parameters["win"].flip()

    #####################
    # Esimation Responses
    #####################
    (
        responseMadeTrigger,
        responseTrigger,
        respProvided,
        decision,
        decisionRT,
        isCorrect,
    ) = responseDecision(responseSound, parameters, feedback, condition)
    press.autoDraw = False
    message.autoDraw = False
    if modality == "Intero":
        parameters["heartLogo"].autoDraw = False
    elif modality == "Extero":
        parameters["listenLogo"].autoDraw = False
    else:
        raise ValueError("Invalid modality provided")
    ###################
    # Confidence Rating
    ###################

    # Record participant confidence
    if (confidenceRating is True) & (respProvided is True):

        # Confidence rating start trigger
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = 4  # Trigger

        # Confidence rating scale
        ratingStartTrigger: Optional[float] = time.time()
        (
            confidence,
            confidenceRT,
            ratingProvided,
            ratingEndTrigger,
        ) = confidenceRatingTask(parameters)
    else:
        ratingStartTrigger, ratingEndTrigger = None, None

    # Confidence rating end trigger
    parameters["oxiTask"].readInWaiting()
    parameters["oxiTask"].channels["Channel_0"][-1] = 5
    endTrigger = time.time()

    # Save PPG signal
    if nTrial is not None:  # Not during the tutorial
        if modality == "Intero":
            this_df = None
            # Save physio signal
            this_df = pd.DataFrame(
                {
                    "signal": signal,
                    "nTrial": pd.Series([nTrial] * len(signal), dtype="category"),
                }
            )

            parameters["signal_df"] = pd.concat(
                [parameters["signal_df"], this_df], ignore_index=True
            )

    return (
        condition,
        listenBPM,
        responseBPM,
        decision,
        decisionRT,
        confidence,
        confidenceRT,
        alpha,
        isCorrect,
        respProvided,
        ratingProvided,
        startTrigger,
        soundTrigger,
        responseMadeTrigger,
        ratingStartTrigger,
        ratingEndTrigger,
        endTrigger,
    )


def waitInput(parameters: dict):
    """Wait for participant input before continue"""

    from psychopy import core, event

    if parameters["device"] == "keyboard":
        while True:
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()
            elif parameters["startKey"] in keys:
                break
    elif parameters["device"] == "mouse":
        parameters["myMouse"].clickReset()
        while True:
            buttons = parameters["myMouse"].getPressed()
            if buttons != [0, 0, 0]:
                break
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()


def _draw_instruction_buttons(parameters: dict, allow_back: bool):
    """Draw navigation controls for tutorial instruction pages."""

    from psychopy import visual

    controls = {}
    button_width, button_height = 0.22, 0.08

    next_box = visual.Rect(
        parameters["win"],
        width=button_width,
        height=button_height,
        pos=(0.28, -0.42),
        lineColor="white",
        fillColor=None,
    )
    next_text = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=next_box.pos,
        text=parameters["texts"].get("textNextButton", "Next"),
    )
    next_box.draw()
    next_text.draw()
    controls["next"] = next_box

    if allow_back:
        back_box = visual.Rect(
            parameters["win"],
            width=button_width,
            height=button_height,
            pos=(-0.28, -0.42),
            lineColor="white",
            fillColor=None,
        )
        back_text = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=back_box.pos,
            text=parameters["texts"].get("textBackButton", "Back"),
        )
        back_box.draw()
        back_text.draw()
        controls["back"] = back_box

    return controls


def _wait_for_instruction_navigation(
    parameters: dict, controls: dict, allow_back: bool
) -> str:
    """Wait for an explicit next/back action on tutorial instruction pages."""

    from psychopy import core, event

    if parameters["device"] == "keyboard":
        back_keys = ["left", "backspace"]
        while True:
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()
            if allow_back and any(key in keys for key in back_keys):
                return "back"
            if parameters["startKey"] in keys or "right" in keys:
                return "next"

    if parameters["device"] == "mouse":
        mouse = parameters["myMouse"]
        while any(mouse.getPressed()):
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()
            core.wait(0.01)

        mouse.clickReset()
        while True:
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()

            buttons = mouse.getPressed()
            if buttons[0]:
                mouse_pos = mouse.getPos()
                if allow_back and controls["back"].contains(mouse_pos):
                    return "back"
                if controls["next"].contains(mouse_pos):
                    return "next"

                while any(mouse.getPressed()):
                    core.wait(0.01)

    raise ValueError("device should be 'keyboard' or 'mouse'")


def _run_instruction_pages(parameters: dict, draw_pages: list) -> None:
    """Run tutorial instruction pages with explicit next/back navigation."""

    page_idx = 0
    while page_idx < len(draw_pages):
        allow_back = page_idx > 0
        draw_pages[page_idx]()
        controls = _draw_instruction_buttons(parameters, allow_back)
        parameters["win"].flip()

        action = _wait_for_instruction_navigation(parameters, controls, allow_back)
        if action == "back":
            page_idx -= 1
        else:
            page_idx += 1


def tutorial(parameters: dict):
    """Run tutorial before task run.

    Parameters
    ----------
    parameters : dict
        Task parameters.

    """

    from psychopy import core, event, visual

    def add_page(pages, *stims):
        def draw_page():
            for stim in stims:
                stim.draw()

        pages.append(draw_page)

    intro = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial1"],
    )
    pulse1 = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["texts"]["pulseTutorial1"],
    )

    setup_pages = []
    add_page(setup_pages, intro)
    add_page(setup_pages, pulse1, parameters["pulseSchema"])

    if parameters["texts"]["pulseTutorial2"]:
        pulse2 = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text=parameters["texts"]["pulseTutorial2"],
        )
        pulse3 = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, -0.2),
            text=parameters["texts"]["pulseTutorial3"],
        )
        add_page(setup_pages, pulse2, pulse3)

    _run_instruction_pages(parameters, setup_pages)

    pulse4 = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["texts"]["pulseTutorial4"],
    )
    pulse4.draw()
    parameters["handSchema"].draw()
    parameters["win"].flip()

    # Record number
    nFinger = ""
    finger_key_list = digit_key_list(1, 5)
    while True:
        # Record new key
        key = event.waitKeys(keyList=finger_key_list)
        if key:
            digit = parse_digit_key(key[0])
            if digit is None:
                continue
            nFinger += digit

            # Save the finger number in the task parameters dictionary
            parameters["nFinger"] = nFinger

            core.wait(0.5)
            break

    recording = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["texts"]["Tutorial2"],
    )
    listenIcon = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["texts"]["Tutorial3_icon"],
    )
    listenResponse = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.0),
        text=parameters["texts"]["Tutorial3_responses"],
    )

    task_pages = []
    add_page(task_pages, recording, parameters["heartLogo"])
    add_page(task_pages, listenIcon, parameters["heartLogo"])
    add_page(task_pages, listenResponse)

    if parameters["ExteroCondition"] is True:
        exteroText = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, -0.2),
            text=parameters["texts"]["Tutorial3bis"],
        )
        exteroResponse = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.0),
            text=parameters["texts"]["Tutorial3ter"],
        )
        add_page(task_pages, exteroText, parameters["listenLogo"])
        add_page(task_pages, exteroResponse)

    confidenceText = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial4"],
    )
    add_page(task_pages, confidenceText)

    _run_instruction_pages(parameters, task_pages)

    ###################
    # Practice trials
    ###################
    parameters["oxiTask"].setup().read(duration=2)

    practice_modalities = ["Intero"]
    if parameters["ExteroCondition"] is True:
        practice_modalities.append("Extero")

    for modality in practice_modalities:
        for _ in range(parameters.get("nPractice", 1)):
            condition = np.random.choice(["More", "Less"])
            alpha = -20.0 if condition == "Less" else 20.0
            _ = trial(
                parameters,
                alpha,
                modality,
                feedback=True,
                confidenceRating=True,
            )

    taskPresentation = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial5"],
    )
    taskStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial6"],
    )
    end_pages = []
    add_page(end_pages, taskPresentation)
    add_page(end_pages, taskStart)
    _run_instruction_pages(parameters, end_pages)


def responseDecision(
    this_hr,
    parameters: dict,
    feedback: bool,
    condition: str,
) -> Tuple[
    float, Optional[float], bool, Optional[str], Optional[float], Optional[bool]
]:
    """Recording response during the decision phase.

    Parameters
    ----------
    this_hr : psychopy sound instance
        The sound .wav file to play.
    parameters : dict
        Parameters dictionary.
    feedback : bool
        If `True`, provide feedback after decision.
    condition : str
        The trial condition [`'More'` or `'Less'`] used to check is response is
        correct or not.

    Returns
    -------
    responseMadeTrigger : float
        Time stamp of response provided.
    responseTrigger : float
        Time stamp of response start.
    respProvided : bool
        `True` if the response was provided, `False` otherwise.
    decision : str or None
        The decision made ('Higher', 'Lower' or None)
    decisionRT : float
        Decision response time (seconds).
    isCorrect : bool or None
        `True` if the response provided was correct, `False` otherwise.

    """

    from psychopy import core, event, visual

    print("...starting decision phase.")

    decision, decisionRT, isCorrect = None, None, None
    responseTrigger = time.time()

    if parameters["device"] == "keyboard":
        this_hr.play()
        clock = core.Clock()
        responseKey = event.waitKeys(
            keyList=parameters["allowedKeys"],
            maxWait=parameters["respMax"],
            timeStamped=clock,
        )
        this_hr.stop()

        responseMadeTrigger = time.time()

        # Check for response provided by the participant
        if not responseKey:
            respProvided = False
            decision, decisionRT = None, None
            # Record participant response (+/-)
            message = visual.TextStim(
                parameters["win"], height=parameters["textSize"], text=parameters["texts"]["tooLate"]
            )
            message.draw()
            parameters["win"].flip()
            core.wait(1)
        else:
            respProvided = True
            decision = responseKey[0][0]
            decisionRT = responseKey[0][1]

            # Translate keyboard response to decision labels if mapping provided
            response_keys = parameters.get("response_keys")
            if response_keys:
                key_to_condition = {key: cond for cond, key in response_keys.items()}
                decision_label = key_to_condition.get(decision, decision)
                isCorrect = decision_label == condition
                decision = decision_label
            else:
                isCorrect = True if (decision == condition) else False

            # Read oximeter
            parameters["oxiTask"].readInWaiting()

            # Feedback
            if feedback is True:
                if isCorrect is False:
                    acc = visual.TextStim(
                        parameters["win"],
                        height=parameters["textSize"],
                        color="red",
                        text="False",
                    )
                    acc.draw()
                    parameters["win"].flip()
                    core.wait(2)
                elif isCorrect is True:
                    acc = visual.TextStim(
                        parameters["win"],
                        height=parameters["textSize"],
                        color="green",
                        text="Correct",
                    )
                    acc.draw()
                    parameters["win"].flip()
                    core.wait(2)

    if parameters["device"] == "mouse":
        button_to_idx = {"left": 0, "middle": 1, "right": 2}
        mouse_response_buttons = parameters.get(
            "mouse_response_buttons", {"Less": "left", "More": "right"}
        )
        less_button_idx = button_to_idx[mouse_response_buttons["Less"]]
        more_button_idx = button_to_idx[mouse_response_buttons["More"]]

        # Initialise response feedback
        slower = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            color="white",
            text=parameters["texts"]["slower"],
            pos=(-0.2, 0.2),
        )
        faster = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            color="white",
            text=parameters["texts"]["faster"],
            pos=(0.2, 0.2),
        )
        slower.draw()
        faster.draw()
        parameters["win"].flip()

        this_hr.play()
        clock = core.Clock()
        clock.reset()
        parameters["myMouse"].clickReset()
        buttons, decisionRT = parameters["myMouse"].getPressed(getTime=True)
        while True:
            buttons, decisionRT = parameters["myMouse"].getPressed(getTime=True)
            trialdur = clock.getTime()
            parameters["oxiTask"].readInWaiting()
            if buttons[less_button_idx]:
                decisionRT = decisionRT[less_button_idx]
                decision, respProvided = "Less", True
                slower.color = "blue"
                slower.draw()
                parameters["win"].flip()

                # Show feedback for .5 seconds if enough time
                remain = parameters["respMax"] - trialdur
                pauseFeedback = 0.5 if (remain > 0.5) else remain
                core.wait(pauseFeedback)
                break
            elif buttons[more_button_idx]:
                decisionRT = decisionRT[more_button_idx]
                decision, respProvided = "More", True
                faster.color = "blue"
                faster.draw()
                parameters["win"].flip()

                # Show feedback for .5 seconds if enough time
                remain = parameters["respMax"] - trialdur
                pauseFeedback = 0.5 if (remain > 0.5) else remain
                core.wait(pauseFeedback)
                break
            elif trialdur > parameters["respMax"]:  # if too long
                respProvided = False
                decisionRT = None
                break
            else:
                slower.draw()
                faster.draw()
                parameters["win"].flip()
        responseMadeTrigger = time.time()
        this_hr.stop()

        # Check for response provided by the participant
        if respProvided is False:
            # Record participant response (+/-)
            message = visual.TextStim(
                parameters["win"],
                height=parameters["textSize"],
                text=parameters["texts"]["tooLate"],
                color="red",
                pos=(0.0, -0.2),
            )
            message.draw()
            parameters["win"].flip()
            core.wait(0.5)
        else:
            # Is the answer Correct?
            isCorrect = True if (decision == condition) else False
            # Feedback
            if feedback is True:
                if isCorrect == 0:
                    textFeedback = parameters["texts"]["incorrectResponse"]
                else:
                    textFeedback = parameters["texts"]["correctResponse"]
                colorFeedback = "red" if isCorrect == 0 else "green"
                acc = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    pos=(0.0, -0.2),
                    color=colorFeedback,
                    text=textFeedback,
                )
                acc.draw()
                parameters["win"].flip()
                core.wait(1)

    return (
        responseMadeTrigger,
        responseTrigger,
        respProvided,
        decision,
        decisionRT,
        isCorrect,
    )


def confidenceRatingTask(
    parameters: dict,
) -> Tuple[Optional[float], Optional[float], bool, Optional[float]]:
    """Confidence rating scale, using keyboard or mouse inputs.

    Parameters
    ----------
    parameters : dict
        Parameters dictionary.

    """

    from psychopy import core, event, visual

    print("...starting confidence rating.")

    # Initialise default values
    confidence, confidenceRT = None, None
    ratingProvided = False

    if parameters["device"] == "keyboard":

        markerStart = np.random.choice(
            np.arange(parameters["confScale"][0], parameters["confScale"][1] + 1)
        )
        slider = visual.Slider(
            win=parameters["win"],
            pos=(0, -0.2),
            size=(0.7, 0.1),
            ticks=np.arange(parameters["confScale"][0], parameters["confScale"][1] + 1),
            labels=parameters["labelsRating"],
            granularity=1,
            style="rating",
            font="Arial",
            color="LightGray",
            labelHeight=0.1 * 0.6,
        )
        slider.markerPos = markerStart

        message = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            text=parameters["texts"]["Confidence"],
        )

        event.clearEvents(eventType="keyboard")
        clock = core.Clock()
        while clock.getTime() < parameters["maxRatingTime"]:
            keys = event.getKeys(keyList=["left", "right", "down", "escape"])
            for key in keys:
                if key == "escape":
                    print("User abort")
                    parameters["win"].close()
                    core.quit()
                elif key == "left":
                    slider.markerPos = max(
                        parameters["confScale"][0], slider.markerPos - 1
                    )
                elif key == "right":
                    slider.markerPos = min(
                        parameters["confScale"][1], slider.markerPos + 1
                    )
                elif (key == "down") and (clock.getTime() > parameters["minRatingTime"]):
                    ratingProvided = True
                    confidence = slider.markerPos
                    confidenceRT = clock.getTime()
                    slider.marker.color = "green"
                    break
            slider.draw()
            message.draw()
            parameters["win"].flip()
            if ratingProvided:
                core.wait(0.2)
                break

        if ratingProvided:
            print(
                f"... Confidence level: {confidence}"
                + f" with response time {round(confidenceRT, 2)} seconds"
            )

    elif parameters["device"] == "mouse":

        parameters["win"].mouseVisible = True
        message = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0, 0.2),
            text=parameters["texts"]["Confidence"],
        )
        slider = visual.Slider(
            win=parameters["win"],
            name="slider",
            pos=(0, -0.2),
            size=(0.7, 0.1),
            labels=parameters["texts"]["VASlabels"],
            granularity=1,
            ticks=(0, 100),
            style=("rating"),
            font="Arial",
            color="LightGray",
            flip=False,
            labelHeight=0.1 * 0.6,
        )
        slider.marker.size = (0.03, 0.03)
        slider.markerPos = 50
        clock = core.Clock()
        parameters["myMouse"].clickReset()
        left_was_pressed = False
        pressed_since_last_release = False
        slider_half_width = 0.35

        while True:
            trialdur = clock.getTime()
            keys = event.getKeys(keyList=["escape"])
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()

            if trialdur > parameters["maxRatingTime"]:  # if too long
                ratingProvided = False
                confidenceRT = None

                # Text feedback if no rating provided
                message = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    text=parameters["texts"]["tooLate"],
                    color="red",
                    pos=(0.0, -0.2),
                )
                message.draw()
                parameters["win"].flip()
                core.wait(0.5)
                break

            buttons = parameters["myMouse"].getPressed()
            left_pressed = bool(buttons[0]) if len(buttons) > 0 else False

            if left_pressed:
                pressed_since_last_release = True
                mouse_x, _ = parameters["myMouse"].getPos()
                clamped_x = min(max(mouse_x, -slider_half_width), slider_half_width)
                slider.markerPos = ((clamped_x + slider_half_width) / (2 * slider_half_width)) * 100
            elif left_was_pressed:
                if pressed_since_last_release and (trialdur > parameters["minRatingTime"]):
                    confidence, confidenceRT, ratingProvided = (
                        slider.markerPos,
                        clock.getTime(),
                        True,
                    )
                    print(
                        f"... Confidence level: {confidence}"
                        + f" with response time {round(confidenceRT, 2)} seconds"
                    )
                    slider.marker.color = "green"
                    slider.draw()
                    message.draw()
                    parameters["win"].flip()
                    core.wait(0.2)
                    break
                pressed_since_last_release = False

            left_was_pressed = left_pressed
            slider.draw()
            message.draw()
            parameters["win"].flip()
    else:
        raise ValueError("device should be 'keyboard' or 'mouse'")

    ratingEndTrigger = time.time()
    parameters["win"].flip()

    return confidence, confidenceRT, ratingProvided, ratingEndTrigger
