# Skill: Notifications

Use this skill to send push notifications to the user via ntfy by using the PowerShell script in the repo:  
scripts/notify.ps1

The script takes parameters event and message. The event can be one of: success, error, or input. The message is a short description of the event, for example the task id and time spent.

## When to send notifications:
Task completed successfully, task failed, or user input is required. 

## Examples
When the entire user-requested task is completed successfully, run:  
```powershell
& "<skill-directory>/scripts/notify.ps1" -Event success -Message "TASK-22 completed in 3min 12s"
```

If the task fails and cannot be completed, run:  
```powershell
& "<skill-directory>/scripts/notify.ps1" -Event error -Message "TASK-04 failed: Short error summary"
```

If you need a decision, clarification or approval from the user before continuing, run:
```powershell
& "<skill-directory>/scripts/notify.ps1" -Event input -Message "TASK-103 requires input: Short summary of decision or question"
```

## Important rules
* Always notify when a task is fully completed.
* Always notify when a task fails.
* Always notify when waiting for user input.
* Always include task id if applicable.
* Do not send completion notifications after individual tool calls.
* Do not claim a task is completed if it is still running.
* Keep notification messages short and informative.
* Never include passwords, API keys, tokens or other secrets in notifications.
* Do not send repeated notifications for the same event.
* Notifications are informational to alert the user on completion; they do not replace the normal task response.
