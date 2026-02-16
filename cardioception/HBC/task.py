# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

from typing import Optional, Tuple

import numpy as np
import pandas as pd

from cardioception.input import digit_key_list, parse_digit_key


def _start_key_list(parameters: dict) -> list:
    return [parameters["startKey"]]


def _fire_trigger(parameters: dict, name: str) -> None:
    trigger = parameters["triggers"].get(name)
    if callable(trigger):
        trigger()


def run(
    parameters: dict,
    runTutorial: bool = True,
):
    """Run the entire task sequence.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    tutorial : bool
        If `True`, will present a tutorial with 10 training trial with feedback and 5
        trials with confidence rating.

    """

    from psychopy import core, visual

    # Run tutorial
    if runTutorial is True:
        tutorial(parameters)

    # Rest
    if parameters["restPeriod"] is True:
        rest(parameters, duration=parameters["restLength"])

    for condition, duration, nTrial in zip(
        parameters["conditions"],
        parameters["times"],
        range(0, len(parameters["conditions"])),
    ):

        _fire_trigger(parameters, "trialStart")

        nCount, confidence, confidenceRT = trial(
            condition, duration, nTrial, parameters
        )

        _fire_trigger(parameters, "trialStop")

        # Store results in a DataFrame
        parameters["results_df"] = pd.concat(
            [
                parameters["results_df"],
                pd.DataFrame(
                    {
                        "nTrial": [nTrial],
                        "Reported": [nCount],
                        "Condition": [condition],
                        "Duration": [duration],
                        "Confidence": [confidence],
                        "ConfidenceRT": [confidenceRT],
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

    # Save results
    parameters["results_df"].to_csv(
        parameters["resultPath"]
        + "/"
        + parameters["participant"]
        + parameters["session"]
        + "_final.txt",
        index=False,
    )

    # End of the task
    end = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.0),
        text="You have completed the task. Thank you for your participation.",
    )
    end.draw()
    parameters["win"].flip()
    core.wait(3)


def trial(
    condition: str,
    duration: int,
    nTrial: int,
    parameters: dict,
) -> Tuple[Optional[int], Optional[float], Optional[float]]:
    """Run one trial.

    Parameters
    ----------
    condition : str
        The trial condition, can be `"Rest"` or `"Count"`.
    duration : int
        The lenght of the recording (in seconds).
    ntrial : int
        Trial number.
    parameters : dict
        Task parameters.

    Returns
    -------
    nCount : int
        The number of heartbeat estimated by the participant.
    confidence : int
        The confidence in the estimation of the heartbeat provided by the
        participant.
    confidenceRT : float
        The response time to provide confidence rating.

    """

    from psychopy import core, event, visual

    # Initialize default values
    confidence, confidenceRT = None, None
    nCounts: str = ""

    # Ask the participant to press 'Space' (default) to start the trial
    messageStart = visual.TextStim(
        parameters["win"], height=parameters["textSize"], text="Press space to continue"
    )
    messageStart.draw()
    parameters["win"].flip()
    event.waitKeys(keyList=_start_key_list(parameters))
    parameters["win"].flip()

    parameters["oxiTask"].setup()
    parameters["oxiTask"].read(duration=2)

    # Show instructions
    if condition == "Rest":
        message = visual.TextStim(
            parameters["win"],
            text=parameters["texts"]["Rest"],
            pos=(0.0, 0.2),
            height=parameters["textSize"],
        )
        message.draw()
        parameters["restLogo"].draw()
    elif (condition == "Count") | (condition == "Training"):
        message = visual.TextStim(
            parameters["win"],
            text=parameters["texts"]["Count"],
            pos=(0.0, 0.2),
            height=parameters["textSize"],
        )
        message.draw()
        parameters["heartLogo"].draw()
    parameters["win"].flip()

    # Wait for a beat to start the task
    parameters["oxiTask"].waitBeat()
    core.wait(3)

    # Sound signaling trial start
    if (condition == "Count") | (condition == "Training"):
        parameters["oxiTask"].readInWaiting()
        # Add event marker
        parameters["oxiTask"].channels["Channel_0"][-1] = 1
        parameters["noteStart"].play()
        _fire_trigger(parameters, "listeningStart")
        core.wait(1)

    # Record for a desired time length
    parameters["oxiTask"].read(duration=duration - 1)

    # Sound signaling trial stop
    if (condition == "Count") | (condition == "Training"):
        # Add event marker
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = 2
        parameters["noteStop"].play()
        _fire_trigger(parameters, "listeningStop")
        core.wait(3)
        parameters["oxiTask"].readInWaiting()

    # Hide instructions
    parameters["win"].flip()

    # Save recording
    parameters["oxiTask"].save(
        parameters["resultPath"]
        + "/"
        + parameters["participant"]
        + str(nTrial)
        + "_"
        + str(nTrial)
    )

    ###############################
    # Record participant estimation
    ###############################
    if (condition == "Count") | (condition == "Training"):
        # Ask the participant to press 'Space' (default) to start the trial
        messageCount = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0, 0.2),
            text=parameters["texts"]["nCount"],
        )
        messageCount.draw()
        parameters["win"].flip()

        _fire_trigger(parameters, "decisionStart")

        nCounts = ""
        count_key_list = [
            "escape",
            "backspace",
            "return",
            "enter",
            "num_enter",
            "numpad_enter",
            "kp_enter",
            *digit_key_list(0, 9),
        ]
        while True:

            # Record new key
            key = event.waitKeys(keyList=count_key_list)

            if key[0] == "escape":
                keys = event.getKeys()
                if "escape" in keys:
                    print("User abort")
                    parameters["win"].close()
                    core.quit()
            if key[0] == "backspace":
                if nCounts:
                    nCounts = nCounts[:-1]
            elif key[0] in {"return", "enter", "num_enter", "numpad_enter", "kp_enter"}:
                if not all(char.isdigit() for char in nCounts):
                    messageError = visual.TextStim(
                        parameters["win"],
                        height=parameters["textSize"],
                        pos=(0, 0.2),
                        text="You should only provide numbers",
                    )
                    messageError.draw()
                    parameters["win"].flip()
                    core.wait(2)
                elif nCounts == "":
                    messageError = visual.TextStim(
                        parameters["win"],
                        height=parameters["textSize"],
                        pos=(0, 0.2),
                        text="You should provide numbers",
                    )
                    messageError.draw()
                    parameters["win"].flip()
                    core.wait(2)
                else:
                    break

            else:
                if key:
                    digit = parse_digit_key(key[0])
                    if digit is not None:
                        nCounts += digit

            # Show the text on the screen
            recordedText = visual.TextStim(
                parameters["win"], height=parameters["textSize"], text=nCounts
            )
            recordedText.draw()
            messageCount.draw()
            parameters["win"].flip()

        _fire_trigger(parameters, "decisionStop")

        ##############
        # Rating scale
        ##############
        if parameters["rating"] is True:
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
                color="LightGray",
                labelHeight=0.1 * 0.6,
            )
            slider.markerPos = markerStart
            message = visual.TextStim(
                parameters["win"],
                text=parameters["texts"]["confidence"],
                height=parameters["textSize"],
            )

            _fire_trigger(parameters, "confidenceStart")
            event.clearEvents(eventType="keyboard")
            rating_clock = core.Clock()
            while True:
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
                    elif key == "down":
                        confidence = slider.markerPos
                        confidenceRT = rating_clock.getTime()
                        break
                if confidence is not None:
                    slider.marker.color = "green"
                    slider.draw()
                    message.draw()
                    parameters["win"].flip()
                    core.wait(0.2)
                    break
                message.draw()
                slider.draw()
                parameters["win"].flip()
            _fire_trigger(parameters, "confidenceStop")

    finalCount = int(nCounts) if nCounts else None

    return finalCount, confidence, confidenceRT


