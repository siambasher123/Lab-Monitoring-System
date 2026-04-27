# Lab Monitoring System

A practical, Windows-based Classroom Monitoring System supporting real-time supervision and secure controls in lab environments.  
Designed for educational settings where a teacher's control panel (server) manages multiple student agent (client) machines.

---

## Table of Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Classroom Workflow](#classroom-workflow)
- [Feature List](#feature-list)
- [Repository Structure](#repository-structure)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [How to Run](#how-to-run)
- [Network and Protocol Notes](#network-and-protocol-notes)
- [Quiz Workflow](#quiz-workflow)
- [Troubleshooting](#troubleshooting)
- [Security, Privacy, and Responsible Use](#security-privacy-and-responsible-use)
- [Limitations and Known Issues](#limitations-and-known-issues)
- [Roadmap](#roadmap)
- [Quick Start](#quick-start)

---

## Project Overview

**Lab Monitoring System** enables teachers to supervise, control, and assess students in a networked computer lab.  
The suite consists of:
- **Teacher App _(Control Panel/Server)_**: Centralized dashboard and control utilities.
- **Student App _(Agent/Client)_**: Lightweight agent installed on each student PC.

> **Purpose:**  
Give supervisors real-time visibility and fine-grained control during practical sessions, assignments, and examinations.

---

## System Architecture

```
+------------------+         LAN/Wi-Fi         +----------------+
| Teacher App      | <-----------------------> | Student App(s) |
| (Windows Server) |       TCP Sockets         |   (Windows)    |
+------------------+                          +----------------+
```

- **Teacher App**: Manages all discovered or manually configured student agents.
- **Student App**: Connects to teacher, exposes system state and accepts commands.

---

## Classroom Workflow

1. **Preparation:** Teacher starts server; students run agent on their machines (optionally in admin mode).
2. **Discovery:** Students connect to teacher IP (auto/test mode or via setup dialog).
3. **Supervision:** Teacher views live screens, sends commands, locks/unlocks machines, runs quizzes, and more.
4. **Control:** Teacher initiates class operations—lock screens, restrict Internet/copy-paste, start IDE sessions, and distribute/collect quizzes.
5. **Session End/Cleanup:** Graceful shutdown and all restrictions are lifted on completion.

---

## Feature List

| Feature                        | Status   | Notes                                                                     |
|---------------------------------|----------|---------------------------------------------------------------------------|
| Student Discovery/Connection   | ✅       | By LAN IP, static config, or test mode.                                   |
| Screen Monitoring/Streaming    | ✅       | Teacher can view all student screens on dashboard.                        |
| Remote Control Support         | ✅       | Open remote control panel per student (confirmed in code).                |
| Quiz Distribution/Submission   | ✅       | Teacher can start quiz, students register, submit answers (timed).        |
| Broadcast Message/File Sharing | TBD      | Not directly verifiable from current codebase.                            |
| Block/Unblock Internet         | ✅       | Student app requires admin mode for full blocking.                        |
| Block/Unblock Copy-Paste       | ✅       | Enforced when specified by teacher.                                       |
| Screen Lock/Unlock with PIN    | ✅       | Teacher sets/unlocks PIN, students must enter correct code.               |
| IDE Session Controls           | ✅       | Launch/end coding sessions from teacher panel.                            |
| Graceful Shutdown/Cleanup      | ✅       | On disconnect or teacher trigger, app reverts all restrictions.           |

---

## Repository Structure

| Folder          | Purpose                                            |
|-----------------|---------------------------------------------------|
| `teacher/`      | Teacher (server) app: GUI, server, dashboard      |
| `student/`      | Student (client) app: agent, GUI, and config      |

**Key files:**

### Teacher (server)

- **server.py**: Core network server, student connection, and command logic.
- **gui.py**: Tkinter-based control panel, student list, screen panel.
- **state.py**: Tracks student connections, locks, commands.
- **screen_dashboard.py**: Handles screen streaming and remote panel.
- **quiz_teacher.py**: Quiz setup, monitoring, and responses. (Details in codebase.)

### Student (client)

- **main.py**: Entry point for student agent, startup validation, and lifecycle.
- **config.py**: Loads and saves settings, supports test/configure-first-run.
- **screen_lock_student.py**: Implements PIN lock screen logic.
- **quiz_student.py**: Shows registration and quiz UI, answer submission.
- **run_student.bat**: Batch file to launch with administrator privileges.

---

## Requirements

| Requirement                | Value/Status   |
|----------------------------|---------------|
| OS                         | Windows only  |
| Python                     | ≥3.8 (inferred from usage of modern Python features; verify if needed) |
| Libraries (Student/Teacher)| `tkinter`, `threading`, `socket`, `json`, others per `import` list |
| Admin Required For         | Internet/copy-paste block & screen locking (run student in admin mode using batch file) |

Sample Python packages (install with `pip` if needed):

```
pip install pillow pywin32 # and any other required by codebase
```
(See each script for any `import` statements to verify additional needs.)

---

## Configuration

### Student App

- **First Run:** If not in `TEST_MODE`, a setup popup prompts for Teacher IP and student number.
- **Test Mode:** Hardcoded config values set in `config.py` (`TEST_MODE=True`) for quick offline/LAN testing.
- **Config Files:**  
  - `student_config.json`: Runtime-generated. Stores teacher IP, student details, etc.
- **Admin Launch:** Use `run_student.bat` to run in admin mode for firewall/lock features.

### Teacher App

- **Config:**  
  - Typically via GUI prompts or settings (see `gui.py`).
  - May require email or test mode, depending on deployment scenario (see application startup behavior).

---

## How to Run

### 1. Teacher App

```shell
cd teacher
python gui.py
```

- Ensure your firewall allows selected port (`5000` by default).
- Run on the network-visible machine—wired LAN preferred for stability.

### 2. Student App

Standard mode:
```shell
cd student
python main.py
```

**Admin (recommended for full control features):**
```shell
cd student
run_student.bat
```
- Batch file (Windows only) requests UAC elevation to enable all features.

---

### Multi-Machine Setup

- All devices (teacher + students) must be on the same LAN.
- Use the teacher server's local IP address for student config.
- Port defaults to 5000, can be changed in `config.py`.

---

## Network and Protocol Notes

| Aspect                | Value/Notes                |
|-----------------------|---------------------------|
| Protocol              | Plain TCP sockets         |
| Port usage            | 5000 (can be changed)     |
| LAN requirements      | All devices on same subnet|
| Command/Message flow  | Custom string-based commands (see `state.py`, `server.py`) |
| Reliability/Timeouts  | Student timeouts handled; unresponsive students disconnected |

---

## Quiz Workflow

**Teacher Side:**
- Initiate quiz session from GUI (`quiz_teacher.py`).
- See real-time registration and response from each student.

**Student Side:**
- Student receives registration popup for roll number.
- Quiz presented via GUI window, auto-submits on timeout.
- Submissions sent back to teacher (JSON, scored per teacher code).
- Scoring/timer: per code logic, auto-submit if timer expires.

---

## Troubleshooting

| Symptom                         | Cause                                     | Solution                                              |
|----------------------------------|-------------------------------------------|-------------------------------------------------------|
| Student not connecting           | Wrong IP, port, or teacher app not running| Check teacher IP/port, ensure server started          |
| Port already in use              | Port conflict from another app            | Change port in `config.py` or free the port           |
| Admin features not working       | Not running student with admin privileges | Use `run_student.bat` on Windows, accept UAC prompt   |
| Firewall/network issues          | Blocked port on teacher or student        | Allow app through Windows Firewall & any antivirus    |
| Missing modules                  | Python dependency missing                 | Install missing packages via `pip`                    |

---

## Security, Privacy, and Responsible Use

- **For Educational/Lab Settings Only:** Use strictly for computer lab/classroom supervision.
- **User Notification:** Students should be informed that their screen, keyboard, and application activity may be monitored or controlled.
- **Consent/Policy:** Deploy in accordance with institutional policies and legal requirements.
- **Limit Remote Features:** Only personnel with institution-granted authority should operate the teacher panel.

---

## Limitations and Known Issues

- **Windows-only**: No support for Mac or Linux clients.
- **Plain TCP protocol**: No encryption; use on trusted LAN only.
- **Feature/Protocol Discovery**: Some control/quiz features may not handle all edge cases.
- **No full persistence**: State resets when apps are restarted.
- **Minimal error handling**: Some errors may not display clear messages.
- **File/broadcast**: File sharing/broadcast not yet implemented (TBD).
- **GUI scaling**: Fixed window dimensions; high-DPI Windows may affect rendering.

---

## Roadmap

- [ ] Add file broadcast/messaging from teacher to all students
- [ ] Add basic encryption for network traffic
- [ ] Improve UI scaling for HiDPI displays
- [ ] Implement auto-upgrade/self-update feature
- [ ] Support multi-section classrooms (one teacher, many labs)
- [ ] Add detailed error messages and logs
- [ ] (Community) Planned for future: Mac/Linux student agent

---

## Quick Start

### Teacher:
1. Install Python (Windows).
2. `cd teacher` and run `python gui.py`; allow firewall access.
3. Verify your local (LAN) IP address.

### Student:
1. Install Python and dependencies.
2. `cd student`; edit `config.py` to set teacher IP, or use setup popup at first run.
3. Launch via `python main.py` (normal mode) or `run_student.bat` (admin mode for full functionality).
4. Check for "Connected" status in the teacher dashboard.

---

> For detailed documentation and updates, visit the [GitHub repository](https://github.com/siambasher123/Lab-Monitoring-System).
