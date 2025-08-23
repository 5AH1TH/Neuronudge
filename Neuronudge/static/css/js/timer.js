// static/js/timer.js

document.addEventListener("DOMContentLoaded", function () {
    const startTaskBtn = document.getElementById("startTaskBtn");
    const taskTimerSection = document.getElementById("taskTimerSection");
    const taskTimer = document.getElementById("taskTimer");
    const stopTaskBtn = document.getElementById("stopTaskBtn");
    const pauseTaskBtn = document.getElementById("pauseTaskBtn");
    const resumeTaskBtn = document.getElementById("resumeTaskBtn");
    const timeInput = document.getElementById("timeEstimate");

    let countdownInterval;
    let remainingTime = 0;
    let paused = false;

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s < 10 ? "0" : ""}${s}`;
    }

    startTaskBtn.addEventListener("click", function () {
        const minutes = parseInt(timeInput.value);
        if (!minutes || minutes <= 0) {
            alert("Please enter a valid time in minutes.");
            return;
        }

        remainingTime = minutes * 60;
        taskTimerSection.style.display = "flex";
        taskTimer.textContent = formatTime(remainingTime);

        // ✅ Smooth scroll to timer
        taskTimerSection.scrollIntoView({ behavior: "smooth", block: "center" });

        clearInterval(countdownInterval);
        countdownInterval = setInterval(() => {
            if (!paused) {
                remainingTime--;
                taskTimer.textContent = formatTime(remainingTime);

                if (remainingTime <= 0) {
                    clearInterval(countdownInterval);
                    taskTimer.textContent = "Time's up!";
                }
            }
        }, 1000);
    });

    pauseTaskBtn.addEventListener("click", function () {
        paused = true;
    });

    resumeTaskBtn.addEventListener("click", function () {
        paused = false;
    });

    stopTaskBtn.addEventListener("click", function () {
        clearInterval(countdownInterval);
        taskTimer.textContent = "Stopped";
    });
});

document.addEventListener("DOMContentLoaded", function () {
    // Read user preference config safely from JSON script block
    const configScript = document.getElementById("timer-config");
    let config = { focusMinutes: 25, breakMinutes: 5 };
    if (configScript) {
        try {
            config = JSON.parse(configScript.textContent);
        } catch (err) {
            console.warn("Failed to parse timer config, using defaults", err);
        }
    }

    // DOM Elements
    const taskTimerSection = document.getElementById("task-timer-section");
    const selectedTaskName = document.getElementById("selected-task-name");
    const timeInput = document.getElementById("timeInput");
    const startBtn = document.getElementById("start-timer");
    const pauseBtn = document.getElementById("pause-timer");
    const resumeBtn = document.getElementById("resume-timer");
    const stopBtn = document.getElementById("stop-timer");
    const timerDisplay = document.getElementById("timer-display");
    const timerStatus = document.getElementById("timer-status");
    const dashboardContainer = document.getElementById("dashboard-container");

    // State
    let countdownInterval = null;
    let remainingSeconds = 0;
    let currentTaskId = null;
    let isBreak = false;

    // Format helper
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60)
            .toString()
            .padStart(2, "0");
        const secs = (seconds % 60).toString().padStart(2, "0");
        return `${mins}:${secs}`;
    }

    // Start Timer
    function startTimer(durationMinutes) {
        clearInterval(countdownInterval);
        isBreak = false;
        remainingSeconds = durationMinutes * 60;
        updateDisplay();
        timerStatus.textContent = "Focus Time";
        timerStatus.classList.remove("text-muted");
        timerStatus.classList.add("text-success");

        // ✅ Scroll to timer section when timer starts
        if (taskTimerSection) {
            taskTimerSection.scrollIntoView({ behavior: "smooth", block: "center" });
        }

        countdownInterval = setInterval(() => {
            remainingSeconds--;
            updateDisplay();

            if (remainingSeconds <= 0) {
                clearInterval(countdownInterval);

                if (!isBreak) {
                    // Start break after focus
                    isBreak = true;
                    remainingSeconds = config.breakMinutes * 60;
                    timerStatus.textContent = "Break Time!";
                    timerStatus.classList.remove("text-success");
                    timerStatus.classList.add("text-warning");
                    countdownInterval = setInterval(() => {
                        remainingSeconds--;
                        updateDisplay();
                        if (remainingSeconds <= 0) {
                            clearInterval(countdownInterval);
                            timerStatus.textContent = "Focus complete 🎉";
                        }
                    }, 1000);
                }
            }
        }, 1000);
    }

    // Update Display
    function updateDisplay() {
        timerDisplay.textContent = formatTime(remainingSeconds);
    }

    // Event: Start Task button inside table
    document.querySelectorAll(".start-task-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            currentTaskId = btn.getAttribute("data-task-id");
            const taskTitle = btn.getAttribute("data-task-title") || "Unnamed Task";

            selectedTaskName.textContent = `Task: ${taskTitle}`;
            taskTimerSection.style.display = "block";

            // Shrink dashboard container to 65%
            //dashboardContainer.style.maxWidth = "65%";
            //dashboardContainer.style.transition = "max-width 0.3s ease";

            // ✅ Scroll into view when expanded
            taskTimerSection.scrollIntoView({ behavior: "smooth", block: "center" });
        });
    });

    // Event: Start Timer (after entering minutes)
    if (startBtn) {
        startBtn.addEventListener("click", () => {
            const minutes = parseInt(timeInput.value, 10);
            if (!minutes || minutes <= 0) {
                alert("Please enter a valid time in minutes.");
                return;
            }
            startTimer(minutes);
        });
    }

    // Pause Timer
    if (pauseBtn) {
        pauseBtn.addEventListener("click", () => {
            if (countdownInterval) {
                clearInterval(countdownInterval);
                countdownInterval = null;
                timerStatus.textContent = "Paused";
                timerStatus.classList.remove("text-success", "text-warning");
                timerStatus.classList.add("text-muted");
            }
        });
    }

    // Resume Timer
    if (resumeBtn) {
        resumeBtn.addEventListener("click", () => {
            if (!countdownInterval && remainingSeconds > 0) {
                timerStatus.textContent = isBreak ? "Break Time!" : "Focus Time";
                countdownInterval = setInterval(() => {
                    remainingSeconds--;
                    updateDisplay();

                    if (remainingSeconds <= 0) {
                        clearInterval(countdownInterval);

                        if (!isBreak) {
                            // Start break after focus
                            isBreak = true;
                            remainingSeconds = config.breakMinutes * 60;
                            timerStatus.textContent = "Break Time!";
                            countdownInterval = setInterval(() => {
                                remainingSeconds--;
                                updateDisplay();
                                if (remainingSeconds <= 0) {
                                    clearInterval(countdownInterval);
                                    timerStatus.textContent = "Focus complete 🎉";
                                }
                            }, 1000);
                        }
                    }
                }, 1000);
            }
        });
    }

    // Stop Timer
    if (stopBtn) {
        stopBtn.addEventListener("click", () => {
            clearInterval(countdownInterval);
            countdownInterval = null;
            remainingSeconds = 0;
            updateDisplay();
            timerStatus.textContent = "Stopped";
            timerStatus.classList.remove("text-success", "text-warning");
            timerStatus.classList.add("text-muted");

            // Reset dashboard width
            dashboardContainer.style.maxWidth = "100%";

            // ✅ Scroll back up to dashboard top
            dashboardContainer.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    }

    // Init display
    updateDisplay();
});