def tutorial(parameters: dict):
    """Run tutorial for the Heartbeat Counting Task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : `psychopy.visual.window` or None
        The window in which to draw objects.
    """

    from psychopy import event, visual

    # Tutorial 1
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial1"],
    )
    messageStart.draw()
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text="Please press SPACE to continue",
        pos=(0.0, -0.4),
    )
    press.draw()
    parameters["win"].flip()
    event.waitKeys(keyList=_start_key_list(parameters))

    # Tutorial 2
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.2),
        text=parameters["texts"]["Tutorial2"],
    )
    messageStart.draw()
    parameters["heartLogo"].draw()
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text="Please press SPACE to continue",
        pos=(0.0, -0.4),
    )
    press.draw()
    parameters["win"].flip()
    event.waitKeys(keyList=_start_key_list(parameters))

    # Tutorial 3
    if parameters["taskVersion"] == "Shandry":

        messageStart = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text=parameters["texts"]["Tutorial3"],
        )
        messageStart.draw()
        parameters["restLogo"].draw()
        press = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            text="Please press SPACE to continue",
            pos=(0.0, -0.4),
        )
        press.draw()
        parameters["win"].flip()
        event.waitKeys(keyList=_start_key_list(parameters))

    # Tutorial 4
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial4"],
    )
    messageStart.draw()
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text="Please press SPACE to continue",
        pos=(0.0, -0.4),
    )
    press.draw()
    parameters["win"].flip()

    event.waitKeys(keyList=_start_key_list(parameters))

    # Tutorial 5
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial5"],
    )
    messageStart.draw()
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text="Please press SPACE to continue",
        pos=(0.0, -0.4),
    )
    press.draw()
    parameters["win"].flip()
    event.waitKeys(keyList=_start_key_list(parameters))

    # Tutorial 6
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial6"],
    )
    messageStart.draw()
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text="Please press SPACE to continue",
        pos=(0.0, -0.4),
    )
    press.draw()
    parameters["win"].flip()
    event.waitKeys(keyList=_start_key_list(parameters))

    # Tutorial 7
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial7"],
    )
    messageStart.draw()
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text="Please press SPACE to continue",
        pos=(0.0, -0.4),
    )
    press.draw()
    parameters["win"].flip()
    event.waitKeys(keyList=_start_key_list(parameters))

    # Tutorial 8
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial8"],
    )
    messageStart.draw()
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text="Please press SPACE to continue",
        pos=(0.0, -0.4),
    )
    press.draw()
    parameters["win"].flip()
    event.waitKeys(keyList=_start_key_list(parameters))

    # Practice trial
    _ = trial("Count", 15, 0, parameters)

    # Tutorial 9
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial9"],
    )
    messageStart.draw()
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text="Please press SPACE to continue",
        pos=(0.0, -0.4),
    )
    press.draw()
    parameters["win"].flip()
    event.waitKeys(keyList=_start_key_list(parameters))


def rest(parameters: dict, duration: float = 300.0):
    """Run a resting state period for heart rate variability before running the Heart
    Beat Counting Task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    duration : float
        Duration or the recording (seconds).

    """

    from psychopy import visual

    # Show the resting state instructions
    messageStart = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.2),
        text=("Calibrating... Please sit quietly" " until the end of the recording."),
    )
    messageStart.draw()
    parameters["restLogo"].draw()
    parameters["win"].flip()

    # Record PPG signal
    parameters["oxiTask"].setup()
    parameters["oxiTask"].read(duration=duration)

    # Save recording
    parameters["oxiTask"].save(
        parameters["resultPath"] + "/" + parameters["participant"] + "_Rest"
    )
